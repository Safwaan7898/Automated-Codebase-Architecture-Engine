"""Tests for admin provisioning key security, environment-only configuration, and compromise protection."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings


def test_admin_registration_disabled_by_default(client: TestClient, monkeypatch) -> None:
    """When ARCHLENS_ADMIN_PROVISION_KEY is not configured, admin registration must return 403."""
    monkeypatch.setattr(settings, "admin_provision_key", None)

    resp = client.post(
        "/auth/register-admin",
        json={
            "full_name": "New Admin",
            "work_email": "newadmin@archlens.io",
            "password": "StrongPassword!2026",
            "employee_id": "ADM-999",
            "department": "Security",
            "position": "Director",
            "admin_key": "ARCHLENS-ADMIN-SEC-2026",
        },
    )
    assert resp.status_code == 403
    assert "Public admin registration is disabled" in resp.json()["detail"]


def test_legacy_compromised_keys_are_rejected(client: TestClient, monkeypatch) -> None:
    """Legacy hardcoded keys must be rejected even if admin key is configured."""
    monkeypatch.setattr(settings, "admin_provision_key", "SuperSecretCustomKey!2026")

    for legacy_key in ["ARCHLENS-ADMIN-SEC-2026", "ARCHLENS-ROOT-KEY", "SEC-ADMIN-99"]:
        resp = client.post(
            "/auth/register-admin",
            json={
                "full_name": "Hacker Admin",
                "work_email": f"hacker_{legacy_key.lower()}@archlens.io",
                "password": "StrongPassword!2026",
                "employee_id": f"ADM-{legacy_key[:4]}",
                "department": "Security",
                "position": "Director",
                "admin_key": legacy_key,
            },
        )
        assert resp.status_code == 403
        assert "Invalid Admin Master Key" in resp.json()["detail"]


def test_admin_registration_succeeds_with_configured_secret(client: TestClient, monkeypatch) -> None:
    """When configured secret is provided, admin is provisioned successfully."""
    import uuid

    configured_key = "ValidSecretCustomKey!2026"
    monkeypatch.setattr(settings, "admin_provision_key", configured_key)
    uid = uuid.uuid4().hex[:8]
    work_email = f"validadmin_{uid}@archlens.io"
    emp_id = f"ADM-{uid}"

    resp = client.post(
        "/auth/register-admin",
        json={
            "full_name": "Valid Admin",
            "work_email": work_email,
            "password": "StrongPassword!2026",
            "employee_id": emp_id,
            "department": "Security",
            "position": "Director",
            "admin_key": configured_key,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "ADMIN"
    assert data["work_email"] == work_email
