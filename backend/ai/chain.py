"""Provider chain managing failover, rate limits, privacy restrictions, and caching."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, List, Type
from pydantic import BaseModel

from .config import AISettings, ProviderConfig, get_ai_settings
from .models import AIResponse, AIStatusResponse, ProviderHealthStatus
from .providers import BaseAIProvider, get_provider, AIProviderError, RateLimitError, BudgetExceededError
from .privacy import redact_secrets
from .cache import GLOBAL_AI_CACHE
from .rate_limiter import GLOBAL_RATE_LIMITER, ProviderRateLimiter
from .audit import log_ai_invocation

logger = logging.getLogger("archlens.ai.chain")


class ProviderChain:
    """Manages ordered failover across multiple AI providers with rate limiting and privacy guards."""

    def __init__(
        self,
        settings: AISettings | None = None,
        rate_limiter: ProviderRateLimiter | None = None,
    ) -> None:
        self.settings = settings or get_ai_settings()
        self.rate_limiter = rate_limiter or GLOBAL_RATE_LIMITER
        self._providers: dict[str, BaseAIProvider] = {}
        self.accumulated_tokens: int = 0
        self.accumulated_cost_usd: float = 0.0
        self._init_providers()

    def reset_usage(self) -> None:
        """Reset per-analysis token and budget counters across chain and providers."""
        self.accumulated_tokens = 0
        self.accumulated_cost_usd = 0.0
        for p in self._providers.values():
            p.reset_usage()

    def check_budget(self, anticipated_tokens: int = 10) -> None:
        """Check if request would violate max tokens or USD budget."""
        if self.accumulated_tokens + anticipated_tokens > self.settings.max_tokens_per_analysis:
            raise BudgetExceededError(
                f"Token budget exceeded: {self.accumulated_tokens} + {anticipated_tokens} > {self.settings.max_tokens_per_analysis}"
            )
        if self.accumulated_cost_usd >= self.settings.budget_usd:
            raise BudgetExceededError(
                f"Cost budget exceeded: ${self.accumulated_cost_usd:.4f} >= ${self.settings.budget_usd:.4f}"
            )

    def _init_providers(self) -> None:
        """Instantiate providers from configuration."""
        self._providers.clear()
        for name, cfg in self.settings.providers.items():
            # Skip providers with no key, unless it's the fake test provider or local ollama
            if name not in ("fake", "ollama") and not cfg.api_key:
                logger.debug("Skipping provider '%s' (no API key configured)", name)
                continue
            try:
                self._providers[name] = get_provider(name, self.settings)
            except Exception as exc:
                logger.warning("Failed to initialize provider '%s': %s", name, exc)

    def get_provider(self, name: str) -> BaseAIProvider | None:
        return self._providers.get(name.lower())

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        response_schema: Type[BaseModel] | None = None,
        is_private_repo: bool = False,
        source_type: str = "",
        feature: str = "general",
        use_cache: bool = True,
    ) -> AIResponse:
        """Execute request across provider chain with failover on 429, timeout, or quota errors."""
        # 1. Enforce privacy: redact secrets from prompt text
        clean_prompt = redact_secrets(prompt)
        clean_system = redact_secrets(system_prompt) if system_prompt else None

        # 2. Response cache check (content-hash keyed so repeated analyses cost zero calls)
        schema_name = response_schema.__name__ if response_schema else ""
        if use_cache:
            # Check global content-hash cache using first candidate provider or general key
            cached_resp = GLOBAL_AI_CACHE.get(
                "chain", "content_hash", clean_prompt, schema_name
            )
            if cached_resp:
                logger.debug("AI Chain cache hit for content hash (0 API calls incurred)")
                log_ai_invocation(
                    feature=feature,
                    provider="cache",
                    model=cached_resp.model,
                    input_tokens=cached_resp.input_tokens,
                    output_tokens=cached_resp.output_tokens,
                    cost_usd=0.0,
                    success=True,
                    cached=True,
                )
                return cached_resp

        # 3. Budget pre-check
        anticipated = max(10, len(clean_prompt) // 4)
        self.check_budget(anticipated_tokens=anticipated)

        # 4. Walk provider order
        candidate_order = [p for p in self.settings.provider_order if p in self._providers]
        if not candidate_order:
            # Fallback to any initialized provider if none in specified order
            candidate_order = list(self._providers.keys())

        if not candidate_order:
            raise AIProviderError("No AI providers are configured or have valid API keys.")

        is_upload_or_private = (
            is_private_repo
            or source_type.lower() in ("zip", "folder", "archive", "upload", "local")
        )

        last_error: Exception | None = None

        for provider_name in candidate_order:
            provider = self._providers[provider_name]
            cfg = self.settings.providers.get(provider_name, ProviderConfig(name=provider_name))

            # Rule: Skip training providers on private repos or uploads unless permitted
            if provider.trains_on_prompts and is_upload_or_private and not self.settings.allow_training_providers:
                logger.info(
                    "Skipping provider '%s' (trains_on_prompts=True) because repo is private/uploaded and ARCHLENS_AI_ALLOW_TRAINING_PROVIDERS is false.",
                    provider_name,
                )
                continue

            # Rule: Check RPM limit and cooldown (from Retry-After / 429)
            can_req, block_reason = self.rate_limiter.can_request(provider_name, cfg.rpm_limit)
            if not can_req:
                logger.warning(
                    "Provider '%s' unavailable: %s. Failing over to next provider in chain.",
                    provider_name,
                    block_reason,
                )
                continue

            # Attempt completion with this provider
            start_time = time.perf_counter()
            self.rate_limiter.record_request(provider_name)

            try:
                # Direct execute on provider
                response = await provider._execute_completion(
                    clean_prompt, clean_system, response_schema
                )
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                response.latency_ms = round(latency_ms, 2)
                response.provider = provider_name

                # Record success telemetry
                self.rate_limiter.record_success(provider_name, latency_ms)

                # Track budget
                self.accumulated_tokens += response.total_tokens
                self.accumulated_cost_usd += response.cost_usd

                # Store in content-hash cache
                if use_cache:
                    GLOBAL_AI_CACHE.set(
                        "chain", "content_hash", clean_prompt, response, schema_name
                    )

                # Record audit log
                log_ai_invocation(
                    feature=feature,
                    provider=provider_name,
                    model=response.model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    cost_usd=response.cost_usd,
                    success=True,
                    cached=False,
                )

                return response

            except RateLimitError as exc:
                last_error = exc
                self.rate_limiter.record_failure(
                    provider_name, str(exc), status_code=exc.status_code, retry_after=exc.retry_after
                )
                logger.warning(
                    "Provider '%s' rate limited (Retry-After: %s). Failing over to next provider. Error: %s",
                    provider_name,
                    exc.retry_after,
                    exc,
                )
            except Exception as exc:
                last_error = exc
                self.rate_limiter.record_failure(provider_name, str(exc))
                logger.warning(
                    "Provider '%s' failed (%s). Failing over to next provider in chain.",
                    provider_name,
                    exc,
                )

        raise AIProviderError(f"All configured providers in chain failed or were skipped: {last_error}")

    def get_status_report(self) -> AIStatusResponse:
        """Generate admin status report for AI providers (never exposes API keys)."""
        import datetime
        provider_reports: list[ProviderHealthStatus] = []

        active_provider: str | None = None
        for name in self.settings.provider_order:
            cfg = self.settings.providers.get(name)
            if not cfg:
                cfg = ProviderConfig(name=name)

            health = self.rate_limiter.get_health_status(name, cfg)
            provider_reports.append(health)

            if active_provider is None and health.status == "healthy" and (health.has_api_key or name in ("fake", "ollama")):
                active_provider = name

        return AIStatusResponse(
            enabled=self.settings.enabled,
            provider_order=self.settings.provider_order,
            active_provider=active_provider,
            allow_training_providers=self.settings.allow_training_providers,
            providers=provider_reports,
            cache_entries=len(GLOBAL_AI_CACHE._cache),
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )


GLOBAL_PROVIDER_CHAIN = ProviderChain()
