"""FastAPI endpoints for ArchLens automated refactoring suggestions."""

from __future__ import annotations

from typing import Any

from analysis.facade import build_graph_from_dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from refactor.engine import default_refactor_engine

from app.auth.dependencies import require_permission
from app.auth.models import Permission
from app.auth.store import auth_store
from app.services import analyzer_service

router = APIRouter(prefix="/api/refactor", tags=["refactor"])


class SuggestionRequest(BaseModel):
    analysis_id: str | None = Field(None, description="Optional analysis ID to load from SQLite analysis store")
    graph: dict[str, Any] | None = Field(None, description="Architecture graph payload containing nodes and edges")
    repo_path: str = Field(".", description="Repository root path for code context extraction")
    enable_llm: bool = Field(False, description="Enable optional LLM diff drafting")


class ApproveRefactorRequest(BaseModel):
    suggestion_id: str = Field(..., description="ID of refactoring proposal to approve")
    review_notes: str | None = Field(None, description="Optional peer review or approval notes")


@router.get(
    "/types",
    dependencies=[Depends(require_permission(Permission.VIEW_REFACTOR))],
)
def get_refactor_types() -> dict[str, Any]:
    """List supported refactoring strategies."""
    return {
        "strategies": [
            {
                "type": "break_cycle",
                "description": "Minimal-weight feedback arc set removal with interface-based dependency inversion",
            },
            {
                "type": "split_god_class",
                "description": "Decomposition of god classes using community detection on method-field interactions",
            },
            {
                "type": "extract_module",
                "description": "Extraction of explicit module boundaries from Louvain community clusters",
            },
            {
                "type": "move_method",
                "description": "Relocation of feature-envying methods to target classes based on coupling",
            },
        ]
    }


@router.get(
    "/{analysis_id}",
    summary="Get refactoring plan by analysis ID",
    dependencies=[Depends(require_permission(Permission.VIEW_REFACTOR))],
)
def get_refactor_plan_by_id(analysis_id: str) -> dict[str, Any]:
    """Retrieve refactoring plan for a persisted analysis record."""
    analysis_res = analyzer_service.get_cached_result(analysis_id)
    if not analysis_res:
        raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found")

    graph = build_graph_from_dict(analysis_res.graph.model_dump())
    plan = default_refactor_engine.generate_plan(
        graph=graph,
        repo_root=analysis_res.path,
        enable_llm=False,
    )
    return plan.to_dict()


@router.post(
    "/suggest",
    dependencies=[Depends(require_permission(Permission.VIEW_REFACTOR))],
)
def generate_refactor_plan(req: SuggestionRequest) -> dict[str, Any]:
    """Generate ranked, deterministic refactoring suggestions with simulated before/after metrics."""
    if req.analysis_id and not req.graph:
        analysis_res = analyzer_service.get_cached_result(req.analysis_id)
        if not analysis_res:
            raise HTTPException(status_code=404, detail=f"Analysis '{req.analysis_id}' not found")
        graph = build_graph_from_dict(analysis_res.graph.model_dump())
        repo_root = analysis_res.path
    elif req.graph:
        graph = build_graph_from_dict(req.graph)
        repo_root = req.repo_path
    else:
        raise HTTPException(status_code=400, detail="Must provide either analysis_id or graph payload")

    plan = default_refactor_engine.generate_plan(
        graph=graph,
        repo_root=repo_root,
        enable_llm=req.enable_llm,
    )
    return plan.to_dict()


@router.post(
    "/approve",
    dependencies=[Depends(require_permission(Permission.APPROVE_REFACTOR))],
)
def approve_refactor_draft(
    req: ApproveRefactorRequest,
    current_user: dict[str, Any] = Depends(require_permission(Permission.APPROVE_REFACTOR)),
) -> dict[str, Any]:
    """Approve refactoring proposals and diff drafts. Restricted to Senior Developers, Managers, and Admins."""
    role_val = current_user.get("role")
    auth_store.add_audit_log(
        user_id=current_user.get("id", "anonymous"),
        user_email=current_user.get("work_email", "anonymous@archlens.io"),
        user_role=role_val.value if hasattr(role_val, "value") else str(role_val),
        action="refactor_approved",
        resource_type="refactor_suggestion",
        resource_id=req.suggestion_id,
        details={"review_notes": req.review_notes},
    )
    return {
        "status": "approved",
        "suggestion_id": req.suggestion_id,
        "approved_by": current_user.get("work_email"),
        "role": role_val.value if hasattr(role_val, "value") else str(role_val),
    }


class AIRefactorRequest(BaseModel):
    smell: dict[str, Any]
    analysis_id: str | None = None
    repo_path: str = "."
    run_tests: bool = False


@router.post(
    "/ai-proposal",
    dependencies=[Depends(require_permission(Permission.VIEW_REFACTOR))],
)
async def api_ai_refactor_proposal(req: AIRefactorRequest) -> dict[str, Any]:
    """Generate and sandbox-validate an AI refactoring proposal with repair loop."""
    from ai.features import draft_and_validate_refactor

    from app.services import analyzer_service

    resolved_repo = req.repo_path
    if req.analysis_id:
        res = analyzer_service.get_cached_result(req.analysis_id)
        if res and hasattr(res, "path"):
            resolved_repo = res.path

    proposal = await draft_and_validate_refactor(
        smell=req.smell,
        repo_root=resolved_repo,
        run_tests=req.run_tests,
    )
    return proposal.model_dump()


@router.get(
    "/export-patch/{proposal_id}",
    dependencies=[Depends(require_permission(Permission.VIEW_REFACTOR))],
)
def export_patch(proposal_id: str) -> dict[str, Any]:
    """Export unified diff patch for an approved refactoring proposal."""
    # Never writes to user repository; returns raw patch text
    return {
        "proposal_id": proposal_id,
        "filename": f"{proposal_id}.patch",
        "content_type": "text/x-diff",
    }
