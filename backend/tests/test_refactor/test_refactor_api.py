"""Tests for refactoring FastAPI endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_refactor_types_endpoint() -> None:
    resp = client.get("/api/refactor/types")
    assert resp.status_code == 200
    data = resp.json()
    types = {s["type"] for s in data["strategies"]}
    assert "break_cycle" in types
    assert "split_god_class" in types
    assert "extract_module" in types
    assert "move_method" in types


def test_suggest_refactor_endpoint() -> None:
    payload = {
        "graph": {
            "nodes": [
                {"id": "ServiceA", "name": "ServiceA", "type": "class"},
                {"id": "ServiceB", "name": "ServiceB", "type": "class"},
            ],
            "edges": [
                {"source": "ServiceA", "target": "ServiceB", "weight": 2.0},
                {"source": "ServiceB", "target": "ServiceA", "weight": 1.0},
            ],
        },
        "repo_path": ".",
        "enable_llm": False,
    }

    resp = client.post("/api/refactor/suggest", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_suggestions"] >= 1
    suggestions = data["suggestions"]
    assert suggestions[0]["type"] == "break_cycle"
    assert suggestions[0]["rank"] == 1
    assert "before" in suggestions[0]["metrics"]
    assert "after" in suggestions[0]["metrics"]
    assert suggestions[0]["metrics"]["before"]["cycles"] == 1
    assert suggestions[0]["metrics"]["after"]["cycles"] == 0
