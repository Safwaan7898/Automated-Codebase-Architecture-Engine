"""Unit tests for SQLite analysis cache keyed by commit hash."""

from __future__ import annotations

from pathlib import Path


from analysis.cache import AnalysisCache


class TestAnalysisCache:
    def test_cache_set_and_get(self, tmp_path: Path) -> None:
        db_file = tmp_path / "cache.db"
        cache = AnalysisCache(db_path=db_file)

        commit = "a1b2c3d4e5f67890"
        payload = {"cycles": 2, "details": ["A->B->A", "C->D->C"]}

        # Miss initially
        assert cache.get(commit, "cycles") is None

        # Store
        cache.set(commit, "cycles", payload)

        # Hit
        cached = cache.get(commit, "cycles")
        assert cached == payload

        # Different commit is a miss
        assert cache.get("different_commit", "cycles") is None

        # Different analysis type is a miss
        assert cache.get(commit, "layers") is None

    def test_cache_clear(self, tmp_path: Path) -> None:
        cache = AnalysisCache(db_path=tmp_path / "cache2.db")
        cache.set("commit_1", "cycles", {"val": 1})
        cache.set("commit_2", "cycles", {"val": 2})

        assert cache.get("commit_1", "cycles") is not None
        assert cache.get("commit_2", "cycles") is not None

        # Clear single commit
        cache.clear(commit_hash="commit_1")
        assert cache.get("commit_1", "cycles") is None
        assert cache.get("commit_2", "cycles") is not None

        # Clear all
        cache.clear()
        assert cache.get("commit_2", "cycles") is None
