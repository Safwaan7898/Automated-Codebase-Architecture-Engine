"""Abstract base class for all language analyzers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.models.graph import AnalysisResult
from app.models.refactor import Smell


class BaseAnalyzer(ABC):
    """Contract that every language analyzer must fulfill."""

    @property
    @abstractmethod
    def language(self) -> str:
        """Return the language identifier (e.g. 'python', 'java')."""

    @abstractmethod
    def can_handle(self, path: Path) -> bool:
        """Return True if this analyzer can process the given path."""

    @abstractmethod
    def analyze(self, root: Path, include_tests: bool = False) -> AnalysisResult:
        """
        Traverse *root* and build a dependency graph + analysis result.

        Args:
            root: Absolute path to the repo / directory root.
            include_tests: Whether to include tests, fixtures, samples, migrations, docs.

        Returns:
            AnalysisResult containing the graph, metadata, and detected smells.
        """

    @abstractmethod
    def detect_smells(self, result: AnalysisResult) -> list[Smell]:
        """
        Inspect an AnalysisResult and return detected architectural smells.

        Args:
            result: A completed AnalysisResult from :meth:`analyze`.

        Returns:
            List of Smell instances (may be empty).
        """
