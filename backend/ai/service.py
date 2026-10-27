"""AIService facade providing safe execution, graceful degradation, and grounding verification."""

from __future__ import annotations

import logging
from typing import Any, Callable, Type, TypeVar
from pydantic import BaseModel

from .config import AISettings, get_ai_settings
from .models import AIResponse, AIStatusResponse
from .chain import ProviderChain, GLOBAL_PROVIDER_CHAIN
from .providers import BaseAIProvider, AIProviderError
from .security import quote_untrusted_data, validate_grounded_references
from .json_utils import extract_and_validate_pydantic

logger = logging.getLogger("archlens.ai.service")

T = TypeVar("T", bound=BaseModel)


class AIService:
    """Core AI service coordinating provider execution, chain failover, and safe fallbacks."""

    def __init__(
        self,
        chain: ProviderChain | None = None,
        provider: BaseAIProvider | None = None,
        settings: AISettings | None = None,
    ) -> None:
        self.settings = settings or get_ai_settings()
        self.chain = chain or GLOBAL_PROVIDER_CHAIN
        # Optional legacy single provider override (for isolated unit tests)
        self.provider = provider

    @property
    def is_enabled(self) -> bool:
        """Check if AI is enabled in current environment."""
        return self.settings.enabled

    async def invoke_feature(
        self,
        feature_name: str,
        prompt: str,
        system_prompt: str | None = None,
        response_schema: Type[T] | None = None,
        fallback_factory: Callable[[], T | str] | None = None,
        valid_nodes: set[str] | None = None,
        valid_files: set[str] | None = None,
        is_private_repo: bool = False,
        source_type: str = "",
        use_cache: bool = True,
    ) -> T | str:
        """Execute an AI feature call with automatic failover and graceful degradation on any error."""
        # Check enabled switch
        if not self.is_enabled:
            return self._get_fallback(fallback_factory, "AI unavailable (disabled in environment)")

        try:
            if self.provider is not None:
                # Direct single provider override
                resp: AIResponse = await self.provider.complete(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    response_schema=response_schema,
                    feature=feature_name,
                    use_cache=use_cache,
                )
            else:
                # Execute through provider chain with failover
                resp = await self.chain.complete(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    response_schema=response_schema,
                    is_private_repo=is_private_repo,
                    source_type=source_type,
                    feature=feature_name,
                    use_cache=use_cache,
                )

            # If structured schema was expected
            if response_schema is not None:
                if resp.structured_data:
                    try:
                        parsed = response_schema.model_validate(resp.structured_data)
                    except Exception:
                        parsed = extract_and_validate_pydantic(resp.content, response_schema)
                else:
                    parsed = extract_and_validate_pydantic(resp.content, response_schema)

                # Grounding defense: verify that referenced nodes exist
                if valid_nodes is not None:
                    if not validate_grounded_references(parsed, valid_nodes, valid_files):
                        logger.warning("AI output failed grounding validation (hallucinated references). Degrading to fallback.")
                        return self._get_fallback(fallback_factory, "AI unavailable (ungrounded references)")

                return parsed

            return resp.content

        except Exception as exc:
            logger.warning("AI feature '%s' degraded gracefully to fallback due to error: %s", feature_name, exc)
            return self._get_fallback(fallback_factory, "AI unavailable")

    def get_status(self) -> AIStatusResponse:
        """Retrieve admin health status report across provider chain (never exposes keys)."""
        return self.chain.get_status_report()

    def _get_fallback(self, fallback_factory: Callable[[], T | str] | None, default_msg: str) -> T | str:
        if fallback_factory is not None:
            try:
                return fallback_factory()
            except Exception as exc:
                logger.error("Fallback factory failed: %s", exc)
        return default_msg


# Default global instance
GLOBAL_AI_SERVICE = AIService()
