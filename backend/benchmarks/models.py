"""Pydantic models for accuracy benchmarks."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class BenchmarkMetric(BaseModel):
    """Precision, recall, and F1 accuracy metric container."""

    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 1.0
    recall: float = 1.0
    f1: float = 1.0

    @classmethod
    def calculate(cls, expected: set[Any], actual: set[Any]) -> BenchmarkMetric:
        tp = len(expected & actual)
        fp = len(actual - expected)
        fn = len(expected - actual)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        return cls(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
        )


class GoldStandard(BaseModel):
    """Ground truth expectations for a reference codebase fixture."""

    language: str
    fixture_path: str
    expected_nodes: set[str] = Field(default_factory=set)
    expected_edges: set[tuple[str, str]] = Field(default_factory=set)
    expected_cycles: list[list[str]] = Field(default_factory=list)
    description: str = ""


class LanguageBenchmarkResult(BaseModel):
    """Benchmark results for a single programming language / fixture."""

    language: str
    fixture_name: str
    total_nodes_gold: int
    total_nodes_extracted: int
    node_metrics: BenchmarkMetric
    total_edges_gold: int
    total_edges_extracted: int
    edge_metrics: BenchmarkMetric
    cycles_detected: int
    expected_cycles: int
    cycles_match: bool
    execution_time_ms: float


class BenchmarkSuiteResult(BaseModel):
    """Overall benchmark evaluation suite output."""

    timestamp: str
    version: str
    results: list[LanguageBenchmarkResult] = Field(default_factory=list)
    overall_node_f1: float = 0.0
    overall_edge_f1: float = 0.0
    total_execution_time_ms: float = 0.0
