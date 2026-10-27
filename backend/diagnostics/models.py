"""Data models for the ArchLens rule and diagnostics engine.

Includes rule definitions, severity levels, CWE/OWASP mappings,
findings, and risk score models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class Severity(StrEnum):
    """Rule and vulnerability severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Severity weight mapping for risk scoring
SEVERITY_WEIGHTS: dict[Severity, float] = {
    Severity.CRITICAL: 40.0,
    Severity.HIGH: 25.0,
    Severity.MEDIUM: 12.0,
    Severity.LOW: 5.0,
}


class RuleCategory(StrEnum):
    """Categories of diagnostic rules."""

    SECURITY = "security"
    DESIGN_SMELL = "design_smell"
    DEPENDENCY = "dependency"


@dataclass
class Finding:
    """A single diagnostic issue detected by a rule."""

    rule_id: str
    rule_name: str
    severity: Severity
    category: RuleCategory | str
    message: str
    remediation: str
    cwe: str | None = None
    owasp: str | None = None
    file_path: str = ""
    line_number: int | None = None
    column_number: int | None = None
    node_id: str | None = None
    snippet: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        finding_id = f"{self.rule_id}-{Path(self.file_path).name if self.file_path else 'snippet'}-{self.line_number or 1}"
        return {
            "id": finding_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "title": self.message,
            "severity": str(self.severity),
            "category": str(self.category),
            "message": self.message,
            "remediation": self.remediation,
            "cwe": self.cwe,
            "owasp": self.owasp,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "node_id": self.node_id,
            "snippet": self.snippet,
            "code_snippet": self.snippet,
            "metadata": self.metadata,
        }


@dataclass
class NodeRiskScore:
    """Calculated risk score and breakdown for a graph node."""

    node_id: str
    risk_score: float  # 0.0 to 100.0
    level: str  # "critical", "high", "medium", "low", "clean"
    severity_score: float  # 0.0 to 100.0
    centrality_score: float  # 0.0 to 100.0
    complexity_score: float  # 0.0 to 100.0
    findings_count: int = 0
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "risk_score": round(self.risk_score, 2),
            "level": self.level,
            "severity_score": round(self.severity_score, 2),
            "centrality_score": round(self.centrality_score, 2),
            "complexity_score": round(self.complexity_score, 2),
            "findings_count": self.findings_count,
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class DiagnosticsReport:
    """Full diagnostics report across all rule types."""

    summary: dict[str, Any]
    findings: list[Finding]
    risk_scores: dict[str, NodeRiskScore] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
            "risk_scores": {nid: s.to_dict() for nid, s in self.risk_scores.items()},
        }
