"""Deterministic source fingerprinting and provenance metadata.

Computes a canonical SHA-256 hash over sorted relative POSIX paths and file SHA-256s.
Provides git commit extraction, settings hashing, and parser version constants.
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PARSER_VERSION = "2.0.0"
DEFAULT_RANDOM_SEED = 42

DEFAULT_SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "venv",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "target",
        ".gradle",
        "bin",
        "obj",
        ".idea",
        ".vscode",
        "coverage",
        ".pytest_cache",
        ".tox",
        ".ruff_cache",
        ".reports_storage",
        "reports_output",
    }
)


import uuid


def compute_cache_key(
    source_fingerprint: str,
    parser_version: str = PARSER_VERSION,
    settings_hash: str = "",
    language: str = "auto",
    include_tests: bool = False,
) -> str:
    """Compute canonical deterministic cache key."""
    return f"{source_fingerprint}:{parser_version}:{settings_hash}:{language}:{str(include_tests).lower()}"


def compute_analysis_id(
    source_fingerprint: str,
    parser_version: str = PARSER_VERSION,
    settings_hash: str = "",
    language: str = "auto",
    include_tests: bool = False,
) -> uuid.UUID:
    """Compute deterministic UUID based on the full cache key.

    Guarantees two runs (e.g. include_tests true vs false) never share an ID or overwrite each other.
    """
    key = compute_cache_key(
        source_fingerprint=source_fingerprint,
        parser_version=parser_version,
        settings_hash=settings_hash,
        language=language,
        include_tests=include_tests,
    )
    return uuid.uuid5(uuid.NAMESPACE_URL, f"archlens:{key}")


def compute_settings_hash(settings: dict[str, Any] | None = None) -> str:
    """Compute a deterministic hash of analysis settings."""
    if not settings:
        settings = {"version": PARSER_VERSION, "random_seed": DEFAULT_RANDOM_SEED}
    payload = json.dumps(settings, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def get_git_commit_sha(root: Path) -> str | None:
    """Extract current HEAD commit SHA if root is a git repository."""
    try:
        git_dir = root / ".git"
        if not git_dir.exists():
            return None
        res = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            sha = res.stdout.strip()
            if len(sha) == 40 and all(c in "0123456789abcdef" for c in sha):
                return sha
    except Exception as exc:
        logger.debug("Could not determine git commit SHA in %s: %s", root, exc)
    return None


def compute_source_fingerprint(
    root: Path,
    skip_dirs: frozenset[str] | set[str] | None = None,
    max_file_size_bytes: int = 10 * 1024 * 1024,
) -> tuple[str, list[tuple[str, str]]]:
    """Compute deterministic SHA-256 fingerprint over sorted POSIX relative paths and file contents.

    Returns:
        tuple of (master_sha256_hash, list_of_sorted_file_entries)
        where each entry is (rel_posix_path, file_sha256).
    """
    root = root.resolve()
    effective_skip_dirs = DEFAULT_SKIP_DIRS if skip_dirs is None else set(skip_dirs)

    # 1. Collect all files with deterministic recursion
    file_entries: list[tuple[str, str]] = []

    def _walk(curr: Path) -> None:
        try:
            entries = sorted(curr.iterdir(), key=lambda p: p.name)
        except (PermissionError, OSError):
            return

        for entry in entries:
            if entry.is_symlink():
                continue

            if entry.is_dir():
                if entry.name in effective_skip_dirs:
                    continue
                _walk(entry)
            elif entry.is_file():
                try:
                    stat = entry.stat()
                    if stat.st_size > max_file_size_bytes:
                        continue
                    content = entry.read_bytes()
                    # Normalize line endings so source fingerprint is identical across OS and git autocrlf settings
                    content = content.replace(b"\r\n", b"\n")
                    fhash = hashlib.sha256(content).hexdigest()
                    rel_posix = entry.relative_to(root).as_posix()
                    file_entries.append((rel_posix, fhash))
                except (PermissionError, OSError):
                    continue

    _walk(root)

    # 2. Sort by relative POSIX path
    file_entries.sort(key=lambda item: item[0])

    # 3. Compute master SHA-256 over canonical lines: "rel_path:sha256\n"
    hasher = hashlib.sha256()
    for rel_path, fhash in file_entries:
        line = f"{rel_path}:{fhash}\n".encode("utf-8")
        hasher.update(line)

    master_hash = hasher.hexdigest()
    return master_hash, file_entries
