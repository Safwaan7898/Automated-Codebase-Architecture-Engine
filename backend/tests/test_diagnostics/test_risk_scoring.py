"""Tests for multi-factor per-node risk scoring (0-100)."""

from analysis.graph import DirectedGraph
from diagnostics.models import Finding, Severity
from diagnostics.scoring import NodeRiskScorer


def test_severity_subscore_calculation() -> None:
    scorer = NodeRiskScorer()
    f_crit = Finding("R1", "Crit", Severity.CRITICAL, "security", "msg", "rem")
    f_high = Finding("R2", "High", Severity.HIGH, "security", "msg", "rem")

    s1 = scorer.calculate_severity_subscore([f_crit])
    assert s1 == 40.0

    s2 = scorer.calculate_severity_subscore([f_crit, f_high])
    assert s2 == 65.0

    # Test cap at 100
    s_max = scorer.calculate_severity_subscore([f_crit, f_crit, f_crit])
    assert s_max == 100.0


def test_complexity_subscore_calculation() -> None:
    scorer = NodeRiskScorer()
    # Baseline node: cc=1, loc=10 -> minimal score
    k1 = scorer.calculate_complexity_subscore({"cyclomatic_complexity": 1, "loc": 10})
    assert k1 == 1.0

    # Highly complex node: cc=15, loc=400
    # (15-1)*3.5 = 49.0, 400/10 = 40.0 -> total 89.0
    k2 = scorer.calculate_complexity_subscore({"cyclomatic_complexity": 15, "loc": 400})
    assert k2 == 89.0


def test_centrality_subscore_calculation() -> None:
    scorer = NodeRiskScorer()
    g = DirectedGraph()
    g.add_node("A")
    g.add_node("B")
    g.add_edge("A", "B")

    c = scorer.calculate_centrality_subscore("B", g, betweenness={"B": 0.5}, pagerank={"B": 0.6})
    assert 0.0 <= c <= 100.0


def test_unified_risk_score_bounds_and_levels() -> None:
    scorer = NodeRiskScorer()
    f_crit = Finding("R1", "Crit", Severity.CRITICAL, "security", "msg", "rem")
    f_high = Finding("R2", "High", Severity.HIGH, "security", "msg", "rem")

    # High-risk node: critical findings + high complexity + central
    high_risk = scorer.score_node(
        node_id="PaymentProcessor",
        findings=[f_crit, f_high],
        metrics={"cyclomatic_complexity": 12, "loc": 350},
        graph=None,
    )

    assert 0.0 <= high_risk.risk_score <= 100.0
    assert high_risk.risk_score >= 50.0
    assert high_risk.level in ("high", "critical")
    assert high_risk.findings_count == 2

    # Clean node: 0 findings, low complexity
    clean_node = scorer.score_node(
        node_id="SimpleDTO",
        findings=[],
        metrics={"cyclomatic_complexity": 1, "loc": 20},
        graph=None,
    )

    assert clean_node.risk_score <= 20.0
    assert clean_node.level in ("clean", "low")
    assert clean_node.findings_count == 0
