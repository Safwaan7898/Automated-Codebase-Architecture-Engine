"""Fake AI Provider for automated tests and offline execution."""

from __future__ import annotations

import json
from typing import Any, Type
from pydantic import BaseModel

from .base import BaseAIProvider, AIProviderError, RateLimitError
from ..models import (
    AIResponse,
    AIMetricExplanation,
    AISmellFixSuggestion,
    AISecurityEnrichment,
    AITopologySummary,
    AIDashboardSummary,
)


class FakeProvider(BaseAIProvider):
    """Deterministic mock provider for unit testing and CI."""

    name: str = "fake"
    trains_on_prompts: bool = False

    def __init__(self, settings=None) -> None:
        super().__init__(settings)
        self.simulate_failure: bool = False
        self.simulate_timeout: bool = False
        self.simulate_rate_limit: bool = False
        self.mock_retry_after: str | int | float | None = None
        self.custom_responses: dict[str, str] = {}

    async def _execute_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        response_schema: Type[BaseModel] | None = None,
    ) -> AIResponse:
        if self.simulate_rate_limit:
            raise RateLimitError("Simulated 429 rate limit exceeded", status_code=429, retry_after=self.mock_retry_after)

        if self.simulate_failure:
            raise AIProviderError("Simulated provider failure")

        if self.simulate_timeout:
            import asyncio
            await asyncio.sleep(self.settings.request_timeout_seconds + 1.0)

        # Check for custom prompt override
        for k, v in self.custom_responses.items():
            if k in prompt:
                return AIResponse(
                    content=v,
                    structured_data=json.loads(v) if v.startswith("{") else None,
                    input_tokens=len(prompt) // 4,
                    output_tokens=len(v) // 4,
                    total_tokens=(len(prompt) + len(v)) // 4,
                    cost_usd=0.0,
                    provider="fake",
                    model="fake-v1",
                )

        # Generate structured response if schema requested
        if response_schema is not None:
            structured_data = self._generate_mock_structured_data(response_schema, prompt)
            content_str = json.dumps(structured_data)
            return AIResponse(
                content=content_str,
                structured_data=structured_data,
                input_tokens=150,
                output_tokens=100,
                total_tokens=250,
                cost_usd=0.0,
                provider="fake",
                model="fake-v1",
            )

        content = "AI-generated architecture analysis: The system demonstrates modular coupling and bounded layer domains."
        return AIResponse(
            content=content,
            structured_data=None,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.0,
            provider="fake",
            model="fake-v1",
        )

    def _generate_mock_structured_data(self, schema: Type[BaseModel], prompt: str) -> dict[str, Any]:
        if issubclass(schema, AIMetricExplanation):
            return {
                "metric_name": "Instability",
                "explanation": "Instability index measures the ratio of afferent to efferent dependencies.",
                "impact": "High instability without high abstraction indicates fragile architecture.",
                "recommendation": "Introduce abstract interfaces to isolate volatile concrete packages.",
                "is_ai_generated": True,
            }
        elif issubclass(schema, AISmellFixSuggestion):
            return {
                "smell_id": "cyclic_dependency",
                "why_it_matters": "Cycles prevent independent deployment, compilation, and testing.",
                "fix_outline": "Extract shared types or introduce event-driven inversion of control.",
                "refactor_pattern": "Extract Interface",
                "is_ai_generated": True,
            }
        elif issubclass(schema, AISecurityEnrichment):
            return {
                "finding_id": "cwe-78-command-injection",
                "explanation": "Untrusted user data reaching command execution can allow remote code execution.",
                "false_positive_likelihood": "Low",
                "false_positive_reason": "No sanitization detected between input and subprocess execution.",
                "suggested_fix": "Use safe array invocation with shell=False.",
                "is_ai_generated": True,
            }
        elif issubclass(schema, AITopologySummary):
            return {
                "community_id": 1,
                "community_name": "Core Service Domain",
                "description": "Orchestrates business logic and service interactions.",
                "verified_nodes": [],
                "is_ai_generated": True,
            }
        elif issubclass(schema, AIDashboardSummary):
            return {
                "headline": "System Architecture Review",
                "summary": "Overall architecture is healthy with isolated modular clusters.",
                "priority_actions": ["Resolve 1 circular dependency", "Isolate core database access"],
                "is_ai_generated": True,
            }
        # Generic fallback
        return {"result": "ok", "is_ai_generated": True}
