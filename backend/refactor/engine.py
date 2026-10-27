"""Refactor engine: orchestrates cycle breaking, god class splitting, module extraction, and method moves."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from refactor.cycle_breaker import CycleBreaker
from refactor.god_class_splitter import GodClassSplitter
from refactor.llm_drafter import LLMDiffDrafter
from refactor.method_mover import MethodMover
from refactor.models import RefactorPlan, RefactorSuggestion, RefactorType
from refactor.module_extractor import ModuleBoundaryExtractor
from refactor.simulation import GraphRefactorSimulator

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph

logger = logging.getLogger(__name__)


class RefactorEngine:
    """Orchestrates generation, graph simulation, ranking, and drafting of refactor suggestions."""

    def __init__(
        self,
        cycle_breaker: CycleBreaker | None = None,
        god_class_splitter: GodClassSplitter | None = None,
        module_extractor: ModuleBoundaryExtractor | None = None,
        method_mover: MethodMover | None = None,
        simulator: GraphRefactorSimulator | None = None,
        llm_drafter: LLMDiffDrafter | None = None,
    ) -> None:
        self.cycle_breaker = cycle_breaker or CycleBreaker()
        self.god_class_splitter = god_class_splitter or GodClassSplitter()
        self.module_extractor = module_extractor or ModuleBoundaryExtractor()
        self.method_mover = method_mover or MethodMover()
        self.simulator = simulator or GraphRefactorSimulator()
        self.llm_drafter = llm_drafter or LLMDiffDrafter()

    def generate_plan(
        self,
        graph: DirectedGraph,
        repo_root: Path | str = ".",
        enable_llm: bool = False,
    ) -> RefactorPlan:
        """Generate a complete, ranked, and simulated refactoring plan for an architecture graph."""
        raw_suggestions: list[RefactorSuggestion] = []

        # 1. Generate suggestions across all 4 dimensions
        raw_suggestions.extend(self.cycle_breaker.generate_suggestions(graph))
        raw_suggestions.extend(self.god_class_splitter.generate_suggestions(graph))
        raw_suggestions.extend(self.module_extractor.generate_suggestions(graph))
        raw_suggestions.extend(self.method_mover.generate_suggestions(graph))

        # 2. Run graph simulation to compute before & after metrics
        for s in raw_suggestions:
            metrics = self.simulator.simulate(graph, s)
            s.metrics = metrics

            # Boost priority based on measurable simulated improvements
            improvement_boost = (
                (metrics.cycles_before - metrics.cycles_after) * 25.0
                + (metrics.god_classes_before - metrics.god_classes_after) * 15.0
                + (metrics.coupling_before - metrics.coupling_after) * 2.0
            )
            s.priority_score += max(0.0, improvement_boost)

            # 3. Optional LLM diff generation
            if enable_llm or self.llm_drafter.enabled:
                context = self.llm_drafter.extract_code_context(s, repo_root)
                s.diff = self.llm_drafter.generate_draft_diff(s, context)
                s.llm_assisted = bool(self.llm_drafter.enabled and self.llm_drafter.api_key)

        # 4. Deterministic Ranking
        # Priority score desc, then type asc, then primary affected node asc, then title asc
        ranked_suggestions = sorted(
            raw_suggestions,
            key=lambda item: (
                -item.priority_score,
                str(item.type),
                item.affected_nodes[0] if item.affected_nodes else "",
                item.title,
            ),
        )

        for rank_idx, s in enumerate(ranked_suggestions, 1):
            s.rank = rank_idx

        # 5. Summary statistics
        by_type = {
            "break_cycle": sum(1 for s in ranked_suggestions if s.type == RefactorType.BREAK_CYCLE),
            "split_god_class": sum(1 for s in ranked_suggestions if s.type == RefactorType.SPLIT_GOD_CLASS),
            "extract_module": sum(1 for s in ranked_suggestions if s.type == RefactorType.EXTRACT_MODULE),
            "move_method": sum(1 for s in ranked_suggestions if s.type == RefactorType.MOVE_METHOD),
        }
        total_cycle_reduction = sum(s.metrics.cycles_before - s.metrics.cycles_after for s in ranked_suggestions)
        total_coupling_reduction = sum(s.metrics.coupling_before - s.metrics.coupling_after for s in ranked_suggestions)

        summary = {
            "total_suggestions": len(ranked_suggestions),
            "by_type": by_type,
            "total_cycle_reduction": total_cycle_reduction,
            "total_coupling_reduction": total_coupling_reduction,
            "llm_enabled": self.llm_drafter.enabled or enable_llm,
        }

        return RefactorPlan(
            total_suggestions=len(ranked_suggestions),
            suggestions=ranked_suggestions,
            summary=summary,
        )


# Default global singleton
default_refactor_engine = RefactorEngine()
