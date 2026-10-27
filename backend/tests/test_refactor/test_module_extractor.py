"""Tests for ModuleBoundaryExtractor using Louvain modularity clustering."""

from analysis.graph import DirectedGraph
from refactor.models import Effort, RefactorType
from refactor.module_extractor import ModuleBoundaryExtractor


def test_extract_module_from_dense_cluster() -> None:
    extractor = ModuleBoundaryExtractor(min_cluster_size=3)
    g = DirectedGraph()

    # Create a dense billing cluster
    billing_nodes = ["BillingService", "BillingRepository", "InvoiceGenerator", "PaymentGateway"]
    for n in billing_nodes:
        g.add_node(n, name=n, node_type="class")

    for i, u in enumerate(billing_nodes):
        for v in billing_nodes[i + 1 :]:
            g.add_edge(u, v)
            g.add_edge(v, u)

    suggestions = extractor.generate_suggestions(g)
    assert len(suggestions) >= 1

    s = suggestions[0]
    assert s.type == RefactorType.EXTRACT_MODULE
    assert s.effort == Effort.M
    assert "Module" in s.title
    assert s.action_details["node_count"] >= 3
    assert s.action_details["cohesion_ratio"] > 0.0
