"""Data models for ArchLens architectural, security, and refactoring reports."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReportFormat(str, Enum):
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    MARKDOWN = "markdown"


class SectionCallout(BaseModel):
    what_means: str
    why_matters: str
    what_to_do: str

    @property
    def what_it_means(self) -> str:
        return self.what_means

    @property
    def why_it_matters(self) -> str:
        return self.why_matters


class GlossaryItem(BaseModel):
    term: str
    definition: str
    analogy: str


class TopRiskItem(BaseModel):
    rank: int
    node_id: str
    risk_score: float
    primary_issue: str
    severity: str
    category: str
    plain_english_impact: str = ""
    remediation_target: str = ""

    @property
    def title(self) -> str:
        return self.primary_issue

    @property
    def description(self) -> str:
        return self.plain_english_impact


class TrendData(BaseModel):
    health_score_delta: float
    previous_score: float | None = None
    previous_scan_date: str | None = None
    fixed_issues_count: int = 0
    new_issues_count: int = 0
    status: str = "stable"  # "improved", "degraded", "stable"


class ExecutiveSummary(BaseModel):
    health_score: float | None = Field(None, ge=0.0, le=100.0)
    grade: str | None = None  # "A+", "A", "B", "C", "D", "F" or None
    health_status: str = "ok"  # "ok" or "insufficient_data"
    sub_scores: dict[str, float] = Field(default_factory=dict)
    status_indicator: str = "GREEN"  # "GREEN", "AMBER", "RED"
    status_label: str = "HEALTHY"
    summary_text: str
    summary_sentences: list[str] = Field(default_factory=list)
    total_components: int
    total_dependencies: int
    total_loc: int
    total_critical_vulnerabilities: int
    total_circular_cycles: int
    top_3_risks: list[TopRiskItem] = Field(default_factory=list)
    top_5_risks: list[TopRiskItem] = Field(default_factory=list)
    trend: TrendData
    callout: SectionCallout | None = None


class LayerDistribution(BaseModel):
    name: str
    count: int
    percentage: float
    components: list[str] = Field(default_factory=list)


class ClusterOverview(BaseModel):
    cluster_id: int
    name: str
    component_count: int
    internal_edges: int
    external_edges: int
    cohesion_score: float
    key_components: list[str] = Field(default_factory=list)


class ArchitectureOverview(BaseModel):
    total_layers: int
    layers: list[LayerDistribution]
    total_clusters: int
    clusters: list[ClusterOverview]
    graph_image_base64: str = ""
    callout: SectionCallout | None = None


class CycleDetail(BaseModel):
    cycle_id: str
    path: list[str]
    formatted_path: str = ""  # e.g. "A -> B -> C -> A"
    length: int
    recommended_break_edge: tuple[str, str] | None = None
    interface_remedy: str = ""
    severity_label: str = "HIGH"
    severity_color: str = "#dc2626"


class BottleneckNode(BaseModel):
    node_id: str
    name: str
    betweenness_centrality: float
    in_degree: int
    out_degree: int
    risk_score: float = 0.0
    impact_level: str = "Moderate"  # "Critical", "High", "Moderate"


class InstabilityMetric(BaseModel):
    package_name: str
    afferent_coupling: int  # Ca
    efferent_coupling: int  # Ce
    instability: float  # I = Ce / (Ca + Ce)
    abstractness: float = 0.5  # A
    distance_main_sequence: float = 0.0  # D = |A + I - 1|
    category: str = "Balanced"  # "Stable", "Balanced", "Volatile"


class GodClassDetail(BaseModel):
    name: str
    file_path: str
    methods_count: int
    loc: int
    fan_in: int
    fan_out: int
    severity_label: str = "HIGH"
    severity_color: str = "#dc2626"
    recommendation: str = ""


class DependencyAnalysis(BaseModel):
    total_cycles: int
    cycles: list[CycleDetail]
    bottlenecks: list[BottleneckNode]
    instability_chart: list[InstabilityMetric]
    callout: SectionCallout | None = None


class SecurityFindingDetail(BaseModel):
    id: str
    rule_id: str
    title: str
    severity: str  # "critical", "high", "medium", "low"
    severity_label: str = "HIGH"  # Accessible text label
    severity_color: str = "#dc2626"
    cwe: str | None = None
    owasp: str | None = None
    file_path: str
    line_number: int | None = None
    code_snippet: str | None = None
    remediation: str | None = None


class SecurityOverview(BaseModel):
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    findings_by_severity: dict[str, list[SecurityFindingDetail]] = Field(default_factory=dict)
    all_findings: list[SecurityFindingDetail] = Field(default_factory=list)
    callout: SectionCallout | None = None


class CodeQualityOverview(BaseModel):
    average_complexity: float
    high_complexity_count: int
    complexity_distribution: dict[str, int]
    dead_code_nodes: list[str] = Field(default_factory=list)
    god_classes: list[GodClassDetail] = Field(default_factory=list)
    total_smells: int
    smell_breakdown: dict[str, int] = Field(default_factory=dict)
    callout: SectionCallout | None = None


class ActionPlanItem(BaseModel):
    id: str
    title: str
    description: str
    impact: str  # "High", "Medium", "Low"
    effort_estimate: str  # "1–2 days", "3–5 days", "1 sprint"
    affected_components: list[str] = Field(default_factory=list)
    category: str = "Architecture"  # "Architecture", "Security", "Modularity"


class PrioritizedActionPlan(BaseModel):
    fix_now: list[ActionPlanItem] = Field(default_factory=list)
    next_sprint: list[ActionPlanItem] = Field(default_factory=list)
    later: list[ActionPlanItem] = Field(default_factory=list)
    callout: SectionCallout | None = None


class RefactorRoadmapItem(BaseModel):
    rank: int
    id: str
    type: str
    title: str
    rationale: str
    affected_nodes: list[str]
    effort: str  # "S", "M", "L"
    estimated_time: str
    roi_score: float
    expected_coupling_reduction: int
    expected_cycles_eliminated: int


class RefactorRoadmap(BaseModel):
    total_recommendations: int
    items: list[RefactorRoadmapItem] = Field(default_factory=list)


class RefactorSimulation(BaseModel):
    has_simulation: bool = False
    before_metrics: dict[str, Any] = Field(default_factory=dict)
    after_metrics: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""


class ReportMetadata(BaseModel):
    report_id: str
    title: str = "Architecture Diagnostic Report"
    repo_name: str
    repo_path: str
    branch: str = "main"
    commit_hash: str = "HEAD"
    commit_sha: str | None = None
    source_fingerprint: str | None = None
    parser_version: str = "1.0.0"
    files_analyzed: int = 0
    files_skipped: int = 0
    truncated: bool = False
    external_dependencies_count: int = 0
    sub_scores: dict[str, float] = Field(default_factory=dict)
    health_status: str = "ok"
    language: str
    generated_at: str
    archlens_version: str = "2.4.0"
    overall_grade: str | None = None


class FullReport(BaseModel):
    metadata: ReportMetadata
    executive_summary: ExecutiveSummary
    glossary: list[GlossaryItem] = Field(default_factory=list)
    architecture_overview: ArchitectureOverview
    dependency_analysis: DependencyAnalysis
    security_findings: SecurityOverview
    code_quality: CodeQualityOverview
    prioritized_action_plan: PrioritizedActionPlan
    refactor_simulation: RefactorSimulation = Field(default_factory=RefactorSimulation)
    appendix: dict[str, Any] = Field(default_factory=dict)
    svg_charts: dict[str, str] = Field(default_factory=dict)

    @property
    def refactoring_roadmap(self) -> RefactorRoadmap:
        all_items = (
            self.prioritized_action_plan.fix_now
            + self.prioritized_action_plan.next_sprint
            + self.prioritized_action_plan.later
        )
        roadmap_items: list[RefactorRoadmapItem] = []
        for rank, item in enumerate(all_items, start=1):
            effort = "M"
            if "1–2" in item.effort_estimate or item.impact == "Low":
                effort = "S"
            elif "sprint" in item.effort_estimate.lower() or item.impact == "High":
                effort = "L"
            roadmap_items.append(
                RefactorRoadmapItem(
                    rank=rank,
                    id=item.id,
                    type=item.category,
                    title=item.title,
                    rationale=item.description,
                    affected_nodes=item.affected_components if item.affected_components else [item.title],
                    effort=effort,
                    estimated_time=item.effort_estimate,
                    roi_score=8.5 if item.impact == "High" else 5.0,
                    expected_coupling_reduction=1,
                    expected_cycles_eliminated=1,
                )
            )
        return RefactorRoadmap(total_recommendations=len(roadmap_items), items=roadmap_items)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
