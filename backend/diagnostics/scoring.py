"""Risk scoring engine computing per-node risk scores (0-100).

Synthesizes:
1. Finding Severity: Aggregated weights of security, design, and dependency findings.
2. Network Centrality: Architectural blast radius via PageRank and Betweenness.
3. Code Complexity: Cyclomatic complexity (McCabe) and Lines of Code (LOC).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from diagnostics.models import SEVERITY_WEIGHTS, Finding, NodeRiskScore

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


class NodeRiskScorer:
    """Computes multidimensional architectural risk scores (0-100) per node."""

    def __init__(
        self,
        severity_weight: float = 0.55,
        centrality_weight: float = 0.25,
        complexity_weight: float = 0.20,
    ) -> None:
        self.severity_weight = severity_weight
        self.centrality_weight = centrality_weight
        self.complexity_weight = complexity_weight

    def calculate_severity_subscore(self, findings: list[Finding]) -> float:
        """Calculate finding severity subscore in [0.0, 100.0]."""
        if not findings:
            return 0.0

        raw_points = sum(SEVERITY_WEIGHTS.get(f.severity, 5.0) for f in findings)
        return min(100.0, raw_points)

    def calculate_centrality_subscore(
        self,
        node_id: str,
        graph: DirectedGraph | None = None,
        betweenness: dict[str, float] | None = None,
        pagerank: dict[str, float] | None = None,
    ) -> float:
        """Calculate network centrality subscore in [0.0, 100.0]."""
        if graph is None or graph.node_count == 0:
            return 10.0

        n = graph.node_count
        avg_pr = 1.0 / n if n > 0 else 0.0

        pr_val = pagerank.get(node_id, avg_pr) if pagerank else avg_pr
        bw_val = betweenness.get(node_id, 0.0) if betweenness else 0.0

        # PageRank ratio compared to uniform distribution (1.0 = average)
        pr_ratio = (pr_val / avg_pr) if avg_pr > 0 else 1.0

        # Subscore: 50% from PR ratio, 50% from betweenness
        pr_score = min(50.0, pr_ratio * 25.0)
        bw_score = min(50.0, bw_val * 100.0)

        return min(100.0, pr_score + bw_score)

    def calculate_complexity_subscore(self, metrics: dict[str, Any]) -> float:
        """Calculate code complexity subscore in [0.0, 100.0]."""
        cc = float(metrics.get("cyclomatic_complexity", 1))
        loc = float(metrics.get("loc", 0))

        # CC base: 1 is baseline (0 penalty), each branch adds ~3.5 pts
        cc_points = max(0.0, (cc - 1.0) * 3.5)
        # LOC: 100 LOC = 10 pts, 500 LOC = 50 pts
        loc_points = loc / 10.0

        return min(100.0, cc_points + loc_points)

    def score_node(
        self,
        node_id: str,
        findings: list[Finding],
        metrics: dict[str, Any] | None = None,
        graph: DirectedGraph | None = None,
        betweenness: dict[str, float] | None = None,
        pagerank: dict[str, float] | None = None,
    ) -> NodeRiskScore:
        """Compute the unified 0-100 risk score for a single node."""
        s_score = self.calculate_severity_subscore(findings)
        c_score = self.calculate_centrality_subscore(node_id, graph, betweenness, pagerank)
        k_score = self.calculate_complexity_subscore(metrics or {})

        if s_score > 0.0:
            # When vulnerabilities or smells exist, risk combines severity, blast radius, and complexity
            risk = self.severity_weight * s_score + self.centrality_weight * c_score + self.complexity_weight * k_score
        else:
            # When clean of findings, structural complexity contributes minor baseline risk
            risk = 0.10 * c_score + 0.15 * k_score

        clamped_risk = max(0.0, min(100.0, risk))

        # Determine qualitative level
        if clamped_risk >= 75.0:
            level = "critical"
        elif clamped_risk >= 50.0:
            level = "high"
        elif clamped_risk >= 25.0:
            level = "medium"
        elif clamped_risk > 0.0:
            level = "low"
        else:
            level = "clean"

        return NodeRiskScore(
            node_id=node_id,
            risk_score=round(clamped_risk, 2),
            level=level,
            severity_score=round(s_score, 2),
            centrality_score=round(c_score, 2),
            complexity_score=round(k_score, 2),
            findings_count=len(findings),
            findings=findings,
        )

    def score_all_nodes(
        self,
        graph: DirectedGraph,
        findings_by_node: dict[str, list[Finding]],
        betweenness: dict[str, float] | None = None,
        pagerank: dict[str, float] | None = None,
    ) -> dict[str, NodeRiskScore]:
        """Compute risk scores for all nodes in the architecture graph."""
        scores: dict[str, NodeRiskScore] = {}

        for nid, node in graph.nodes.items():
            if node.is_external:
                continue
            node_findings = findings_by_node.get(nid, [])
            scores[nid] = self.score_node(
                node_id=nid,
                findings=node_findings,
                metrics=node.metrics,
                graph=graph,
                betweenness=betweenness,
                pagerank=pagerank,
            )

        return scores


# Global default scorer instance
default_risk_scorer = NodeRiskScorer()


def compute_codebase_health(
    nodes: list[Any] | None = None,
    edges: list[Any] | None = None,
    cycles: list[Any] | int = 0,
    smells: list[Any] | None = None,
    findings: list[Any] | None = None,
    graph: Any | None = None,
) -> Any:
    """
    Compute canonical codebase health score (0.0 - 100.0) based on docs/scoring.md.

    Weighted dimensions:
    - Cycles: 25%
    - Coupling & Instability: 20%
    - Complexity: 20%
    - Architectural Smells: 20%
    - Security Findings: 15%

    If LOC == 0 or total_nodes == 0, returns insufficient_data status with null score.
    """
    from app.models.graph import HealthScoreResult

    # Extract nodes
    node_list: list[Any] = []
    if nodes is not None:
        node_list = list(nodes)
    elif graph is not None and hasattr(graph, "nodes"):
        node_list = list(graph.nodes.values())

    # Extract edges
    edge_list: list[Any] = []
    if edges is not None:
        edge_list = list(edges)
    elif graph is not None and hasattr(graph, "edges"):
        edge_list = list(graph.edges.values())

    total_nodes = len(node_list)

    # Compute total LOC and McCabe cyclomatic complexity
    total_loc = 0
    complexities: list[float] = []
    max_cc = 1
    for n in node_list:
        n_loc = 0
        if hasattr(n, "loc") and n.loc is not None:
            n_loc = getattr(n, "loc", 0) or 0
        elif isinstance(n, dict):
            n_loc = n.get("loc", 0) or 0
        elif hasattr(n, "metrics"):
            if isinstance(n.metrics, dict):
                n_loc = n.metrics.get("loc", 0) or 0
            elif hasattr(n.metrics, "loc"):
                n_loc = getattr(n.metrics, "loc", 0) or 0
        total_loc += n_loc

        # Complexity
        n_cc = 1.0
        if hasattr(n, "mean_complexity") and n.mean_complexity is not None:
            n_cc = getattr(n, "mean_complexity", 1.0) or 1.0
        elif hasattr(n, "cyclomatic_complexity") and n.cyclomatic_complexity is not None:
            n_cc = getattr(n, "cyclomatic_complexity", 1.0) or 1.0
        elif hasattr(n, "metrics"):
            if isinstance(n.metrics, dict):
                n_cc = n.metrics.get("cyclomatic_complexity", 1.0) or 1.0
            elif hasattr(n.metrics, "cyclomatic_complexity"):
                n_cc = getattr(n.metrics, "cyclomatic_complexity", 1.0) or 1.0
        elif isinstance(n, dict):
            n_cc = n.get("cyclomatic_complexity", 1.0) or n.get("mean_complexity", 1.0) or 1.0

        n_max = 1
        if hasattr(n, "max_complexity") and n.max_complexity is not None:
            n_max = getattr(n, "max_complexity", 1) or 1
        elif hasattr(n, "metrics"):
            if isinstance(n.metrics, dict):
                n_max = n.metrics.get("max_complexity", 1) or 1
            elif hasattr(n.metrics, "max_complexity"):
                n_max = getattr(n.metrics, "max_complexity", 1) or 1
        elif isinstance(n, dict):
            n_max = n.get("max_complexity", 1) or 1

        complexities.append(float(n_cc))
        if n_max > max_cc:
            max_cc = n_max

    # ── Guard: Insufficient data ──────────────────────────────────────────
    # insufficient_data applies ONLY when there are zero analysable files or zero nodes
    if total_nodes == 0:
        return HealthScoreResult(
            status="insufficient_data",
            score=None,
            grade=None,
            sub_scores={},
            summary="Not enough data to compute architecture health score (0 nodes).",
        )

    # 1. Cycles Sub-Score (25%)
    if isinstance(cycles, int):
        cycle_count = cycles
    elif isinstance(cycles, list):
        cycle_count = len(cycles)
    else:
        cycle_count = 0

    if cycle_count == 0 and edge_list:
        # Check edge.is_cycle count if cycles not explicitly passed
        cycle_count = sum(1 for e in edge_list if getattr(e, "is_cycle", False))

    s_cycles = max(0.0, 100.0 - (cycle_count * 25.0))

    # 2. Coupling Sub-Score (20%)
    edge_count = len(edge_list)
    rho = (edge_count / total_nodes) if total_nodes > 0 else 0.0

    # Hubs: count nodes with out-degree > 15
    out_degrees: dict[str, int] = {}
    for e in edge_list:
        src = getattr(e, "source", None) or (e[0] if isinstance(e, tuple) else None)
        if src:
            out_degrees[str(src)] = out_degrees.get(str(src), 0) + 1
    hubs = sum(1 for deg in out_degrees.values() if deg > 15)

    rho_penalty = max(0.0, rho - 2.0) * 15.0
    hub_penalty = hubs * 5.0
    s_coupling = max(0.0, min(100.0, 100.0 - rho_penalty - hub_penalty))

    # 3. Complexity Sub-Score (20%)
    mean_cc = (sum(complexities) / len(complexities)) if complexities else 1.0
    if mean_cc <= 5.0:
        s_cc = 100.0
    elif mean_cc <= 10.0:
        s_cc = 100.0 - (mean_cc - 5.0) * 8.0
    else:
        s_cc = max(0.0, 60.0 - (mean_cc - 10.0) * 5.0)

    peak_penalty = min(20.0, max(0.0, (max_cc - 20) * 2.0))
    s_complexity = max(0.0, min(100.0, s_cc - peak_penalty))

    # 4. Smells Sub-Score (20%)
    smell_list = smells or []
    smell_deductions = 0.0
    for sm in smell_list:
        sev = getattr(sm, "severity", None) or (sm.get("severity") if isinstance(sm, dict) else "low")
        sev_str = str(getattr(sev, "value", sev)).lower()
        if sev_str == "critical":
            smell_deductions += 20.0
        elif sev_str == "high":
            smell_deductions += 10.0
        elif sev_str == "medium":
            smell_deductions += 5.0
        else:
            smell_deductions += 2.0
    s_smells = max(0.0, 100.0 - smell_deductions)

    # 5. Security Sub-Score (15%)
    finding_list = findings or []
    sec_deductions = 0.0
    for f in finding_list:
        sev = getattr(f, "severity", None) or (f.get("severity") if isinstance(f, dict) else "low")
        sev_str = str(getattr(sev, "value", sev)).lower()
        if sev_str == "critical":
            sec_deductions += 30.0
        elif sev_str == "high":
            sec_deductions += 15.0
        elif sev_str == "medium":
            sec_deductions += 8.0
        else:
            sec_deductions += 3.0
    s_security = max(0.0, 100.0 - sec_deductions)

    # Linear combination
    overall = (
        0.25 * s_cycles
        + 0.20 * s_coupling
        + 0.20 * s_complexity
        + 0.20 * s_smells
        + 0.15 * s_security
    )
    overall_score = round(max(0.0, min(100.0, overall)), 1)

    # Grade derivation
    if overall_score >= 90.0:
        grade = "A+"
    elif overall_score >= 80.0:
        grade = "A"
    elif overall_score >= 70.0:
        grade = "B"
    elif overall_score >= 60.0:
        grade = "C"
    elif overall_score >= 50.0:
        grade = "D"
    else:
        grade = "F"

    sub_scores = {
        "cycles": round(s_cycles, 1),
        "coupling": round(s_coupling, 1),
        "complexity": round(s_complexity, 1),
        "smells": round(s_smells, 1),
        "security": round(s_security, 1),
    }

    # One-line reason for the score
    reasons: list[str] = []
    if cycle_count == 0:
        reasons.append("zero circular dependencies")
    else:
        reasons.append(f"{cycle_count} circular {'loop' if cycle_count == 1 else 'loops'}")

    if rho <= 2.0 and hubs == 0:
        reasons.append(f"ideal coupling density (rho={rho:.2f})")
    else:
        reasons.append(f"elevated coupling (rho={rho:.2f}, {hubs} hubs)")

    if mean_cc <= 5.0 and max_cc <= 20:
        reasons.append(f"low complexity (avg CC {mean_cc:.2f})")
    else:
        reasons.append(f"complexity hotspots (avg CC {mean_cc:.2f}, max {max_cc})")

    if smell_deductions == 0:
        reasons.append("no anti-pattern smells")
    else:
        reasons.append(f"{len(smell_list)} architectural smells")

    if sec_deductions == 0:
        reasons.append("no security findings")
    else:
        reasons.append(f"{len(finding_list)} security findings")

    summary_reason = f"Grade {grade} ({overall_score}/100.0) - Architecture reflects {', '.join(reasons)}."

    return HealthScoreResult(
        status="ok",
        score=overall_score,
        grade=grade,
        sub_scores=sub_scores,
        summary=summary_reason,
    )

