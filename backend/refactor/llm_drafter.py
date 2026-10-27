"""Optional LLM-assisted diff drafter behind feature flag and environment API key."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path

import httpx

from refactor.models import RefactorSuggestion

logger = logging.getLogger(__name__)


def is_llm_refactor_enabled() -> bool:
    """Check if the LLM refactoring feature flag is active."""
    val = os.getenv("LLM_REFACTOR_ENABLED", os.getenv("ARCHLENS_LLM_REFACTOR_ENABLED", "false")).lower()
    return val in ("1", "true", "yes", "on")


def get_llm_api_key() -> str | None:
    """Retrieve the LLM API key from environment."""
    return os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")


class LLMDiffDrafter:
    """Drafts concrete unified code diffs for refactoring suggestions using an LLM API."""

    def __init__(
        self,
        api_key: str | None = None,
        enabled: bool | None = None,
        http_client: httpx.Client | None = None,
        custom_caller: Callable[[str, RefactorSuggestion], str] | None = None,
    ) -> None:
        self.api_key = api_key or get_llm_api_key()
        self.enabled = is_llm_refactor_enabled() if enabled is None else enabled
        self._client = http_client
        self._custom_caller = custom_caller

    def extract_code_context(self, suggestion: RefactorSuggestion, base_dir: Path | str = ".") -> str:
        """Gather source code snippets from affected files to feed to the LLM."""
        context_parts = []
        base = Path(base_dir)

        # Check nodes that point to actual files
        for nid in suggestion.affected_nodes:
            # File node format e.g. "file:src/app.py" or relative path
            path_str = nid.replace("file:", "")
            candidate_file = base / path_str
            if candidate_file.exists() and candidate_file.is_file():
                try:
                    code = candidate_file.read_text(encoding="utf-8", errors="replace")
                    # Limit size per file to 200 lines to avoid token exhaustion
                    truncated = "\n".join(code.splitlines()[:200])
                    context_parts.append(f"--- File: {path_str} ---\n{truncated}\n")
                except Exception as exc:
                    logger.debug("Could not read context file %s: %s", candidate_file, exc)

        if not context_parts:
            # Provide high-level metadata as context
            context_parts.append(f"Affected components: {', '.join(suggestion.affected_nodes)}")
            context_parts.append(f"Action specifications: {suggestion.action_details}")

        return "\n".join(context_parts)

    def generate_draft_diff(self, suggestion: RefactorSuggestion, code_context: str) -> str:
        """Generate a unified diff via LLM or template fallback."""
        if not self.enabled or not self.api_key:
            return self._generate_template_diff(suggestion)

        # Custom caller override for testing
        if self._custom_caller:
            return self._custom_caller(code_context, suggestion)

        prompt = (
            f"You are an expert software architect.\n"
            f"Generate a clean unified git diff (diff --git a/... b/...) applying this refactoring:\n"
            f"Title: {suggestion.title}\n"
            f"Type: {suggestion.type}\n"
            f"Rationale: {suggestion.rationale}\n"
            f"Action Details: {suggestion.action_details}\n\n"
            f"Code Context:\n{code_context}\n"
        )

        try:
            # Check if Gemini API key
            gemini_key = os.getenv("GEMINI_API_KEY") or (self.api_key if self.api_key.startswith("AIza") else None)
            if gemini_key:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2},
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            return text.strip()
            else:
                # OpenAI compatible endpoint
                url = os.getenv("LLM_ENDPOINT", "https://api.openai.com/v1/chat/completions")
                headers = {"Authorization": f"Bearer {self.api_key}"}
                payload = {
                    "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        text = resp.json()["choices"][0]["message"]["content"]
                        return text.strip()
        except Exception as exc:
            logger.warning("LLM API diff drafting failed: %s; falling back to template diff", exc)

        return self._generate_template_diff(suggestion)

    def _generate_template_diff(self, suggestion: RefactorSuggestion) -> str:
        """Produce a deterministic structural unified diff template when LLM is inactive."""
        target = suggestion.affected_nodes[0] if suggestion.affected_nodes else "component"
        clean_target = target.replace(":", "_").replace("/", "_")

        return (
            f"# Refactoring Draft Diff for: {suggestion.title}\n"
            f"# Type: {suggestion.type} | Effort: {suggestion.effort}\n"
            f"diff --git a/{clean_target}.py b/{clean_target}.py\n"
            f"--- a/{clean_target}.py\n"
            f"+++ b/{clean_target}.py\n"
            f"@@ -1,5 +1,10 @@\n"
            f"+# Refactored: {suggestion.title}\n"
            f"+# Rationale: {suggestion.rationale[:90]}...\n"
        )
