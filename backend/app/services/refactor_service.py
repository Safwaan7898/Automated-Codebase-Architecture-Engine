"""Refactoring suggestion service.

Aggregates smells from an AnalysisResult and produces high-level
Suggestion objects ranked by impact.
"""

from __future__ import annotations

from app.models.graph import AnalysisResult
from app.models.refactor import SmellType, Suggestion


def generate_suggestions(result: AnalysisResult) -> list[Suggestion]:
    """
    Generate refactoring suggestions from an analysis result.

    Args:
        result: Completed AnalysisResult (smells must be populated).

    Returns:
        List of Suggestion objects ordered by impact (high → low).
    """
    smells_by_type: dict[str, list[dict]] = {}
    for smell in result.smells:
        smell_type = smell.get("type", "unknown")
        smells_by_type.setdefault(smell_type, []).append(smell)

    suggestions: list[Suggestion] = []

    # ── God modules → Extract Services ──────────────────────────────────────
    if SmellType.GOD_MODULE in smells_by_type:
        affected = [s.get("file", "") for s in smells_by_type[SmellType.GOD_MODULE]]
        suggestions.append(
            Suggestion(
                title="Extract God Modules into Smaller Services",
                description=(
                    f"{len(affected)} module(s) exceed the line threshold. "
                    "Each should be decomposed by responsibility into separate modules or packages."
                ),
                affected_files=affected,
                effort="high",
                impact="high",
            )
        )

    # ── Circular imports → Introduce Abstraction ─────────────────────────────
    if SmellType.CIRCULAR_IMPORT in smells_by_type:
        affected = [s.get("file", "") for s in smells_by_type[SmellType.CIRCULAR_IMPORT]]
        suggestions.append(
            Suggestion(
                title="Break Circular Import Cycles",
                description=(
                    f"{len(affected)} circular import(s) detected. "
                    "Introduce an interface module or move shared definitions to a common utility module."
                ),
                affected_files=affected,
                effort="medium",
                impact="high",
            )
        )

    # ── Large classes → SRP ──────────────────────────────────────────────────
    if SmellType.LARGE_CLASS in smells_by_type:
        affected = [s.get("file", "") for s in smells_by_type[SmellType.LARGE_CLASS]]
        suggestions.append(
            Suggestion(
                title="Apply Single Responsibility to Large Classes",
                description=(
                    f"{len(affected)} class(es) are too large. "
                    "Apply the Single Responsibility Principle and extract cohesive groups of methods."
                ),
                affected_files=affected,
                effort="medium",
                impact="medium",
            )
        )

    # ── Deep inheritance → Composition ──────────────────────────────────────
    if SmellType.DEEP_INHERITANCE in smells_by_type:
        affected = [s.get("file", "") for s in smells_by_type[SmellType.DEEP_INHERITANCE]]
        suggestions.append(
            Suggestion(
                title="Prefer Composition Over Deep Inheritance",
                description=(
                    f"{len(affected)} class(es) have deep inheritance chains. "
                    "Flatten hierarchies using mixins or strategy pattern."
                ),
                affected_files=affected,
                effort="high",
                impact="medium",
            )
        )

    # Sort by impact (high → medium → low)
    impact_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda s: impact_order.get(s.impact, 99))
    return suggestions
