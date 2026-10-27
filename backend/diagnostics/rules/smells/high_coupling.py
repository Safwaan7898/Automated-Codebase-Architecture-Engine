"""Design smell rule: High Coupling detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from diagnostics.models import Finding, Severity
from diagnostics.rules.base import DesignSmellRule

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


class HighCouplingRule(DesignSmellRule):
    """Detects nodes with excessive afferent/efferent coupling (fan-in + fan-out)."""

    id = "SMELL-HIGH-COUPLING"
    name = "High Coupling"
    severity = Severity.MEDIUM
    cwe = "CWE-1064: Highly Coupled Components"
    owasp = "A04:2021-Insecure Design"
    remediation = (
        "Reduce dependencies by applying the Facade pattern or Dependency Inversion. "
        "High efferent coupling (fan-out) makes changes fragile; high afferent coupling makes changes hard to deploy."
    )

    def __init__(self, fan_out_threshold: int = 8, total_coupling_threshold: int = 12) -> None:
        super().__init__()
        self.fan_out_threshold = fan_out_threshold
        self.total_coupling_threshold = total_coupling_threshold

    def check_graph(self, graph: DirectedGraph) -> list[Finding]:
        findings: list[Finding] = []

        for nid, node in graph.nodes.items():
            if node.is_external:
                continue

            fan_in = graph.in_degree(nid)
            fan_out = graph.out_degree(nid)
            total = fan_in + fan_out

            if fan_out > self.fan_out_threshold or total > self.total_coupling_threshold:
                findings.append(
                    self.create_finding(
                        message=(
                            f"Node '{node.name or nid}' has excessive coupling: "
                            f"fan-out={fan_out} (threshold {self.fan_out_threshold}), "
                            f"fan-in={fan_in}, total={total} (threshold {self.total_coupling_threshold})."
                        ),
                        file_path=node.path,
                        node_id=nid,
                        metadata={
                            "fan_in": fan_in,
                            "fan_out": fan_out,
                            "total_coupling": total,
                        },
                    )
                )

        return findings
