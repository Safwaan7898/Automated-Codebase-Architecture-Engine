"""Data models for the ingestion layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(UTC)


# ── Job status ────────────────────────────────────────────────────────────────


class JobStatus(StrEnum):
    PENDING = "pending"
    FETCHING = "fetching"  # cloning / downloading
    EXTRACTING = "extracting"  # unzipping / untarring
    SCANNING = "scanning"  # language detection
    PARSING = "parsing"  # AST parsing
    ANALYZING = "analyzing"  # graph analysis
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Workspace metadata ────────────────────────────────────────────────────────


@dataclass
class WorkspaceMetadata:
    """Everything callers need to know about an ingested workspace."""

    job_id: str
    source_type: str
    """One of: ``git``, ``archive``, ``archive_url``, ``folder``, ``snippet``, ``local``."""

    display_name: str
    """Human-readable label (URL, filename, …)."""

    repo_name: str
    """Short name derived from the source (repo name, filename stem, …)."""

    workspace_path: Path
    """Root of the job directory, e.g. ``/tmp/archlens/<job_id>/``."""

    src_path: Path
    """Directory containing the sanitised source files — pass this to parsers."""

    language_breakdown: dict[str, int]
    """``{language: file_count}`` for every language detected."""

    primary_language: str
    """The language with the most files."""

    file_count: int
    total_bytes: int

    supported: bool = True
    """False when the primary language has no registered parser yet."""

    skipped_files: int = 0
    skipped_by_dir: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    commit_hash: str | None = None
    branch: str | None = None
    source_hash: str = ""
    """SHA-256 of the source descriptor — used for deduplication."""

    created_at: datetime = field(default_factory=_utc_now)
    expires_at: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_type": self.source_type,
            "display_name": self.display_name,
            "repo_name": self.repo_name,
            "commit_hash": self.commit_hash,
            "branch": self.branch,
            "language_breakdown": self.language_breakdown,
            "primary_language": self.primary_language,
            "file_count": self.file_count,
            "skipped_files": self.skipped_files,
            "skipped_by_dir": self.skipped_by_dir,
            "total_bytes": self.total_bytes,
            "supported": self.supported,
            "warnings": self.warnings,
            "source_hash": self.source_hash,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }


# ── Job events (for WebSocket streaming) ─────────────────────────────────────


@dataclass
class JobEvent:
    job_id: str
    status: JobStatus
    stage: str
    progress_pct: float
    message: str
    timestamp: datetime = field(default_factory=_utc_now)
    error: str | None = None
    metadata: WorkspaceMetadata | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "type": "job_event",
            "job_id": self.job_id,
            "status": str(self.status),
            "stage": self.stage,
            "progress_pct": round(self.progress_pct, 1),
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.error:
            d["error"] = self.error
        if self.metadata:
            d["metadata"] = self.metadata.to_dict()
        return d


# ── Progress reporter ─────────────────────────────────────────────────────────

ProgressReporter = Callable[[JobStatus, str, float, str], Awaitable[None]]
"""Signature: (status, stage, pct, message) → coroutine"""


# ── IngestionSource interface ─────────────────────────────────────────────────


class IngestionSource(ABC):
    """Contract every source implementation must satisfy.

    Each source is responsible for:
    1. Populating ``workspace / 'src' /`` with sanitised source files.
    2. Performing source-specific security checks (archive extraction, SSRF, …).
    3. Reporting progress via *progress*.

    The orchestrator handles: workspace creation, language detection, job
    tracking, deduplication, and cleanup.
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Short type string: ``git``, ``archive``, ``folder``, ``snippet``, ``local``."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable identifier for logs and API responses."""

    @property
    @abstractmethod
    def source_hash(self) -> str:
        """SHA-256 hex of the normalised source descriptor.

        Used for deduplication. Two sources with the same hash produce
        identical workspaces so the second can reuse the first's results.
        """

    @property
    def fingerprint(self) -> str:
        """64-character lowercase SHA-256 hex string."""
        raw = getattr(self, "_hash", "")
        if raw and len(raw) == 64:
            return raw.lower()
        if hasattr(self, "source_hash"):
            parts = self.source_hash.split(":")
            if parts and len(parts[0]) == 64:
                return parts[0].lower()
        return raw.lower()

    @property
    def cache_key(self) -> str:
        """Deterministic cache key: fingerprint:parser_version:settings_hash:language:include_tests"""
        from parsers.fingerprint import PARSER_VERSION, compute_cache_key, compute_settings_hash

        lang = getattr(self, "language", "auto")
        include_tests = getattr(self, "include_tests", False)
        settings_hash = compute_settings_hash({"language": lang, "include_tests": include_tests})
        return compute_cache_key(
            source_fingerprint=self.fingerprint,
            parser_version=PARSER_VERSION,
            settings_hash=settings_hash,
            language=lang,
            include_tests=include_tests,
        )

    @abstractmethod
    async def fetch(
        self,
        src_dir: Path,
        limits: IngestionLimits,
        progress: ProgressReporter,
    ) -> dict[str, Any]:
        """Populate *src_dir* with source files.

        Args:
            src_dir:  Workspace source directory (guaranteed empty, writable).
            limits:   Resource limits — must be enforced by the implementation.
            progress: Async callable for streaming progress updates.

        Returns:
            Extra metadata dict merged into :class:`WorkspaceMetadata`
            (e.g. ``{'commit_hash': '...', 'branch': 'main'}``).

        Raises:
            IngestionError: For all expected error conditions.
        """


# ── Avoid circular import for type hint ──────────────────────────────────────
from ingestion.config import IngestionLimits  # noqa: E402
