"""REST API endpoints for architectural graph analysis with OpenAPI JSON schemas.

Endpoints:
- POST /analysis/cycles: Circular dependencies via Tarjan's SCC
- POST /analysis/layers: Architectural layers via DAG topological sorting
- POST /analysis/centrality: Betweenness & PageRank bottleneck/god-class detection
- POST /analysis/metrics: Fan-in, Fan-out, Instability I = Ce / (Ca + Ce)
- POST /analysis/communities: Module clustering via Louvain community detection
- POST /analysis/impact: Blast radius impact analysis via Dijkstra/BFS
- POST /analysis/dead-code: Unused / dead code candidates
- POST /analysis/full: Comprehensive architectural health report
"""

from __future__ import annotations

from typing import Any

from analysis.facade import (
    build_graph_from_dict,
    build_graph_from_parse_result,
    default_architecture_analyzer,
)
from analysis.graph import DirectedGraph
from fastapi import APIRouter, Depends, HTTPException
from parsers.models import RepositoryParseResult
from pydantic import BaseModel, Field

from app.auth.dependencies import require_permission
from app.auth.models import Permission
from ingestion.job_store import default_job_store

router = APIRouter(
    prefix="/analysis",
    tags=["analysis"],
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)


# ── Request Models ────────────────────────────────────────────────────────────


class NodeInput(BaseModel):
    id: str = Field(..., description="Unique node identifier")
    name: str | None = Field(None, description="Human-readable node name")
    type: str = Field("class", description="Node type: file, class, method, function, package")
    path: str = Field("", description="File path relative to repo root")
    language: str = Field("", description="Language (python, java, etc.)")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Code metrics (loc, complexity, etc.)")
    annotations: list[str] = Field(default_factory=list, description="Annotations or decorators")
    is_external: bool = Field(False, description="True if unresolved external dependency")


class EdgeInput(BaseModel):
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field("calls", description="Dependency relationship: imports, calls, extends, implements, uses")
    weight: float = Field(1.0, description="Edge weight (frequency of calls or coupling strength)")


class GraphAnalysisRequest(BaseModel):
    job_id: str | None = Field(None, description="Job ID of a completed ingestion/parsing job")
    commit_hash: str | None = Field(None, description="Repo commit hash used for SQLite caching")
    nodes: list[NodeInput] = Field(default_factory=list, description="Explicit nodes list (if not using job_id)")
    edges: list[EdgeInput] = Field(default_factory=list, description="Explicit edges list (if not using job_id)")


class ImpactAnalysisRequest(GraphAnalysisRequest):
    target_node: str = Field(..., description="The node ID whose blast radius is being analyzed")
    weighted: bool = Field(False, description="If True, use Dijkstra with edge weights; if False, use BFS hop count")


# ── Response Models ───────────────────────────────────────────────────────────


class CycleEdge(BaseModel):
    source: str
    target: str


class CycleItem(BaseModel):
    cycle_id: str
    nodes: list[str]
    size: int
    edges: list[CycleEdge]
    is_self_loop: bool


class CyclesResponse(BaseModel):
    total_cycles: int
    cycles: list[CycleItem]


class LayerItem(BaseModel):
    layer_index: int
    nodes: list[str]


class LayersResponse(BaseModel):
    total_layers: int
    layers: list[LayerItem]
    node_to_layer: dict[str, int]
    topological_order: list[str]
    is_dag: bool
    condensed_scc_count: int


class CentralityNodeItem(BaseModel):
    node_id: str
    betweenness: float
    pagerank: float
    is_bottleneck: bool
    is_god_class: bool


class CentralityResponse(BaseModel):
    bottlenecks: list[str]
    god_classes: list[str]
    betweenness: dict[str, float]
    pagerank: dict[str, float]
    nodes: list[CentralityNodeItem]


class NodeCouplingItem(BaseModel):
    node_id: str
    fan_in: int
    fan_out: int
    instability: float


class PackageCouplingItem(BaseModel):
    package_name: str
    class_count: int
    ca: int
    ce: int
    instability: float
    abstractness: float
    distance: float


class CouplingResponse(BaseModel):
    mean_instability: float
    node_couplings: list[NodeCouplingItem]
    package_couplings: list[PackageCouplingItem]


class CommunityItem(BaseModel):
    cluster_id: int
    name: str
    size: int
    nodes: list[str]


class CommunitiesResponse(BaseModel):
    community_count: int
    modularity: float
    communities: list[CommunityItem]
    node_to_community: dict[str, int]


class ImpactedNodeItem(BaseModel):
    node_id: str
    depth: int
    distance: float
    is_direct: bool
    path: list[str]


class BlastRadiusResponse(BaseModel):
    target_node: str
    total_impacted_count: int
    blast_radius_pct: float
    direct_impact_count: int
    transitive_impact_count: int
    max_depth: int
    impacted_nodes: list[ImpactedNodeItem]


class DeadCodeItem(BaseModel):
    node_id: str
    name: str
    node_type: str
    path: str
    loc: int
    confidence: float
    reason: str


class DeadCodeResponse(BaseModel):
    total_candidates: int
    total_wasted_loc: int
    candidates: list[DeadCodeItem]


# ── Helper to resolve graph from request ──────────────────────────────────────


