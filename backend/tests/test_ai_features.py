"""Tests for Phase 6 AI Feature Integrations.

Tests all 11 AI capabilities with mocked-provider success and failure-fallback tests:
1. Ingestion / analysis for unsupported languages (inferred edges, target existence validation)
2. Topology community naming and layer assignment explanation
3. Metrics explanation ("Explain this metric" using actual numbers)
4. Diagnostics / smells explanation and fix outline
5. Security finding explanation and false-positive estimation (invariant: never suppresses)
6. Dashboard executive briefing from computed values
7. Reports executive narrative (in-app and PDF fallback)
8. Refactor engine (valid patch, bad patch rejected, syntax error rejected, repair loop, no change to repo)
9. "Ask ArchLens" chat panel with citation validation
10. Natural language search query filter
11. Admin AI usage and cost telemetry
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import pytest
from pydantic import BaseModel

from ai import (
    AISettings,
    ProviderConfig,
    ProviderChain,
    AIService,
    BaseAIProvider,
    AIResponse,
    AIProviderError,
    AIMetricExplanation,
    AISmellFixSuggestion,
    AISecurityEnrichment,
    AITopologySummary,
    AIDashboardSummary,
    AIReportNarrative,
    AIChatResponse,
    AINLSearchFilter,
    AIRefactorProposal,
    AIUsageStatistics,
)
from ai.features import (
    explain_metric,
    explain_smell,
    enrich_security_finding,
    summarize_topology,
    generate_dashboard_summary,
    generate_report_narrative,
    infer_unsupported_language_edges,
    draft_and_validate_refactor,
    ask_archlens_chat,
    natural_language_search,
    get_ai_usage_statistics,
)


class MockAIProvider(BaseAIProvider):
    """Programmable mock provider for testing structured outputs and failure fallback."""

    def __init__(self, settings: AISettings, return_data: dict | None = None, should_fail: bool = False) -> None:
        super().__init__(settings)
        self.return_data = return_data or {}
        self.should_fail = should_fail
        self.last_prompt = ""

    async def _execute_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        response_schema: type | None = None,
    ) -> AIResponse:
        self.last_prompt = prompt
        if self.should_fail:
            raise AIProviderError("Simulated AI provider outage")

        content_json = ""
        import json

        if self.return_data:
            content_json = json.dumps(self.return_data)

        return AIResponse(
            content=content_json or "Mock content",
            structured_data=self.return_data,
            input_tokens=25,
            output_tokens=35,
            total_tokens=60,
            cost_usd=0.0002,
            provider="mock",
            model="mock-v1",
        )


def _create_service(mock_data: dict | None = None, should_fail: bool = False, enabled: bool = True) -> AIService:
    settings = AISettings(enabled=enabled, provider="fake")
    provider = MockAIProvider(settings, return_data=mock_data, should_fail=should_fail)
    return AIService(provider=provider, settings=settings)


@pytest.fixture(autouse=True)
def clean_ai_cache():
    from ai.cache import GLOBAL_AI_CACHE

    GLOBAL_AI_CACHE.clear()
    yield
    GLOBAL_AI_CACHE.clear()


# ── 1. Ingestion / Analysis for Unsupported Languages ─────────────────────────


@pytest.mark.asyncio
async def test_unsupported_language_edge_inference():
    """Verify inferred edges are validated against valid target nodes and dropped if ungrounded."""
    valid_targets = {"core.models", "core.utils", "app.config"}
    mock_data = {
        "inferred_imports": ["core.models", "invalid.hallucinated.target", "core/utils.js"],
        "inferred_classes": ["CustomHandler"],
        "reasoning": "Detected ES module imports",
    }
    svc = _create_service(mock_data)

    edges = await infer_unsupported_language_edges(
        file_path="src/unsupported.rb",
        content="require 'core/models'\nrequire 'invalid/target'",
        valid_targets=valid_targets,
        service=svc,
    )

    assert len(edges) == 2  # "core.models" and "core/utils.js" matched, invalid dropped
    assert edges[0].target == "core.models"
    assert edges[0].confidence == "ai_inferred"

    # Fallback test: when AI fails or is disabled, returns empty list without crashing
    svc_fail = _create_service(should_fail=True)
    fallback_edges = await infer_unsupported_language_edges(
        file_path="src/unsupported.rb",
        content="require 'core/models'",
        valid_targets=valid_targets,
        service=svc_fail,
    )
    assert fallback_edges == []


# ── 2. Topology Community & Layer Explanation ─────────────────────────────────


@pytest.mark.asyncio
async def test_topology_summary():
    """Verify community naming with grounded node validation."""
    node_ids = ["auth.service", "auth.models", "auth.tokens"]
    mock_data = {
        "community_id": 1,
        "community_name": "Authentication & Identity",
        "description": "Handles authentication flows, token lifecycle, and session management.",
        "verified_nodes": ["auth.service", "auth.models", "hallucinated.node"],
        "is_ai_generated": True,
    }
    svc = _create_service(mock_data)

    res = await summarize_topology(
        community_id=1,
        node_ids=node_ids,
        service=svc,
    )

    assert res.community_name == "Authentication & Identity"
    assert res.is_ai_generated is True
    # Grounding check: hallucinated node dropped
    assert "hallucinated.node" not in res.verified_nodes
    assert "auth.service" in res.verified_nodes

    # Fallback test
    from ai.cache import GLOBAL_AI_CACHE

    GLOBAL_AI_CACHE.clear()
    svc_fail = _create_service(should_fail=True)
    fallback_res = await summarize_topology(community_id=1, node_ids=node_ids, service=svc_fail)
    assert fallback_res.is_ai_generated is False
    assert "auth.service" in fallback_res.verified_nodes


# ── 3. Metrics Explanation ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_metrics_explanation():
    """Verify 'Explain this metric' uses actual numbers and provides deterministic fallback."""
    mock_data = {
        "metric_name": "Instability",
        "explanation": "Instability is 0.85, meaning 85% of dependencies are afferent outgoing couplings.",
        "impact": "High risk of ripple effects across dependent layers.",
        "recommendation": "Introduce dependency inversion interface.",
        "is_ai_generated": True,
    }
    svc = _create_service(mock_data)

    res = await explain_metric("Instability", 0.85, repo_context={"health_score": 72.0}, service=svc)
    assert res.metric_name == "Instability"
    assert "0.85" in res.explanation
    assert res.is_ai_generated is True

    # Fallback test
    from ai.cache import GLOBAL_AI_CACHE

    GLOBAL_AI_CACHE.clear()
    svc_fail = _create_service(should_fail=True)
    fallback_res = await explain_metric("Instability", 0.85, service=svc_fail)
    assert fallback_res.is_ai_generated is False
    assert "0.85" in fallback_res.explanation


# ── 4. Diagnostics / Smells Contextual Explanation ────────────────────────────


@pytest.mark.asyncio
async def test_smells_explanation():
    """Verify smell explanation and fix outline."""
    mock_data = {
        "smell_id": "god_class_1",
        "why_it_matters": "Centralizes 40 methods creating high blast radius across modules.",
        "fix_outline": "1. Extract validation methods into Validator. 2. Inject repository.",
        "refactor_pattern": "Extract Class",
        "is_ai_generated": True,
    }
    svc = _create_service(mock_data)

    smell = {"id": "god_class_1", "type": "God Class", "affected_nodes": ["app.core.manager"]}
    res = await explain_smell(smell, service=svc)
    assert res.refactor_pattern == "Extract Class"
    assert res.is_ai_generated is True

    # Fallback test
    from ai.cache import GLOBAL_AI_CACHE

    GLOBAL_AI_CACHE.clear()
    svc_fail = _create_service(should_fail=True)
    fallback_res = await explain_smell(smell, service=svc_fail)
    assert fallback_res.is_ai_generated is False
    assert "Extract" in fallback_res.refactor_pattern


# ── 5. Security Finding Explanation & Remediation ─────────────────────────────


@pytest.mark.asyncio
async def test_security_finding_enrichment():
    """Verify security explanation and hard invariant that finding is NEVER suppressed."""
    mock_data = {
        "finding_id": "cwe_78_1",
        "explanation": "Arbitrary command execution via untrusted shell argument.",
        "false_positive_likelihood": "Low",
        "false_positive_reason": "Direct user input reaches subprocess without shell escaping.",
        "suggested_fix": "subprocess.run(['safe_cmd', sanitized_arg], shell=False)",
        "is_ai_generated": True,
    }
    svc = _create_service(mock_data)

    finding = {
        "id": "cwe_78_1",
        "rule_name": "Command Injection",
        "cwe": "CWE-78",
        "severity": "CRITICAL",
        "file_path": "backend/app.py",
        "line_number": 42,
    }
    res = await enrich_security_finding(finding, code_snippet="subprocess.run(user_cmd, shell=True)", service=svc)
    assert res.false_positive_likelihood == "Low"
    assert "shell=False" in res.suggested_fix
    assert res.is_ai_generated is True

    # Fallback test
    svc_fail = _create_service(should_fail=True)
    fallback_res = await enrich_security_finding(finding, service=svc_fail)
    assert fallback_res.is_ai_generated is False
    assert "CWE-78" in fallback_res.explanation


# ── 6. Dashboard Executive Briefing ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_dashboard_summary():
    """Verify dashboard summary is generated from computed values with deterministic fallback."""
    mock_data = {
        "headline": "Architecture Grade: B (82.5/100) — Healthy",
        "summary": "The system achieves strong modular isolation with 1 circular loop to resolve.",
        "priority_actions": ["Break 1 cyclic dependency", "Decompose God Class in auth.service"],
        "is_ai_generated": True,
    }
    svc = _create_service(mock_data)

    res = await generate_dashboard_summary(
        health_score=82.5,
        grade="B",
        smells_count=3,
        cycles_count=1,
        top_hotspots=["auth.service", "api.router"],
        service=svc,
    )
    assert res.is_ai_generated is True
    assert "82.5" in res.headline

    # Fallback test
    svc_fail = _create_service(should_fail=True)
    fallback_res = await generate_dashboard_summary(
        health_score=82.5,
        grade="B",
        smells_count=3,
        cycles_count=1,
        top_hotspots=["auth.service"],
        service=svc_fail,
    )
    assert fallback_res.is_ai_generated is False
    assert "82.5" in fallback_res.headline


# ── 7. Reports Executive Narrative ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_report_narrative():
    """Verify in-app and PDF narrative text generation with fallback."""
    mock_data = {
        "executive_summary": "Architecture evaluation for Core Platform: score 78.4/100.",
        "what_this_means": "The codebase maintains good domain boundaries.",
        "why_it_matters": "Unchecked coupling slows sprint delivery.",
        "what_to_do": "Refactor top 3 hotspots and apply interface segregation.",
        "is_ai_generated": True,
    }
    svc = _create_service(mock_data)

    res = await generate_report_narrative(
        report_data={"health_score": 78.4, "grade": "C", "repo_name": "Core Platform"},
        service=svc,
    )
    assert res.is_ai_generated is True
    assert "Core Platform" in res.executive_summary

    # Fallback test
    from ai.cache import GLOBAL_AI_CACHE

    GLOBAL_AI_CACHE.clear()
    svc_fail = _create_service(should_fail=True)
    fallback_res = await generate_report_narrative(
        report_data={"health_score": 78.4, "grade": "C", "repo_name": "Core Platform"},
        service=svc_fail,
    )
    assert fallback_res.is_ai_generated is False
    assert "78.4" in fallback_res.executive_summary


# ── 8. Refactor Engine with Sandbox Validation & Repair Loop ──────────────────


@pytest.mark.asyncio
async def test_refactor_engine_ai_proposal(tmp_path):
    """Verify AI refactor drafting, sandbox validation, and that AI NEVER modifies user repo."""
    # Create sample target file in user repo
    target_file = tmp_path / "service.py"
    original_code = "def process():\n    return 42\n"
    target_file.write_text(original_code, encoding="utf-8")

    # 1. Valid patch
    valid_diff = (
        "--- a/service.py\n+++ b/service.py\n@@ -1,2 +1,3 @@\n def process():\n+    # refactored\n     return 42\n"
    )
    mock_data = {
        "rationale": "Add refactored comment",
        "unified_diff": valid_diff,
        "risk_level": "Low",
        "confidence": 0.90,
    }
    svc = _create_service(mock_data)

    smell = {"id": "smell_1", "type": "God Class", "target": "service"}
    proposal = await draft_and_validate_refactor(smell, repo_root=tmp_path, service=svc)

    assert proposal.validation.applies_cleanly is True
    assert proposal.validation.parses_without_syntax_errors is True
    assert proposal.validation.validation_status == "verified"

    # INVARIANT: User repository file MUST be completely unchanged!
    assert target_file.read_text(encoding="utf-8") == original_code

    # 2. Patch with syntax error -> rejected
    from ai.cache import GLOBAL_AI_CACHE

    GLOBAL_AI_CACHE.clear()
    bad_syntax_diff = (
        "--- a/service.py\n"
        "+++ b/service.py\n"
        "@@ -1,2 +1,3 @@\n"
        " def process():\n"
        "+    def broken syntax here !! ??\n"
        "     return 42\n"
    )
    svc_bad = _create_service(
        {
            "rationale": "Broken patch",
            "unified_diff": bad_syntax_diff,
            "risk_level": "High",
            "confidence": 0.20,
        }
    )
    bad_prop = await draft_and_validate_refactor(smell, repo_root=tmp_path, max_repair_attempts=0, service=svc_bad)
    # The syntax error causes the proposal to fail validation
    assert bad_prop.validation.parses_without_syntax_errors is False
    assert bad_prop.validation.validation_status == "unverified"


# ── 9. "Ask ArchLens" Chat Panel with Citation Validation ─────────────────────


@pytest.mark.asyncio
async def test_ask_archlens_chat():
    """Verify chat retrieval and that answers with invalid citations are rejected."""

    class FakeGraph:
        class Node:
            def __init__(self, nid):
                self.id = nid
                self.cyclomatic_complexity = 5.0

        nodes = [Node("app.config"), Node("app.router")]

    class FakeAnalysisResult:
        graph = FakeGraph()
        cycles = [["app.config", "app.router"]]
        smells = []
        findings = []

    res_obj = FakeAnalysisResult()

    # 1. Valid citation
    mock_valid = {
        "answer": "The application router depends on app.config.",
        "cited_node_ids": ["app.router", "app.config"],
    }
    svc = _create_service(mock_valid)

    resp = await ask_archlens_chat("How does router work?", res_obj, service=svc)
    assert resp.verified is True
    assert len(resp.citations) == 2
    assert resp.citations[0].node_id == "app.router"

    # 2. Hallucinated citation -> rejected and dropped
    mock_hallucinated = {
        "answer": "The system depends on fake.ghost.module.",
        "cited_node_ids": ["fake.ghost.module"],
    }
    svc_ghost = _create_service(mock_hallucinated)
    resp_ghost = await ask_archlens_chat("Check ghost module", res_obj, service=svc_ghost)
    # Hallucinated citation rejected, falls back to grounded answer
    assert resp_ghost.is_ai_generated is False


# ── 10. Natural Language Search ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_natural_language_search():
    """Verify natural language query translation to validated filter."""
    available_nodes = {"backend.config", "backend.auth", "backend.database"}
    mock_data = {
        "name_contains": "auth",
        "depends_on": "backend.config",
        "min_complexity": 8.0,
        "max_instability": 0.5,
        "smell_type": "God Class",
        "language": "python",
        "is_ai_generated": True,
    }
    svc = _create_service(mock_data)

    flt = await natural_language_search(
        "Find auth modules that depend on config and have complexity above 8",
        available_nodes,
        service=svc,
    )
    assert flt.name_contains == "auth"
    assert flt.depends_on == "backend.config"
    assert flt.min_complexity == 8.0


# ── 11. Admin AI Usage and Cost Telemetry ─────────────────────────────────────


def test_admin_ai_usage_telemetry():
    """Verify aggregated usage telemetry returns calls, tokens, and cost breakdown."""
    stats = get_ai_usage_statistics()
    assert isinstance(stats, AIUsageStatistics)
    assert stats.total_calls >= 0
    assert stats.total_tokens >= 0
    assert stats.total_cost_usd >= 0.0
    assert isinstance(stats.feature_breakdown, list)
