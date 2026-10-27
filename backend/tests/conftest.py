"""Test suite conftest — shared fixtures."""

from __future__ import annotations

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture()
async def client() -> AsyncClient:
    """Async test client wired to the FastAPI app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
