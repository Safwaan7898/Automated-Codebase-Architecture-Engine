"""Tests for rate limiting login attempts and brute-force account lockout."""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient

from app.auth.models import Role, UserStatus
from app.auth.store import auth_store
from tests.test_auth.conftest import auth_headers_for_role


def test_repeated_failed_logins_trigger_brute_force_lockout(client: TestClient) -> None:
    """Five consecutive failed login attempts lock the user account; admin can unlock."""
    unique_suffix = str(uuid.uuid4())[:8]
    email = f"target_{unique_suffix}@archlens.io"
    password = "CorrectSecretPassword!2026"

    # 1. Create an active user directly
    user_record = auth_store.create_user(
        full_name="Brute Force Target",
        work_email=email,
        password_hash=auth_store.get_user_by_email("admin@archlens.io")["password_hash"],
        employee_id=f"EMP-BF-{unique_suffix}",
        department="Engineering",
        position="Developer",
        role=Role.DEVELOPER,
        status=UserStatus.ACTIVE,
    )
    user_id = user_record["id"]

    # 2. Perform 4 failed login attempts with wrong password
    for i in range(1, 5):
        resp = client.post(
            "/auth/login",
            json={
                "work_email": email,
                "password": f"WrongPassword_{i}",
            },
        )
        assert resp.status_code == 401
        assert "attempt(s) remaining" in resp.json()["detail"]

    # 3. 5th failed attempt triggers account lockout -> 429
    fifth_resp = client.post(
        "/auth/login",
        json={
            "work_email": email,
            "password": "WrongPassword_5",
        },
    )
    assert fifth_resp.status_code == 429
    assert "account locked after 5 consecutive failed login attempts" in fifth_resp.json()["detail"].lower()

    # Verify user status in database is locked
    locked_user = auth_store.get_user_by_id(user_id)
    assert locked_user["status"] == UserStatus.LOCKED

    # 4. 6th attempt (even with correct password) is blocked by lockout
    admin_hash = auth_store.get_user_by_email("admin@archlens.io")["password_hash"]
    sixth_resp = client.post(
        "/auth/login",
        json={
            "work_email": email,
            "password": "AdminPassword!2026",  # Matching admin_hash
        },
    )
    assert sixth_resp.status_code == 429
    assert "account temporarily locked" in sixth_resp.json()["detail"].lower()

    # 5. Admin unlocks the account
    admin_headers = auth_headers_for_role(Role.ADMIN)
    unlock_resp = client.post(f"/api/admin/users/{user_id}/unlock", headers=admin_headers)
    assert unlock_resp.status_code == 200
    assert unlock_resp.json()["status"] == UserStatus.ACTIVE.value

    # 6. User can now login successfully
    success_resp = client.post(
        "/auth/login",
        json={
            "work_email": email,
            "password": "AdminPassword!2026",
        },
    )
    assert success_resp.status_code == 200
    assert "access_token" in success_resp.json()
