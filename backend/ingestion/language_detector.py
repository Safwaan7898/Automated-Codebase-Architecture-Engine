"""Language detection and workspace scanning.

Provides:
- Detection by file extension and shebang / magic content.
- Binary file detection (skip binary files).
- Language breakdown computation and primary language determination.
- Clear user-facing warnings for unsupported languages.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from ingestion.config import IngestionLimits

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES: set[str] = {"java", "python"}

# Extension mappings (case-insensitive)
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "Python",
    ".pyi": "Python",
    ".pyx": "Python",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".scala": "Scala",
    ".swift": "Swift",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".bat": "Batch",
    ".cmd": "Batch",
    ".ps1": "PowerShell",
    ".toml": "TOML",
    ".ini": "INI",
    ".cfg": "Config",
    ".dockerfile": "Dockerfile",
}

# Known binary extensions to skip immediately
BINARY_EXTENSIONS: set[str] = {
    ".class",
    ".pyc",
    ".pyo",
    ".so",
    ".dll",
    ".dylib",
    ".exe",
    ".bin",
    ".jar",
    ".war",
    ".ear",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".svg",
    ".bmp",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".mp3",
    ".mp4",
    ".wav",
    ".avi",
    ".mov",
    ".flv",
    ".db",
    ".sqlite",
    ".sqlite3",
}


def is_binary_file(path: Path) -> bool:
    """Return True if file is binary by extension or null-byte check."""
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with path.open("rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
    except OSError:
        return True
    return False


def detect_file_language(path: Path) -> str:
    """Detect language of a single file from extension or filename."""
    name_lower = path.name.lower()
    if name_lower == "dockerfile":
        return "Dockerfile"
    if name_lower == "makefile":
        return "Makefile"

    suffix = path.suffix.lower()
    if suffix in EXTENSION_TO_LANGUAGE:
        return EXTENSION_TO_LANGUAGE[suffix]

    return "Unknown"


@dataclass
class ScanResult:
    language_breakdown: dict[str, int]
    primary_language: str
    file_count: int
    total_bytes: int
    supported: bool
    warnings: list[str]


def scan_workspace(src_dir: Path, limits: IngestionLimits) -> ScanResult:
    """Walk src_dir, skipping vendored/build dirs and binaries, computing language stats.

    Returns ScanResult with breakdown, primary language, and helpful warnings.
    """
    skip_set = {d.lower() for d in limits.skip_dirs}
    counts: Counter[str] = Counter()
    total_bytes = 0
    total_files = 0
    warnings: list[str] = []

    if not src_dir.exists():
        return ScanResult(
            language_breakdown={},
            primary_language="Unknown",
            file_count=0,
            total_bytes=0,
            supported=False,
            warnings=["Source directory does not exist."],
        )

    for entry in sorted(src_dir.rglob("*"), key=lambda p: p.as_posix()):
        if entry.is_symlink():
            continue

        # Skip ignored directory trees
        rel_parts = entry.relative_to(src_dir).parts
        if any(part.lower() in skip_set for part in rel_parts[:-1]):
            continue

        if entry.is_dir():
            continue

        if entry.is_file():
            # Check size limit
            try:
                size = entry.stat().st_size
            except OSError:
                continue

            if size > limits.max_file_size_bytes:
                warnings.append(f"Skipped large file: {entry.relative_to(src_dir).as_posix()} ({size} bytes > limit).")
                continue

            if is_binary_file(entry):
                continue

            total_files += 1
            total_bytes += size
            lang = detect_file_language(entry)
            counts[lang] += 1

    breakdown = dict(counts.most_common())

    if not breakdown:
        return ScanResult(
            language_breakdown={},
            primary_language="Unknown",
            file_count=0,
            total_bytes=0,
            supported=False,
            warnings=["No text or source code files found in repository."],
        )

    # Determine primary language
    # Prioritize code languages over config/docs if both exist
    non_code = {"Markdown", "JSON", "YAML", "XML", "TOML", "INI", "Config", "Unknown"}
    code_counts = {k: v for k, v in breakdown.items() if k not in non_code}
    if code_counts:
        primary = max(code_counts, key=lambda k: code_counts[k])
    else:
        primary = max(breakdown, key=lambda k: breakdown[k])

    is_supported = primary.lower() in SUPPORTED_LANGUAGES

    if not is_supported:
        supported_str = ", ".join(sorted(lang.capitalize() for lang in SUPPORTED_LANGUAGES))
        warnings.append(
            f"Primary detected language is '{primary}', which is not yet supported for deep AST analysis. "
            f"Currently supported languages: {supported_str}."
        )

    # Inform user about other unsupported languages present
    unsupported_present = [
        f"{lang} ({cnt} files)"
        for lang, cnt in breakdown.items()
        if lang.lower() not in SUPPORTED_LANGUAGES and lang not in ("Markdown", "Unknown") and lang != primary
    ]
    if unsupported_present:
        warnings.append(f"Additional unsupported language files present: {', '.join(unsupported_present)}.")

    return ScanResult(
        language_breakdown=breakdown,
        primary_language=primary,
        file_count=total_files,
        total_bytes=total_bytes,
        supported=is_supported,
        warnings=warnings,
    )
