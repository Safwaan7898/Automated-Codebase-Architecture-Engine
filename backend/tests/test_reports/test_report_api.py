"""Tests for report API endpoints."""

from __future__ import annotations

from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FIXTURE_REPO = str(Path(__file__).parent.parent / "fixtures" / "python")


class TestReportEndpoints:
    """Test report generation, history listing, and download endpoints."""

    def test_generate_json_report(self):
        payload = {
            "repo_path": FIXTURE_REPO,
            "repo_name": "APITestRepo",
            "format": "json",
            "query_osv": False,
        }
        resp = client.post("/api/reports/generate", json=payload)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        data = resp.json()
        assert "metadata" in data
        assert "executive_summary" in data
        assert data["executive_summary"]["health_score"] >= 0.0
        assert "X-Report-Id" in resp.headers

    def test_generate_html_report(self):
        payload = {
            "repo_path": FIXTURE_REPO,
            "repo_name": "APITestRepo",
            "format": "html",
            "query_osv": False,
        }
        resp = client.post("/api/reports/generate", json=payload)
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "<!DOCTYPE html>" in resp.text
        assert "APITestRepo" in resp.text

    def test_generate_pdf_report(self):
        payload = {
            "repo_path": FIXTURE_REPO,
            "repo_name": "APITestRepo",
            "format": "pdf",
            "query_osv": False,
        }
        resp = client.post("/api/reports/generate", json=payload)
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]
        assert resp.content.startswith(b"%PDF")
        assert len(resp.content) > 5000

    def test_report_history_and_download(self):
        # 1. Generate a report first
        payload = {
            "repo_path": FIXTURE_REPO,
            "repo_name": "HistoryTestRepo",
            "format": "json",
            "query_osv": False,
        }
        gen_resp = client.post("/api/reports/generate", json=payload)
        assert gen_resp.status_code == 200
        report_id = gen_resp.headers.get("X-Report-Id")
        assert report_id is not None

        # 2. Check history includes this report
        hist_resp = client.get("/api/reports/history")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert hist_data["total_reports"] >= 1
        ids = [r["report_id"] for r in hist_data["reports"]]
        assert report_id in ids

        # 3. Retrieve report by ID
        get_resp = client.get(f"/api/reports/{report_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["metadata"]["report_id"] == report_id

        # 4. Download report as HTML
        dl_resp = client.get(f"/api/reports/{report_id}/download?format=html")
        assert dl_resp.status_code == 200
        assert "text/html" in dl_resp.headers["content-type"]
        assert "<!DOCTYPE html>" in dl_resp.text

        # 5. Non-existent report 404
        bad_resp = client.get("/api/reports/REP-NONEXISTENT")
        assert bad_resp.status_code == 404
