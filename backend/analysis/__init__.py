"""ArchLens architectural analysis engine using custom graph algorithms."""

from __future__ import annotations

from analysis.cache import AnalysisCache, default_analysis_cache
from analysis.centrality import (
    CentralityAnalysis,
    NodeCentralityResult,
    analyze_centrality,
    compute_betweenness_centrality,
    compute_pagerank,
)
from analysis.community import (
    CommunityAnalysis,
    CommunityCluster,
    compute_louvain_communities,
)
from analysis.coupling import (
    CouplingAnalysis,
    NodeCoupling,
    PackageCoupling,
    compute_coupling_metrics,
)
from analysis.dead_code import (
    DeadCodeAnalysis,
    DeadCodeCandidate,
    find_dead_code_candidates,
)
from analysis.facade import (
    ArchitectureAnalyzer,
    build_graph_from_dict,
    build_graph_from_parse_result,
    default_architecture_analyzer,
)
from analysis.graph import DirectedGraph, GraphEdge, GraphNode
from analysis.impact import (
    BlastRadiusResult,
    ImpactedNode,
    compute_blast_radius_bfs,
    compute_blast_radius_dijkstra,
)
from analysis.scc import (
    CircularDependency,
    detect_circular_dependencies,
    find_strongly_connected_components,
)
from analysis.topo_sort import (
    ArchitecturalLayers,
    compute_architectural_layers,
    condense_graph,
)

__all__ = [
    "AnalysisCache",
    "ArchitecturalLayers",
    "ArchitectureAnalyzer",
    "BlastRadiusResult",
    "CentralityAnalysis",
    "CircularDependency",
    "CommunityAnalysis",
    "CommunityCluster",
    "CouplingAnalysis",
    "DeadCodeAnalysis",
    "DeadCodeCandidate",
    "DirectedGraph",
    "GraphEdge",
    "GraphNode",
    "ImpactedNode",
    "NodeCentralityResult",
    "NodeCoupling",
    "PackageCoupling",
    "analyze_centrality",
    "build_graph_from_dict",
    "build_graph_from_parse_result",
    "compute_architectural_layers",
    "compute_betweenness_centrality",
    "compute_blast_radius_bfs",
    "compute_blast_radius_dijkstra",
    "compute_coupling_metrics",
    "compute_louvain_communities",
    "compute_pagerank",
    "condense_graph",
    "default_analysis_cache",
    "default_architecture_analyzer",
    "detect_circular_dependencies",
    "find_dead_code_candidates",
    "find_strongly_connected_components",
]
