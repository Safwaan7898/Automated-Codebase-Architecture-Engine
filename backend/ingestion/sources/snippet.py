"""Single file and pasted code snippet ingestion source.

Supports:
- Pasted code snippets with a language selector (e.g. Python, Java)
- Single or multiple file uploads
- Maps language to appropriate file extension
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ingestion.config import IngestionLimits
from ingestion.exceptions import LimitExceeded, SecurityError
from ingestion.hash_utils import hash_snippet
from ingestion.models import IngestionSource, JobStatus, ProgressReporter

logger = logging.getLogger(__name__)

LANGUAGE_TO_EXTENSION: dict[str, str] = {
    "python": ".py",
    "py": ".py",
    "java": ".java",
    "javascript": ".js",
    "js": ".js",
    "typescript": ".ts",
    "ts": ".ts",
    "go": ".go",
    "rust": ".rs",
    "c": ".c",
    "cpp": ".cpp",
    "c++": ".cpp",
    "csharp": ".cs",
    "c#": ".cs",
    "ruby": ".rb",
    "php": ".php",
    "kotlin": ".kt",
}


class SnippetSource(IngestionSource):
    """Ingests a pasted code snippet or single file."""

    def __init__(
        self,
        code: str,
        language: str,
        filename: str | None = None,
    ) -> None:
        self.code = code
        self.language = language.strip().lower()
        ext = LANGUAGE_TO_EXTENSION.get(self.language, ".txt")
        self.filename = filename or f"snippet{ext}"
        has_known_ext = any(self.filename.endswith(e) for e in LANGUAGE_TO_EXTENSION.values())
        if not self.filename.endswith(ext) and not has_known_ext:
            self.filename = f"{self.filename}{ext}"

    @property
    def source_type(self) -> str:
        return "snippet"

    @property
    def display_name(self) -> str:
        return f"{self.filename} ({self.language.capitalize()})"

    @property
    def repo_name(self) -> str:
        return Path(self.filename).stem or "snippet"

    @property
    def source_hash(self) -> str:
        return hash_snippet(self.code, self.language)

    async def fetch(
        self,
        src_dir: Path,
        limits: IngestionLimits,
        progress: ProgressReporter,
    ) -> dict[str, Any]:
        await progress(JobStatus.EXTRACTING, "saving_snippet", 20.0, f"Writing snippet '{self.filename}'")

        code_bytes = self.code.encode("utf-8")
        if len(code_bytes) > limits.max_file_size_bytes:
            msg = (
                f"Snippet size ({len(code_bytes)} bytes) exceeds single file "
                f"limit ({limits.max_file_size_bytes} bytes)."
            )
            raise LimitExceeded(msg)

        # Path traversal guard for custom filename
        parts = Path(self.filename).parts
        if ".." in parts:
            raise SecurityError(f"Path traversal in snippet filename: '{self.filename}'")

        target_file = (src_dir / self.filename).resolve()
        try:
            target_file.relative_to(src_dir.resolve())
        except ValueError:
            raise SecurityError(f"Snippet filename '{self.filename}' resolves outside workspace.") from None

        target_file.parent.mkdir(parents=True, exist_ok=True)
        with target_file.open("wb") as f:
            f.write(code_bytes)

        await progress(JobStatus.EXTRACTING, "complete", 100.0, f"Saved '{self.filename}'.")

        return {
            "filename": self.filename,
            "language": self.language,
            "bytes": len(code_bytes),
        }
