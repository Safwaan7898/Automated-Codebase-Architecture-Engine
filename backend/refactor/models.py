"""Data models for architectural refactoring engine.

Defines:
- RefactorType (break_cycle, split_god_class, extract_module, move_method)
- Effort (S, M, L)
- ImpactMetrics (before & after metrics on simulated graph)
- RefactorSuggestion (actionable suggestion with diff and ranking)
- RefactorPlan (aggregated ranked suggestions)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RefactorType(StrEnum):
    BREAK_CYCLE = "break_cycle"
    SPLIT_GOD_CLASS = "split_god_class"
    EXTRACT_MODULE = "extract_module"
    MOVE_METHOD = "move_method"


class Effort(StrEnum):
    S = "S"
    M = "M"
    L = "L"


@dataclass
class ImpactMetrics:
    """Coupling and complexity metrics before and after simulated refactoring."""

    cycles_before: int = 0
    cycles_after: int = 0
    coupling_before: int = 0
    coupling_after: int = 0
    complexity_before: int = 0
    complexity_after: int = 0
    god_classes_before: int = 0
    god_classes_after: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "before": {
                "cycles": self.cycles_before,
                "coupling": self.coupling_before,
                "complexity": self.complexity_before,
                "god_classes": self.god_classes_before,
            },
            "after": {
                "cycles": self.cycles_after,
                "coupling": self.coupling_after,
                "complexity": self.complexity_after,
                "god_classes": self.god_classes_after,
            },
            "improvement": {
                "cycle_reduction": self.cycles_before - self.cycles_after,
                "coupling_reduction": self.coupling_before - self.coupling_after,
                "complexity_reduction": self.complexity_before - self.complexity_after,
                "god_class_reduction": self.god_classes_before - self.god_classes_after,
            },
            "details": self.details,
        }


@dataclass
class RefactorSuggestion:
    """A concrete, ranked architectural refactoring suggestion."""

    id: str
    type: RefactorType
    title: str
    rationale: str
    affected_nodes: list[str]
    effort: Effort
    priority_score: float
    rank: int = 0
    metrics: ImpactMetrics = field(default_factory=ImpactMetrics)
    action_details: dict[str, Any] = field(default_factory=dict)
    diff: str | None = None
    llm_assisted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": str(self.type),
            "title": self.title,
            "rationale": self.rationale,
            "affected_nodes": self.affected_nodes,
            "effort": str(self.effort),
            "priority_score": round(self.priority_score, 2),
            "rank": self.rank,
            "metrics": self.metrics.to_dict(),
            "action_details": self.action_details,
            "diff": self.diff,
            "llm_assisted": self.llm_assisted,
        }


@dataclass
class RefactorPlan:
    """Ordered collection of refactoring suggestions."""

    total_suggestions: int
    suggestions: list[RefactorSuggestion] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_suggestions": self.total_suggestions,
            "summary": self.summary,
            "suggestions": [s.to_dict() for s in self.suggestions],
        }
