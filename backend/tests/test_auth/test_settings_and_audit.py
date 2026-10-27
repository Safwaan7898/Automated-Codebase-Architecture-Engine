"""Tests for user settings (profile, password, preferences), audit logs, and demo user seeding."""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient

from app.auth.models import Role
from tests.test_auth.conftest import auth_headers_for_role


def test_user_profile_and_preferences_settings(client: TestClient) -> None:
    """User can view and update their profile metadata, theme, and notification preferences."""
    dev_headers = auth_headers_for_role(Role.DEVELOPER)

    # 1. Get profile
    prof_resp = client.get("/api/settings/profile", headers=dev_headers)
    assert prof_resp.status_code == 200
    assert prof_resp.json()["role"] == Role.DEVELOPER.value

    # 2. Update profile
    update_resp = client.put(
        "/api/settings/profile",
        headers=dev_headers,
        json={"department": "Core Platform Architecture", "position": "Senior Systems Engineer"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["department"] == "Core Platform Architecture"
    assert update_resp.json()["position"] == "Senior Systems Engineer"

    # 3. Get preferences
    pref_resp = client.get("/api/settings/preferences", headers=dev_headers)
    assert pref_resp.status_code == 200
    assert "theme_preference" in pref_resp.json()

    # 4. Update preferences
    set_pref_resp = client.put(
        "/api/settings/preferences",
        headers=dev_headers,
        json={
            "theme_preference": "light",
            "notification_preferences": {"email_reports": False, "security_alerts": True},
        },
    )
    assert set_pref_resp.status_code == 200
    assert set_pref_resp.json()["theme_preference"] == "light"
    assert set_pref_resp.json()["notification_preferences"]["security_alerts"] is True


def test_change_password_workflow(client: TestClient) -> None:
    """User changes password after validating current password; new password works for login."""
    unique_suffix = str(uuid.uuid4())[:8]
    email = f"pwd_user_{unique_suffix}@archlens.io"
    old_password = "OriginalPassword!2026"
    new_password = "NewlyUpdatedPassword!2026"

    # Register user
    reg = client.post(
        "/auth/register",
        json={
            "full_name": "Password Tester",
            "work_email": email,
            "password": old_password,
            "employee_id": f"EMP-PWD-{unique_suffix}",
            "department": "Security",
            "position": "Analyst",
        },
    )
    user_id = reg.json()["id"]

    # Admin approves user
    admin_headers = auth_headers_for_role(Role.ADMIN)
    client.post(f"/api/admin/users/{user_id}/approve", headers=admin_headers, json={"role": Role.DEVELOPER.value})

    # Login to obtain access token
    login_resp = client.post("/auth/login", json={"work_email": email, "password": old_password})
    token = login_resp.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {token}"}

    # 1. Attempt change with wrong current password -> 400
    bad_change = client.post(
        "/api/settings/change-password",
        headers=user_headers,
        json={"current_password": "IncorrectPassword", "new_password": new_password},
    )
    assert bad_change.status_code == 400
    assert "verification failed" in bad_change.json()["detail"].lower()

    # 2. Change password with correct current password -> 200
    good_change = client.post(
        "/api/settings/change-password",
        headers=user_headers,
        json={"current_password": old_password, "new_password": new_password},
    )
    assert good_change.status_code == 200

    # 3. Old password should fail
    fail_login = client.post("/auth/login", json={"work_email": email, "password": old_password})
    assert fail_login.status_code == 401

    # 4. New password should succeed
    succ_login = client.post("/auth/login", json={"work_email": email, "password": new_password})
    assert succ_login.status_code == 200
    assert "access_token" in succ_login.json()


def test_audit_logs_record_ingestions_and_reports(client: TestClient) -> None:
    """Audit log records who ran which ingestion/report and when, inspectable by Admin."""
    dev_headers = auth_headers_for_role(Role.DEVELOPER)
    admin_headers = auth_headers_for_role(Role.ADMIN)

    # 1. Developer runs ingestion
    ingest_resp = client.post(
        "/ingest",
        headers=dev_headers,
        json={"source_type": "snippet", "code": "def test_audit(): return 42", "language": "python"},
    )
    assert ingest_resp.status_code == 202
    job_id = ingest_resp.json()["job_id"]

    # 2. Developer generates a report
    rep_resp = client.post(
        "/api/reports/generate",
        headers=dev_headers,
        json={
            "repo_path": "nonexistent_mock",
            "format": "json",
            "graph": {"nodes": [], "edges": []},
            "query_osv": False,
        },
    )
    assert rep_resp.status_code == 200
    report_id = rep_resp.headers.get("X-Report-Id")

    # 3. Admin queries audit logs
    audit_resp = client.get("/api/admin/audit-logs", headers=admin_headers)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert len(logs) > 0

    # Check ingestion audit log exists
    ingest_logs = [log for log in logs if log["action"] == "ingestion_start" and log["resource_id"] == job_id]
    assert len(ingest_logs) >= 1
    assert ingest_logs[0]["user_role"] == Role.DEVELOPER.value
    assert "timestamp" in ingest_logs[0]

    # Check report audit log exists
    report_logs = [log for log in logs if log["action"] == "report_generate" and log["resource_id"] == report_id]
    assert len(report_logs) >= 1
    assert report_logs[0]["user_role"] == Role.DEVELOPER.value


def test_demo_users_endpoint(client: TestClient) -> None:
    """GET /auth/demo-users returns seeded demo users covering all 7 roles."""
    resp = client.get("/auth/demo-users")
    assert resp.status_code == 200
    demos = resp.json()
    assert len(demos) == 7

    roles = {d["role"] for d in demos}
    expected_roles = {
        Role.ADMIN.value,
        Role.ENGINEERING_MANAGER.value,
        Role.SENIOR_DEVELOPER.value,
        Role.DEVELOPER.value,
        Role.SECURITY_ANALYST.value,
        Role.QA_ENGINEER.value,
        Role.VIEWER.value,
    }
    assert roles == expected_roles
