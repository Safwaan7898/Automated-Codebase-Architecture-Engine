"""Tests for CycleBreaker using minimal-weight feedback arc set heuristic."""

from analysis.graph import DirectedGraph
from refactor.cycle_breaker import CycleBreaker
from refactor.models import Effort, RefactorType


def test_minimal_feedback_arc_selection() -> None:
    breaker = CycleBreaker()
    g = DirectedGraph()

    # Cycle A -> B (weight 5.0) -> C (weight 10.0) -> A (weight 1.0)
    g.add_node("ServiceA", name="ServiceA")
    g.add_node("ServiceB", name="ServiceB")
    g.add_node("ServiceC", name="ServiceC")

    g.add_edge("ServiceA", "ServiceB", weight=5.0)
    g.add_edge("ServiceB", "ServiceC", weight=10.0)
    g.add_edge("ServiceC", "ServiceA", weight=1.0)

    u, v, weight = breaker.find_minimal_feedback_arc(
        [("ServiceA", "ServiceB"), ("ServiceB", "ServiceC"), ("ServiceC", "ServiceA")],
        g,
    )

    assert (u, v) == ("ServiceC", "ServiceA")
    assert weight == 1.0


def test_cycle_breaker_generates_interface_suggestions() -> None:
    breaker = CycleBreaker()
    g = DirectedGraph()

    g.add_node("OrderService", name="OrderService")
    g.add_node("PaymentService", name="PaymentService")

    # Cycle OrderService -> PaymentService (weight 5.0) -> OrderService (weight 1.0)
    g.add_edge("OrderService", "PaymentService", weight=5.0)
    g.add_edge("PaymentService", "OrderService", weight=1.0)

    suggestions = breaker.generate_suggestions(g)
    assert len(suggestions) == 1

    s = suggestions[0]
    assert s.type == RefactorType.BREAK_CYCLE
    assert s.effort == Effort.S
    assert "IOrderService" in s.title or "IOrderService" in s.action_details["interface_name"]
    assert s.action_details["feedback_arc"]["source"] == "PaymentService"
    assert s.action_details["feedback_arc"]["target"] == "OrderService"
    assert "interface" in s.rationale.lower()


def test_cycle_breaker_deterministic() -> None:
    breaker = CycleBreaker()
    g = DirectedGraph()
    g.add_edge("A", "B", weight=1.0)
    g.add_edge("B", "A", weight=1.0)

    # Multiple runs must return identical output
    s1 = breaker.generate_suggestions(g)
    s2 = breaker.generate_suggestions(g)

    assert len(s1) == len(s2) == 1
    assert s1[0].title == s2[0].title
    assert s1[0].action_details == s2[0].action_details
