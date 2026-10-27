"""GET /health — liveness and readiness endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health() -> HealthResponse:
    """Return service health status and version."""
    return HealthResponse(
        status="ok",
        version=settings.version,
        environment=settings.env,
    )
