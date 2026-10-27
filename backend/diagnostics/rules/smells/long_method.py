"""Design smell rule: Long Method detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from diagnostics.models import Finding, Severity
from diagnostics.rules.base import DesignSmellRule

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


class LongMethodRule(DesignSmellRule):
    """Detects methods/functions with excessive length or cyclomatic complexity."""

    id = "SMELL-LONG-METHOD"
    name = "Long Method"
    severity = Severity.MEDIUM
    cwe = "CWE-1074: Class with Excessively Complex Logic"
    owasp = "A04:2021-Insecure Design"
    remediation = (
        "Extract Method refactoring: split long methods into smaller, well-named helper functions "
        "that encapsulate discrete processing steps."
    )

    def __init__(self, loc_threshold: int = 50, complexity_threshold: int = 10) -> None:
        super().__init__()
        self.loc_threshold = loc_threshold
        self.complexity_threshold = complexity_threshold

    def check_graph(self, graph: DirectedGraph) -> list[Finding]:
        findings: list[Finding] = []

        for nid, node in graph.nodes.items():
            if node.is_external:
                continue
            if node.node_type not in ("method", "function"):
                continue

            loc = int(node.metrics.get("loc", 0))
            cc = int(node.metrics.get("cyclomatic_complexity", 1))

            if loc > self.loc_threshold or cc > self.complexity_threshold:
                reasons = []
                if loc > self.loc_threshold:
                    reasons.append(f"lines of code ({loc} > {self.loc_threshold})")
                if cc > self.complexity_threshold:
                    reasons.append(f"cyclomatic complexity ({cc} > {self.complexity_threshold})")

                reason_str = " and ".join(reasons)
                findings.append(
                    self.create_finding(
                        message=(
                            f"{node.node_type.capitalize()} '{node.name or nid}' "
                            f"is overly long/complex: {reason_str}."
                        ),
                        file_path=node.path,
                        node_id=nid,
                        metadata={
                            "loc": loc,
                            "cyclomatic_complexity": cc,
                        },
                    )
                )

        return findings
