"""Tests for MethodMover coupling-based refactoring."""

from analysis.graph import DirectedGraph
from refactor.method_mover import MethodMover
from refactor.models import Effort, RefactorType


def test_move_method_suggestion() -> None:
    mover = MethodMover()
    g = DirectedGraph()

    g.add_node("OrderService", name="OrderService", node_type="class")
    g.add_node("CustomerService", name="CustomerService", node_type="class")

    # Method belongs to OrderService
    method_id = "OrderService#calculateCustomerDiscount"
    g.add_node(method_id, name="calculateCustomerDiscount", node_type="method")
    g.add_edge("OrderService", method_id, edge_type="contains")

    # Method makes 4 calls to CustomerService, 0 to OrderService
    for i in range(4):
        target_m = f"CustomerService#getAttr{i}"
        g.add_node(target_m, node_type="method")
        g.add_edge(method_id, target_m, edge_type="calls")

    suggestions = mover.generate_suggestions(g)
    assert len(suggestions) == 1

    s = suggestions[0]
    assert s.type == RefactorType.MOVE_METHOD
    assert s.effort == Effort.S
    assert "calculateCustomerDiscount" in s.title
    assert "CustomerService" in s.title
    assert s.action_details["source_class"] == "OrderService"
    assert s.action_details["target_class"] == "CustomerService"
