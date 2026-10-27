"""Design smell rule: God Class detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from diagnostics.models import Finding, Severity
from diagnostics.rules.base import DesignSmellRule

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


class GodClassRule(DesignSmellRule):
    """Detects God Classes that concentrate too much system logic and responsibility."""

    id = "SMELL-GOD-CLASS"
    name = "God Class"
    severity = Severity.HIGH
    cwe = "CWE-1061: Insufficient Encapsulation"
    owasp = "A04:2021-Insecure Design"
    remediation = (
        "Decompose this class into smaller, cohesive components following the Single Responsibility Principle. "
        "Extract distinct behavioral domains into delegate classes or domain services."
    )

    def __init__(self, loc_threshold: int = 300, method_threshold: int = 15) -> None:
        super().__init__()
        self.loc_threshold = loc_threshold
        self.method_threshold = method_threshold

    def check_graph(self, graph: DirectedGraph) -> list[Finding]:
        findings: list[Finding] = []

        for nid, node in graph.nodes.items():
            if node.is_external:
                continue
            if node.node_type not in ("class", "interface"):
                continue

            loc = int(node.metrics.get("loc", 0))
            num_methods = int(node.metrics.get("num_methods", 0))
            num_fields = int(node.metrics.get("num_fields", 0))

            is_god = False
            reasons = []

            if loc > self.loc_threshold:
                is_god = True
                reasons.append(f"lines of code ({loc} > {self.loc_threshold})")
            if num_methods > self.method_threshold:
                is_god = True
                reasons.append(f"method count ({num_methods} > {self.method_threshold})")

            # Also check if fan-out and fan-in are both huge
            fan_in = graph.in_degree(nid)
            fan_out = graph.out_degree(nid)
            if fan_in > 10 and fan_out > 10:
                is_god = True
                reasons.append(f"high connectivity (fan-in={fan_in}, fan-out={fan_out})")

            if is_god:
                reason_str = ", ".join(reasons)
                findings.append(
                    self.create_finding(
                        message=f"Class '{node.name or nid}' exhibits God Class smell: excessive {reason_str}.",
                        file_path=node.path,
                        node_id=nid,
                        metadata={
                            "loc": loc,
                            "num_methods": num_methods,
                            "num_fields": num_fields,
                            "fan_in": fan_in,
                            "fan_out": fan_out,
                        },
                    )
                )

        return findings
