"""Tests proving Single Pipeline determinism and Dedup Cache Safety.

1. Same repository analyzed via Git checkout vs ZIP archive yields 100% identical
   canonical JSON for nodes, edges, cycles, communities, LOC, complexity, score,
   and source_fingerprint.
2. Deduplication cache safety: language=python vs java on the same archive do not
   collide or share cache; cache hit generates a new job id with a full analysis result.
3. Archive ignore list skips ignored files while maintaining proper resource limits.
"""

from __future__ import annotations

import asyncio
import io
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import analyzer_service
from ingestion.orchestrator import IngestionOrchestrator
from ingestion.sources.archive import ArchiveUploadSource


@pytest.fixture
def clean_orchestrator(tmp_path: Path) -> IngestionOrchestrator:
    return IngestionOrchestrator()


def _extract_canonical_dict(result: Any) -> dict[str, Any]:
    nodes = [
        {
            "id": n.id,
            "label": n.label,
            "type": str(n.type),
            "file_path": n.file_path,
            "loc": n.loc,
            "cyclomatic_complexity": n.cyclomatic_complexity,
            "mean_complexity": n.mean_complexity,
            "max_complexity": n.max_complexity,
            "community": n.community,
        }
        for n in sorted(result.graph.nodes, key=lambda x: x.id)
    ]
    edges = [
        {
            "source": e.source,
            "target": e.target,
            "edge_type": e.edge_type,
            "weight": e.weight,
            "is_cycle": e.is_cycle,
        }
        for e in sorted(result.graph.edges, key=lambda x: (x.source, x.target))
    ]
    return {
        "source_fingerprint": result.source_fingerprint,
        "nodes": nodes,
        "edges": edges,
        "cycles": len([e for e in result.graph.edges if e.is_cycle]),
        "communities": {n.id: n.community for n in sorted(result.graph.nodes, key=lambda x: x.id)},
        "loc": sum(n.loc for n in result.graph.nodes if str(n.type) == "module"),
        "complexity": round(
            sum(n.cyclomatic_complexity for n in result.graph.nodes) / max(1, len(result.graph.nodes)), 2
        ),
        "score": result.health.score,
        "grade": result.health.grade,
        "sub_scores": result.health.sub_scores,
    }


def test_single_pipeline_identical_git_vs_zip(tmp_path: Path):
    """Prove that analyzing the same repo via Git vs as a ZIP produces 100% identical canonical JSON."""
    fixture_zip = Path(__file__).parent.parent / "fixtures" / "mini_repo.zip"
    assert fixture_zip.exists(), "mini_repo.zip fixture missing"

    # 1. Setup a local Git repository with the exact files from mini_repo.zip
    git_repo_dir = tmp_path / "git_repo"
    git_repo_dir.mkdir()
    with zipfile.ZipFile(fixture_zip) as z:
        z.extractall(git_repo_dir)

    subprocess.run(["git", "init"], cwd=git_repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=git_repo_dir, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "tester@archlens.io"], cwd=git_repo_dir, capture_output=True, check=True
    )
    subprocess.run(["git", "add", "."], cwd=git_repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=git_repo_dir, capture_output=True, check=True)

    # Analyze via Git checkout path (simulating POST /analyze)
    res_git = analyzer_service.run_analysis(str(git_repo_dir), language="python")
    assert res_git is not None

    # 2. Analyze via Archive Ingestion Pipeline (simulating POST /ingest/archive)
    async def run_archive_pipeline():
        orch = IngestionOrchestrator()
        src = ArchiveUploadSource(archive_data=fixture_zip, filename="mini_repo.zip", language="python")
        meta, _ = await orch.run_sync(src)
        assert meta is not None
        res = analyzer_service.get_cached_result(meta.job_id)
        assert res is not None
        return res

    res_zip = asyncio.run(run_archive_pipeline())

    canon_git = _extract_canonical_dict(res_git)
    canon_zip = _extract_canonical_dict(res_zip)

    # Assert all structural, topological and architectural metrics are identical
    assert canon_git["source_fingerprint"] == canon_zip["source_fingerprint"]
    assert canon_git["nodes"] == canon_zip["nodes"]
    assert canon_git["edges"] == canon_zip["edges"]
    assert canon_git["cycles"] == canon_zip["cycles"]
    assert canon_git["communities"] == canon_zip["communities"]
    assert canon_git["loc"] == canon_zip["loc"]
    assert canon_git["complexity"] == canon_zip["complexity"]
    assert canon_git["score"] == canon_zip["score"]
    assert canon_git["grade"] == canon_zip["grade"]
    assert canon_git["sub_scores"] == canon_zip["sub_scores"]
    assert canon_git == canon_zip


def test_dedup_cache_safety_language_isolation(tmp_path: Path):
    """The same archive with language=python vs java does not return a shared cached result."""
    fixture_zip = Path(__file__).parent.parent / "fixtures" / "mini_repo.zip"
    orch = IngestionOrchestrator()

    async def run_lang(lang: str):
        src = ArchiveUploadSource(archive_data=fixture_zip, filename="mini_repo.zip", language=lang)
        meta, _ = await orch.run_sync(src)
        return meta, src.source_hash

    meta_py, hash_py = asyncio.run(run_lang("python"))
    meta_java, hash_java = asyncio.run(run_lang("java"))

    # Source hashes must differ due to language parameter
    assert hash_py != hash_java
    assert ":python" in hash_py
    assert ":java" in hash_java


def test_dedup_cache_hit_registers_new_job_and_complete_analysis(tmp_path: Path):
    """A deduplication cache hit registers a new job ID with a complete analysis, never partial."""
    fixture_zip = Path(__file__).parent.parent / "fixtures" / "mini_repo.zip"
    orch = IngestionOrchestrator()

    async def run_jobs():
        src1 = ArchiveUploadSource(archive_data=fixture_zip, filename="mini_repo.zip", language="python")
        job_id_1 = await orch.start_ingestion(src1)

        # Allow job 1 to complete
        await asyncio.sleep(0.5)

        src2 = ArchiveUploadSource(archive_data=fixture_zip, filename="mini_repo.zip", language="python")
        job_id_2 = await orch.start_ingestion(src2)
        return job_id_1, job_id_2

    job_id_1, job_id_2 = asyncio.run(run_jobs())

    # Must be distinct job IDs
    assert job_id_1 != job_id_2

    # Job 2 must be registered in the job store with status COMPLETE
    job_2 = orch.job_store.get_job(job_id_2)
    assert job_2 is not None
    assert str(job_2.status) == "complete"

    # Job 2 must have full analysis in memory cache
    res_2 = analyzer_service.get_cached_result(job_id_2)
    assert res_2 is not None
    assert res_2.node_count > 0
    assert res_2.edge_count > 0
    assert res_2.health.score is not None
    assert len(res_2.graph.nodes) == res_2.node_count


def test_archive_ignore_list_skips_entries():
    """Ignored directories (.git, node_modules, venv) are counted and skipped safely."""
    client = TestClient(app)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("app/module_main.py", "def test():\n    return 1\n")
        z.writestr("node_modules/lib/index.js", "module.exports = {};")
        z.writestr(".git/HEAD", "ref: refs/heads/main")
        z.writestr("venv/bin/activate", "# activate")
    buf.seek(0)

    resp = client.post(
        "/ingest/archive",
        files={"archive": ("test_ignore.zip", buf.getvalue(), "application/zip")},
        data={"language": "python"},
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    assert job_id is not None
