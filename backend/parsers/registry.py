"""Language detection and parser registry."""

from __future__ import annotations

from pathlib import Path

from parsers.base import LanguageParser

# ── Extension → language map ──────────────────────────────────────────────────

_EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".java": "java",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".cs": "csharp",
    ".rb": "ruby",
    ".kt": "kotlin",
    ".scala": "scala",
    ".swift": "swift",
}

# ── Global parser registry ────────────────────────────────────────────────────

_REGISTRY: dict[str, LanguageParser] = {}
_registry_initialised = False


def _ensure_registry() -> None:
    global _registry_initialised  # noqa: PLW0603
    if _registry_initialised:
        return
    # Import here to avoid circular imports at module load time
    try:
        from parsers.java_parser import JavaParser

        _REGISTRY["java"] = JavaParser()
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning("JavaParser unavailable: %s", exc)

    try:
        from parsers.python_parser import PythonParser

        _REGISTRY["python"] = PythonParser()
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning("PythonParser unavailable: %s", exc)

    _registry_initialised = True


def detect_language_by_extension(path: Path) -> str:
    """Return the canonical language name for a file path, or ``'unknown'``."""
    return _EXT_TO_LANG.get(path.suffix.lower(), "unknown")


def get_parser(language: str) -> LanguageParser | None:
    """Return the parser for *language*, or ``None`` if unsupported."""
    _ensure_registry()
    return _REGISTRY.get(language)


def get_parser_for_file(path: Path) -> LanguageParser | None:
    """Detect language from *path*'s extension and return its parser."""
    lang = detect_language_by_extension(path)
    return get_parser(lang)


def available_languages() -> list[str]:
    """Return a list of language names for which parsers are registered."""
    _ensure_registry()
    return list(_REGISTRY.keys())
