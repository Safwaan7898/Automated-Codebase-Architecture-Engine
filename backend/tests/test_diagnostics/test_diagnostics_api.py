"""Tests for diagnostics FastAPI endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_rules_endpoint() -> None:
    resp = client.get("/api/diagnostics/rules")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rules"] >= 15
    rule_ids = {r["id"] for r in data["rules"]}
    assert "SEC-SQL-CONCAT" in rule_ids
    assert "SMELL-GOD-CLASS" in rule_ids
    assert "DEP-VULNERABLE-PACKAGE" in rule_ids


def test_analyze_file_endpoint_vulnerable() -> None:
    payload = {
        "content": 'cursor.execute("SELECT * FROM u WHERE id = " + uid)',
        "language": "python",
        "file_path": "test.py",
    }
    resp = client.post("/api/diagnostics/analyze-file", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_findings"] >= 1
    assert data["findings"][0]["rule_id"] == "SEC-SQL-CONCAT"


def test_analyze_file_endpoint_clean() -> None:
    payload = {
        "content": 'cursor.execute("SELECT * FROM u WHERE id = %s", (uid,))',
        "language": "python",
        "file_path": "clean.py",
    }
    resp = client.post("/api/diagnostics/analyze-file", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_findings"] == 0


def test_analyze_graph_endpoint() -> None:
    graph_data = {
        "nodes": [
            {
                "id": "GodClassA",
                "name": "GodClassA",
                "type": "class",
                "metrics": {"loc": 500, "num_methods": 30},
            },
            {
                "id": "NormalClassB",
                "name": "NormalClassB",
                "type": "class",
                "metrics": {"loc": 30, "num_methods": 3},
            },
        ],
        "edges": [
            {"source": "GodClassA", "target": "NormalClassB", "type": "calls"},
        ],
    }

    resp = client.post("/api/diagnostics/analyze-graph", json=graph_data)
    assert resp.status_code == 200
    data = resp.json()
    assert data["node_count"] == 2
    assert data["smell_findings_count"] >= 1
    assert "GodClassA" in data["risk_scores"]
    assert data["risk_scores"]["GodClassA"]["risk_score"] > data["risk_scores"]["NormalClassB"]["risk_score"]
