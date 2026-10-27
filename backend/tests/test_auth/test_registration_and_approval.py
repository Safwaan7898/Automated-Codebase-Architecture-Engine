"""Tests for employee self-registration, role restrictions, and admin approval."""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient

from app.auth.models import Role, UserStatus
from tests.test_auth.conftest import auth_headers_for_role


def test_self_registration_creates_viewer_in_pending_status(client: TestClient) -> None:
    """Verify registration creates VIEWER with pending status even if ADMIN role requested."""
    unique_suffix = str(uuid.uuid4())[:8]
    payload = {
        "full_name": "Alice Candidate",
        "work_email": f"alice_{unique_suffix}@archlens.io",
        "password": "SecurePassword!2026",
        "employee_id": f"EMP-{unique_suffix}",
        "department": "Platform Core",
        "position": "Software Engineer",
        "role": "ADMIN",  # Attempting to self-assign ADMIN
    }

    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    # Must be forced to VIEWER and PENDING
    assert data["role"] == Role.VIEWER.value
    assert data["status"] == UserStatus.PENDING.value
    assert data["work_email"] == payload["work_email"].lower()
    assert "password" not in data
    assert "password_hash" not in data


def test_pending_user_cannot_login(client: TestClient) -> None:
    """Verify accounts in pending status cannot authenticate and receive 403."""
    unique_suffix = str(uuid.uuid4())[:8]
    email = f"pending_{unique_suffix}@archlens.io"
    password = "MyPassword!2026"

    # Register
    reg_resp = client.post(
        "/auth/register",
        json={
            "full_name": "Pending User",
            "work_email": email,
            "password": password,
            "employee_id": f"EMP-{unique_suffix}",
            "department": "QA",
            "position": "Tester",
        },
    )
    assert reg_resp.status_code == 201

    # Attempt Login -> 403 Forbidden
    login_resp = client.post(
        "/auth/login",
        json={
            "work_email": email,
            "password": password,
        },
    )
    assert login_resp.status_code == 403
    assert "pending administrator approval" in login_resp.json()["detail"].lower()


def test_admin_approves_user_and_assigns_role(client: TestClient) -> None:
    """Admin approves pending user, assigns final role, and enables login."""
    unique_suffix = str(uuid.uuid4())[:8]
    email = f"approved_{unique_suffix}@archlens.io"
    password = "MyPassword!2026"

    # 1. Register user
    reg_resp = client.post(
        "/auth/register",
        json={
            "full_name": "Candidate Approved",
            "work_email": email,
            "password": password,
            "employee_id": f"EMP-{unique_suffix}",
            "department": "Architecture",
            "position": "Senior Dev",
        },
    )
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    # 2. Non-admin cannot approve (e.g. Developer -> 403)
    dev_headers = auth_headers_for_role(Role.DEVELOPER)
    forbidden_resp = client.post(
        f"/api/admin/users/{user_id}/approve",
        headers=dev_headers,
        json={"role": Role.SENIOR_DEVELOPER.value},
    )
    assert forbidden_resp.status_code == 403

    # 3. Admin approves and assigns SENIOR_DEVELOPER role
    admin_headers = auth_headers_for_role(Role.ADMIN)
    approve_resp = client.post(
        f"/api/admin/users/{user_id}/approve",
        headers=admin_headers,
        json={"role": Role.SENIOR_DEVELOPER.value},
    )
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()
    assert approved_data["role"] == Role.SENIOR_DEVELOPER.value
    assert approved_data["status"] == UserStatus.ACTIVE.value

    # 4. Approved user can now log in successfully
    login_resp = client.post(
        "/auth/login",
        json={
            "work_email": email,
            "password": password,
        },
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert token_data["role"] == Role.SENIOR_DEVELOPER.value
    assert "approve:refactor" in token_data["permissions"]
