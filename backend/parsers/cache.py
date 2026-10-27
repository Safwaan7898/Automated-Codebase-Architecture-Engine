"""Thread-safe incremental file parsing cache keyed by SHA-256 content hash."""

from __future__ import annotations

import copy
import hashlib
import logging
import threading
from pathlib import Path
from typing import Any

from parsers.models import ParseResult

logger = logging.getLogger(__name__)


def hash_file_content(path: Path, chunk_size: int = 1 << 20) -> str:
    """Compute SHA-256 of file content in streaming chunks."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


class FileParseCache:
    """In-memory thread-safe LRU-capable cache of ParseResults by content SHA-256.

    Enables fast incremental parsing of huge repositories where only modified files
    need full AST re-parsing.
    """

    def __init__(self, max_entries: int = 50_000) -> None:
        self.max_entries = max_entries
        self._cache: dict[str, ParseResult] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, content_hash: str, current_rel_path: str) -> ParseResult | None:
        """Retrieve cached ParseResult for *content_hash*, re-pathed to *current_rel_path*."""
        with self._lock:
            cached = self._cache.get(content_hash)
            if cached is None:
                self._misses += 1
                return None
            self._hits += 1

        # Deep-copy and adjust relative file paths to match current target workspace
        res = copy.deepcopy(cached)
        res.file_path = current_rel_path
        for node in res.nodes:
            node.path = current_rel_path
        return res

    def set(self, content_hash: str, result: ParseResult) -> None:
        """Store ParseResult in cache under *content_hash*."""
        with self._lock:
            if len(self._cache) >= self.max_entries:
                # Evict oldest entry (dict is insertion-ordered in Python 3.7+)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[content_hash] = copy.deepcopy(result)

    def clear(self) -> None:
        """Flush the cache and reset counters."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict[str, Any]:
        """Return cache hit/miss statistics and current size."""
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = (self._hits / total) if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_entries": self.max_entries,
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": hit_ratio,
            }


# Global default instance used across parser runs
default_file_parse_cache = FileParseCache()
