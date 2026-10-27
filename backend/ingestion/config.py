"""Ingestion resource limits and security settings.

All tuneable via environment variables; everything has a safe default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

_MB = 1024 * 1024


def _env_int(key: str, default: int) -> int:
    return int(os.environ.get(key, default))


def _env_bool(key: str, default: bool) -> bool:
    return os.environ.get(key, str(default)).lower() in ("1", "true", "yes")


def _env_float(key: str, default: float) -> float:
    return float(os.environ.get(key, default))


@dataclass
class IngestionLimits:
    """All resource limits controlling ingestion behaviour.

    Change defaults at startup via environment variables or by constructing
    a custom ``IngestionLimits`` and passing it to the orchestrator.
    """

    # ── Size / count ──────────────────────────────────────────────────────────
    max_compressed_bytes: int = 100 * _MB
    """Maximum size of a compressed/downloaded archive (bytes)."""

    max_uncompressed_bytes: int = 500 * _MB
    """Maximum total uncompressed bytes extracted from an archive."""

    max_files: int = 50_000
    """Maximum number of files allowed in a workspace."""

    max_file_size_bytes: int = 5 * _MB
    """Maximum size of a single file (larger files are skipped)."""

    # ── Bomb detection ────────────────────────────────────────────────────────
    max_compression_ratio: float = 50.0
    """Maximum per-file compression ratio before declaring a zip bomb."""

    max_archive_nesting: int = 2
    """Maximum levels of nested archives (e.g. .zip inside .zip)."""

    # ── Network ───────────────────────────────────────────────────────────────
    fetch_timeout_s: int = 120
    """Total time budget for fetching (cloning, downloading)."""

    max_redirects: int = 5
    """Maximum HTTP redirects before aborting a URL download."""

    # ── Git ───────────────────────────────────────────────────────────────────
    git_clone_depth: int = 1
    """Shallow-clone depth (1 = tip only)."""

    # ── Workspace TTL ─────────────────────────────────────────────────────────
    workspace_ttl_s: int = 3600
    """Seconds before a workspace is eligible for cleanup."""

    # ── Feature flags ─────────────────────────────────────────────────────────
    allow_local_paths: bool = False
    """Gate for local filesystem ingestion (ARCHLENS_ALLOW_LOCAL_PATHS)."""

    # ── Skip lists ────────────────────────────────────────────────────────────
    skip_dirs: list[str] = field(
        default_factory=lambda: [
            "node_modules",
            ".git",
            "build",
            "dist",
            "target",
            "venv",
            ".venv",
            "__pycache__",
            "vendor",
            ".gradle",
            "out",
            "bin",
            "obj",
            ".idea",
            ".vscode",
            "coverage",
        ]
    )
    """Directory names to exclude when scanning a workspace."""

    # ── Parallelism ───────────────────────────────────────────────────────────
    max_parse_workers: int = field(default_factory=lambda: min(12, (os.cpu_count() or 1) + 4))

    @classmethod
    def from_env(cls) -> IngestionLimits:
        """Construct from environment variables."""
        upload_mb = _env_int("ARCHLENS_MAX_UPLOAD_SIZE_MB", _env_int("ARCHLENS_MAX_COMPRESSED_MB", 100))
        return cls(
            max_compressed_bytes=upload_mb * _MB,
            max_uncompressed_bytes=_env_int("ARCHLENS_MAX_UNCOMPRESSED_MB", 500) * _MB,
            max_files=_env_int("ARCHLENS_MAX_FILES", 50_000),
            max_file_size_bytes=_env_int("ARCHLENS_MAX_FILE_SIZE_MB", 5) * _MB,
            max_compression_ratio=_env_float("ARCHLENS_MAX_COMPRESSION_RATIO", 50.0),
            max_archive_nesting=_env_int("ARCHLENS_MAX_ARCHIVE_NESTING", 2),
            fetch_timeout_s=_env_int("ARCHLENS_FETCH_TIMEOUT_S", 120),
            max_redirects=_env_int("ARCHLENS_MAX_REDIRECTS", 5),
            git_clone_depth=_env_int("ARCHLENS_GIT_CLONE_DEPTH", 1),
            workspace_ttl_s=_env_int("ARCHLENS_WORKSPACE_TTL_S", 3600),
            allow_local_paths=_env_bool("ARCHLENS_ALLOW_LOCAL_PATHS", False),
            max_parse_workers=_env_int("ARCHLENS_MAX_PARSE_WORKERS", min(12, (os.cpu_count() or 1) + 4)),
        )
