"""Gemini AI Provider adapter."""

from __future__ import annotations

import json
from typing import Any, Type
import httpx
from pydantic import BaseModel

from .base import BaseAIProvider, AIProviderError, RateLimitError
from ..config import AISettings, estimate_token_cost
from ..models import AIResponse
from ..json_utils import extract_and_parse_json


class GeminiProvider(BaseAIProvider):
    """Adapter for Google Gemini API."""

    name: str = "gemini"
    trains_on_prompts: bool = True

    def __init__(self, settings: AISettings | None = None) -> None:
        super().__init__(settings)
        cfg = self.settings.providers.get("gemini") if self.settings.providers else None

        self.api_key = cfg.api_key if cfg else (self.settings.api_key if hasattr(self.settings, "api_key") else "")
        self.model_name = cfg.model if cfg and cfg.model else "gemini-2.5-flash"
        clean_model = self.model_name[len("models/"):] if self.model_name.startswith("models/") else self.model_name
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent"

    async def _execute_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        response_schema: Type[BaseModel] | None = None,
    ) -> AIResponse:
        if not self.api_key:
            raise AIProviderError("Gemini API key is missing (set GEMINI_API_KEY).")

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        contents: list[dict[str, Any]] = []
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System Instructions:\n{system_prompt}\n"}],
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Understood. I will strictly adhere to these instructions."}],
            })

        contents.append({
            "role": "user",
            "parts": [{"text": prompt}],
        })

        generation_config: dict[str, Any] = {
            "temperature": 0.1,
        }
        if response_schema is not None:
            generation_config["responseMimeType"] = "application/json"

        body = {
            "contents": contents,
            "generationConfig": generation_config,
        }

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            resp = await client.post(self.api_url, headers=headers, json=body)

            if resp.status_code == 429 or "RESOURCE_EXHAUSTED" in resp.text:
                retry_after = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
                raise RateLimitError(
                    f"Gemini quota / rate limit exceeded (HTTP {resp.status_code})",
                    status_code=429,
                    retry_after=retry_after,
                )

            if resp.status_code != 200:
                raise AIProviderError(f"Gemini API returned status {resp.status_code}: {resp.text}")

            data = resp.json()

        # Parse text content
        candidates = data.get("candidates", [])
        if not candidates:
            raise AIProviderError("No response candidates returned by Gemini.")

        text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        # Extract tokens
        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", len(prompt) // 4)
        candidates_tokens = usage.get("candidatesTokenCount", len(text_content) // 4)
        total_tokens = usage.get("totalTokenCount", prompt_tokens + candidates_tokens)

        structured_data: dict[str, Any] | None = None
        if response_schema is not None:
            try:
                structured_data = extract_and_parse_json(text_content)
            except Exception as exc:
                raise AIProviderError(f"Failed to decode structured JSON from Gemini: {exc}")

        cost_usd = estimate_token_cost("gemini", self.model_name, prompt_tokens, candidates_tokens)

        return AIResponse(
            content=text_content,
            structured_data=structured_data,
            input_tokens=prompt_tokens,
            output_tokens=candidates_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            provider="gemini",
            model=self.model_name,
        )
