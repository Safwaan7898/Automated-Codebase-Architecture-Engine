"""SQLite persistence layer for AnalysisRecord entities."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel, Field

from app.models.graph import AnalysisResult

logger = logging.getLogger(__name__)


class AnalysisRecord(BaseModel):
    """Persisted analysis record representing a processed codebase."""

    id: str = Field(..., description="Unique analysis record identifier (UUID string)")
    repo_url: str = Field(..., description="Repository URL or local filesystem path")
    branch: str | None = Field(default=None, description="Git branch name if applicable")
    commit_sha: str | None = Field(default=None, description="Git commit hash if applicable")
    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp")
    status: str = Field(default="completed", description="pending | running | completed | failed")
    result_json: str | None = Field(default=None, description="Serialized AnalysisResult JSON")
    cache_key: str | None = Field(
        default=None, description="Cache key: source_fingerprint:parser_version:settings_hash"
    )


class AnalysisStore:
    """Thread-safe SQLite store for AnalysisRecord entities with WAL mode."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            from app.core.config import settings

            self.db_path = settings.analysis_db_path
        else:
            self.db_path = Path(db_path).resolve()

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_records (
                    id TEXT PRIMARY KEY,
                    repo_url TEXT NOT NULL,
                    branch TEXT,
                    commit_sha TEXT,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    cache_key TEXT
                );
                """
            )
            try:
                conn.execute("ALTER TABLE analysis_records ADD COLUMN cache_key TEXT;")
            except sqlite3.OperationalError:
                pass
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analysis_records_cache_key ON analysis_records(cache_key);")
            conn.commit()

    def save(self, record: AnalysisRecord) -> None:
        """Insert or update an analysis record."""
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO analysis_records (
                    id, repo_url, branch, commit_sha, created_at, status, result_json, cache_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    repo_url=excluded.repo_url,
                    branch=excluded.branch,
                    commit_sha=excluded.commit_sha,
                    created_at=excluded.created_at,
                    status=excluded.status,
                    result_json=excluded.result_json,
                    cache_key=excluded.cache_key;
                """,
                (
                    record.id,
                    record.repo_url,
                    record.branch,
                    record.commit_sha,
                    record.created_at,
                    record.status,
                    record.result_json,
                    record.cache_key,
                ),
            )
            conn.commit()

    def get(self, record_id: str) -> AnalysisRecord | None:
        """Retrieve an AnalysisRecord by its ID."""
        with self._connection() as conn:
            query = (
                "SELECT id, repo_url, branch, commit_sha, created_at, status, result_json, cache_key "
                "FROM analysis_records WHERE id = ?"
            )
            cur = conn.execute(query, (record_id,))
            row = cur.fetchone()
            if not row:
                return None
            return AnalysisRecord(
                id=row["id"],
                repo_url=row["repo_url"],
                branch=row["branch"],
                commit_sha=row["commit_sha"],
                created_at=row["created_at"],
                status=row["status"],
                result_json=row["result_json"],
                cache_key=row["cache_key"],
            )

    def get_by_cache_key(self, cache_key: str) -> AnalysisRecord | None:
        """Retrieve an AnalysisRecord by cache key (source_fingerprint:parser_version:settings_hash)."""
        with self._connection() as conn:
            query = (
                "SELECT id, repo_url, branch, commit_sha, created_at, status, result_json, cache_key "
                "FROM analysis_records WHERE cache_key = ? ORDER BY created_at DESC LIMIT 1"
            )
            cur = conn.execute(query, (cache_key,))
            row = cur.fetchone()
            if not row:
                return None
            return AnalysisRecord(
                id=row["id"],
                repo_url=row["repo_url"],
                branch=row["branch"],
                commit_sha=row["commit_sha"],
                created_at=row["created_at"],
                status=row["status"],
                result_json=row["result_json"],
                cache_key=row["cache_key"],
            )

    def get_result(self, record_id: str) -> AnalysisResult | None:
        """Retrieve and deserialize the AnalysisResult for a given record ID."""
        record = self.get(record_id)
        if not record or not record.result_json:
            return None
        try:
            data = json.loads(record.result_json)
            return AnalysisResult.model_validate(data)
        except Exception as exc:
            logger.warning("Failed to deserialize AnalysisResult for id=%s: %s", record_id, exc)
            return None

    def get_result_by_cache_key(self, cache_key: str) -> AnalysisResult | None:
        """Retrieve and deserialize the AnalysisResult by cache key."""
        record = self.get_by_cache_key(cache_key)
        if not record or not record.result_json:
            return None
        try:
            data = json.loads(record.result_json)
            return AnalysisResult.model_validate(data)
        except Exception as exc:
            logger.warning("Failed to deserialize AnalysisResult for cache_key=%s: %s", cache_key, exc)
            return None

    def list_ids(self) -> list[str]:
        """Return all persisted analysis record IDs ordered newest first."""
        with self._connection() as conn:
            cur = conn.execute("SELECT id FROM analysis_records ORDER BY created_at DESC")
            return [row["id"] for row in cur.fetchall()]

    def list_records(self) -> list[AnalysisRecord]:
        """Return all analysis records ordered newest first."""
        with self._connection() as conn:
            query = (
                "SELECT id, repo_url, branch, commit_sha, created_at, status, result_json "
                "FROM analysis_records ORDER BY created_at DESC"
            )
            cur = conn.execute(query)
            return [
                AnalysisRecord(
                    id=row["id"],
                    repo_url=row["repo_url"],
                    branch=row["branch"],
                    commit_sha=row["commit_sha"],
                    created_at=row["created_at"],
                    status=row["status"],
                    result_json=row["result_json"],
                )
                for row in cur.fetchall()
            ]

    def delete(self, record_id: str) -> bool:
        """Delete an analysis record by ID."""
        with self._connection() as conn:
            cur = conn.execute("DELETE FROM analysis_records WHERE id = ?", (record_id,))
            conn.commit()
            return cur.rowcount > 0


# Global singleton instance
default_analysis_store = AnalysisStore()
