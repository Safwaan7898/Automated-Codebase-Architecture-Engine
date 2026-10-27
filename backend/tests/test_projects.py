"""Tests for Step G (Phase 8): Multi-Project Workspaces, Grouping, Trends, and Comparisons."""

from __future__ import annotations

import json
from pathlib import Path
import uuid
import pytest
from fastapi.testclient import TestClient

from app.auth.models import Role
from app.main import app
from app.models.graph import AnalysisResult, DependencyGraph, GraphEdge, GraphNode, HealthScoreResult
from app.services.project_service import ProjectService, compute_project_id, derive_project_name
from app.storage.analysis_store import AnalysisRecord, AnalysisStore
from tests.test_auth.conftest import auth_headers_for_role


def make_dummy_analysis(
    repo_id: str | uuid.UUID,
    nodes: list[str],
    edges: list[tuple[str, str]],
    score: float = 85.0,
    cycles: list[tuple[str, str]] | None = None,
) -> AnalysisResult:
    """Build lightweight synthetic AnalysisResult for workspace tests."""
    uid = uuid.UUID(str(repo_id)) if not isinstance(repo_id, uuid.UUID) else repo_id
    cycle_set = set(cycles or [])
    gnodes = [
        GraphNode(id=nid, label=nid, type="module", loc=100, cyclomatic_complexity=5, language="python")
        for nid in nodes
    ]
    gedges = [
        GraphEdge(
            source=s,
            target=t,
            edge_type="import",
            is_cycle=(s, t) in cycle_set,
        )
        for s, t in edges
    ]
    return AnalysisResult(
        repo_id=uid,
        path=f"/dummy/{repo_id}",
        language="python",
        graph=DependencyGraph(nodes=gnodes, edges=gedges),
        health=HealthScoreResult(
            score=score,
            grade="A" if score >= 80 else "B",
            status="healthy" if score >= 80 else "warning",
            sub_scores={},
        ),
        smells=[],
    )


@pytest.fixture
def temp_project_service(tmp_path: Path):
    """Provide isolated AnalysisStore and ProjectService backed by temporary SQLite DB."""
    db_file = tmp_path / "test_projects.db"
    store = AnalysisStore(db_path=db_file)
    service = ProjectService(store=store)
    return service, store


def test_project_id_and_name_derivation():
    """Test deterministic project IDs and clean display naming."""
    pid1 = compute_project_id("https://github.com/acme/archlens.git", "main")
    pid2 = compute_project_id("https://github.com/acme/archlens", "main")
    pid_branch = compute_project_id("https://github.com/acme/archlens", "feat/ai")

    assert pid1 == pid2, "Trailing .git should normalize to same project"
    assert pid1 != pid_branch, "Different branches must produce distinct projects"

    name1 = derive_project_name("https://github.com/acme/archlens.git", "main")
    assert name1 == "archlens (main)"

    name_local = derive_project_name("C:/Users/dev/repos/my-backend", "develop")
    assert name_local == "my-backend (develop)"


def test_project_grouping_and_history(temp_project_service):
    """Test grouping multiple analyses by repo_url + branch with history trends."""
    service, store = temp_project_service

    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    u2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
    u3 = uuid.UUID("33333333-3333-3333-3333-333333333333")

    # Run 1 for repo A
    res1 = make_dummy_analysis(u1, ["m1", "m2"], [("m1", "m2")], score=80.0)
    rec1 = AnalysisRecord(
        id=str(u1),
        repo_url="https://github.com/org/repo-a",
        branch="main",
        commit_sha="c001",
        created_at="2026-10-20T10:00:00Z",
        status="completed",
        result_json=res1.model_dump_json(),
    )
    store.save(rec1)

    # Run 2 for repo A (newer)
    res2 = make_dummy_analysis(u2, ["m1", "m2", "m3"], [("m1", "m2"), ("m2", "m3")], score=85.0)
    rec2 = AnalysisRecord(
        id=str(u2),
        repo_url="https://github.com/org/repo-a",
        branch="main",
        commit_sha="c002",
        created_at="2026-10-21T10:00:00Z",
        status="completed",
        result_json=res2.model_dump_json(),
    )
    store.save(rec2)

    # Run 1 for repo B
    res3 = make_dummy_analysis(u3, ["b1"], [], score=92.0)
    rec3 = AnalysisRecord(
        id=str(u3),
        repo_url="https://github.com/org/repo-b",
        branch="feat/test",
        commit_sha="b001",
        created_at="2026-10-22T10:00:00Z",
        status="completed",
        result_json=res3.model_dump_json(),
    )
    store.save(rec3)

    projects = service.list_projects()
    assert len(projects) == 2, "Expected 2 grouped projects"

    proj_a = next(p for p in projects if "repo-a" in p["repo_url"])
    assert proj_a["analysis_count"] == 2
    assert proj_a["score"] == 85.0, "Latest score should be 85.0"
    assert proj_a["latest_analysis_id"] == str(u2)
    assert len(proj_a["history"]) == 2
    assert proj_a["history"][0]["analysis_id"] == str(u2)
    assert proj_a["history"][1]["analysis_id"] == str(u1)


