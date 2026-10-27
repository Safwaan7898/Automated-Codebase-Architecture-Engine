"""Pydantic data models for AI Core and feature integrations."""

from __future__ import annotations

from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class AIResponse(BaseModel):
    """Container for the output of an AI provider invocation."""

    content: str
    structured_data: dict[str, Any] | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    cached: bool = False
    provider: str = "fake"
    model: str = "mock"
    latency_ms: float = 0.0
    is_fallback: bool = False


class AICallLog(BaseModel):
    """Audit record for an AI provider call (never stores prompts containing code)."""

    feature: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    success: bool
    error: str | None = None
    timestamp: str
    cached: bool = False


class ProviderHealthStatus(BaseModel):
    """Health, latency, and rate-limit status for a single AI provider (never exposes API keys)."""

    name: str
    status: str = Field(default="healthy", description="'healthy' | 'rate_limited' | 'cooldown' | 'no_key' | 'disabled'")
    model: str = ""
    trains_on_prompts: bool = False
    has_api_key: bool = Field(default=False, description="Flag indicating if key is set (key itself is NEVER exposed)")
    rpm_limit: int = 30
    rpm_used: int = 0
    rpm_remaining: int = 30
    cooldown_remaining_seconds: float = 0.0
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    last_error: str | None = None
    last_latency_ms: float = 0.0


class AIStatusResponse(BaseModel):
    """Admin status report of AI engine and provider chain (never exposes keys)."""

    enabled: bool
    provider_order: list[str]
    active_provider: str | None = None
    allow_training_providers: bool = False
    providers: list[ProviderHealthStatus] = Field(default_factory=list)
    cache_entries: int = 0
    timestamp: str = ""


# Structured domain responses validated by Pydantic

class AIMetricExplanation(BaseModel):
    """Plain-English explanation of an architecture metric using actual numbers."""

    metric_name: str
    explanation: str = Field(..., description="What the metric measures in context of repo values")
    impact: str = Field(..., description="Why this value matters for maintainability/risk")
    recommendation: str = Field(..., description="Actionable recommendation")
    is_ai_generated: bool = True


class AISmellFixSuggestion(BaseModel):
    """Contextual explanation and fix outline for a detected code smell."""

    smell_id: str
    why_it_matters: str = Field(..., description="Specific consequence in this codebase")
    fix_outline: str = Field(..., description="Step-by-step refactoring recommendation")
    refactor_pattern: str = Field(default="Extract Class / Dependency Injection", description="Pattern name")
    is_ai_generated: bool = True


class AISecurityEnrichment(BaseModel):
    """Enrichment for a diagnostic security finding."""

    finding_id: str
    explanation: str = Field(..., description="Explanation of vulnerability mechanism")
    false_positive_likelihood: str = Field(..., description="'Low' | 'Medium' | 'High'")
    false_positive_reason: str = Field(..., description="Reasoning based on sanitizer/call context")
    suggested_fix: str = Field(..., description="Draft remediation code snippet")
    is_ai_generated: bool = True


class AITopologySummary(BaseModel):
    """Explanation and naming of structural communities/layers."""

    community_id: int
    community_name: str = Field(..., description="Descriptive architecture domain name")
    description: str = Field(..., description="Summary of modules belonging to this community")
    verified_nodes: list[str] = Field(default_factory=list, description="Validated nodes in cluster")
    is_ai_generated: bool = True


class AIDashboardSummary(BaseModel):
    """High-level executive briefing for Dashboard overview."""

    headline: str
    summary: str
    priority_actions: list[str] = Field(default_factory=list)
    is_ai_generated: bool = True


class AIInferredEdge(BaseModel):
    """Inferred structural edge for unsupported languages."""

    source: str
    target: str
    edge_type: str = "import"
    confidence: str = "ai_inferred"
    reasoning: str = ""


class AIReportNarrative(BaseModel):
    """Executive narrative and section analysis for downloadable and in-app reports."""

    executive_summary: str = Field(..., description="High-level overview of codebase architecture")
    what_this_means: str = Field(..., description="Plain-English explanation of the health score and findings")
    why_it_matters: str = Field(..., description="Strategic architectural and business risks")
    what_to_do: str = Field(..., description="Recommended sequence of prioritized remediations")
    is_ai_generated: bool = True


class AIChatCitation(BaseModel):
    """Grounded reference citation for Ask ArchLens chat response."""

    node_id: str
    citation_type: str = Field(default="module", description="module, cycle, finding, hotspot")
    context: str = ""


class AIChatResponse(BaseModel):
    """Structured response from 'Ask ArchLens' assistant with verified grounding citations."""

    query: str
    answer: str
    citations: list[AIChatCitation] = Field(default_factory=list)
    verified: bool = True
    is_ai_generated: bool = True


class AINLSearchFilter(BaseModel):
    """Deterministic filter criteria parsed from natural language query."""

    name_contains: str | None = None
    depends_on: str | None = None
    min_complexity: float | None = None
    max_instability: float | None = None
    smell_type: str | None = None
    language: str | None = None
    is_ai_generated: bool = True


class AIRefactorValidationResult(BaseModel):
    """Results from deterministic multi-step patch validation in temporary repo sandbox."""

    applies_cleanly: bool = False
    parses_without_syntax_errors: bool = False
    target_smell_resolved: bool = False
    new_cycles_introduced: int = 0
    new_critical_findings: int = 0
    instability_delta: float = 0.0
    public_symbols_preserved: bool = True
    tests_passed: bool | None = None
    validation_status: str = Field(default="unverified", description="'verified' | 'unverified' | 'rejected'")
    validation_errors: list[str] = Field(default_factory=list)


class AIRefactorProposal(BaseModel):
    """AI-drafted refactoring proposal with unified diff, metrics, and verification status."""

    proposal_id: str
    smell_id: str
    target_node: str
    strategy_name: str
    rationale: str
    unified_diff: str = Field(..., description="Standard git-compatible unified diff patch")
    risk_level: str = Field(default="Medium", description="'Low' | 'Medium' | 'High'")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    validation: AIRefactorValidationResult = Field(default_factory=AIRefactorValidationResult)
    is_ai_generated: bool = True


class AIFeatureUsageSummary(BaseModel):
    """Usage aggregate per feature."""

    feature_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0


class AIUsageStatistics(BaseModel):
    """System-wide AI usage, costs, and token consumption statistics."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost_usd: float = 0.0
    feature_breakdown: list[AIFeatureUsageSummary] = Field(default_factory=list)
    recent_logs: list[AICallLog] = Field(default_factory=list)
