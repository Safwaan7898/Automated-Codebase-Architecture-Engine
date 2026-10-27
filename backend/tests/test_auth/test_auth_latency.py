"""Tests for authentication latency, prompt 401 failures, and avoiding SQLite contention."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.auth.store import DEMO_USERS


def test_wrong_password_returns_401_fast(client: TestClient) -> None:
    """Verify that bad credentials immediately return 401 in under 1 second without hanging."""
    demo_email = DEMO_USERS[0]["email"]

    t0 = time.perf_counter()
    resp = client.post(
        "/auth/login",
        json={"work_email": demo_email, "password": "WrongPassword!999"},
    )
    elapsed = time.perf_counter() - t0

    assert resp.status_code == 401
    assert "Invalid work email or password." in resp.json()["detail"]
    assert elapsed < 1.0, f"Login failure took {elapsed:.3f}s, expected < 1.0s"


def test_nonexistent_user_returns_401_fast(client: TestClient) -> None:
    """Verify non-existent user returns 401 in under 1 second."""
    t0 = time.perf_counter()
    resp = client.post(
        "/auth/login",
        json={"work_email": "nonexistent_employee_12345@archlens.io", "password": "AnyPassword!123"},
    )
    elapsed = time.perf_counter() - t0

    assert resp.status_code == 401
    assert "Invalid work email or password." in resp.json()["detail"]
    assert elapsed < 1.0, f"Login failure took {elapsed:.3f}s, expected < 1.0s"


def test_rapid_consecutive_auth_requests_do_not_deadlock(client: TestClient) -> None:
    """Verify consecutive auth queries with SQLite WAL mode execute without lock timeouts."""
    demo_email = DEMO_USERS[0]["email"]
    for _ in range(4):
        t0 = time.perf_counter()
        resp = client.post(
            "/auth/login",
            json={"work_email": demo_email, "password": "WrongPassword!999"},
        )
        elapsed = time.perf_counter() - t0
        assert resp.status_code in (401, 429)
        assert elapsed < 1.0
