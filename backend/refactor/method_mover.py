"""Move-method suggestions based on afferent/efferent coupling and Feature Envy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from refactor.models import Effort, RefactorSuggestion, RefactorType

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


class MethodMover:
    """Detects misplaced methods with excessive external coupling and suggests moving them to target classes."""

    def generate_suggestions(self, graph: DirectedGraph) -> list[RefactorSuggestion]:
        suggestions: list[RefactorSuggestion] = []

        # Map methods to their declaring class (via 'contains' edges or naming convention)
        method_owner: dict[str, str] = {}
        for (src, tgt), edge in graph.edges.items():
            if edge.edge_type == "contains":
                src_node = graph.nodes.get(src)
                tgt_node = graph.nodes.get(tgt)
                if (
                    src_node
                    and src_node.node_type in ("class", "interface")
                    and tgt_node
                    and tgt_node.node_type in ("method", "function")
                ):
                    method_owner[tgt] = src

        idx = 0
        sorted_nodes = sorted(graph.nodes.values(), key=lambda n: n.id)

        for node in sorted_nodes:
            if node.is_external or node.node_type not in ("method", "function"):
                continue

            owner_id = method_owner.get(node.id)
            if not owner_id and "#" in node.id:
                owner_id = node.id.split("#")[0]

            if not owner_id:
                continue

            owner_node = graph.nodes.get(owner_id)
            owner_name = owner_node.name if owner_node else owner_id.split(".")[-1]

            # Count calls/uses to external classes vs own class
            target_class_counts: dict[str, int] = {}
            own_calls = 0

            for succ in graph.successors(node.id):
                succ_node = graph.nodes.get(succ)
                if not succ_node:
                    continue

                succ_class = succ_node.id if succ_node.node_type in ("class", "interface") else method_owner.get(succ)
                if not succ_class and "#" in succ:
                    succ_class = succ.split("#")[0]

                call_weight = max(1, int(graph.edge_weight(node.id, succ, 1.0)))
                if succ_class:
                    if succ_class == owner_id:
                        own_calls += call_weight
                    else:
                        target_class_counts[succ_class] = target_class_counts.get(succ_class, 0) + call_weight

            # Check if any target class has >= 2 calls and exceeds own calls
            for target_class, count in sorted(target_class_counts.items(), key=lambda x: -x[1]):
                if count >= 2 and count > own_calls:
                    target_node = graph.nodes.get(target_class)
                    target_name = target_node.name if target_node else target_class.split(".")[-1]

                    idx += 1
                    method_display = node.name or node.id.split("#")[-1]
                    priority = 70.0 + min(15.0, (count - own_calls) * 3.0)

                    title = f"Move method '{method_display}' from '{owner_name}' to '{target_name}'"
                    rationale = (
                        f"Method '{method_display}' exhibits strong coupling to '{target_name}' ({count} accesses) "
                        f"compared to only {own_calls} calls to its declaring class '{owner_name}'. "
                        f"Moving this method to '{target_name}' adheres to Information Expert, encapsulates "
                        f"data with behavior, and eliminates unnecessary cross-class coupling."
                    )

                    suggestions.append(
                        RefactorSuggestion(
                            id=f"REFACTOR-MOVE-{idx:03d}",
                            type=RefactorType.MOVE_METHOD,
                            title=title,
                            rationale=rationale,
                            affected_nodes=[owner_id, target_class, node.id],
                            effort=Effort.S,
                            priority_score=priority,
                            action_details={
                                "method_id": node.id,
                                "method_name": method_display,
                                "source_class": owner_id,
                                "target_class": target_class,
                                "target_calls": count,
                                "own_calls": own_calls,
                            },
                        )
                    )
                    break

        return suggestions
