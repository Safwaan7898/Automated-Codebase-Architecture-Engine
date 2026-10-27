"""Tests for Phase 7 Insights SVG chart generators."""

from reports.svg_charts import (
    generate_blast_radius_svg,
    generate_dsm_svg,
    generate_instability_abstractness_svg,
    generate_treemap_svg,
)


def test_dsm_svg_empty_and_populated() -> None:
    # 1. Empty state
    svg_empty = generate_dsm_svg([], [])
    assert "<svg" in svg_empty
    assert "No modules available" in svg_empty

    # 2. Populated with cycle
    nodes = [{"id": "mod_a", "label": "ModuleA"}, {"id": "mod_b", "label": "ModuleB"}]
    edges = [
        {"source": "mod_a", "target": "mod_b", "is_cycle": True},
        {"source": "mod_b", "target": "mod_a", "is_cycle": True},
    ]
    svg_pop = generate_dsm_svg(nodes, edges)
    assert "<svg" in svg_pop
    assert "DEPENDENCY STRUCTURE MATRIX" in svg_pop
    assert "ModuleA" in svg_pop
    assert "#fee2e2" in svg_pop  # Red cycle highlight


def test_treemap_svg_empty_and_populated() -> None:
    # 1. Empty state
    svg_empty = generate_treemap_svg([])
    assert "<svg" in svg_empty
    assert "No nodes available" in svg_empty

    # 2. Populated
    nodes = [
        {"id": "a", "label": "A", "loc": 500, "complexity": 30},
        {"id": "b", "label": "B", "loc": 200, "complexity": 15},
        {"id": "c", "label": "C", "loc": 50, "complexity": 5},
    ]
    svg_pop = generate_treemap_svg(nodes)
    assert "<svg" in svg_pop
    assert "LOC TREEMAP" in svg_pop
    assert "500 LOC" in svg_pop
    assert "#ef4444" in svg_pop  # High complexity red


def test_blast_radius_svg_empty_and_populated() -> None:
    # 1. Empty state
    svg_empty = generate_blast_radius_svg("", [], [])
    assert "<svg" in svg_empty
    assert "No components" in svg_empty

    # 2. Populated with dependents
    nodes = [
        {"id": "core", "label": "Core"},
        {"id": "service", "label": "Service"},
        {"id": "api", "label": "API"},
    ]
    edges = [
        {"source": "service", "target": "core"},
        {"source": "api", "target": "service"},
    ]
    svg_pop = generate_blast_radius_svg("core", nodes, edges)
    assert "<svg" in svg_pop
    assert "BLAST RADIUS IMPACT RINGS" in svg_pop
    assert "Level 1 Direct" in svg_pop
    assert "Level 2 Transitive" in svg_pop


def test_instability_abstractness_svg() -> None:
    metrics = [
        {"package_name": "app.core", "instability": 0.1, "abstractness": 0.8},
        {"package_name": "app.api", "instability": 0.9, "abstractness": 0.1},
    ]
    svg = generate_instability_abstractness_svg(metrics)
    assert "<svg" in svg
    assert "MARTIN INSTABILITY" in svg
    assert "Main Sequence Line" in svg
    assert "ZONE OF PAIN" in svg
    assert "ZONE OF USELESSNESS" in svg
