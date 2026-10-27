"""API routes for Multi-Project Workspaces, Project History, and Analysis Comparisons."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth.dependencies import require_permission
from app.auth.models import Permission
from app.services.project_service import default_project_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


class CompareRequest(BaseModel):
    base_id: str = Field(..., description="Base analysis ID for comparison")
    target_id: str = Field(..., description="Target analysis ID for comparison")
    enable_ai: bool = Field(default=False, description="Whether to request an AI synthesis of comparison changes")


@router.get("", response_model=list[dict[str, Any]])
def list_projects(
    search: str | None = Query(default=None, description="Filter by project or repo name"),
    sort_by: str = Query(
        default="last_analyzed", description="Field to sort by (last_analyzed | score | risk | name | smells)"
    ),
    current_user: dict[str, Any] = Depends(require_permission(Permission.VIEW_GRAPH)),
) -> list[dict[str, Any]]:
    """List all workspace projects grouped by repository URL and branch."""
    return default_project_service.list_projects(search=search, sort_by=sort_by)


@router.get("/{project_id}", response_model=dict[str, Any])
def get_project(
    project_id: str,
    current_user: dict[str, Any] = Depends(require_permission(Permission.VIEW_GRAPH)),
) -> dict[str, Any]:
    """Retrieve details and analysis history trends for a specific project."""
    project = default_project_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found",
        )
    return project


@router.delete("/{project_id}", response_model=dict[str, Any])
def delete_project(
    project_id: str,
    current_user: dict[str, Any] = Depends(require_permission(Permission.RUN_INGESTION)),
) -> dict[str, Any]:
    """Delete all analysis records and workspace artifacts associated with a project."""
    project = default_project_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found",
        )

    deleted_count = default_project_service.delete_project(project_id)
    return {
        "success": True,
        "project_id": project_id,
        "deleted_analyses": deleted_count,
        "message": f"Successfully deleted project '{project['name']}' and {deleted_count} analysis runs.",
    }


@router.post("/compare", response_model=dict[str, Any])
def compare_analyses(
    req: CompareRequest,
    current_user: dict[str, Any] = Depends(require_permission(Permission.VIEW_GRAPH)),
) -> dict[str, Any]:
    """Compare two analysis runs and compute structural deltas (modules, edges, cycles, health)."""
    try:
        comparison = default_project_service.compare_analyses(req.base_id, req.target_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    # Optional AI narrative summary if requested
    if req.enable_ai:
        try:
            from ai.config import get_ai_settings
            from ai.service import get_ai_service

            settings = get_ai_settings()
            if settings.enabled:
                ai = get_ai_service()
                prompt = (
                    f"Summarize the architectural changes between these two codebase analysis runs:\n"
                    f"- Health Score Delta: {comparison['score_delta']:+0.1f} "
                    f"({comparison['base_score']} -> {comparison['target_score']})\n"
                    f"- Added Modules ({len(comparison['added_modules'])}): {comparison['added_modules'][:5]}\n"
                    f"- Removed Modules ({len(comparison['removed_modules'])}): {comparison['removed_modules'][:5]}\n"
                    f"- Modified Modules ({len(comparison['modified_modules'])})\n"
                    f"- Added Edges ({len(comparison['added_edges'])})\n"
                    f"- Cycles Delta: {comparison['cycles_delta']:+d}\n"
                    f"- Smells Delta: {comparison['smells_delta']:+d}\n"
                    "Provide a concise, factual 2-3 sentence summary of the architectural impact."
                )
                ai_text = ai.generate_text(prompt)
                if ai_text:
                    comparison["summary"] = ai_text.strip()
                    comparison["is_ai_generated"] = True
        except Exception as exc:
            logger.warning("AI comparison summary generation failed, keeping deterministic summary: %s", exc)

    return comparison
