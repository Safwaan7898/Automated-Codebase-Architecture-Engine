"""Cycle breaker: minimal-weight Feedback Arc Set (FAS) heuristic with interface suggestions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from analysis.scc import detect_circular_dependencies

from refactor.models import Effort, RefactorSuggestion, RefactorType

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


class CycleBreaker:
    """Identifies minimal-weight edges in cycles and recommends interface-based dependency inversion."""

    def find_minimal_feedback_arc(
        self,
        cycle_edges: list[tuple[str, str]],
        graph: DirectedGraph,
    ) -> tuple[str, str, float]:
        """Pick the edge with the lowest weight in the cycle to minimize refactoring friction.

        Deterministic tie-breaking: edge weight -> degree sum -> alphanumeric source/target.
        """
        best_edge = cycle_edges[0]
        min_weight = float("inf")
        min_degree_sum = float("inf")

        for u, v in cycle_edges:
            edge = graph.edges.get((u, v))
            weight = edge.weight if edge else 1.0
            degree_sum = graph.out_degree(u) + graph.in_degree(v)

            # Heuristic: lowest weight first, then lowest degree sum (least entangled)
            if (
                (weight < min_weight)
                or (weight == min_weight and degree_sum < min_degree_sum)
                or (weight == min_weight and degree_sum == min_degree_sum and (u, v) < best_edge)
            ):
                min_weight = weight
                min_degree_sum = degree_sum
                best_edge = (u, v)

        return best_edge[0], best_edge[1], min_weight

    def generate_suggestions(self, graph: DirectedGraph) -> list[RefactorSuggestion]:
        """Generate cycle breaking refactoring suggestions for all detected architectural cycles."""
        suggestions: list[RefactorSuggestion] = []
        cycles = detect_circular_dependencies(graph)

        for idx, cycle in enumerate(cycles, 1):
            if cycle.size < 2 or not cycle.edges:
                continue

            u, v, weight = self.find_minimal_feedback_arc(cycle.edges, graph)
            u_node = graph.nodes.get(u)
            v_node = graph.nodes.get(v)

            u_name = u_node.name if u_node and u_node.name else u.split(".")[-1].split(":")[-1]
            v_name = v_node.name if v_node and v_node.name else v.split(".")[-1].split(":")[-1]

            interface_name = f"I{v_name}" if not v_name.startswith("I") else f"{v_name}Contract"

            effort = Effort.S if cycle.size == 2 else (Effort.M if cycle.size <= 5 else Effort.L)
            priority = 90.0 + min(10.0, cycle.size * 1.5)

            path_str = " -> ".join(cycle.nodes[:4])
            if len(cycle.nodes) > 4:
                path_str += f" -> ... ({cycle.size} nodes)"

            title = f"Break cycle between '{u_name}' and '{v_name}' via interface '{interface_name}'"
            rationale = (
                f"A circular dependency was detected across {cycle.size} components [{path_str}]. "
                f"The minimal-weight feedback arc is ({u_name} -> {v_name}) with weight {weight:.1f}. "
                f"Introducing interface '{interface_name}' allows '{u_name}' to depend on an abstraction, "
                f"inverting the dependency so '{v_name}' implements '{interface_name}', breaking the cycle."
            )

            suggestions.append(
                RefactorSuggestion(
                    id=f"REFACTOR-CYCLE-{idx:03d}",
                    type=RefactorType.BREAK_CYCLE,
                    title=title,
                    rationale=rationale,
                    affected_nodes=list(cycle.nodes),
                    effort=effort,
                    priority_score=priority,
                    action_details={
                        "cycle_id": cycle.cycle_id,
                        "cycle_size": cycle.size,
                        "feedback_arc": {"source": u, "target": v, "weight": weight},
                        "interface_name": interface_name,
                        "consumer_node": u,
                        "provider_node": v,
                    },
                )
            )

        return suggestions