def test_compare_analyses_structural_diff(temp_project_service):
    """Test deterministic comparison between two analysis runs."""
    service, store = temp_project_service

    u_base = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    u_target = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    # Base: m1 -> m2 -> m1 (circular loop)
    base_res = make_dummy_analysis(
        u_base,
        nodes=["m1", "m2", "deprecated"],
        edges=[("m1", "m2"), ("m2", "m1")],
        score=65.0,
        cycles=[("m1", "m2"), ("m2", "m1")],
    )
    store.save(
        AnalysisRecord(
            id=str(u_base),
            repo_url="repo-diff",
            created_at="2026-10-20T00:00:00Z",
            result_json=base_res.model_dump_json(),
        )
    )

    # Target: m1 -> m2, m2 -> m3 (cycle broken, deprecated removed, m3 added)
    target_res = make_dummy_analysis(
        u_target,
        nodes=["m1", "m2", "m3"],
        edges=[("m1", "m2"), ("m2", "m3")],
        score=88.0,
        cycles=[],
    )
    store.save(
        AnalysisRecord(
            id=str(u_target),
            repo_url="repo-diff",
            created_at="2026-10-21T00:00:00Z",
            result_json=target_res.model_dump_json(),
        )
    )

    diff = service.compare_analyses(str(u_base), str(u_target))

    assert diff["score_delta"] == 23.0
    assert diff["base_score"] == 65.0
    assert diff["target_score"] == 88.0
    assert "m3" in diff["added_modules"]
    assert "deprecated" in diff["removed_modules"]
    assert diff["base_cycles"] == 2
    assert diff["target_cycles"] == 0
    assert diff["cycles_delta"] == -2
    assert len(diff["added_edges"]) == 1
    assert diff["added_edges"][0] == {"source": "m2", "target": "m3"}
    assert len(diff["removed_edges"]) == 1
    assert diff["removed_edges"][0] == {"source": "m2", "target": "m1"}
    assert "Health score changed by +23.0" in diff["summary"]


def test_delete_project_cascades(temp_project_service):
    """Test deleting a project deletes all associated analysis records."""
    service, store = temp_project_service

    pid = compute_project_id("https://github.com/delete/me", "main")
    store.save(
        AnalysisRecord(
            id="del-1",
            repo_url="https://github.com/delete/me",
            branch="main",
            created_at="2026-10-20T00:00:00Z",
        )
    )
    store.save(
        AnalysisRecord(
            id="del-2",
            repo_url="https://github.com/delete/me",
            branch="main",
            created_at="2026-10-21T00:00:00Z",
        )
    )

    assert len(service.list_projects()) == 1
    deleted = service.delete_project(pid)
    assert deleted == 2
    assert len(service.list_projects()) == 0
    assert store.get("del-1") is None
    assert store.get("del-2") is None


def test_project_api_endpoints():
    """Verify HTTP API endpoints for projects, history, deletion, and comparison."""
    client = TestClient(app)
    headers = auth_headers_for_role(Role.DEVELOPER)

    # List projects (returns empty list or existing projects)
    resp = client.get("/api/projects", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # Compare nonexistent returns 404
    resp_cmp = client.post(
        "/api/projects/compare",
        headers=headers,
        json={"base_id": "nonexistent-base", "target_id": "nonexistent-target"},
    )
    assert resp_cmp.status_code == 404
