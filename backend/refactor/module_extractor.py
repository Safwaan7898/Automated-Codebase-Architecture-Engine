"""Extract module boundaries from Louvain community clusters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from analysis.community import compute_louvain_communities

from refactor.models import Effort, RefactorSuggestion, RefactorType

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


class ModuleBoundaryExtractor:
    """Discovers cohesive subgraphs via Louvain modularity clustering and proposes explicit module boundaries."""

    def __init__(self, min_cluster_size: int = 3) -> None:
        self.min_cluster_size = min_cluster_size

    def _infer_module_name(self, nodes: list[str]) -> str:
        """Infer a clean module name from common node path or identifier tokens."""
        # Extract common naming prefixes
        tokens: list[str] = []
        for nid in nodes:
            name_part = nid.split(".")[-1].split(":")[-1].split("#")[0]
            # Strip generic suffixes
            for suffix in ("Service", "Controller", "Repository", "Manager", "Handler", "Helper", "Dto"):
                if name_part.endswith(suffix) and len(name_part) > len(suffix):
                    name_part = name_part[: -len(suffix)]
                    break
            tokens.append(name_part.lower())

        if not tokens:
            return "DomainModule"

        # Most common token or first token
        from collections import Counter

        counts = Counter(tokens)
        most_common = counts.most_common(1)[0][0]
        return f"{most_common.capitalize()}Module"

    def generate_suggestions(self, graph: DirectedGraph) -> list[RefactorSuggestion]:
        """Generate module boundary extraction suggestions from Louvain communities."""
        suggestions: list[RefactorSuggestion] = []
        if graph.node_count < self.min_cluster_size:
            return suggestions

        comm = compute_louvain_communities(graph)
        idx = 0

        # Sort clusters deterministically by size desc, then cluster_id asc
        sorted_clusters = sorted(comm.clusters, key=lambda c: (-c.size, c.cluster_id))

        for cluster in sorted_clusters:
            # Filter internal nodes
            cluster_nodes = [nid for nid in cluster.nodes if not graph.nodes[nid].is_external]
            if len(cluster_nodes) < self.min_cluster_size:
                continue

            # Calculate internal edge count vs outgoing edges
            internal_edges = 0
            external_edges = 0
            node_set = set(cluster_nodes)

            for u in cluster_nodes:
                for v in graph.successors(u):
                    if v in node_set:
                        internal_edges += 1
                    else:
                        external_edges += 1

            # Only suggest if the cluster has meaningful internal cohesion
            if internal_edges == 0 and len(cluster_nodes) < 5:
                continue

            idx += 1
            mod_name = self._infer_module_name(cluster_nodes)
            cohesion_ratio = round(internal_edges / max(1, internal_edges + external_edges), 2)
            priority = 60.0 + min(20.0, len(cluster_nodes) * 2.0 + (cohesion_ratio * 10.0))

            title = f"Extract module '{mod_name}' ({len(cluster_nodes)} cohesive components)"
            rationale = (
                f"Louvain community detection identified {len(cluster_nodes)} tightly coupled components "
                f"forming cluster #{cluster.cluster_id} with internal cohesion ratio {cohesion_ratio}. "
                f"Encapsulating these behind an explicit module '{mod_name}' isolates internal implementation "
                f"details and reduces architectural coupling across the repository."
            )

            suggestions.append(
                RefactorSuggestion(
                    id=f"REFACTOR-MODULE-{idx:03d}",
                    type=RefactorType.EXTRACT_MODULE,
                    title=title,
                    rationale=rationale,
                    affected_nodes=sorted(cluster_nodes),
                    effort=Effort.M,
                    priority_score=priority,
                    action_details={
                        "module_name": mod_name,
                        "cluster_id": cluster.cluster_id,
                        "node_count": len(cluster_nodes),
                        "internal_edges": internal_edges,
                        "external_edges": external_edges,
                        "cohesion_ratio": cohesion_ratio,
                    },
                )
            )

        return suggestions
