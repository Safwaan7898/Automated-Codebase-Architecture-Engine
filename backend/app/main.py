"""ArchLens FastAPI application factory."""

from __future__ import annotations

import sys

if sys.platform == "win32":
    import asyncio

    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception as exc:
        _ = exc  # Best-effort policy setting on Windows

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin_routes,
    analysis_routes,
    analytics_routes,
    analyze,
    auth_routes,
    diagnostics_routes,
    graph,
    health,
    ingestion_routes,
    project_routes,
    refactor_routes,
    report_routes,
    settings_routes,
    ws_analyze,
)
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup → yield → shutdown."""
    configure_logging()
    logger.info(
        "ArchLens %s starting in '%s' mode on %s:%d",
        settings.version,
        settings.env,
        settings.host,
        settings.port,
    )
    yield
    logger.info("ArchLens shutting down.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="ArchLens API",
        description=(
            "Automated Codebase Architecture Visualizer & Refactoring Engine. "
            "Statically analyses Python and Java codebases, generates dependency graphs, "
            "detects architectural smells, and surfaces refactoring suggestions."
        ),
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ─────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(auth_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(admin_routes.direct_admin_ai_router)
    app.include_router(settings_routes.router)
    app.include_router(analytics_routes.router)
    app.include_router(analyze.router)
    app.include_router(graph.router)
    app.include_router(ws_analyze.router)
    app.include_router(ingestion_routes.router)
    app.include_router(analysis_routes.router)
    app.include_router(diagnostics_routes.router)
    app.include_router(refactor_routes.router)
    app.include_router(project_routes.router)
    app.include_router(report_routes.router)
    app.include_router(report_routes.direct_reports_router)

    return app


app = create_app()
