"""Design smell rule: Feature Envy detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from diagnostics.models import Finding, Severity
from diagnostics.rules.base import DesignSmellRule

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


class FeatureEnvyRule(DesignSmellRule):
    """Detects methods that access external classes significantly more than their host class."""

    id = "SMELL-FEATURE-ENVY"
    name = "Feature Envy"
    severity = Severity.MEDIUM
    cwe = "CWE-1065: Runtime Resource Management"
    owasp = "A04:2021-Insecure Design"
    remediation = (
        "Move Method refactoring: relocate this method to the target class it interacts with most frequently, "
        "or pass needed data as method arguments."
    )

    def check_graph(self, graph: DirectedGraph) -> list[Finding]:
        findings: list[Finding] = []

        # Find owner class for each method:
        # Check 'contains' edges (class -> method) or naming convention "class_id#method_name"
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

        for nid, node in graph.nodes.items():
            if node.node_type not in ("method", "function") or node.is_external:
                continue

            owner_id = method_owner.get(nid)
            if not owner_id and "#" in nid:
                owner_id = nid.split("#")[0]

            # Count calls and uses to target classes
            target_class_counts: dict[str, int] = {}
            own_calls = 0

            for succ in graph.successors(nid):
                succ_node = graph.nodes.get(succ)
                if not succ_node:
                    continue

                succ_class = succ_node.id if succ_node.node_type in ("class", "interface") else method_owner.get(succ)
                if not succ_class and "#" in succ:
                    succ_class = succ.split("#")[0]

                if succ_class:
                    if owner_id and succ_class == owner_id:
                        own_calls += 1
                    else:
                        target_class_counts[succ_class] = target_class_counts.get(succ_class, 0) + 1

            # Check if any target class has >= 3 calls and more than twice own_calls
            for target_class, count in target_class_counts.items():
                if count >= 3 and count > (2 * own_calls):
                    target_name = graph.nodes.get(target_class, None)
                    t_display = target_name.name if target_name else target_class
                    findings.append(
                        self.create_finding(
                            message=(
                                f"Method '{node.name or nid}' exhibits Feature Envy: calls target class '{t_display}' "
                                f"{count} times (compared to {own_calls} calls to its own class)."
                            ),
                            file_path=node.path,
                            node_id=nid,
                            metadata={
                                "target_class": target_class,
                                "target_calls": count,
                                "own_calls": own_calls,
                            },
                        )
                    )
                    break

        return findings
