"""Design smell rule: Cyclic Dependency detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from analysis.scc import detect_circular_dependencies

from diagnostics.models import Finding, Severity
from diagnostics.rules.base import DesignSmellRule

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


class CyclicDependencyRule(DesignSmellRule):
    """Detects circular architectural dependencies across components."""

    id = "SMELL-CYCLIC-DEPENDENCY"
    name = "Cyclic Dependency"
    severity = Severity.HIGH
    cwe = "CWE-1047: Modules with Circular Dependencies"
    owasp = "A04:2021-Insecure Design"
    remediation = (
        "Break the cycle using dependency inversion (introduce interfaces), event-driven messaging, "
        "or extract the shared dependency into a lower-tier utility module."
    )

    def check_graph(self, graph: DirectedGraph) -> list[Finding]:
        findings: list[Finding] = []
        cycles = detect_circular_dependencies(graph)

        for cycle in cycles:
            cycle_desc = " -> ".join(cycle.nodes[:5])
            if len(cycle.nodes) > 5:
                cycle_desc += f" -> ... ({len(cycle.nodes)} nodes total)"

            for nid in cycle.nodes:
                node = graph.nodes.get(nid)
                file_path = node.path if node else ""
                findings.append(
                    self.create_finding(
                        message=f"Node '{nid}' is entangled in a cyclic dependency loop: [{cycle_desc}].",
                        file_path=file_path,
                        node_id=nid,
                        metadata={
                            "cycle_size": cycle.size,
                            "cycle_nodes": cycle.nodes,
                        },
                    )
                )

        return findings
