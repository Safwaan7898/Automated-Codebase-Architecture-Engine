"""OpenAI-compatible AI Provider adapter (used by OpenAI, Groq, and NVIDIA)."""

from __future__ import annotations

import json
from typing import Any, Type
import httpx
from pydantic import BaseModel

from .base import BaseAIProvider, AIProviderError, RateLimitError
from ..config import AISettings, estimate_token_cost
from ..models import AIResponse
from ..json_utils import extract_and_parse_json


class OpenAIProvider(BaseAIProvider):
    """Adapter for OpenAI and OpenAI-compatible API endpoints."""

    name: str = "openai"
    trains_on_prompts: bool = False

    def __init__(self, settings: AISettings | None = None, base_url: str | None = None) -> None:
        super().__init__(settings)
        cfg = self.settings.providers.get(self.name) if self.settings.providers else None

        self.api_key = cfg.api_key if cfg else (self.settings.api_key if hasattr(self.settings, "api_key") else "")
        self.model_name = cfg.model if cfg else "gpt-4o-mini"
        endpoint = base_url or (cfg.base_url if cfg else "https://api.openai.com/v1")
        self.api_url = f"{endpoint.rstrip('/')}/chat/completions"

    async def _execute_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        response_schema: Type[BaseModel] | None = None,
    ) -> AIResponse:
        if not self.api_key:
            raise AIProviderError(f"{self.name.capitalize()} API key is missing.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.1,
        }
        if response_schema is not None:
            body["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            resp = await client.post(self.api_url, headers=headers, json=body)

            if resp.status_code == 429:
                retry_after = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
                raise RateLimitError(
                    f"{self.name.capitalize()} rate limit / quota exceeded (HTTP 429)",
                    status_code=429,
                    retry_after=retry_after,
                )

            if resp.status_code != 200:
                raise AIProviderError(f"{self.name.capitalize()} API returned status {resp.status_code}: {resp.text}")

            data = resp.json()

        choices = data.get("choices", [])
        if not choices:
            raise AIProviderError(f"No choices returned from {self.name.capitalize()}.")

        text_content = choices[0].get("message", {}).get("content", "")

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", len(prompt) // 4)
        output_tokens = usage.get("completion_tokens", len(text_content) // 4)
        total_tokens = usage.get("total_tokens", prompt_tokens + output_tokens)

        structured_data: dict[str, Any] | None = None
        if response_schema is not None:
            try:
                structured_data = extract_and_parse_json(text_content)
            except Exception as exc:
                raise AIProviderError(f"Failed to decode structured JSON from {self.name.capitalize()}: {exc}")

        cost_usd = estimate_token_cost(self.name, self.model_name, prompt_tokens, output_tokens)

        return AIResponse(
            content=text_content,
            structured_data=structured_data,
            input_tokens=prompt_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            provider=self.name,
            model=self.model_name,
        )


class GroqProvider(OpenAIProvider):
    """Adapter for Groq Cloud API (OpenAI-compatible)."""

    name: str = "groq"
    trains_on_prompts: bool = False

    def __init__(self, settings: AISettings | None = None) -> None:
        super().__init__(settings=settings, base_url="https://api.groq.com/openai/v1")


class NVIDIAProvider(OpenAIProvider):
    """Adapter for NVIDIA NIM API (OpenAI-compatible)."""

    name: str = "nvidia"
    trains_on_prompts: bool = False

    def __init__(self, settings: AISettings | None = None) -> None:
        super().__init__(settings=settings, base_url="https://integrate.api.nvidia.com/v1")


class OllamaProvider(OpenAIProvider):
    """Adapter for local Ollama server (OpenAI-compatible, no API key required)."""

    name: str = "ollama"
    trains_on_prompts: bool = False

    def __init__(self, settings: AISettings | None = None) -> None:
        base_url = "http://localhost:11434/v1"
        if settings and "ollama" in settings.providers and settings.providers["ollama"].base_url:
            base_url = settings.providers["ollama"].base_url
        super().__init__(settings=settings, base_url=base_url)
