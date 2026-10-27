"""SHA-256 hashing utilities for deduplication."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def hash_bytes(data: bytes) -> str:
    """Return hex SHA-256 of *data*."""
    return hashlib.sha256(data).hexdigest()


def hash_string(s: str) -> str:
    return hash_bytes(s.encode("utf-8"))


def hash_dict(d: dict) -> str:
    """Deterministic hash of a JSON-serialisable dict."""
    canonical = json.dumps(d, sort_keys=True, ensure_ascii=True)
    return hash_string(canonical)


def hash_file(path: Path, chunk: int = 1 << 20) -> str:
    """Stream-hash a file; tolerant of large files."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def hash_git_source(url: str, branch: str | None, commit: str | None, subpath: str | None) -> str:
    return hash_dict(
        {
            "type": "git",
            "url": url.rstrip("/"),
            "branch": branch or "",
            "commit": commit or "",
            "subpath": subpath or "",
        }
    )


def hash_archive_url(url: str) -> str:
    return hash_dict({"type": "archive_url", "url": url.rstrip("?")})


def hash_snippet(code: str, language: str) -> str:
    return hash_dict({"type": "snippet", "code": code, "language": language})
