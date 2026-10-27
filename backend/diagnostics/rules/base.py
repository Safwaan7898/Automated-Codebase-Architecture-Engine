"""Base classes for diagnostic rules.

Every rule is a class with:
- id
- name
- severity (critical | high | medium | low)
- cwe mapping (e.g. CWE-89)
- owasp mapping (e.g. A03:2021-Injection)
- category (security | design_smell | dependency)
- remediation hint
- detection logic
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from diagnostics.models import Finding, RuleCategory, Severity

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


class BaseRule(ABC):
    """Abstract base class for all diagnostic rules."""

    id: str
    name: str
    severity: Severity
    cwe: str | None = None
    owasp: str | None = None
    category: RuleCategory = RuleCategory.SECURITY
    remediation: str = ""

    def __init__(self) -> None:
        if not hasattr(self, "id") or not self.id:
            raise ValueError(f"Rule {self.__class__.__name__} must define a non-empty 'id'")
        if not hasattr(self, "severity"):
            raise ValueError(f"Rule {self.__class__.__name__} must define 'severity'")

    def create_finding(
        self,
        message: str,
        file_path: str = "",
        line_number: int | None = None,
        column_number: int | None = None,
        node_id: str | None = None,
        snippet: str | None = None,
        remediation: str | None = None,
        metadata: dict[str, Any] | None = None,
        cwe: str | None = None,
        owasp: str | None = None,
    ) -> Finding:
        """Helper to construct a Finding matching this rule's metadata."""
        return Finding(
            rule_id=self.id,
            rule_name=self.name,
            severity=self.severity,
            category=self.category,
            message=message,
            remediation=remediation or self.remediation,
            cwe=cwe or self.cwe,
            owasp=owasp or self.owasp,
            file_path=file_path,
            line_number=line_number,
            column_number=column_number,
            node_id=node_id,
            snippet=snippet,
            metadata=metadata or {},
        )


class SecurityRule(BaseRule):
    """Base class for AST-based security rules."""

    category: RuleCategory = RuleCategory.SECURITY

    @abstractmethod
    def check_file(self, file_path: Path, content: str, language: str) -> list[Finding]:
        """Inspect file content via AST analysis and return security findings."""


class DesignSmellRule(BaseRule):
    """Base class for graph and metric-based architectural smell rules."""

    category: RuleCategory = RuleCategory.DESIGN_SMELL

    @abstractmethod
    def check_graph(self, graph: DirectedGraph) -> list[Finding]:
        """Inspect graph structure and node metrics, returning design smell findings."""


class DependencyRule(BaseRule):
    """Base class for dependency and known CVE rules."""

    category: RuleCategory = RuleCategory.DEPENDENCY

    @abstractmethod
    def check_dependency(
        self,
        package_name: str,
        version: str,
        ecosystem: str,
        manifest_path: str,
        cve_data: list[dict[str, Any]],
    ) -> list[Finding]:
        """Evaluate known CVEs for a specific package dependency."""
