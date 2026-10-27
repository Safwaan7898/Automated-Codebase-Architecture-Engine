"""Pydantic models for graph nodes, edges, and analysis results."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, computed_field


class NodeType(StrEnum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    PACKAGE = "package"
    INTERFACE = "interface"
    UNKNOWN = "unknown"


class ExternalDependency(BaseModel):
    """External dependency imported by codebase modules."""

    name: str = Field(..., description="Module/package identifier")
    category: str = Field("third_party", description="stdlib | third_party | unresolved")


class HealthScoreResult(BaseModel):
    """Architectural health score computed deterministically by backend."""

    status: str = Field(default="ok", description="'ok' | 'insufficient_data'")
    score: float | None = Field(default=None, description="0.0 - 100.0 health score")
    grade: str | None = Field(default=None, description="A+, A, B, C, D, F")
    sub_scores: dict[str, float] = Field(default_factory=dict)
    summary: str | None = None


class GraphNode(BaseModel):
    """A node in the dependency graph."""

    id: str = Field(..., description="Unique node identifier (e.g. 'flask.app')")
    label: str = Field(..., description="Human-readable display label")
    type: NodeType = NodeType.UNKNOWN
    language: str = Field(default="unknown", description="Programming language of node")
    file_path: str | None = None
    loc: int = Field(default=0, description="Lines of code")
    cyclomatic_complexity: float = Field(default=1.0, description="McCabe cyclomatic complexity")
    max_complexity: int = Field(default=1, description="Peak cyclomatic complexity in module")
    mean_complexity: float = Field(default=1.0, description="Mean cyclomatic complexity in module")
    community: int = Field(default=0, description="Louvain community cluster ID")
    external_dependencies: list[ExternalDependency] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(
        default_factory=list, description="Diagnostic/CWE findings associated with this node"
    )
    risk_score: float = Field(default=0.0, description="Risk score 0-100")
    is_vulnerable: bool = Field(default=False, description="True if high/critical security findings exist")
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """A directed dependency edge."""

    source: str = Field(..., description="Source node id")
    target: str = Field(..., description="Target node id")
    edge_type: str = "import"  # import | call | inherit | implement
    confidence: str = Field(default="resolved", description="'resolved' | 'parsed' | 'ai_inferred'")
    weight: float = 1.0
    is_cycle: bool = False


class DependencyGraph(BaseModel):
    """Container for the full dependency graph."""

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

    @computed_field
    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @computed_field
    @property
    def edge_count(self) -> int:
        return len(self.edges)


class AnalysisResult(BaseModel):
    """Full result returned from an analysis run."""

    repo_id: UUID
    path: str
    language: str
    graph: DependencyGraph
    smells: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list, description="All diagnostic and security findings")
    cycles: list[list[str]] = Field(default_factory=list, description="Detected circular dependency loops")
    summary: dict[str, Any] = Field(default_factory=dict, description="Summary statistics including security counts")
    external_dependencies: list[ExternalDependency] = Field(default_factory=list)
    health: HealthScoreResult = Field(default_factory=HealthScoreResult)
    refactor_suggestions: list[dict[str, Any]] = Field(
        default_factory=list, description="Automated architectural refactoring suggestions"
    )

    # Provenance, reproducibility & determinism fields
    commit_sha: str | None = Field(default=None, description="Git commit hash if available")
    parser_version: str = Field(default="1.5.0", description="Parser version")
    settings_hash: str = Field(default="", description="Hash of analysis settings")
    source_fingerprint: str = Field(default="", description="Deterministic hash of sorted file paths + contents")
    truncated: bool = Field(default=False, description="Flag indicating if limits truncated the analysis")
    truncated_counts: dict[str, int] = Field(default_factory=dict, description="Counts of truncated files/nodes if any")
    random_seed: int = Field(default=42, description="Fixed seed used for deterministic algorithms")
    ambiguous_imports: int = Field(
        default=0, description="Count of ambiguous import resolutions resolved deterministically"
    )
    files_excluded: int = Field(
        default=0, description="Count of files excluded from analysis scope (e.g. tests, fixtures, samples)"
    )
    include_tests: bool = Field(
        default=False, description="Flag indicating whether test/sample/fixture files were included"
    )
    unsupported_files: dict[str, int] = Field(
        default_factory=dict, description="Extension -> count of unsupported files"
    )
    languages: list[str] = Field(default_factory=list, description="All languages detected in analysis")

    @computed_field
    @property
    def node_count(self) -> int:
        return self.graph.node_count

    @computed_field
    @property
    def edge_count(self) -> int:
        return self.graph.edge_count
