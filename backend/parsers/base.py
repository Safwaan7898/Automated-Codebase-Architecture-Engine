"""Abstract base class for all language parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from parsers.models import ParseResult


class LanguageParser(ABC):
    """Common interface every language parser must implement.

    Implementations:
        - :class:`parsers.java_parser.JavaParser`
        - :class:`parsers.python_parser.PythonParser`
    """

    @property
    @abstractmethod
    def language(self) -> str:
        """Return the canonical language name, e.g. ``'java'`` or ``'python'``."""

    @property
    @abstractmethod
    def file_extensions(self) -> frozenset[str]:
        """File extensions this parser handles, e.g. ``frozenset({'.java'})``."""

    @abstractmethod
    def parse_file(self, abs_path: Path, rel_path: str, source: str) -> ParseResult:
        """Parse a single source file.

        Args:
            abs_path: Absolute path (for reading, already read into *source*).
            rel_path: Relative path from the repo root — used as stable key.
            source:   Full UTF-8 source text of the file.

        Returns:
            :class:`~parsers.models.ParseResult` — never raises; syntax errors
            go into ``result.errors``.
        """

    def can_handle(self, path: Path) -> bool:
        """Return True if *path*'s extension is in :attr:`file_extensions`."""
        return path.suffix.lower() in self.file_extensions

    def safe_parse_file(self, abs_path: Path, rel_path: str) -> ParseResult:
        """Read *abs_path*, call :meth:`parse_file`, catch all exceptions.

        This is the method called by the parallel runner — it guarantees that
        a broken file can never crash the whole pipeline.
        """
        try:
            source = abs_path.read_text(encoding="utf-8", errors="replace")
            return self.parse_file(abs_path, rel_path, source)
        except Exception as exc:  # noqa: BLE001
            result = ParseResult(file_path=rel_path, language=self.language)
            result.errors.append(f"Fatal error reading/parsing file: {exc}")
            return result
