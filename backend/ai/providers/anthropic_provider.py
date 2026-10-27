"""Anthropic Claude AI Provider adapter."""

from __future__ import annotations

import json
from typing import Any, Type
import httpx
from pydantic import BaseModel

from .base import BaseAIProvider, AIProviderError
from ..config import estimate_token_cost
from ..models import AIResponse
from ..json_utils import extract_and_parse_json


class AnthropicProvider(BaseAIProvider):
    """Adapter for Anthropic Claude Messages API."""

    def __init__(self, settings=None) -> None:
        super().__init__(settings)
        self.model_name = self.settings.model or "claude-3-5-sonnet-20241022"
        self.api_url = "https://api.anthropic.com/v1/messages"

    async def _execute_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        response_schema: Type[BaseModel] | None = None,
    ) -> AIResponse:
        if not self.settings.api_key:
            raise AIProviderError("Anthropic API key is missing (set ARCHLENS_AI_API_KEY).")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.settings.api_key,
            "anthropic-version": "2023-06-01",
        }

        user_content = prompt
        if response_schema is not None:
            user_content = (
                f"{prompt}\n\nIMPORTANT: Return strictly valid JSON conforming to the target schema. "
                f"Do not wrap in markdown or backticks."
            )

        body: dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": user_content}],
        }
        if system_prompt:
            body["system"] = system_prompt

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            resp = await client.post(self.api_url, headers=headers, json=body)
            if resp.status_code != 200:
                raise AIProviderError(f"Anthropic API returned status {resp.status_code}: {resp.text}")

            data = resp.json()

        # Parse text content
        content_blocks = data.get("content", [])
        text_content = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")

        usage = data.get("usage", {})
        prompt_tokens = usage.get("input_tokens", len(prompt) // 4)
        output_tokens = usage.get("output_tokens", len(text_content) // 4)
        total_tokens = prompt_tokens + output_tokens

        structured_data: dict[str, Any] | None = None
        if response_schema is not None:
            try:
                structured_data = extract_and_parse_json(text_content)
            except Exception as exc:
                raise AIProviderError(f"Failed to decode structured JSON from Anthropic: {exc}")

        cost_usd = estimate_token_cost("anthropic", self.model_name, prompt_tokens, output_tokens)

        return AIResponse(
            content=text_content,
            structured_data=structured_data,
            input_tokens=prompt_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            provider="anthropic",
            model=self.model_name,
        )
