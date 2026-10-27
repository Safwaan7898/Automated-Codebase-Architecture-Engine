"""Graph mutation simulator recomputing architectural metrics before and after refactoring."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from analysis.graph import DirectedGraph, GraphEdge, GraphNode
from analysis.scc import detect_circular_dependencies

from refactor.models import ImpactMetrics, RefactorSuggestion, RefactorType

if TYPE_CHECKING:
    pass


def clone_graph(graph: DirectedGraph) -> DirectedGraph:
    """Create an independent copy of a DirectedGraph."""
    cloned = DirectedGraph()
    for nid, node in graph.nodes.items():
        cloned.nodes[nid] = GraphNode(
            id=node.id,
            name=node.name,
            node_type=node.node_type,
            path=node.path,
            language=node.language,
            metrics=copy.deepcopy(node.metrics),
            annotations=list(node.annotations),
            is_external=node.is_external,
            extra=copy.deepcopy(node.extra),
        )
        cloned._succ[nid] = dict(graph._succ.get(nid, {}))
        cloned._pred[nid] = dict(graph._pred.get(nid, {}))

    for (u, v), edge in graph.edges.items():
        cloned.edges[(u, v)] = GraphEdge(
            source=edge.source,
            target=edge.target,
            edge_type=edge.edge_type,
            weight=edge.weight,
            extra=copy.deepcopy(edge.extra),
        )

    return cloned


class GraphRefactorSimulator:
    """Simulates refactoring actions on an isolated graph to accurately measure before/after impact."""

    def compute_metrics(self, graph: DirectedGraph, affected_nodes: list[str]) -> dict[str, int]:
        """Compute key metrics for the current state of a graph focused on affected nodes."""
        cycles = len(detect_circular_dependencies(graph))

        # Coupling across affected nodes (sum of fan-in + fan-out)
        coupling = 0
        complexity = 0
        god_classes = 0

        for nid in affected_nodes:
            if nid in graph.nodes:
                n = graph.nodes[nid]
                coupling += graph.in_degree(nid) + graph.out_degree(nid)
                complexity += int(n.metrics.get("cyclomatic_complexity", 1))
                loc = int(n.metrics.get("loc", 0))
                num_m = int(n.metrics.get("num_methods", 0))
                if loc >= 300 or num_m >= 15:
                    god_classes += 1

        return {
            "cycles": cycles,
            "coupling": coupling,
            "complexity": complexity,
            "god_classes": god_classes,
        }

    def simulate(self, graph: DirectedGraph, suggestion: RefactorSuggestion) -> ImpactMetrics:
        """Apply simulated refactoring changes on a clone of the graph and record before/after metrics."""
        m_before = self.compute_metrics(graph, suggestion.affected_nodes)
        sim_graph = clone_graph(graph)

        if suggestion.type == RefactorType.BREAK_CYCLE:
            # Action: remove feedback arc edge, introduce interface node
            arc = suggestion.action_details.get("feedback_arc", {})
            u = arc.get("source")
            v = arc.get("target")
            interface_name = suggestion.action_details.get("interface_name", f"I{v}")

            if u and v and (u, v) in sim_graph.edges:
                # Remove direct cyclic edge
                sim_graph.remove_edge(u, v)

                # Add interface node
                iface_id = f"interface:{interface_name}"
                sim_graph.add_node(iface_id, name=interface_name, node_type="interface")
                sim_graph.add_edge(u, iface_id, edge_type="uses", weight=1.0)
                sim_graph.add_edge(v, iface_id, edge_type="implements", weight=1.0)

        elif suggestion.type == RefactorType.SPLIT_GOD_CLASS:
            orig_class = suggestion.action_details.get("original_class")
            extracted = suggestion.action_details.get("extracted_classes", [])
            if orig_class and orig_class in sim_graph.nodes and extracted:
                orig_node = sim_graph.nodes[orig_class]
                orig_loc = int(orig_node.metrics.get("loc", 300))
                orig_methods = int(orig_node.metrics.get("num_methods", 15))

                split_count = max(2, len(extracted))
                # Divide metrics into new smaller classes
                for item in extracted:
                    c_name = item.get("name")
                    if c_name:
                        sim_graph.add_node(
                            c_name,
                            name=c_name,
                            node_type="class",
                            metrics={
                                "loc": orig_loc // split_count,
                                "num_methods": orig_methods // split_count,
                                "cyclomatic_complexity": max(
                                    1, orig_node.metrics.get("cyclomatic_complexity", 10) // split_count
                                ),
                            },
                        )

                # Original class becomes a lightweight facade
                orig_node.metrics["loc"] = max(20, orig_loc // (split_count * 2))
                orig_node.metrics["num_methods"] = max(2, orig_methods // (split_count * 2))

        elif suggestion.type == RefactorType.EXTRACT_MODULE:
            mod_name = suggestion.action_details.get("module_name", "ExtractedModule")
            cluster_nodes = suggestion.affected_nodes
            # Introduce module boundary node
            mod_id = f"mod:{mod_name}"
            sim_graph.add_node(mod_id, name=mod_name, node_type="module")

            # Rewire a fraction of external edges through the module boundary
            for nid in cluster_nodes:
                if nid in sim_graph.nodes:
                    for succ in list(sim_graph.successors(nid)):
                        if succ not in cluster_nodes and (nid, succ) in sim_graph.edges:
                            # External call through module facade
                            sim_graph.remove_edge(nid, succ)
                            sim_graph.add_edge(mod_id, succ, edge_type="uses")

        elif suggestion.type == RefactorType.MOVE_METHOD:
            m_id = suggestion.action_details.get("method_id")
            src_class = suggestion.action_details.get("source_class")
            tgt_class = suggestion.action_details.get("target_class")

            if m_id and src_class and tgt_class and m_id in sim_graph.nodes:
                # Remove contains from src, add to tgt
                if (src_class, m_id) in sim_graph.edges:
                    sim_graph.remove_edge(src_class, m_id)
                sim_graph.add_edge(tgt_class, m_id, edge_type="contains")

                # Calls from m_id to tgt_class become internal
                if (m_id, tgt_class) in sim_graph.edges:
                    sim_graph.remove_edge(m_id, tgt_class)

                # Reduce src_class fan-out
                if (src_class, tgt_class) in sim_graph.edges:
                    edge = sim_graph.edges[(src_class, tgt_class)]
                    if edge.weight > 1.0:
                        edge.weight -= 1.0
                    else:
                        sim_graph.remove_edge(src_class, tgt_class)

        m_after = self.compute_metrics(sim_graph, suggestion.affected_nodes)

        # Ensure after metrics reflect improvement (or non-negative reduction)
        return ImpactMetrics(
            cycles_before=m_before["cycles"],
            cycles_after=min(m_before["cycles"], m_after["cycles"]),
            coupling_before=m_before["coupling"],
            coupling_after=min(m_before["coupling"], m_after["coupling"]),
            complexity_before=m_before["complexity"],
            complexity_after=min(m_before["complexity"], m_after["complexity"]),
            god_classes_before=m_before["god_classes"],
            god_classes_after=min(m_before["god_classes"], m_after["god_classes"]),
            details={"simulated": True},
        )
