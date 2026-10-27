"""Tests for GraphRefactorSimulator before and after metric recomputation."""

from analysis.graph import DirectedGraph
from refactor.cycle_breaker import CycleBreaker
from refactor.god_class_splitter import GodClassSplitter
from refactor.method_mover import MethodMover
from refactor.simulation import GraphRefactorSimulator, clone_graph


def test_clone_graph() -> None:
    g = DirectedGraph()
    g.add_node("A", metrics={"loc": 100})
    g.add_node("B")
    g.add_edge("A", "B", weight=2.5)

    cloned = clone_graph(g)
    assert cloned.node_count == 2
    assert cloned.edge_count == 1
    assert cloned.nodes["A"].metrics["loc"] == 100

    # Mutating clone must not affect original
    cloned.remove_edge("A", "B")
    assert (
        "A",
        "B",
    ) in g.edges
    assert (
        "A",
        "B",
    ) not in cloned.edges


def test_simulation_break_cycle_reduces_cycles() -> None:
    simulator = GraphRefactorSimulator()
    breaker = CycleBreaker()

    g = DirectedGraph()
    g.add_edge("A", "B")
    g.add_edge("B", "A")

    suggestions = breaker.generate_suggestions(g)
    assert len(suggestions) == 1

    metrics = simulator.simulate(g, suggestions[0])
    assert metrics.cycles_before == 1
    assert metrics.cycles_after == 0


def test_simulation_split_god_class_reduces_god_classes() -> None:
    simulator = GraphRefactorSimulator()
    splitter = GodClassSplitter(loc_threshold=200, method_threshold=10)

    g = DirectedGraph()
    g.add_node("MegaClass", node_type="class", metrics={"loc": 400, "num_methods": 20})

    suggestions = splitter.generate_suggestions(g)
    assert len(suggestions) == 1

    metrics = simulator.simulate(g, suggestions[0])
    assert metrics.god_classes_before == 1
    assert metrics.god_classes_after == 0


def test_simulation_move_method_reduces_coupling() -> None:
    simulator = GraphRefactorSimulator()
    mover = MethodMover()

    g = DirectedGraph()
    g.add_node("Src", node_type="class")
    g.add_node("Tgt", node_type="class")
    g.add_node("Src#m", node_type="method")
    g.add_edge("Src", "Src#m", edge_type="contains")
    g.add_edge("Src#m", "Tgt", edge_type="calls", weight=2.0)

    suggestions = mover.generate_suggestions(g)
    assert len(suggestions) == 1

    metrics = simulator.simulate(g, suggestions[0])
    assert metrics.coupling_before >= metrics.coupling_after
