"""Test fixtures and client helpers for authentication and RBAC test suite."""

from __future__ import annotations


from fastapi.testclient import TestClient
import pytest

from app.auth.models import Role
from app.auth.security import create_access_token
from app.auth.store import DEMO_USERS, auth_store
from app.main import app


@pytest.fixture(autouse=True)
def _ensure_demo_users() -> None:
    """Ensure demo users are seeded and unlocked for tests."""
    auth_store.seed_demo_users()
    for demo in DEMO_USERS:
        u = auth_store.get_user_by_email(demo["email"])
        if u:
            auth_store.reset_failed_logins(u["id"])
            auth_store.update_user(u["id"], {"status": "active"})


@pytest.fixture()
def client() -> TestClient:
    """Standard TestClient instance."""
    return TestClient(app)


def get_token_for_role(role: Role) -> str:
    """Generate a valid JWT access token for a specific role."""
    from app.auth.models import ROLE_PERMISSIONS

    demo = next(d for d in DEMO_USERS if d["role"] == role)
    user = auth_store.get_user_by_email(demo["email"])
    if not user:
        raise ValueError(f"User for role {role} not found in store")

    permissions = sorted(ROLE_PERMISSIONS.get(role, set()))
    return create_access_token(
        user_id=user["id"],
        email=user["work_email"],
        role=role,
        permissions=permissions,
    )


def auth_headers_for_role(role: Role) -> dict[str, str]:
    """Return Authorization Bearer header for a given role."""
    token = get_token_for_role(role)
    return {"Authorization": f"Bearer {token}"}


def auth_cookies_for_role(role: Role) -> dict[str, str]:
    """Return access_token cookie dict for a given role."""
    token = get_token_for_role(role)
    return {"access_token": token}
