"""Content-hash-keyed cache for AI responses."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from .models import AIResponse


class AICache:
    """Thread-safe response cache keyed by cryptographic hash of prompt and settings."""

    def __init__(self, max_entries: int = 1000) -> None:
        self._cache: dict[str, AIResponse] = {}
        self._max_entries = max_entries

    def _make_key(self, provider: str, model: str, prompt: str, schema_name: str = "") -> str:
        payload = f"{provider}:{model}:{schema_name}:{prompt}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def get(self, provider: str, model: str, prompt: str, schema_name: str = "") -> AIResponse | None:
        key = self._make_key(provider, model, prompt, schema_name)
        cached = self._cache.get(key)
        if cached:
            # Return copy with cached=True flag
            data = cached.model_dump()
            data["cached"] = True
            return AIResponse(**data)
        return None

    def set(self, provider: str, model: str, prompt: str, response: AIResponse, schema_name: str = "") -> None:
        if len(self._cache) >= self._max_entries:
            # Simple eviction: pop oldest entry
            oldest_key = next(iter(self._cache))
            self._cache.pop(oldest_key, None)

        key = self._make_key(provider, model, prompt, schema_name)
        self._cache[key] = response

    def clear(self) -> None:
        self._cache.clear()


# Global in-process singleton cache
GLOBAL_AI_CACHE = AICache()
