"""Tests verifying benchmark execution and accuracy metrics for Tier 1 languages."""

import pytest
from benchmarks.runner import run_all_benchmarks
from benchmarks.gold_sets import GOLD_STANDARDS


def test_tier1_benchmark_suite_execution():
    """Verify that all Tier 1 benchmarks run cleanly and meet accuracy thresholds."""
    suite = run_all_benchmarks(output_json=True, output_docs=False)

    assert len(suite.results) == 4, f"Expected 4 Tier 1 language results, got {len(suite.results)}"
    assert suite.overall_node_f1 >= 0.95, f"Expected node F1 >= 0.95, got {suite.overall_node_f1}"
    assert suite.overall_edge_f1 >= 0.95, f"Expected edge F1 >= 0.95, got {suite.overall_edge_f1}"

    results_by_lang = {r.language: r for r in suite.results}

    for lang in ["python", "java", "javascript", "go"]:
        assert lang in results_by_lang, f"Missing benchmark result for language '{lang}'"
        r = results_by_lang[lang]

        # Verify precision, recall, and F1
        assert r.node_metrics.f1 >= 0.90, f"{lang} node F1 below 0.90: {r.node_metrics.f1}"
        assert r.edge_metrics.f1 >= 0.90, f"{lang} edge F1 below 0.90: {r.edge_metrics.f1}"

        # Verify cycle detection match
        assert r.cycles_match is True, f"{lang} cycle detection did not match gold standard"
        assert r.cycles_detected == r.expected_cycles, (
            f"{lang} cycles count mismatch: expected {r.expected_cycles}, got {r.cycles_detected}"
        )


def test_gold_standards_consistency():
    """Verify that all gold standards specify valid paths and non-empty expectations."""
    for lang, gold in GOLD_STANDARDS.items():
        assert gold.language == lang
        assert len(gold.expected_nodes) > 0, f"{lang} gold standard has empty expected_nodes"
        assert len(gold.expected_edges) > 0, f"{lang} gold standard has empty expected_edges"


def test_hand_labelled_30_edges_and_reference_repos():
    """Verify that exactly 30 hand-labelled reference edges exist per Tier 1 language."""
    from benchmarks.gold_sets import HAND_LABELLED_GOLD_EDGES, REFERENCE_REPOS

    tier1_langs = ["python", "javascript", "go", "java"]

    for lang in tier1_langs:
        assert lang in HAND_LABELLED_GOLD_EDGES, f"Missing 30 gold edges for '{lang}'"
        edges = HAND_LABELLED_GOLD_EDGES[lang]
        assert len(edges) == 30, f"Expected exactly 30 gold edges for '{lang}', got {len(edges)}"

        # Validate edge tuples
        for src, dst in edges:
            assert isinstance(src, str) and len(src) > 0
            assert isinstance(dst, str) and len(dst) > 0
            assert src != dst, f"Self-loop detected in gold set edge: {src} -> {dst}"

        # Validate reference repos
        assert lang in REFERENCE_REPOS, f"Missing reference repos for '{lang}'"
        assert len(REFERENCE_REPOS[lang]) == 3, (
            f"Expected 3 pinned repos for '{lang}', got {len(REFERENCE_REPOS[lang])}"
        )
        for repo in REFERENCE_REPOS[lang]:
            assert "name" in repo and len(repo["name"]) > 0
            assert "commit" in repo and len(repo["commit"]) >= 7
            assert "tool" in repo and len(repo["tool"]) > 0


def test_external_benchmark_results_schema():
    """Verify that external benchmark results exist and contain required keys and honest reasons."""
    import json
    from pathlib import Path

    results_file = (
        Path(__file__).resolve().parent.parent / "benchmarks" / "results" / "external_benchmarks_results.json"
    )
    assert results_file.exists(), "external_benchmarks_results.json must exist after benchmark run"

    with open(results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "parser_version" in data
    assert "timestamp" in data
    assert "results" in data
    assert len(data["results"]) >= 12, (
        f"Expected at least 12 pinned repository benchmark results, got {len(data['results'])}"
    )

    for row in data["results"]:
        assert "language" in row
        assert "repository" in row
        assert "reference_tool" in row
        assert "tool_status" in row
        assert "honest_reason" in row
        if row["tool_status"] == "verified":
            assert row["precision"] is not None
            assert row["recall"] is not None
            assert row["f1"] is not None
        else:
            assert "not externally verified" in row["tool_status"]
            assert len(row["tool_status_reason"]) > 0
