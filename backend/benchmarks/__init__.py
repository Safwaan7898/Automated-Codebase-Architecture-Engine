"""ArchLens Accuracy Benchmarking Framework for Tier 1 Languages.

Evaluates AST parsing accuracy, node/symbol extraction, dependency edge resolution,
and cycle detection precision/recall/F1 against curated ground-truth gold sets.
"""

from .evaluator import evaluate_accuracy
from .gold_sets import GOLD_STANDARDS
from .models import BenchmarkMetric, BenchmarkSuiteResult, GoldStandard, LanguageBenchmarkResult
from .runner import run_all_benchmarks

__all__ = [
    "GoldStandard",
    "BenchmarkMetric",
    "LanguageBenchmarkResult",
    "BenchmarkSuiteResult",
    "GOLD_STANDARDS",
    "evaluate_accuracy",
    "run_all_benchmarks",
]
