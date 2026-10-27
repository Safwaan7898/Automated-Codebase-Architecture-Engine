"""Base class and common infrastructure for AI provider adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
import json
import logging
import time
from typing import Any, Type
from pydantic import BaseModel

from ..config import AISettings, estimate_token_cost
from ..models import AIResponse
from ..privacy import redact_secrets
from ..cache import GLOBAL_AI_CACHE
from ..audit import log_ai_invocation

logger = logging.getLogger("archlens.ai.provider")


class AIProviderError(Exception):
    """Base exception for AI provider failures."""


class RateLimitError(AIProviderError):
    """Raised on 429 Too Many Requests or quota exhaustion with optional Retry-After."""

    def __init__(self, message: str, status_code: int = 429, retry_after: str | int | float | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class BudgetExceededError(AIProviderError):
    """Raised when analysis or session token/cost budget is exceeded."""


class BaseAIProvider(ABC):
    """Abstract base class for all AI provider adapters."""

    name: str = "base"
    trains_on_prompts: bool = False

    def __init__(self, settings: AISettings | None = None) -> None:
        self.settings = settings or AISettings.from_env()
        self.accumulated_tokens: int = 0
        self.accumulated_cost_usd: float = 0.0

    def reset_usage(self) -> None:
        """Reset per-analysis token and budget counters."""
        self.accumulated_tokens = 0
        self.accumulated_cost_usd = 0.0

    def check_budget(self, anticipated_tokens: int = 100) -> None:
        """Check if request would violate max tokens or USD budget."""
        if self.accumulated_tokens + anticipated_tokens > self.settings.max_tokens_per_analysis:
            raise BudgetExceededError(
                f"Token budget exceeded: {self.accumulated_tokens} + {anticipated_tokens} > {self.settings.max_tokens_per_analysis}"
            )
        if self.accumulated_cost_usd >= self.settings.budget_usd:
            raise BudgetExceededError(
                f"Cost budget exceeded: ${self.accumulated_cost_usd:.4f} >= ${self.settings.budget_usd:.4f}"
            )

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        response_schema: Type[BaseModel] | None = None,
        feature: str = "general",
        use_cache: bool = True,
    ) -> AIResponse:
        """Execute a completion with redaction, caching, budget enforcement, and retries."""
        # 1. Enforce privacy: redact secrets from prompt and system prompt
        clean_prompt = redact_secrets(prompt)
        clean_system = redact_secrets(system_prompt) if system_prompt else None

        # 2. Check cache
        schema_name = response_schema.__name__ if response_schema else ""
        if use_cache:
            cached_resp = GLOBAL_AI_CACHE.get(
                self.settings.provider, self.settings.model or "default", clean_prompt, schema_name
            )
            if cached_resp:
                log_ai_invocation(
                    feature=feature,
                    provider=self.settings.provider,
                    model=self.settings.model or "default",
                    input_tokens=cached_resp.input_tokens,
                    output_tokens=cached_resp.output_tokens,
                    cost_usd=0.0,
                    success=True,
                    cached=True,
                )
                return cached_resp

        # 3. Budget pre-check
        self.check_budget()

        # 4. Retry loop with exponential backoff
        last_error: Exception | None = None
        for attempt in range(1, self.settings.max_retries + 1):
            try:
                start_time = time.perf_counter()
                # Run with timeout
                response = await asyncio.wait_for(
                    self._execute_completion(clean_prompt, clean_system, response_schema),
                    timeout=self.settings.request_timeout_seconds,
                )
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                response.latency_ms = round(latency_ms, 2)

                # Track budget
                self.accumulated_tokens += response.total_tokens
                self.accumulated_cost_usd += response.cost_usd

                # Update cache
                if use_cache:
                    GLOBAL_AI_CACHE.set(
                        self.settings.provider,
                        self.settings.model or "default",
                        clean_prompt,
                        response,
                        schema_name,
                    )

                # Log audit
                log_ai_invocation(
                    feature=feature,
                    provider=self.settings.provider,
                    model=self.settings.model or "default",
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    cost_usd=response.cost_usd,
                    success=True,
                    cached=False,
                )

                return response

            except asyncio.TimeoutError as exc:
                last_error = AIProviderError(f"AI request timed out after {self.settings.request_timeout_seconds}s")
                logger.warning("AI request attempt %d timed out: %s", attempt, exc)
            except Exception as exc:
                last_error = exc
                logger.warning("AI request attempt %d failed: %s", attempt, exc)

            if attempt < self.settings.max_retries:
                backoff = self.settings.backoff_factor ** attempt
                await asyncio.sleep(backoff)

        # Log failed attempt
        log_ai_invocation(
            feature=feature,
            provider=self.settings.provider,
            model=self.settings.model or "default",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            success=False,
            error=str(last_error),
        )

        raise AIProviderError(f"All {self.settings.max_retries} attempts failed: {last_error}") from last_error

    @abstractmethod
    async def _execute_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        response_schema: Type[BaseModel] | None = None,
    ) -> AIResponse:
        """Provider-specific API call implementation."""
        raise NotImplementedError
