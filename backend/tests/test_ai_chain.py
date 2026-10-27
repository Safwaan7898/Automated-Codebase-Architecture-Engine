"""Tests for Phase 5 Provider Chain: failover order, 429 Retry-After, privacy skipping, and secret redaction."""

import asyncio
import time
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from ai import (
    AISettings,
    ProviderConfig,
    ProviderChain,
    BaseAIProvider,
    AIProviderError,
    RateLimitError,
    BudgetExceededError,
    AIResponse,
    extract_and_parse_json,
    extract_and_validate_pydantic,
)
from ai.rate_limiter import ProviderRateLimiter
from ai.check import _sanitize_message
from app.main import app
from app.auth.store import auth_store
from app.auth.models import Role, UserStatus


class MockChainProvider(BaseAIProvider):
    """Test provider with programmable behavior."""

    def __init__(
        self,
        name: str,
        settings: AISettings | None = None,
        trains_on_prompts: bool = False,
        should_fail: bool = False,
        rate_limit_error: RateLimitError | None = None,
        response_text: str = "Mock response",
    ) -> None:
        super().__init__(settings or AISettings.from_env())
        self.name = name
        self.trains_on_prompts = trains_on_prompts
        self.should_fail = should_fail
        self.rate_limit_error = rate_limit_error
        self.response_text = response_text
        self.call_count = 0

    async def _execute_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        response_schema: type | None = None,
    ) -> AIResponse:
        self.call_count += 1
        if self.rate_limit_error:
            raise self.rate_limit_error
        if self.should_fail:
            raise AIProviderError(f"Provider {self.name} simulated failure with key mock_secret_123456789")

        return AIResponse(
            content=f"{self.name}: {self.response_text}",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            cost_usd=0.0001,
            provider=self.name,
            model="mock-model",
        )


@pytest.mark.asyncio
async def test_provider_chain_failover_order():
    """Verify provider chain fails over in the exact configured order when earlier providers fail."""
    rate_limiter = ProviderRateLimiter()
    settings = AISettings(
        enabled=True,
        provider_order=["provider_a", "provider_b", "provider_c"],
        providers={
            "provider_a": ProviderConfig(name="provider_a", api_key="key-a", model="m-a"),
            "provider_b": ProviderConfig(name="provider_b", api_key="key-b", model="m-b"),
            "provider_c": ProviderConfig(name="provider_c", api_key="key-c", model="m-c"),
        },
    )

    chain = ProviderChain(settings=settings, rate_limiter=rate_limiter)

    # Provider A fails, Provider B succeeds
    prov_a = MockChainProvider("provider_a", should_fail=True)
    prov_b = MockChainProvider("provider_b", response_text="Success from B")
    prov_c = MockChainProvider("provider_c", response_text="Success from C")

    chain._providers = {
        "provider_a": prov_a,
        "provider_b": prov_b,
        "provider_c": prov_c,
    }

    resp = await chain.complete("Test failover", use_cache=False)

    assert prov_a.call_count == 1
    assert prov_b.call_count == 1
    assert prov_c.call_count == 0  # Should not be called since B succeeded
    assert resp.provider == "provider_b"
    assert "Success from B" in resp.content


@pytest.mark.asyncio
async def test_provider_chain_429_handling_and_retry_after():
    """Verify 429 RateLimitError triggers Retry-After cooldown and immediate failover."""
    rate_limiter = ProviderRateLimiter()
    settings = AISettings(
        enabled=True,
        provider_order=["provider_429", "provider_backup"],
        providers={
            "provider_429": ProviderConfig(name="provider_429", api_key="key-1", model="m-1"),
            "provider_backup": ProviderConfig(name="provider_backup", api_key="key-2", model="m-2"),
        },
    )

    chain = ProviderChain(settings=settings, rate_limiter=rate_limiter)

    prov_429 = MockChainProvider(
        "provider_429",
        rate_limit_error=RateLimitError("Rate limit exceeded", status_code=429, retry_after=45),
    )
    prov_backup = MockChainProvider("provider_backup", response_text="Backup answered")

    chain._providers = {
        "provider_429": prov_429,
        "provider_backup": prov_backup,
    }

    # 1. First call fails on prov_429 and succeeds on prov_backup
    resp1 = await chain.complete("Call 1", use_cache=False)
    assert prov_429.call_count == 1
    assert prov_backup.call_count == 1
    assert resp1.provider == "provider_backup"

    # Verify provider_429 is under cooldown
    health_429 = rate_limiter.get_health_status("provider_429", settings.providers["provider_429"])
    assert health_429.status == "cooldown"
    assert health_429.cooldown_remaining_seconds > 0

    # 2. Second call should skip provider_429 completely due to cooldown without calling it again
    resp2 = await chain.complete("Call 2", use_cache=False)
    assert prov_429.call_count == 1  # Unchanged!
    assert prov_backup.call_count == 2
    assert resp2.provider == "provider_backup"


