"""Integration tests for the /analysis REST API endpoints."""

from __future__ import annotations

import httpx
import pytest

from app.main import app


@pytest.fixture
def sample_graph_payload() -> dict:
    return {
        "nodes": [
            {"id": "A", "name": "A", "type": "class", "path": "src/a.py", "metrics": {"loc": 100}},
            {"id": "B", "name": "B", "type": "class", "path": "src/b.py", "metrics": {"loc": 200}},
            {"id": "C", "name": "C", "type": "class", "path": "src/c.py", "metrics": {"loc": 300}},
        ],
        "edges": [
            {"source": "A", "target": "B", "type": "calls", "weight": 1.0},
            {"source": "B", "target": "C", "type": "calls", "weight": 2.0},
            {"source": "C", "target": "A", "type": "calls", "weight": 1.0},
        ],
    }


class TestAnalysisAPI:
    @pytest.mark.asyncio
    async def test_api_cycles(self, sample_graph_payload: dict) -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/analysis/cycles", json=sample_graph_payload)
            assert res.status_code == 200
            data = res.json()
            assert data["total_cycles"] == 1
            assert data["cycles"][0]["size"] == 3

    @pytest.mark.asyncio
    async def test_api_layers(self, sample_graph_payload: dict) -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/analysis/layers", json=sample_graph_payload)
            assert res.status_code == 200
            data = res.json()
            assert data["total_layers"] >= 1
            assert "node_to_layer" in data

    @pytest.mark.asyncio
    async def test_api_centrality(self, sample_graph_payload: dict) -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/analysis/centrality", json=sample_graph_payload)
            assert res.status_code == 200
            data = res.json()
            assert "betweenness" in data
            assert "pagerank" in data

    @pytest.mark.asyncio
    async def test_api_metrics_coupling(self, sample_graph_payload: dict) -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/analysis/metrics", json=sample_graph_payload)
            assert res.status_code == 200
            data = res.json()
            assert "mean_instability" in data
            assert len(data["node_couplings"]) == 3

    @pytest.mark.asyncio
    async def test_api_communities(self, sample_graph_payload: dict) -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/analysis/communities", json=sample_graph_payload)
            assert res.status_code == 200
            data = res.json()
            assert data["community_count"] >= 1

    @pytest.mark.asyncio
    async def test_api_impact(self, sample_graph_payload: dict) -> None:
        payload = {
            **sample_graph_payload,
            "target_node": "A",
            "weighted": True,
        }
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/analysis/impact", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["target_node"] == "A"
            assert data["total_impacted_count"] == 2

    @pytest.mark.asyncio
    async def test_api_dead_code(self, sample_graph_payload: dict) -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/analysis/dead-code", json=sample_graph_payload)
            assert res.status_code == 200
            data = res.json()
            assert "candidates" in data

    @pytest.mark.asyncio
    async def test_api_full_suite_and_sqlite_caching(self, sample_graph_payload: dict) -> None:
        commit = "test_commit_hash_123456"
        payload = {
            **sample_graph_payload,
            "commit_hash": commit,
        }
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            # First call populates cache
            res1 = await ac.post("/analysis/full", json=payload)
            assert res1.status_code == 200
            data1 = res1.json()

            # Second call retrieves from SQLite cache
            res2 = await ac.post("/analysis/full", json=payload)
            assert res2.status_code == 200
            data2 = res2.json()

            assert data1["summary"] == data2["summary"]
