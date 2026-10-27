"""Diagnostics rule engine and rule registry.

Orchestrates:
1. AST-based security analysis across source files.
2. Graph and metric-based architectural smell analysis.
3. Dependency CVE queries via OSV.dev.
4. Multidimensional per-node risk scoring (0-100).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from analysis.centrality import compute_betweenness_centrality, compute_pagerank

from diagnostics.dependencies.osv_client import OSVClient, default_osv_client
from diagnostics.dependencies.parsers import (
    Dependency,
    parse_build_gradle,
    parse_pom_xml,
    parse_requirements_txt,
)
from diagnostics.dependencies.rules import VulnerableDependencyRule
from diagnostics.models import (
    DiagnosticsReport,
    Finding,
    NodeRiskScore,
    RuleCategory,
    Severity,
)
from diagnostics.rules.base import (
    BaseRule,
    DependencyRule,
    DesignSmellRule,
    SecurityRule,
)
from diagnostics.rules.security import ALL_SECURITY_RULES
from diagnostics.rules.smells import ALL_DESIGN_SMELL_RULES
from diagnostics.scoring import NodeRiskScorer, default_risk_scorer

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph

logger = logging.getLogger(__name__)


class RuleRegistry:
    """Registry maintaining active diagnostic rules."""

    def __init__(self, load_defaults: bool = True) -> None:
        self._rules: dict[str, BaseRule] = {}
        if load_defaults:
            self._register_defaults()

    def _register_defaults(self) -> None:
        for rule_cls in ALL_SECURITY_RULES:
            self.register(rule_cls())
        for smell_cls in ALL_DESIGN_SMELL_RULES:
            self.register(smell_cls())
        self.register(VulnerableDependencyRule())

    def register(self, rule: BaseRule) -> None:
        """Register a rule instance."""
        self._rules[rule.id] = rule

    def get_rule(self, rule_id: str) -> BaseRule | None:
        """Retrieve a rule by its unique identifier."""
        return self._rules.get(rule_id)

    def security_rules(self) -> list[SecurityRule]:
        """Return all registered security rules."""
        return [r for r in self._rules.values() if isinstance(r, SecurityRule)]

    def design_smell_rules(self) -> list[DesignSmellRule]:
        """Return all registered design smell rules."""
        return [r for r in self._rules.values() if isinstance(r, DesignSmellRule)]

    def dependency_rules(self) -> list[DependencyRule]:
        """Return all registered dependency rules."""
        return [r for r in self._rules.values() if isinstance(r, DependencyRule)]

    def list_rules(self) -> list[dict[str, Any]]:
        """Return summary of all registered rules."""
        return [
            {
                "id": r.id,
                "name": r.name,
                "severity": str(r.severity),
                "category": str(r.category),
                "cwe": r.cwe,
                "owasp": r.owasp,
                "remediation": r.remediation,
            }
            for r in self._rules.values()
        ]


class DiagnosticsEngine:
    """Central engine executing rules, dependency scans, and risk scoring."""

    def __init__(
        self,
        registry: RuleRegistry | None = None,
        osv_client: OSVClient | None = None,
        scorer: NodeRiskScorer | None = None,
    ) -> None:
        self.registry = registry or RuleRegistry()
        self.osv_client = osv_client or default_osv_client
        self.scorer = scorer or default_risk_scorer

    def analyze_source_code(
        self,
        content: str,
        language: str,
        file_path: str = "in_memory",
    ) -> list[Finding]:
        """Run all security rules on an isolated source code string."""
        path = Path(file_path)
        findings: list[Finding] = []
        lang_norm = language.lower().strip()
        for rule in self.registry.security_rules():
            try:
                rule_findings = rule.check_file(path, content, lang_norm)
                findings.extend(rule_findings)
            except Exception as exc:
                logger.error("Error executing rule %s on %s: %s", rule.id, file_path, exc)
        return findings

    def analyze_graph(self, graph: DirectedGraph) -> list[Finding]:
        """Run all design smell rules on an architectural graph."""
        findings: list[Finding] = []
        for smell_rule in self.registry.design_smell_rules():
            try:
                smell_findings = smell_rule.check_graph(graph)
                findings.extend(smell_findings)
            except Exception as exc:
                logger.error("Error executing smell rule %s: %s", smell_rule.id, exc)
        return findings

    def analyze_dependencies_content(
        self,
        content: str,
        manifest_type: str,  # "requirements.txt", "pom.xml", "build.gradle"
        manifest_path: str = "",
        query_osv: bool = True,
    ) -> list[Finding]:
        """Parse dependencies from manifest content and query OSV.dev for CVEs."""
        m_path = manifest_path or manifest_type
        deps: list[Dependency] = []

        if manifest_type.endswith("requirements.txt"):
            deps = parse_requirements_txt(content, m_path)
        elif manifest_type.endswith("pom.xml"):
            deps = parse_pom_xml(content, m_path)
        elif manifest_type.endswith("build.gradle"):
            deps = parse_build_gradle(content, m_path)

        if not deps or not query_osv:
            return []

        dep_rule = next(iter(self.registry.dependency_rules()), VulnerableDependencyRule())
        findings: list[Finding] = []

        for dep in deps:
            cve_data = self.osv_client.query_sync(dep.name, dep.version, dep.ecosystem)
            if cve_data:
                f_list = dep_rule.check_dependency(
                    dep.name,
                    dep.version,
                    dep.ecosystem,
                    dep.manifest_path,
                    cve_data,
                )
                findings.extend(f_list)

        return findings

    def analyze_directory(
        self,
        root_dir: Path | str,
        graph: DirectedGraph | None = None,
        query_osv: bool = True,
    ) -> DiagnosticsReport:
        """Analyze an entire codebase directory: security rules, smells, manifests, and risk scores."""
        root = Path(root_dir)
        all_findings: list[Finding] = []

        import os

        skip_dirs = {
            ".git",
            "venv",
            ".venv",
            "node_modules",
            "target",
            "build",
            "dist",
            "__pycache__",
            ".tox",
            ".idea",
            ".vscode",
            "coverage",
            ".pytest_cache",
            ".ruff_cache",
            ".reports_storage",
            "reports_output",
            "data",
            "scratch",
        }
        source_candidates: list[Path] = []
        manifest_candidates: list[Path] = []

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not (d in skip_dirs or d.startswith("."))]
            dp = Path(dirpath)
            for f in filenames:
                if f in ("requirements.txt", "pom.xml", "build.gradle"):
                    manifest_candidates.append(dp / f)
                else:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in (".py", ".java", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"):
                        source_candidates.append(dp / f)

        # 1. Run security rules over all matching source files
        for p in sorted(source_candidates, key=lambda p: p.as_posix()):
            lang = None
            if p.suffix == ".py":
                lang = "python"
            elif p.suffix == ".java":
                lang = "java"
            elif p.suffix in (".js", ".jsx", ".mjs", ".cjs"):
                lang = "javascript"
            elif p.suffix in (".ts", ".tsx"):
                lang = "typescript"

            if lang:
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                    rel_path = p.relative_to(root).as_posix()
                    file_findings = self.analyze_source_code(content, lang, rel_path)
                    all_findings.extend(file_findings)
                except Exception as exc:
                    logger.warning("Could not read file %s: %s", p, exc)

        # 2. Check dependency manifests
        for m_file in sorted(manifest_candidates, key=lambda p: p.as_posix()):
            try:
                m_content = m_file.read_text(encoding="utf-8", errors="replace")
                rel_path = str(m_file.relative_to(root)).replace("\\", "/")
                dep_findings = self.analyze_dependencies_content(
                    content=m_content,
                    manifest_type=m_file.name,
                    manifest_path=rel_path,
                    query_osv=query_osv,
                )
                all_findings.extend(dep_findings)
            except Exception as exc:
                logger.warning("Could not process manifest %s: %s", m_file, exc)

        # 3. Check design smells if graph is provided
        if graph:
            smell_findings = self.analyze_graph(graph)
            all_findings.extend(smell_findings)

        all_findings.sort(
            key=lambda f: (
                str(getattr(f.severity, "value", f.severity)),
                f.rule_id,
                f.file_path or "",
                getattr(f, "line_number", getattr(f, "line", 0)) or 0,
                getattr(f, "message", getattr(f, "description", "")),
            )
        )

        # 4. Compute risk scores per node
        risk_scores: dict[str, NodeRiskScore] = {}
        if graph and graph.node_count > 0:
            bw = compute_betweenness_centrality(graph)
            pr = compute_pagerank(graph)

            # Index findings by node_id and file_path
            findings_by_node: dict[str, list[Finding]] = {}
            for f in all_findings:
                if f.node_id:
                    findings_by_node.setdefault(f.node_id, []).append(f)
                elif f.file_path:
                    # Match to nodes with same path
                    for nid, n in graph.nodes.items():
                        if n.path and n.path.replace("\\", "/") == f.file_path.replace("\\", "/"):
                            findings_by_node.setdefault(nid, []).append(f)

            risk_scores = self.scorer.score_all_nodes(graph, findings_by_node, bw, pr)

        # 5. Build summary
        sev_counts = {
            "critical": sum(1 for f in all_findings if f.severity == Severity.CRITICAL),
            "high": sum(1 for f in all_findings if f.severity == Severity.HIGH),
            "medium": sum(1 for f in all_findings if f.severity == Severity.MEDIUM),
            "low": sum(1 for f in all_findings if f.severity == Severity.LOW),
        }
        cat_counts = {
            "security": sum(1 for f in all_findings if f.category == RuleCategory.SECURITY),
            "design_smell": sum(1 for f in all_findings if f.category == RuleCategory.DESIGN_SMELL),
            "dependency": sum(1 for f in all_findings if f.category == RuleCategory.DEPENDENCY),
        }

        summary = {
            "total_findings": len(all_findings),
            "severity_counts": sev_counts,
            "category_counts": cat_counts,
            "max_risk_score": max((s.risk_score for s in risk_scores.values()), default=0.0),
            "scored_nodes_count": len(risk_scores),
        }

        return DiagnosticsReport(
            summary=summary,
            findings=all_findings,
            risk_scores=risk_scores,
        )


# Default global engine instance
default_diagnostics_engine = DiagnosticsEngine()
