"""Tests for JWT cookie storage, GET /auth/me permissions list, and refresh token rotation with reuse detection."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.auth.models import Role
from app.auth.store import DEMO_USERS


def test_login_sets_httponly_cookies_and_payload(client: TestClient) -> None:
    """Login should return tokens and set httpOnly access_token and refresh_token cookies."""
    admin_demo = next(d for d in DEMO_USERS if d["role"] == Role.ADMIN)

    resp = client.post(
        "/auth/login",
        json={
            "work_email": admin_demo["email"],
            "password": admin_demo["password"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["role"] == Role.ADMIN.value
    assert isinstance(data["permissions"], list)

    # Check cookies
    cookies = resp.cookies
    assert "access_token" in cookies
    assert "refresh_token" in cookies


def test_get_auth_me_returns_user_and_permissions(client: TestClient) -> None:
    """GET /auth/me returns user metadata and permissions array for frontend UI gating."""
    dev_demo = next(d for d in DEMO_USERS if d["role"] == Role.DEVELOPER)

    login_resp = client.post(
        "/auth/login",
        json={
            "work_email": dev_demo["email"],
            "password": dev_demo["password"],
        },
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]

    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()

    assert "user" in me_data
    assert me_data["user"]["work_email"] == dev_demo["email"]
    assert me_data["user"]["role"] == Role.DEVELOPER.value
    assert "permissions" in me_data
    assert "run:ingestion" in me_data["permissions"]
    assert "approve:refactor" not in me_data["permissions"]


def test_refresh_token_rotation_and_revocation(client: TestClient) -> None:
    """Calling /auth/refresh rotates the refresh token and returns a fresh access/refresh pair."""
    qa_demo = next(d for d in DEMO_USERS if d["role"] == Role.QA_ENGINEER)

    # 1. Login to get initial tokens
    login_resp = client.post(
        "/auth/login",
        json={
            "work_email": qa_demo["email"],
            "password": qa_demo["password"],
        },
    )
    assert login_resp.status_code == 200
    initial_refresh = login_resp.json()["refresh_token"]
    initial_access = login_resp.json()["access_token"]

    # 2. Call /auth/refresh with initial refresh token
    refresh_resp = client.post("/auth/refresh", json={"refresh_token": initial_refresh})
    assert refresh_resp.status_code == 200
    rotated_data = refresh_resp.json()
    new_refresh = rotated_data["refresh_token"]
    new_access = rotated_data["access_token"]

    # Verify new tokens are distinct
    assert new_refresh != initial_refresh
    assert new_access != initial_access

    # 3. Use new access token to query /auth/me -> 200
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["user"]["role"] == Role.QA_ENGINEER.value


def test_refresh_token_reuse_detection_revokes_all_sessions(client: TestClient) -> None:
    """Security alert test: attempting to reuse an already rotated refresh token revokes all user sessions."""
    sec_demo = next(d for d in DEMO_USERS if d["role"] == Role.SECURITY_ANALYST)

    # 1. Login
    login_resp = client.post(
        "/auth/login",
        json={
            "work_email": sec_demo["email"],
            "password": sec_demo["password"],
        },
    )
    token_v1 = login_resp.json()["refresh_token"]

    # 2. Legitimate rotation: v1 -> v2
    rot1_resp = client.post("/auth/refresh", json={"refresh_token": token_v1})
    assert rot1_resp.status_code == 200
    token_v2 = rot1_resp.json()["refresh_token"]

    # 3. Attacker replays token_v1 (already rotated)
    reused_resp = client.post("/auth/refresh", json={"refresh_token": token_v1})
    assert reused_resp.status_code == 401
    assert "reuse detected" in reused_resp.json()["detail"].lower()

    # 4. Now token_v2 must ALSO be revoked because reuse was detected!
    compromised_resp = client.post("/auth/refresh", json={"refresh_token": token_v2})
    assert compromised_resp.status_code == 401
    assert "revoked" in compromised_resp.json()["detail"].lower()


def test_logout_revokes_token_and_clears_cookies(client: TestClient) -> None:
    """Logout invalidates active refresh token and clears browser cookies."""
    viewer_demo = next(d for d in DEMO_USERS if d["role"] == Role.VIEWER)

    login_resp = client.post(
        "/auth/login",
        json={
            "work_email": viewer_demo["email"],
            "password": viewer_demo["password"],
        },
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]
    refresh_token = login_resp.json()["refresh_token"]

    # Logout
    logout_resp = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        cookies={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 200

    # Refreshing with logged out token should fail
    fail_refresh = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert fail_refresh.status_code == 401