@pytest.mark.asyncio
async def test_private_repo_provider_skipping():
    """Verify providers with trains_on_prompts=True are skipped for private repos or uploads."""
    rate_limiter = ProviderRateLimiter()
    settings = AISettings(
        enabled=True,
        allow_training_providers=False,
        provider_order=["training_prov", "privacy_prov"],
        providers={
            "training_prov": ProviderConfig(name="training_prov", api_key="k1", trains_on_prompts=True),
            "privacy_prov": ProviderConfig(name="privacy_prov", api_key="k2", trains_on_prompts=False),
        },
    )

    chain = ProviderChain(settings=settings, rate_limiter=rate_limiter)

    prov_train = MockChainProvider("training_prov", trains_on_prompts=True, response_text="Trained response")
    prov_priv = MockChainProvider("privacy_prov", trains_on_prompts=False, response_text="Private response")

    chain._providers = {
        "training_prov": prov_train,
        "privacy_prov": prov_priv,
    }

    # 1. Private repo (e.g. token supplied): training_prov MUST be skipped
    resp_private = await chain.complete("Private prompt", is_private_repo=True, use_cache=False)
    assert prov_train.call_count == 0
    assert prov_priv.call_count == 1
    assert resp_private.provider == "privacy_prov"

    # 2. Upload / ZIP source: training_prov MUST be skipped
    resp_upload = await chain.complete("Upload prompt", source_type="zip", use_cache=False)
    assert prov_train.call_count == 0
    assert prov_priv.call_count == 2
    assert resp_upload.provider == "privacy_prov"

    # 3. Public repo: training_prov is allowed
    resp_public = await chain.complete("Public prompt", is_private_repo=False, source_type="git", use_cache=False)
    assert prov_train.call_count == 1
    assert resp_public.provider == "training_prov"

    # 4. If ARCHLENS_AI_ALLOW_TRAINING_PROVIDERS is True: allowed even for private repos
    settings.allow_training_providers = True
    resp_allowed = await chain.complete("Private prompt with override", is_private_repo=True, use_cache=False)
    assert prov_train.call_count == 2
    assert resp_allowed.provider == "training_prov"


def test_keys_never_appear_in_response_log_or_exception():
    """Verify secret API keys are never exposed in exceptions, sanitize outputs, or admin status."""
    dummy_key = "mock_live_9876543210abcdef12345"

    # 1. Sanitize message check
    raw_error = f"HTTP 401 Unauthorized for Bearer {dummy_key} at https://api.groq.com/openai/v1?key={dummy_key}"
    clean = _sanitize_message(raw_error, [dummy_key])
    assert dummy_key not in clean
    assert "[REDACTED" in clean

    # 2. Admin status report check
    settings = AISettings(
        enabled=True,
        provider_order=["groq", "nvidia", "gemini"],
        providers={
            "groq": ProviderConfig(name="groq", api_key=dummy_key, model="llama-3.3-70b-versatile"),
        },
    )
    chain = ProviderChain(settings=settings)
    status_report = chain.get_status_report().model_dump()

    status_str = str(status_report)
    assert dummy_key not in status_str
    # Provider health has boolean has_api_key, not the key string
    groq_health = next(p for p in status_report["providers"] if p["name"] == "groq")
    assert groq_health["has_api_key"] is True
    assert "api_key" not in groq_health


