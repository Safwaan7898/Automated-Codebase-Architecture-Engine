"""Tests for optional LLM diff drafting step."""

from refactor.llm_drafter import LLMDiffDrafter
from refactor.models import Effort, RefactorSuggestion, RefactorType


def test_llm_drafter_disabled_fallback() -> None:
    drafter = LLMDiffDrafter(enabled=False)
    suggestion = RefactorSuggestion(
        id="R1",
        type=RefactorType.BREAK_CYCLE,
        title="Break cycle between A and B",
        rationale="Circular dependency",
        affected_nodes=["A", "B"],
        effort=Effort.S,
        priority_score=90.0,
    )

    diff = drafter.generate_draft_diff(suggestion, "code context")
    assert diff is not None
    assert "diff --git" in diff
    assert "Break cycle" in diff


def test_llm_drafter_enabled_with_custom_caller() -> None:
    def mock_caller(context: str, suggestion: RefactorSuggestion) -> str:
        return f"diff --git a/{suggestion.id} b/{suggestion.id}\n+# Custom LLM diff for {suggestion.title}"

    drafter = LLMDiffDrafter(
        api_key="mock-api-key",
        enabled=True,
        custom_caller=mock_caller,
    )

    suggestion = RefactorSuggestion(
        id="R1",
        type=RefactorType.MOVE_METHOD,
        title="Move method foo to Bar",
        rationale="High coupling",
        affected_nodes=["Foo", "Bar"],
        effort=Effort.S,
        priority_score=75.0,
    )

    diff = drafter.generate_draft_diff(suggestion, "code context")
    assert "+# Custom LLM diff for Move method foo to Bar" in diff