def _resolve_graph(request: GraphAnalysisRequest) -> tuple[DirectedGraph, str | None]:
    if request.job_id:
        job = default_job_store.get_job(request.job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{request.job_id}' not found.")
        if not job.result:
            raise HTTPException(status_code=400, detail=f"Job '{request.job_id}' has no parse results.")
        if isinstance(job.result, RepositoryParseResult):
            commit = request.commit_hash or (job.metadata.commit_hash if job.metadata else None)
            return build_graph_from_parse_result(job.result), commit
        elif isinstance(job.result, dict):
            commit = request.commit_hash or (job.metadata.commit_hash if job.metadata else None)
            return build_graph_from_dict(job.result), commit

    if not request.nodes and not request.edges:
        raise HTTPException(
            status_code=400,
            detail="Must provide either a valid 'job_id' or non-empty 'nodes' and 'edges' in the body.",
        )

    dict_data = {
        "nodes": [n.model_dump() for n in request.nodes],
        "edges": [e.model_dump() for e in request.edges],
    }
    return build_graph_from_dict(dict_data), request.commit_hash


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post("/cycles", response_model=CyclesResponse, summary="Detect circular dependencies via Tarjan's SCC")
async def get_cycles(request: GraphAnalysisRequest) -> Any:
    graph, commit = _resolve_graph(request)
    return default_architecture_analyzer.analyze_cycles(graph, commit_hash=commit)


@router.post("/layers", response_model=LayersResponse, summary="Topological sort over condensed DAG (layers)")
async def get_layers(request: GraphAnalysisRequest) -> Any:
    graph, commit = _resolve_graph(request)
    return default_architecture_analyzer.analyze_layers(graph, commit_hash=commit)


@router.post("/centrality", response_model=CentralityResponse, summary="Betweenness & PageRank centrality")
async def get_centrality(request: GraphAnalysisRequest) -> Any:
    graph, commit = _resolve_graph(request)
    return default_architecture_analyzer.analyze_centrality(graph, commit_hash=commit)


@router.post("/metrics", response_model=CouplingResponse, summary="Fan-in, fan-out, and instability metric")
async def get_coupling(request: GraphAnalysisRequest) -> Any:
    graph, commit = _resolve_graph(request)
    return default_architecture_analyzer.analyze_coupling(graph, commit_hash=commit)


@router.post("/communities", response_model=CommunitiesResponse, summary="Louvain community detection")
async def get_communities(request: GraphAnalysisRequest) -> Any:
    graph, commit = _resolve_graph(request)
    return default_architecture_analyzer.analyze_communities(graph, commit_hash=commit)


@router.post("/impact", response_model=BlastRadiusResponse, summary="Blast radius / impact analysis of node X")
async def get_impact(request: ImpactAnalysisRequest) -> Any:
    graph, commit = _resolve_graph(request)
    return default_architecture_analyzer.analyze_impact(
        graph,
        target_node=request.target_node,
        weighted=request.weighted,
        commit_hash=commit,
    )


@router.post("/dead-code", response_model=DeadCodeResponse, summary="Find dead code candidates with zero in-degree")
async def get_dead_code(request: GraphAnalysisRequest) -> Any:
    graph, commit = _resolve_graph(request)
    return default_architecture_analyzer.analyze_dead_code(graph, commit_hash=commit)


@router.post("/full", summary="Comprehensive architectural analysis suite")
async def get_full_analysis(request: GraphAnalysisRequest) -> Any:
    graph, commit = _resolve_graph(request)
    return default_architecture_analyzer.analyze_full(graph, commit_hash=commit)


# ── AI Feature Endpoints ───────────────────────────────────────────────────────


class ExplainMetricRequest(BaseModel):
    metric_name: str
    value: float
    analysis_id: str | None = None
    repo_context: dict[str, Any] = Field(default_factory=dict)


class TopologySummaryRequest(BaseModel):
    community_id: int
    node_ids: list[str]


class DashboardSummaryRequest(BaseModel):
    health_score: float
    grade: str
    smells_count: int = 0
    cycles_count: int = 0
    top_hotspots: list[str] = Field(default_factory=list)


class ChatQueryRequest(BaseModel):
    query: str
    analysis_id: str | None = None


class NLSearchRequest(BaseModel):
    query: str
    analysis_id: str | None = None


@router.post("/explain-metric", summary="Plain-English explanation of an architectural metric")
async def api_explain_metric(req: ExplainMetricRequest) -> Any:
    from ai.features import explain_metric

    res = await explain_metric(req.metric_name, req.value, req.repo_context)
    return res.model_dump()


@router.post("/topology-summary", summary="AI explanation and naming for community clusters")
async def api_topology_summary(req: TopologySummaryRequest) -> Any:
    from ai.features import summarize_topology

    res = await summarize_topology(req.community_id, req.node_ids)
    return res.model_dump()


@router.post("/dashboard-summary", summary="Executive status summary generated from computed metrics")
async def api_dashboard_summary(req: DashboardSummaryRequest) -> Any:
    from ai.features import generate_dashboard_summary

    res = await generate_dashboard_summary(
        req.health_score,
        req.grade,
        req.smells_count,
        req.cycles_count,
        req.top_hotspots,
    )
    return res.model_dump()


@router.post("/chat", summary="Ask ArchLens architectural assistant with verified grounding citations")
async def api_ask_archlens_chat(req: ChatQueryRequest) -> Any:
    from ai.features import ask_archlens_chat

    from app.services import analyzer_service

    analysis_res = None
    if req.analysis_id:
        analysis_res = analyzer_service.get_cached_result(req.analysis_id)

    res = await ask_archlens_chat(req.query, analysis_res)
    return res.model_dump()


@router.post("/nl-search", summary="Convert natural language query into validated deterministic filter")
async def api_nl_search(req: NLSearchRequest) -> Any:
    from ai.features import natural_language_search

    from app.services import analyzer_service

    available_nodes: set[str] = set()
    if req.analysis_id:
        res = analyzer_service.get_cached_result(req.analysis_id)
        if res and hasattr(res, "graph"):
            available_nodes = {n.id for n in res.graph.nodes}

    filter_res = await natural_language_search(req.query, available_nodes)
    return filter_res.model_dump()
