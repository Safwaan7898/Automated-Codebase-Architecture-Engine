"""Tests for POST /analyze and GET /graph/{repo_id}."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

# Path to the bundled Python sample repo (relative to monorepo root)
SAMPLES_ROOT = Path(__file__).parent.parent.parent / "samples"
PYTHON_SAMPLE = SAMPLES_ROOT / "python-flask"
JAVA_SAMPLE = SAMPLES_ROOT / "java-spring"


@pytest.mark.asyncio
async def test_analyze_invalid_path(client: AsyncClient) -> None:
    response = await client.post("/analyze", json={"path": "/nonexistent/path/xyz"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analyze_not_a_directory(client: AsyncClient, tmp_path: Path) -> None:
    file = tmp_path / "dummy.txt"
    file.write_text("hello")
    response = await client.post("/analyze", json={"path": str(file)})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analyze_python_sample(client: AsyncClient) -> None:
    if not PYTHON_SAMPLE.exists():
        pytest.skip("Python sample not cloned — run 'make samples' first.")

    response = await client.post(
        "/analyze",
        json={"path": str(PYTHON_SAMPLE), "language": "python"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "python"
    assert "repo_id" in data
    assert data["node_count"] >= 0
    assert "graph" in data
    assert "nodes" in data["graph"]
    assert "edges" in data["graph"]


@pytest.mark.asyncio
async def test_analyze_auto_detection(client: AsyncClient, tmp_path: Path) -> None:
    """Auto-detect Python from a temp directory with a .py file."""
    (tmp_path / "main.py").write_text("import os\nimport sys\n")
    response = await client.post("/analyze", json={"path": str(tmp_path), "language": "auto"})
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "python"
    assert data["node_count"] >= 1


@pytest.mark.asyncio
async def test_analyze_returns_suggestions(client: AsyncClient, tmp_path: Path) -> None:
    """Response always includes a suggestions field."""
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("import a\n")  # circular
    response = await client.post("/analyze", json={"path": str(tmp_path)})
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)


@pytest.mark.asyncio
async def test_graph_retrieval(client: AsyncClient, tmp_path: Path) -> None:
    """Graph can be retrieved by repo_id after analysis."""
    (tmp_path / "module.py").write_text("import os\n")
    analyze_resp = await client.post("/analyze", json={"path": str(tmp_path)})
    assert analyze_resp.status_code == 200
    repo_id = analyze_resp.json()["repo_id"]

    graph_resp = await client.get(f"/graph/{repo_id}")
    assert graph_resp.status_code == 200
    assert graph_resp.json()["repo_id"] == repo_id


@pytest.mark.asyncio
async def test_graph_not_found(client: AsyncClient) -> None:
    response = await client.get("/graph/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_graphs(client: AsyncClient) -> None:
    response = await client.get("/graphs")
    assert response.status_code == 200
    assert "repo_ids" in response.json()
