"""AI provider adapters and factory."""

from __future__ import annotations

from typing import Type
from ..config import AISettings
from .base import BaseAIProvider, AIProviderError, BudgetExceededError, RateLimitError
from .fake_provider import FakeProvider
from .gemini_provider import GeminiProvider
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider, GroqProvider, NVIDIAProvider, OllamaProvider

PROVIDER_REGISTRY: dict[str, Type[BaseAIProvider]] = {
    "fake": FakeProvider,
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "nvidia": NVIDIAProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
}


def get_provider(
    provider_or_settings: str | AISettings = "fake",
    settings: AISettings | None = None,
) -> BaseAIProvider:
    """Instantiate configured AI provider adapter."""
    if isinstance(provider_or_settings, AISettings):
        cfg = provider_or_settings
        name = cfg.provider or (cfg.provider_order[0] if cfg.provider_order else "fake")
    else:
        name = provider_or_settings
        cfg = settings or AISettings.from_env()
    provider_cls = PROVIDER_REGISTRY.get(name.lower(), FakeProvider)
    return provider_cls(cfg)


__all__ = [
    "BaseAIProvider",
    "AIProviderError",
    "BudgetExceededError",
    "RateLimitError",
    "FakeProvider",
    "GeminiProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "GroqProvider",
    "NVIDIAProvider",
    "OllamaProvider",
    "PROVIDER_REGISTRY",
    "get_provider",
]
