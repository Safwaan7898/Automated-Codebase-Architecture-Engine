"""High-level facade coordinating all analysis algorithms and SQLite caching."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from analysis.cache import AnalysisCache, default_analysis_cache
from analysis.centrality import analyze_centrality
from analysis.community import compute_louvain_communities
from analysis.coupling import compute_coupling_metrics
from analysis.dead_code import find_dead_code_candidates
from analysis.graph import DirectedGraph
from analysis.impact import compute_blast_radius_bfs, compute_blast_radius_dijkstra
from analysis.scc import detect_circular_dependencies
from analysis.topo_sort import compute_architectural_layers

if TYPE_CHECKING:
    from parsers.models import RepositoryParseResult


def build_graph_from_parse_result(result: RepositoryParseResult) -> DirectedGraph:
    """Convert RepositoryParseResult (nodes and edges) into a DirectedGraph."""
    dg = DirectedGraph()

    for node in result.nodes:
        metrics_dict = {
            "loc": node.metrics.loc,
            "cyclomatic_complexity": node.metrics.cyclomatic_complexity,
            "num_methods": node.metrics.num_methods,
            "num_fields": node.metrics.num_fields,
            "num_parameters": node.metrics.num_parameters,
            "depth": node.metrics.depth,
        }
        dg.add_node(
            node_id=node.id,
            name=node.name,
            node_type=str(node.type),
            path=node.path,
            language=node.language,
            metrics=metrics_dict,
            annotations=node.annotations,
            is_external=node.is_external,
            **node.extra,
        )

    for edge in result.edges:
        dg.add_edge(
            source=edge.source,
            target=edge.target,
            edge_type=str(edge.type),
            weight=getattr(edge, "weight", 1.0),
        )

    return dg


def build_graph_from_dict(graph_data: dict[str, Any]) -> DirectedGraph:
    """Build DirectedGraph from a raw dictionary with 'nodes' and 'edges' lists."""
    dg = DirectedGraph()
    for n in graph_data.get("nodes", []):
        node_metrics = dict(n.get("metrics", {}))
        for key in ("loc", "cyclomatic_complexity", "mean_complexity", "max_complexity"):
            if key in n:
                node_metrics[key] = n[key]

        nid = n.get("id") or n.get("name")
        if nid:
            dg.add_node(
                node_id=str(nid),
                name=n.get("name", str(nid)),
                node_type=n.get("type", n.get("node_type", "class")),
                path=n.get("path", ""),
                language=n.get("language", ""),
                metrics=node_metrics,
                annotations=n.get("annotations", []),
                is_external=n.get("is_external", False),
            )

    for e in graph_data.get("edges", []):
        src = e.get("source")
        tgt = e.get("target")
        if src and tgt:
            dg.add_edge(
                source=str(src),
                target=str(tgt),
                edge_type=e.get("type", e.get("edge_type", "calls")),
                weight=float(e.get("weight", 1.0)),
            )

    return dg


class ArchitectureAnalyzer:
    """Facade orchestrating graph analysis algorithms with SQLite result caching."""

    def __init__(self, cache: AnalysisCache | None = None) -> None:
        self.cache = cache or default_analysis_cache

    def analyze_cycles(self, graph: DirectedGraph, commit_hash: str | None = None) -> dict[str, Any]:
        if commit_hash:
            cached = self.cache.get(commit_hash, "cycles")
            if cached:
                return cached

        cycles = detect_circular_dependencies(graph)
        result = {
            "total_cycles": len(cycles),
            "cycles": [c.to_dict() for c in cycles],
        }
        if commit_hash:
            self.cache.set(commit_hash, "cycles", result)
        return result

    def analyze_layers(self, graph: DirectedGraph, commit_hash: str | None = None) -> dict[str, Any]:
        if commit_hash:
            cached = self.cache.get(commit_hash, "layers")
            if cached:
                return cached

        layers = compute_architectural_layers(graph)
        result = layers.to_dict()
        if commit_hash:
            self.cache.set(commit_hash, "layers", result)
        return result

    def analyze_centrality(self, graph: DirectedGraph, commit_hash: str | None = None) -> dict[str, Any]:
        if commit_hash:
            cached = self.cache.get(commit_hash, "centrality")
            if cached:
                return cached

        cent = analyze_centrality(graph)
        result = cent.to_dict()
        if commit_hash:
            self.cache.set(commit_hash, "centrality", result)
        return result

    def analyze_coupling(self, graph: DirectedGraph, commit_hash: str | None = None) -> dict[str, Any]:
        if commit_hash:
            cached = self.cache.get(commit_hash, "coupling")
            if cached:
                return cached

        cpl = compute_coupling_metrics(graph)
        result = cpl.to_dict()
        if commit_hash:
            self.cache.set(commit_hash, "coupling", result)
        return result

    def analyze_communities(self, graph: DirectedGraph, commit_hash: str | None = None) -> dict[str, Any]:
        if commit_hash:
            cached = self.cache.get(commit_hash, "communities")
            if cached:
                return cached

        comm = compute_louvain_communities(graph)
        result = comm.to_dict()
        if commit_hash:
            self.cache.set(commit_hash, "communities", result)
        return result

    def analyze_impact(
        self,
        graph: DirectedGraph,
        target_node: str,
        weighted: bool = False,
        commit_hash: str | None = None,
    ) -> dict[str, Any]:
        cache_key = f"impact_{target_node}_{weighted}"
        if commit_hash:
            cached = self.cache.get(commit_hash, cache_key)
            if cached:
                return cached

        if weighted:
            blast = compute_blast_radius_dijkstra(graph, target_node)
        else:
            blast = compute_blast_radius_bfs(graph, target_node)

        result = blast.to_dict()
        if commit_hash:
            self.cache.set(commit_hash, cache_key, result)
        return result

    def analyze_dead_code(self, graph: DirectedGraph, commit_hash: str | None = None) -> dict[str, Any]:
        if commit_hash:
            cached = self.cache.get(commit_hash, "dead_code")
            if cached:
                return cached

        dc = find_dead_code_candidates(graph)
        result = dc.to_dict()
        if commit_hash:
            self.cache.set(commit_hash, "dead_code", result)
        return result

    def analyze_full(self, graph: DirectedGraph, commit_hash: str | None = None) -> dict[str, Any]:
        """Run all algorithms and return an aggregated architectural report."""
        if commit_hash:
            cached = self.cache.get(commit_hash, "full")
            if cached:
                return cached

        cycles = self.analyze_cycles(graph, commit_hash=None)
        layers = self.analyze_layers(graph, commit_hash=None)
        centrality = self.analyze_centrality(graph, commit_hash=None)
        coupling = self.analyze_coupling(graph, commit_hash=None)
        communities = self.analyze_communities(graph, commit_hash=None)
        dead_code = self.analyze_dead_code(graph, commit_hash=None)

        result = {
            "summary": {
                "node_count": graph.node_count,
                "edge_count": graph.edge_count,
                "cycle_count": cycles["total_cycles"],
                "layer_count": layers["total_layers"],
                "bottleneck_count": len(centrality["bottlenecks"]),
                "god_class_count": len(centrality["god_classes"]),
                "community_count": communities["community_count"],
                "dead_code_candidates": dead_code["total_candidates"],
            },
            "cycles": cycles,
            "layers": layers,
            "centrality": centrality,
            "coupling": coupling,
            "communities": communities,
            "dead_code": dead_code,
        }

        if commit_hash:
            self.cache.set(commit_hash, "full", result)
        return result


# Default global instance
default_architecture_analyzer = ArchitectureAnalyzer()
