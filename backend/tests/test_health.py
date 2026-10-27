"""Tests for GET /health."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_payload_shape(client: AsyncClient) -> None:
    response = await client.get("/health")
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_health_content_type(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert "application/json" in response.headers["content-type"]
