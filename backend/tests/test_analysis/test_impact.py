"""Unit tests for impact analysis and blast radius calculation (Dijkstra / BFS)."""

from __future__ import annotations

import pytest

from analysis.graph import DirectedGraph
from analysis.impact import compute_blast_radius_bfs, compute_blast_radius_dijkstra


class TestImpactAnalysis:
    def test_linear_chain_blast_radius(self) -> None:
        # Dependency: A depends on B, B depends on C, C depends on D
        # A -> B -> C -> D
        # Changing D directly impacts C, transitively impacts B and A
        g = DirectedGraph()
        g.add_edge("A", "B", weight=1.0)
        g.add_edge("B", "C", weight=2.0)
        g.add_edge("C", "D", weight=3.0)

        # BFS (hop count)
        bfs_res = compute_blast_radius_bfs(g, target_node="D")
        assert bfs_res.total_impacted_count == 3
        assert bfs_res.direct_impact_count == 1
        assert bfs_res.transitive_impact_count == 2
        assert bfs_res.max_depth == 3
        # 3 out of 4 nodes impacted = 75%
        assert bfs_res.blast_radius_pct == 75.0

        node_map = {n.node_id: n for n in bfs_res.impacted_nodes}
        assert node_map["C"].is_direct is True
        assert node_map["C"].depth == 1
        assert node_map["C"].path == ["D", "C"]

        assert node_map["B"].is_direct is False
        assert node_map["B"].depth == 2
        assert node_map["B"].path == ["D", "C", "B"]

        assert node_map["A"].depth == 3
        assert node_map["A"].path == ["D", "C", "B", "A"]

        # Dijkstra (weighted distance)
        dijk_res = compute_blast_radius_dijkstra(g, target_node="D")
        assert dijk_res.total_impacted_count == 3
        dijk_map = {n.node_id: n for n in dijk_res.impacted_nodes}
        # Edge C->D weight is 3.0, B->C weight is 2.0, A->B weight is 1.0
        assert dijk_map["C"].distance == pytest.approx(3.0)
        assert dijk_map["B"].distance == pytest.approx(5.0)  # 3.0 + 2.0
        assert dijk_map["A"].distance == pytest.approx(6.0)  # 5.0 + 1.0

    def test_isolated_node_zero_blast_radius(self) -> None:
        g = DirectedGraph()
        g.add_node("Isolated")
        g.add_edge("A", "B")

        res = compute_blast_radius_bfs(g, target_node="Isolated")
        assert res.total_impacted_count == 0
        assert res.blast_radius_pct == 0.0
