"""Unit tests for Louvain community detection cross-checked with NetworkX."""

from __future__ import annotations

import networkx as nx

from analysis.community import compute_louvain_communities
from analysis.graph import DirectedGraph


class TestLouvainCommunities:
    def test_two_cliques_separated_into_communities(self) -> None:
        # Clique 1: A, B, C (all pairwise connected)
        # Clique 2: X, Y, Z (all pairwise connected)
        # Single inter-clique edge: C -> X
        g = DirectedGraph()

        # Clique 1
        for u in ("A", "B", "C"):
            for v in ("A", "B", "C"):
                if u != v:
                    g.add_edge(u, v)

        # Clique 2
        for u in ("X", "Y", "Z"):
            for v in ("X", "Y", "Z"):
                if u != v:
                    g.add_edge(u, v)

        # Weak bridge
        g.add_edge("C", "X")

        res = compute_louvain_communities(g)

        assert res.community_count == 2
        assert res.modularity > 0.0

        # Verify A, B, C are in one community, and X, Y, Z are in the other
        comm_c = res.node_to_community["C"]
        assert res.node_to_community["A"] == comm_c
        assert res.node_to_community["B"] == comm_c

        comm_x = res.node_to_community["X"]
        assert comm_x != comm_c
        assert res.node_to_community["Y"] == comm_x
        assert res.node_to_community["Z"] == comm_x

        # Cross-check with NetworkX Louvain communities
        nx_g = g.to_networkx().to_undirected()
        nx_comms = [set(c) for c in nx.community.louvain_communities(nx_g)]

        assert len(nx_comms) == 2
        assert {"A", "B", "C"} in nx_comms
        assert {"X", "Y", "Z"} in nx_comms
