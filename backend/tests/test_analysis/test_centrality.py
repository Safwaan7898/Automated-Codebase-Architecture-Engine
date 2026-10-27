"""Unit tests for Betweenness Centrality (Brandes) and PageRank cross-checked with NetworkX."""

from __future__ import annotations

import networkx as nx
import pytest

from analysis.centrality import (
    analyze_centrality,
    compute_betweenness_centrality,
    compute_pagerank,
)
from analysis.graph import DirectedGraph


class TestCentralityMetrics:
    def test_betweenness_bridge_node(self) -> None:
        # Bowtie / Bridge graph:
        # Left cluster: A <-> B, B <-> C, C <-> A
        # Bridge: C <-> Bridge <-> D
        # Right cluster: D <-> E, E <-> F, F <-> D
        g = DirectedGraph()
        # Left triangle
        g.add_edge("A", "B")
        g.add_edge("B", "A")
        g.add_edge("B", "C")
        g.add_edge("C", "B")
        g.add_edge("C", "A")
        g.add_edge("A", "C")
        # Bridge connects C to Bridge to D
        g.add_edge("C", "Bridge")
        g.add_edge("Bridge", "C")
        g.add_edge("Bridge", "D")
        g.add_edge("D", "Bridge")
        # Right triangle
        g.add_edge("D", "E")
        g.add_edge("E", "D")
        g.add_edge("E", "F")
        g.add_edge("F", "E")
        g.add_edge("F", "D")
        g.add_edge("D", "F")

        bw = compute_betweenness_centrality(g, normalized=True)

        # The Bridge node MUST have the highest betweenness centrality
        max_node = max(bw, key=lambda k: bw[k])
        assert max_node == "Bridge"

        # Cross-check exact values with NetworkX
        nx_g = g.to_networkx()
        nx_bw = nx.betweenness_centrality(nx_g, normalized=True)

        for node in g.nodes:
            assert pytest.approx(bw[node], abs=1e-5) == nx_bw[node]

    def test_pagerank_hub_node(self) -> None:
        # Star graph where leaves point to the Hub
        # Leaf1 -> Hub, Leaf2 -> Hub, Leaf3 -> Hub, Leaf4 -> Hub
        # Hub -> Leaf1 (so graph has outgoing edge)
        g = DirectedGraph()
        g.add_edge("Leaf1", "Hub")
        g.add_edge("Leaf2", "Hub")
        g.add_edge("Leaf3", "Hub")
        g.add_edge("Leaf4", "Hub")
        g.add_edge("Hub", "Leaf1")

        pr = compute_pagerank(g, alpha=0.85)

        # Hub MUST have the highest PageRank score
        max_node = max(pr, key=lambda k: pr[k])
        assert max_node == "Hub"
        assert sum(pr.values()) == pytest.approx(1.0, abs=1e-5)

        # Cross-check with NetworkX PageRank
        nx_g = g.to_networkx()
        nx_pr = nx.pagerank(nx_g, alpha=0.85)

        for node in g.nodes:
            assert pytest.approx(pr[node], abs=1e-3) == nx_pr[node]

    def test_bottleneck_and_god_class_identification(self) -> None:
        g = DirectedGraph()
        # Create a hub/bottleneck node with many incoming and outgoing links
        for i in range(10):
            g.add_edge(f"Client{i}", "GodClass")
            g.add_edge("GodClass", f"Service{i}")

        analysis = analyze_centrality(g)
        assert "GodClass" in analysis.bottlenecks
        assert "GodClass" in analysis.god_classes
