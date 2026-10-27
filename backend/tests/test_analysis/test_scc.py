"""Unit tests for Tarjan's SCC and circular dependency detection."""

from __future__ import annotations

import networkx as nx

from analysis.graph import DirectedGraph
from analysis.scc import detect_circular_dependencies, find_strongly_connected_components


class TestTarjanSCC:
    def test_dag_has_no_circular_dependencies(self) -> None:
        # A -> B -> C -> D
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("C", "D")

        sccs = find_strongly_connected_components(g)
        assert len(sccs) == 4
        assert all(len(c) == 1 for c in sccs)

        cycles = detect_circular_dependencies(g)
        assert len(cycles) == 0

        # Cross-check with NetworkX
        nx_g = g.to_networkx()
        nx_sccs = list(nx.strongly_connected_components(nx_g))
        assert len(nx_sccs) == 4
        assert len(list(nx.simple_cycles(nx_g))) == 0

    def test_single_cycle_detected(self) -> None:
        # A -> B -> C -> A
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("C", "A")

        sccs = find_strongly_connected_components(g)
        assert len(sccs) == 1
        assert sorted(sccs[0]) == ["A", "B", "C"]

        cycles = detect_circular_dependencies(g)
        assert len(cycles) == 1
        assert cycles[0].size == 3
        assert cycles[0].nodes == ["A", "B", "C"]
        assert not cycles[0].is_self_loop

        # Cross-check with NetworkX
        nx_g = g.to_networkx()
        nx_sccs = [sorted(c) for c in nx.strongly_connected_components(nx_g)]
        assert nx_sccs == [["A", "B", "C"]]

    def test_disjoint_cycles_detected(self) -> None:
        # Cycle 1: A <-> B
        # Cycle 2: C -> D -> E -> C
        # Edge between them: B -> C (DAG edge between cycles)
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "A")
        g.add_edge("B", "C")
        g.add_edge("C", "D")
        g.add_edge("D", "E")
        g.add_edge("E", "C")

        cycles = detect_circular_dependencies(g)
        assert len(cycles) == 2
        # Largest cycle first
        assert cycles[0].size == 3
        assert cycles[0].nodes == ["C", "D", "E"]
        assert cycles[1].size == 2
        assert cycles[1].nodes == ["A", "B"]

        # Cross-check with NetworkX
        nx_g = g.to_networkx()
        nx_sccs = sorted(
            [sorted(c) for c in nx.strongly_connected_components(nx_g) if len(c) > 1],
            key=len,
            reverse=True,
        )
        assert nx_sccs == [["C", "D", "E"], ["A", "B"]]

    def test_self_loop_cycle(self) -> None:
        g = DirectedGraph()
        g.add_edge("A", "A")
        g.add_edge("A", "B")

        cycles = detect_circular_dependencies(g)
        assert len(cycles) == 1
        assert cycles[0].is_self_loop is True
        assert cycles[0].nodes == ["A"]
