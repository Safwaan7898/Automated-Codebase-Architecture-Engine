"""Tests for GodClassSplitter using community detection on method-field interaction graphs."""

from analysis.graph import DirectedGraph
from refactor.god_class_splitter import GodClassSplitter
from refactor.models import Effort, RefactorType


def test_god_class_splitting_via_method_field_graph() -> None:
    splitter = GodClassSplitter(loc_threshold=200, method_threshold=10)
    g = DirectedGraph()

    g.add_node(
        "com.example.MegaController",
        name="MegaController",
        node_type="class",
        metrics={"loc": 450, "num_methods": 20, "cyclomatic_complexity": 18},
    )

    # Add method nodes contained inside MegaController
    # Cluster 1: Auth domain
    for m in ["login", "logout", "refreshToken"]:
        mid = f"com.example.MegaController#{m}"
        g.add_node(mid, name=m, node_type="method")
        g.add_edge("com.example.MegaController", mid, edge_type="contains")

    # Connect cluster 1 methods
    g.add_edge("com.example.MegaController#login", "com.example.MegaController#refreshToken", edge_type="calls")

    # Cluster 2: Reporting domain
    for m in ["exportCsv", "generatePdf", "sendSummaryEmail"]:
        mid = f"com.example.MegaController#{m}"
        g.add_node(mid, name=m, node_type="method")
        g.add_edge("com.example.MegaController", mid, edge_type="contains")

    # Connect cluster 2 methods
    g.add_edge("com.example.MegaController#exportCsv", "com.example.MegaController#generatePdf", edge_type="calls")

    suggestions = splitter.generate_suggestions(g)
    assert len(suggestions) == 1

    s = suggestions[0]
    assert s.type == RefactorType.SPLIT_GOD_CLASS
    assert s.effort == Effort.L
    assert "MegaController" in s.title
    assert len(s.action_details["extracted_classes"]) >= 2
    assert "Single Responsibility" in s.rationale


def test_compact_class_not_split() -> None:
    splitter = GodClassSplitter(loc_threshold=300, method_threshold=15)
    g = DirectedGraph()
    g.add_node(
        "com.example.SmallHelper",
        name="SmallHelper",
        node_type="class",
        metrics={"loc": 50, "num_methods": 3},
    )

    suggestions = splitter.generate_suggestions(g)
    assert len(suggestions) == 0