def test_admin_ai_status_endpoints_require_admin(monkeypatch):
    """Verify /admin/ai/status and /api/admin/ai/status require admin credentials and never leak keys."""
    client = TestClient(app)

    # 1. When auth is required, unauthenticated request -> 401
    monkeypatch.setattr("app.core.config.settings.auth_required", True)

    resp_anon = client.get("/admin/ai/status")
    assert resp_anon.status_code == 401

    resp_anon_api = client.get("/api/admin/ai/status")
    assert resp_anon_api.status_code == 401

    # 2. Authenticated as VIEWER (lacks VIEW_AUDIT_LOGS) -> 403 Forbidden
    from app.auth.store import DEMO_USERS

    viewer_demo = next(d for d in DEMO_USERS if d["role"] == Role.VIEWER)
    v_login = client.post(
        "/auth/login",
        json={"work_email": viewer_demo["email"], "password": viewer_demo["password"]},
    )
    assert v_login.status_code == 200
    viewer_token = v_login.json()["access_token"]

    resp_forbidden = client.get("/admin/ai/status", headers={"Authorization": f"Bearer {viewer_token}"})
    assert resp_forbidden.status_code == 403

    # 3. Authenticated as ADMIN -> 200 OK
    admin_demo = next(d for d in DEMO_USERS if d["role"] == Role.ADMIN)
    a_login = client.post(
        "/auth/login",
        json={"work_email": admin_demo["email"], "password": admin_demo["password"]},
    )
    assert a_login.status_code == 200
    admin_token = a_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 4. Authorized request to /admin/ai/status
    resp_admin = client.get("/admin/ai/status", headers=headers)
    assert resp_admin.status_code == 200
    data = resp_admin.json()
    assert "enabled" in data
    assert "provider_order" in data
    assert "providers" in data

    # Confirm no keys in response
    resp_text = resp_admin.text
    assert "api_key" not in resp_text.lower() or "has_api_key" in resp_text

    # 5. Authorized request to /api/admin/ai/status
    resp_admin_api = client.get("/api/admin/ai/status", headers=headers)
    assert resp_admin_api.status_code == 200
    assert resp_admin_api.json()["provider_order"] == data["provider_order"]


class SampleSchema(BaseModel):
    summary: str
    score: int
    tags: list[str] = []


def test_robust_json_extraction_from_reasoning_models():
    """Verify that reasoning models emitting <think> tags, fences, or conversational text are properly parsed."""
    # 1. Output with <think> tag and markdown code block
    reasoning_text = (
        "<think>\n"
        "The user requested an analysis of the module architecture.\n"
        "Let's calculate the complexity and health score.\n"
        "</think>\n"
        "Here is the structured architecture summary:\n"
        "```json\n"
        '{\n  "summary": "Core engine modularity is sound.",\n  "score": 92,\n  "tags": ["core", "clean"]\n}\n'
        "```\n"
        "Hope this assessment helps!"
    )

    data = extract_and_parse_json(reasoning_text)
    assert isinstance(data, dict)
    assert data["summary"] == "Core engine modularity is sound."
    assert data["score"] == 92
    assert data["tags"] == ["core", "clean"]

    validated = extract_and_validate_pydantic(reasoning_text, SampleSchema)
    assert validated.summary == "Core engine modularity is sound."
    assert validated.score == 92
    assert validated.tags == ["core", "clean"]

    # 2. Output with conversational preamble and postamble without code blocks
    conversational_text = (
        "Certainly! Based on graph analysis, here is the result:\n"
        '{"summary": "Tight coupling detected", "score": 64, "tags": ["smell"]}\n'
        "Let me know if you would like me to draft a refactoring proposal."
    )
    validated_conv = extract_and_validate_pydantic(conversational_text, SampleSchema)
    assert validated_conv.summary == "Tight coupling detected"
    assert validated_conv.score == 64
    assert validated_conv.tags == ["smell"]

    # 3. Clean raw JSON
    raw_json = '{"summary": "Perfect score", "score": 100, "tags": []}'
    validated_raw = extract_and_validate_pydantic(raw_json, SampleSchema)
    assert validated_raw.score == 100


@pytest.mark.asyncio
async def test_provider_chain_budget_enforcement():
    """Verify ProviderChain enforces max tokens and financial budget across calls."""
    settings = AISettings(
        enabled=True,
        provider_order=["mock_prov"],
        providers={
            "mock_prov": ProviderConfig(name="mock_prov", api_key="k1", model="m1"),
        },
        max_tokens_per_analysis=35,
        budget_usd=0.0005,
    )

    chain = ProviderChain(settings=settings)
    prov = MockChainProvider("mock_prov")
    chain._providers = {"mock_prov": prov}

    # Call 1: consumes 30 tokens, $0.0001
    resp1 = await chain.complete("Call 1", use_cache=False)
    assert resp1.total_tokens == 30
    assert chain.accumulated_tokens == 30
    assert chain.accumulated_cost_usd > 0

    # Call 2: anticipated 100 tokens will exceed max_tokens_per_analysis (30 + 100 > 50)
    with pytest.raises(BudgetExceededError) as exc_info:
        await chain.complete("Call 2", use_cache=False)
    assert "Token budget exceeded" in str(exc_info.value)

    # Test reset_usage restores capacity
    chain.reset_usage()
    assert chain.accumulated_tokens == 0
    assert chain.accumulated_cost_usd == 0.0

    # Call succeeds after reset
    resp2 = await chain.complete("Call after reset", use_cache=False)
    assert resp2.total_tokens == 30
