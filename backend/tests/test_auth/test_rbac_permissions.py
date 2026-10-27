"""Tests verifying role-based access control (RBAC): each role gets 403 on forbidden endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.auth.models import Role
from tests.test_auth.conftest import auth_headers_for_role


# ── VIEWER TESTS ─────────────────────────────────────────────────────────────
def test_viewer_forbidden_endpoints(client: TestClient) -> None:
    """VIEWER can view dashboard/graph/metrics, but gets 403 on ingestion, refactoring, and report generation."""
    headers = auth_headers_for_role(Role.VIEWER)

    # 1. Forbidden: Ingestion -> 403
    resp_ingest = client.post("/ingest", headers=headers, json={"source_type": "snippet", "code": "x = 1"})
    assert resp_ingest.status_code == 403
    assert "lacks required permission 'run:ingestion'" in resp_ingest.json()["detail"]

    # 2. Forbidden: Generate Report -> 403
    resp_report = client.post(
        "/api/reports/generate",
        headers=headers,
        json={"repo_path": ".", "format": "json"},
    )
    assert resp_report.status_code == 403
    assert "lacks required permission 'generate:reports'" in resp_report.json()["detail"]

    # 3. Forbidden: Refactoring Suggestion -> 403
    resp_refactor = client.post(
        "/api/refactor/suggest",
        headers=headers,
        json={"graph": {"nodes": [], "edges": []}},
    )
    assert resp_refactor.status_code == 403
    assert "lacks required permission 'view:refactor'" in resp_refactor.json()["detail"]

    # 4. Forbidden: Admin Users -> 403
    resp_admin = client.get("/api/admin/users", headers=headers)
    assert resp_admin.status_code == 403

    # Permitted: View Report History -> 200
    resp_hist = client.get("/api/reports/history", headers=headers)
    assert resp_hist.status_code == 200


# ── QA_ENGINEER TESTS ────────────────────────────────────────────────────────
def test_qa_engineer_forbidden_and_permitted_endpoints(client: TestClient) -> None:
    """QA_ENGINEER views metrics, smells and reports, but gets 403 on ingestion and user management."""
    headers = auth_headers_for_role(Role.QA_ENGINEER)

    # 1. Forbidden: Ingestion -> 403 (explicit requirement: "no ingestion")
    resp_ingest = client.post("/ingest", headers=headers, json={"source_type": "snippet", "code": "x = 1"})
    assert resp_ingest.status_code == 403
    assert "run:ingestion" in resp_ingest.json()["detail"]

    # 2. Forbidden: Approve refactoring -> 403
    resp_approve = client.post("/api/refactor/approve", headers=headers, json={"suggestion_id": "SUGG-001"})
    assert resp_approve.status_code == 403

    # 3. Forbidden: Export security report -> 403
    resp_sec = client.post(
        "/api/reports/export-security",
        headers=headers,
        json={"repo_path": "nonexistent_mock", "graph": {"nodes": [], "edges": []}, "query_osv": False},
    )
    assert resp_sec.status_code == 403

    # Permitted: View diagnostic smells -> 200
    resp_rules = client.get("/api/diagnostics/rules", headers=headers)
    assert resp_rules.status_code == 200

    # Permitted: Generate report -> 200
    resp_gen = client.post(
        "/api/reports/generate",
        headers=headers,
        json={
            "repo_path": "nonexistent_mock",
            "format": "json",
            "graph": {"nodes": [], "edges": []},
            "query_osv": False,
        },
    )
    assert resp_gen.status_code == 200


# ── DEVELOPER TESTS ──────────────────────────────────────────────────────────
def test_developer_forbidden_and_permitted_endpoints(client: TestClient) -> None:
    """DEVELOPER runs ingestion and generates reports, but gets 403 on approving refactor drafts and admin."""
    headers = auth_headers_for_role(Role.DEVELOPER)

    # 1. Forbidden: Approve refactor draft -> 403 (Senior Developer only)
    resp_approve = client.post("/api/refactor/approve", headers=headers, json={"suggestion_id": "SUGG-001"})
    assert resp_approve.status_code == 403
    assert "approve:refactor" in resp_approve.json()["detail"]

    # 2. Forbidden: Security CVE Details -> 403
    resp_cve = client.get("/api/diagnostics/cve", headers=headers)
    assert resp_cve.status_code == 403
    assert "view:security_findings" in resp_cve.json()["detail"]

    # 3. Forbidden: Export Security Reports -> 403
    resp_sec = client.post(
        "/api/reports/export-security",
        headers=headers,
        json={"repo_path": "nonexistent_mock", "graph": {"nodes": [], "edges": []}, "query_osv": False},
    )
    assert resp_sec.status_code == 403

    # 4. Forbidden: Admin Users -> 403
    resp_admin = client.get("/api/admin/users", headers=headers)
    assert resp_admin.status_code == 403

    # Permitted: Run Ingestion -> 202
    resp_ingest = client.post(
        "/ingest",
        headers=headers,
        json={"source_type": "snippet", "code": "def foo(): pass", "language": "python"},
    )
    assert resp_ingest.status_code == 202

    # Permitted: View Refactor suggestions -> 200
    resp_types = client.get("/api/refactor/types", headers=headers)
    assert resp_types.status_code == 200


# ── SENIOR_DEVELOPER TESTS ───────────────────────────────────────────────────
def test_senior_developer_can_approve_refactor_but_forbidden_admin(client: TestClient) -> None:
    """SENIOR_DEVELOPER can approve refactor proposals, but gets 403 on user administration."""
    headers = auth_headers_for_role(Role.SENIOR_DEVELOPER)

    # Permitted: Approve refactor draft -> 200
    resp_approve = client.post(
        "/api/refactor/approve",
        headers=headers,
        json={"suggestion_id": "SUGG-CYCLE-01", "review_notes": "LGTM, interface decoupled."},
    )
    assert resp_approve.status_code == 200
    assert resp_approve.json()["status"] == "approved"

    # Forbidden: Admin Users -> 403
    resp_admin = client.get("/api/admin/users", headers=headers)
    assert resp_admin.status_code == 403
    assert "manage:users" in resp_admin.json()["detail"]


# ── SECURITY_ANALYST TESTS ───────────────────────────────────────────────────
def test_security_analyst_can_access_cve_and_export_security(client: TestClient) -> None:
    """SECURITY_ANALYST accesses CVE details and exports security reports, but gets 403 on admin."""
    headers = auth_headers_for_role(Role.SECURITY_ANALYST)

    # Permitted: Access CVE details -> 200
    resp_cve = client.get("/api/diagnostics/cve", headers=headers)
    assert resp_cve.status_code == 200
    assert "cve_database" in resp_cve.json()

    # Permitted: Export security report -> 200
    resp_sec = client.post(
        "/api/reports/export-security",
        headers=headers,
        json={"repo_path": "nonexistent_mock", "graph": {"nodes": [], "edges": []}, "query_osv": False},
    )
    assert resp_sec.status_code == 200

    # Forbidden: Admin Users -> 403
    resp_admin = client.get("/api/admin/users", headers=headers)
    assert resp_admin.status_code == 403


# ── ENGINEERING_MANAGER TESTS ────────────────────────────────────────────────
def test_engineering_manager_team_analytics_and_admin_forbidden(client: TestClient) -> None:
    """ENGINEERING_MANAGER accesses team analytics, but gets 403 on user administration."""
    headers = auth_headers_for_role(Role.ENGINEERING_MANAGER)

    # Permitted: Team Analytics -> 200
    resp_analytics = client.get("/api/analytics/team", headers=headers)
    assert resp_analytics.status_code == 200
    assert "team_metrics" in resp_analytics.json()

    # Forbidden: Admin user management -> 403 ("everything except user administration")
    resp_admin = client.get("/api/admin/users", headers=headers)
    assert resp_admin.status_code == 403
    assert "manage:users" in resp_admin.json()["detail"]


# ── ADMIN TESTS ──────────────────────────────────────────────────────────────
def test_admin_has_complete_system_access(client: TestClient) -> None:
    """ADMIN has full access to user management, audit logs, and all engine endpoints."""
    headers = auth_headers_for_role(Role.ADMIN)

    # Permitted: List users -> 200
    resp_users = client.get("/api/admin/users", headers=headers)
    assert resp_users.status_code == 200
    assert isinstance(resp_users.json(), list)

    # Permitted: Inspect audit logs -> 200
    resp_audit = client.get("/api/admin/audit-logs", headers=headers)
    assert resp_audit.status_code == 200
    assert isinstance(resp_audit.json(), list)

    # Permitted: Team analytics -> 200
    resp_analytics = client.get("/api/analytics/team", headers=headers)
    assert resp_analytics.status_code == 200
