"""Unit tests for topological sorting and architectural layering."""

from __future__ import annotations

import networkx as nx

from analysis.graph import DirectedGraph
from analysis.topo_sort import compute_architectural_layers


class TestTopologicalSortAndLayers:
    def test_diamond_dag_layers(self) -> None:
        # A -> B, A -> C, B -> D, C -> D
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        g.add_edge("C", "D")

        res = compute_architectural_layers(g)
        assert res.is_dag is True
        assert res.total_layers == 3
        # Layer 0: root [A]
        assert res.layers[0] == ["A"]
        # Layer 1: intermediate [B, C]
        assert sorted(res.layers[1]) == ["B", "C"]
        # Layer 2: sink [D]
        assert res.layers[2] == ["D"]

        # Cross-check topological order validity with NetworkX
        nx_g = g.to_networkx()
        assert nx.is_directed_acyclic_graph(nx_g)
        # In any valid topological sort, A precedes B and C, and B and C precede D
        pos = {node: i for i, node in enumerate(res.topological_order)}
        assert pos["A"] < pos["B"]
        assert pos["A"] < pos["C"]
        assert pos["B"] < pos["D"]
        assert pos["C"] < pos["D"]

    def test_cyclic_graph_condensed_and_layered(self) -> None:
        # Cycle: A <-> B
        # Edge from cycle: B -> C
        # Edge from C: C -> D
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "A")
        g.add_edge("B", "C")
        g.add_edge("C", "D")

        res = compute_architectural_layers(g)
        # Not a pure DAG originally
        assert res.is_dag is False
        assert res.condensed_scc_count == 3  # {A, B}, {C}, {D}
        assert res.total_layers == 3

        # Layer 0 contains the cycle members
        assert sorted(res.layers[0]) == ["A", "B"]
        assert res.layers[1] == ["C"]
        assert res.layers[2] == ["D"]

    def test_multi_tier_enterprise_architecture(self) -> None:
        # Tier 0 (Controllers): WebController, ApiController
        # Tier 1 (Services): UserService, OrderService
        # Tier 2 (Repositories): UserRepository, OrderRepository
        # Tier 3 (Database / Entities): UserEntity, OrderEntity
        g = DirectedGraph()
        g.add_edge("WebController", "UserService")
        g.add_edge("ApiController", "UserService")
        g.add_edge("ApiController", "OrderService")
        g.add_edge("UserService", "UserRepository")
        g.add_edge("OrderService", "OrderRepository")
        g.add_edge("UserRepository", "UserEntity")
        g.add_edge("OrderRepository", "OrderEntity")

        res = compute_architectural_layers(g)
        assert res.is_dag is True
        assert res.total_layers == 4
        assert sorted(res.layers[0]) == ["ApiController", "WebController"]
        assert sorted(res.layers[1]) == ["OrderService", "UserService"]
        assert sorted(res.layers[2]) == ["OrderRepository", "UserRepository"]
        assert sorted(res.layers[3]) == ["OrderEntity", "UserEntity"]
