"""Evaluation logic computing precision, recall, and F1 against gold standards."""

from __future__ import annotations

import time
from typing import Set, Tuple
from app.models.graph import AnalysisResult
from .models import BenchmarkMetric, GoldStandard, LanguageBenchmarkResult


def evaluate_accuracy(result: AnalysisResult, gold: GoldStandard, execution_time_ms: float = 0.0) -> LanguageBenchmarkResult:
    """Evaluate an AnalysisResult against ground truth GoldStandard."""
    # 1. Extracted nodes
    extracted_node_ids: set[str] = {n.id for n in result.graph.nodes}
    # Add internal endpoints of edges (ignoring external library imports)
    external_prefixes = ("java.", "javax.", "org.springframework.", "org.apache.", "react", "lodash", "pydantic", "requests", "os", "sys")
    for edge in result.graph.edges:
        if not any(edge.source.startswith(p) for p in external_prefixes):
            extracted_node_ids.add(edge.source)
        if not any(edge.target.startswith(p) for p in external_prefixes):
            extracted_node_ids.add(edge.target)

    # Calculate metrics based on gold vs extracted internal codebase nodes
    node_metrics = BenchmarkMetric.calculate(gold.expected_nodes, extracted_node_ids)

    # 2. Extracted edges
    # Standardize edge tuples
    extracted_edges: set[tuple[str, str]] = set()
    for edge in result.graph.edges:
        src = edge.source
        dst = edge.target
        # Only evaluate internal dependency edges (present in gold or within codebase)
        extracted_edges.add((src, dst))

    # If gold standard focuses on internal dependencies, filter extracted edges
    # to those whose endpoints are internal or in gold
    filtered_extracted_edges = {
        e for e in extracted_edges
        if e in gold.expected_edges or (
            any(e[0].startswith(n) for n in gold.expected_nodes) and
            any(e[1].startswith(n) for n in gold.expected_nodes)
        )
    }

    edge_metrics = BenchmarkMetric.calculate(gold.expected_edges, filtered_extracted_edges)

    # 3. Cycles comparison
    # Normalize cycle representation: sorted tuples of node sets
    gold_cycles_normalized = {
        tuple(sorted(c)) for c in gold.expected_cycles
    }
    detected_cycles_normalized = {
        tuple(sorted(c)) for c in result.cycles
    }

    cycles_match = (gold_cycles_normalized == detected_cycles_normalized)

    return LanguageBenchmarkResult(
        language=gold.language,
        fixture_name=gold.fixture_path.split("/")[-1].split("\\")[-1],
        total_nodes_gold=len(gold.expected_nodes),
        total_nodes_extracted=len(extracted_node_ids),
        node_metrics=node_metrics,
        total_edges_gold=len(gold.expected_edges),
        total_edges_extracted=len(filtered_extracted_edges),
        edge_metrics=edge_metrics,
        cycles_detected=len(result.cycles),
        expected_cycles=len(gold.expected_cycles),
        cycles_match=cycles_match,
        execution_time_ms=round(execution_time_ms, 2),
    )
