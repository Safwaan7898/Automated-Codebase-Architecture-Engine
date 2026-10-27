"""Design smell rule: Dead Code detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from analysis.dead_code import find_dead_code_candidates

from diagnostics.models import Finding, Severity
from diagnostics.rules.base import DesignSmellRule

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


class DeadCodeRule(DesignSmellRule):
    """Detects unused/unreferenced code components that are not recognized entry points."""

    id = "SMELL-DEAD-CODE"
    name = "Dead Code Candidate"
    severity = Severity.LOW
    cwe = "CWE-561: Dead Code"
    owasp = "A04:2021-Insecure Design"
    remediation = (
        "Safely delete unused methods, classes, and helper routines, or verify if missing call sites "
        "indicate incomplete feature implementations."
    )

    def check_graph(self, graph: DirectedGraph) -> list[Finding]:
        findings: list[Finding] = []
        analysis = find_dead_code_candidates(graph)

        for candidate in analysis.candidates:
            # Only flag high or medium confidence dead code (confidence >= 0.6)
            if candidate.confidence >= 0.6:
                findings.append(
                    self.create_finding(
                        message=(
                            f"{candidate.node_type.capitalize()} '{candidate.name}' "
                            f"appears unreferenced ({candidate.reason})."
                        ),
                        file_path=candidate.path,
                        node_id=candidate.node_id,
                        metadata={
                            "confidence": candidate.confidence,
                            "loc": candidate.loc,
                            "reason": candidate.reason,
                        },
                    )
                )

        return findings
