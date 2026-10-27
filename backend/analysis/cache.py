"""SQLite caching for analysis results keyed by repo commit hash."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import os

def _get_default_cache_db_path() -> Path:
    try:
        from app.core.config import settings

        return settings.cache_db_path
    except Exception:
        env_dir = os.environ.get("ARCHLENS_DATA_DIR")
        if env_dir:
            return Path(env_dir).resolve() / "archlens_analysis_cache.db"
        return (Path(__file__).resolve().parent.parent / "data" / "archlens_analysis_cache.db").resolve()


class AnalysisCache:
    """Thread-safe SQLite storage for caching architectural analysis results."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or _get_default_cache_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    commit_hash TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (commit_hash, analysis_type)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_commit ON analysis_cache(commit_hash)")
            conn.commit()

    def get(self, commit_hash: str, analysis_type: str) -> dict[str, Any] | None:
        """Retrieve cached analysis payload if present."""
        if not commit_hash:
            return None

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT payload FROM analysis_cache WHERE commit_hash = ? AND analysis_type = ?",
                (commit_hash, analysis_type),
            )
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row["payload"])
                except Exception:
                    return None
        return None

    def set(self, commit_hash: str, analysis_type: str, payload: dict[str, Any]) -> None:
        """Store analysis payload in SQLite cache."""
        if not commit_hash:
            return

        payload_json = json.dumps(payload, ensure_ascii=False)
        now_str = datetime.now(UTC).isoformat()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO analysis_cache (commit_hash, analysis_type, payload, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(commit_hash, analysis_type) DO UPDATE SET
                    payload = excluded.payload,
                    created_at = excluded.created_at
                """,
                (commit_hash, analysis_type, payload_json, now_str),
            )
            conn.commit()

    def clear(self, commit_hash: str | None = None) -> int:
        """Clear cache for a specific commit hash or all entries."""
        with self._get_connection() as conn:
            if commit_hash:
                cursor = conn.execute("DELETE FROM analysis_cache WHERE commit_hash = ?", (commit_hash,))
            else:
                cursor = conn.execute("DELETE FROM analysis_cache")
            conn.commit()
            return cursor.rowcount


# Default global instance
default_analysis_cache = AnalysisCache()
