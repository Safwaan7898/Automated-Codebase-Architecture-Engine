"""Design smell rule: Deep Inheritance detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from diagnostics.models import Finding, Severity
from diagnostics.rules.base import DesignSmellRule

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


class DeepInheritanceRule(DesignSmellRule):
    """Detects class inheritance trees with excessive depth (DIT >= threshold)."""

    id = "SMELL-DEEP-INHERITANCE"
    name = "Deep Inheritance"
    severity = Severity.LOW
    cwe = "CWE-1074: Class with Excessively Complex Logic"
    owasp = "A04:2021-Insecure Design"
    remediation = (
        "Favor composition over inheritance. Replace deep class hierarchies with component interfaces, "
        "mixins, or delegation."
    )

    def __init__(self, depth_threshold: int = 4) -> None:
        super().__init__()
        self.depth_threshold = depth_threshold

    def check_graph(self, graph: DirectedGraph) -> list[Finding]:
        findings: list[Finding] = []

        # Build extends adjacency: child -> set of parents
        parents: dict[str, list[str]] = {}
        for (src, tgt), edge in graph.edges.items():
            if edge.edge_type in ("extends", "inherit"):
                parents.setdefault(src, []).append(tgt)

        # Memoized depth function
        memo_depth: dict[str, int] = {}
        visited_in_path: set[str] = set()

        def compute_depth(node_id: str) -> int:
            if node_id in memo_depth:
                return memo_depth[node_id]
            if node_id in visited_in_path:
                return 0  # Cycle safeguard

            visited_in_path.add(node_id)
            node_parents = parents.get(node_id, [])
            if not node_parents:
                d = 0
            else:
                d = 1 + max(compute_depth(p) for p in node_parents)
            visited_in_path.remove(node_id)

            memo_depth[node_id] = d
            return d

        for nid, node in graph.nodes.items():
            if node.is_external or node.node_type not in ("class", "interface"):
                continue

            depth = compute_depth(nid)
            if depth >= self.depth_threshold:
                findings.append(
                    self.create_finding(
                        message=(
                            f"Class '{node.name or nid}' has deep inheritance tree depth of {depth} "
                            f"(threshold is {self.depth_threshold})."
                        ),
                        file_path=node.path,
                        node_id=nid,
                        metadata={"depth": depth, "threshold": self.depth_threshold},
                    )
                )

        return findings
