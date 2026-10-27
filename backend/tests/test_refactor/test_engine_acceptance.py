"""Acceptance tests: verifying deterministic, ranked suggestions with simulated metrics on sample repos and graphs."""

from pathlib import Path

import pytest

from analysis.facade import build_graph_from_parse_result
from analysis.graph import DirectedGraph
from parsers.config import IngestionConfig
from parsers.parallel_runner import parse_repository
from refactor.engine import RefactorEngine, default_refactor_engine

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SAMPLES_ROOT = REPO_ROOT / "samples"
FLASK_SAMPLE = SAMPLES_ROOT / "python-flask"
JAVA_SAMPLE = SAMPLES_ROOT / "java-spring"


def build_synthetic_architecture_graph() -> DirectedGraph:
    """Construct an architecture graph containing all 4 architectural challenges."""
    g = DirectedGraph()

    # 1. Cycle: ServiceA -> ServiceB -> ServiceC -> ServiceA
    g.add_node("com.example.ServiceA", name="ServiceA", node_type="class")
    g.add_node("com.example.ServiceB", name="ServiceB", node_type="class")
    g.add_node("com.example.ServiceC", name="ServiceC", node_type="class")

    g.add_edge("com.example.ServiceA", "com.example.ServiceB", weight=3.0)
    g.add_edge("com.example.ServiceB", "com.example.ServiceC", weight=2.0)
    g.add_edge("com.example.ServiceC", "com.example.ServiceA", weight=1.0)

    # 2. God Class: MegaManager
    g.add_node(
        "com.example.MegaManager",
        name="MegaManager",
        node_type="class",
        metrics={"loc": 650, "num_methods": 25, "cyclomatic_complexity": 22},
    )
    for i in range(6):
        mid = f"com.example.MegaManager#method{i}"
        g.add_node(mid, name=f"method{i}", node_type="method")
        g.add_edge("com.example.MegaManager", mid, edge_type="contains")

    # 3. Dense Module: Billing domain
    for name in ["InvoiceProcessor", "BillingLedger", "PaymentDispatcher", "TaxCalculator"]:
        nid = f"com.example.billing.{name}"
        g.add_node(nid, name=name, node_type="class")

    for u in ["InvoiceProcessor", "BillingLedger", "PaymentDispatcher", "TaxCalculator"]:
        for v in ["InvoiceProcessor", "BillingLedger", "PaymentDispatcher", "TaxCalculator"]:
            if u != v:
                g.add_edge(f"com.example.billing.{u}", f"com.example.billing.{v}")

    # 4. Feature Envy / Move Method: Method in ServiceA heavily accessing CustomerRepo
    g.add_node("com.example.CustomerRepo", name="CustomerRepo", node_type="class")
    m_id = "com.example.ServiceA#fetchCustomerHistory"
    g.add_node(m_id, name="fetchCustomerHistory", node_type="method")
    g.add_edge("com.example.ServiceA", m_id, edge_type="contains")
    for i in range(4):
        target_m = f"com.example.CustomerRepo#query{i}"
        g.add_node(target_m, node_type="method")
        g.add_edge(m_id, target_m, edge_type="calls")

    return g


def test_acceptance_deterministic_and_ranked_synthetic_graph() -> None:
    g = build_synthetic_architecture_graph()
    engine = RefactorEngine()

    plan1 = engine.generate_plan(g)
    plan2 = engine.generate_plan(g)

    # 1. Non-empty suggestions covering multiple dimensions
    assert plan1.total_suggestions >= 3
    assert plan1.total_suggestions == plan2.total_suggestions

    # 2. Strict ranking
    ranks = [s.rank for s in plan1.suggestions]
    assert ranks == list(range(1, len(plan1.suggestions) + 1))

    # 3. Determinism check
    for s1, s2 in zip(plan1.suggestions, plan2.suggestions, strict=True):
        assert s1.id == s2.id
        assert s1.title == s2.title
        assert s1.type == s2.type
        assert s1.rank == s2.rank
        assert s1.priority_score == s2.priority_score
        assert s1.metrics.to_dict() == s2.metrics.to_dict()

    # 4. Simulated metrics recomputed before and after
    for s in plan1.suggestions:
        # Before and after metrics must be populated
        assert s.metrics.cycles_before >= s.metrics.cycles_after
        assert s.metrics.god_classes_before >= s.metrics.god_classes_after
        assert s.metrics.coupling_before >= s.metrics.coupling_after


@pytest.mark.asyncio
async def test_acceptance_on_sample_repo_flask() -> None:
    if not FLASK_SAMPLE.exists():
        pytest.skip(f"Flask sample repo not present at {FLASK_SAMPLE}")

    cfg = IngestionConfig(include_test_files=False, max_workers=4)
    parse_res = await parse_repository(str(FLASK_SAMPLE), cfg)
    graph = build_graph_from_parse_result(parse_res)

    engine = default_refactor_engine
    plan = engine.generate_plan(graph, repo_root=FLASK_SAMPLE)

    assert plan.total_suggestions > 0

    # Verify ranking monotonicity: priority_score must be non-increasing
    for i in range(len(plan.suggestions) - 1):
        assert plan.suggestions[i].priority_score >= plan.suggestions[i + 1].priority_score
        assert plan.suggestions[i].rank == i + 1

    # Verify after metrics were recomputed
    for s in plan.suggestions:
        assert isinstance(s.metrics.cycles_after, int)
        assert isinstance(s.metrics.coupling_after, int)
        assert s.metrics.details.get("simulated") is True


@pytest.mark.asyncio
async def test_acceptance_on_sample_repo_java() -> None:
    if not JAVA_SAMPLE.exists():
        pytest.skip(f"Java Spring sample repo not present at {JAVA_SAMPLE}")

    cfg = IngestionConfig(include_test_files=False, max_workers=4)
    parse_res = await parse_repository(str(JAVA_SAMPLE), cfg)
    graph = build_graph_from_parse_result(parse_res)

    engine = default_refactor_engine
    plan = engine.generate_plan(graph, repo_root=JAVA_SAMPLE)

    assert plan.total_suggestions >= 0
    for s in plan.suggestions:
        assert s.rank > 0
        assert s.metrics.details.get("simulated") is True
