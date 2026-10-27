"""Ingestion configuration — ignore patterns, parallelism settings."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

# ── Default ignore sets ────────────────────────────────────────────────────────

_DEFAULT_IGNORE_DIRS: list[str] = [
    # Build artefacts
    "build",
    "dist",
    "out",
    "target",
    "bin",
    "obj",
    ".output",
    # Dependency trees
    "node_modules",
    "vendor",
    ".gradle",
    "bower_components",
    # VCS / caches
    ".git",
    ".svn",
    ".hg",
    # Python caches
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    # Virtualenvs
    "venv",
    ".venv",
    "env",
    ".env",
    ".virtualenv",
    # IDEs
    ".idea",
    ".vscode",
    ".eclipse",
    # Coverage / reports
    "htmlcov",
    "coverage",
    ".coverage",
    # Misc
    ".eggs",
    "*.egg-info",
]

_DEFAULT_IGNORE_PATTERNS: list[str] = [
    # Compiled artefacts
    "*.class",
    "*.jar",
    "*.war",
    "*.ear",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    # Lock files
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    # Generated / minified
    "*.min.js",
    "*.bundle.js",
    "*.map",
    # Database
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    # Docs / data
    "*.pdf",
    "*.png",
    "*.jpg",
    "*.gif",
    "*.ico",
]

_TEST_DIR_PATTERNS: list[str] = [
    "test",
    "tests",
    "Test",
    "Tests",
    "spec",
    "Spec",
    "__tests__",
    "integration-test",
    "it",
]

_TEST_FILE_PATTERNS: list[str] = [
    "*Test.java",
    "*Tests.java",
    "*IT.java",
    "*Spec.java",
    "test_*.py",
    "*_test.py",
]


def _compile_glob(pattern: str) -> re.Pattern[str]:
    """Convert a simple glob pattern to a compiled regex."""
    escaped = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
    return re.compile(f"^{escaped}$", re.IGNORECASE)


@dataclass
class IngestionConfig:
    """Controls which files are collected and how parsing is parallelised."""

    # ── Ignore lists ──────────────────────────────────────────────────────────
    ignore_dirs: list[str] = field(default_factory=lambda: list(_DEFAULT_IGNORE_DIRS))
    """Directory names (not paths) to skip entirely."""

    ignore_file_patterns: list[str] = field(default_factory=lambda: list(_DEFAULT_IGNORE_PATTERNS))
    """Glob patterns for individual file names to skip."""

    include_test_files: bool = False
    """When False, directories and files matching test patterns are excluded."""

    # ── File limits ────────────────────────────────────────────────────────────
    max_file_size_bytes: int = 2_000_000  # 2 MB
    """Files larger than this are skipped (likely generated/binary)."""

    max_files: int = 50_000
    """Maximum number of files allowed to be parsed from a repository."""

    parse_timeout_s: int = 300
    """Maximum total seconds allowed for parsing a repository."""

    # ── Parallelism ────────────────────────────────────────────────────────────
    max_workers: int = field(default_factory=lambda: min(12, (os.cpu_count() or 1) + 4))
    """Thread-pool worker count for parallel file parsing."""

    # ── Language scope ─────────────────────────────────────────────────────────
    supported_languages: list[str] = field(default_factory=lambda: ["python", "java"])
    """Only files whose language is in this list will be parsed."""

    # ── Clone settings ─────────────────────────────────────────────────────────
    clone_depth: int = 1
    """Shallow-clone depth when ingesting a GitHub URL."""

    clone_timeout_s: int = 120
    """Maximum seconds to wait for a git clone to complete."""

    # ── Internal (compiled) ────────────────────────────────────────────────────
    def __post_init__(self) -> None:
        self._ignore_dir_set: frozenset[str] = frozenset(
            d.lower() for d in (self.ignore_dirs + (_TEST_DIR_PATTERNS if not self.include_test_files else []))
        )
        self._ignore_file_regexes: list[re.Pattern[str]] = [_compile_glob(p) for p in self.ignore_file_patterns] + (
            [_compile_glob(p) for p in _TEST_FILE_PATTERNS] if not self.include_test_files else []
        )

    def should_ignore_dir(self, dir_name: str) -> bool:
        """Return True if a directory should be skipped entirely."""
        return dir_name.lower() in self._ignore_dir_set

    def should_ignore_file(self, file_path: Path) -> bool:
        """Return True if a file should be skipped."""
        name = file_path.name
        if file_path.stat().st_size > self.max_file_size_bytes:
            return True
        return any(rx.match(name) for rx in self._ignore_file_regexes)

    def is_supported_file(self, file_path: Path) -> bool:
        """Return True if the file's language is in ``supported_languages``."""
        from parsers.registry import detect_language_by_extension

        lang = detect_language_by_extension(file_path)
        return lang in self.supported_languages
