"""POST /analyze — trigger a new codebase analysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import require_permission
from app.auth.models import Permission
from app.models.refactor import Suggestion
from app.services import analyzer_service, refactor_service

router = APIRouter(tags=["analyze"])


class AnalyzeRequest(BaseModel):
    path: str = Field(..., description="Absolute or relative path to the repo root")
    language: str = Field(
        default="auto",
        description="Language hint: 'python', 'java', or 'auto' for auto-detection",
    )
    include_tests: bool = Field(
        default=False,
        description="Whether to include test/sample/fixture files in analysis scope",
    )
    enable_ai: bool = Field(
        default=False,
        description="Whether to enable AI assistance features (e.g. unsupported language inference)",
    )
    ai_consent: bool = Field(
        default=False,
        description="Explicit user consent for AI assistance",
    )


class AnalyzeResponse(BaseModel):
    repo_id: str
    path: str
    language: str
    node_count: int
    edge_count: int
    smells: list[dict]
    findings: list[dict] = Field(default_factory=list)
    cycles: list[list[str]] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    suggestions: list[Suggestion]
    graph: dict
    health: dict | None = None
    files_excluded: int = 0
    include_tests: bool = False
    parser_version: str = "1.4.0"
    settings_hash: str = ""
    source_fingerprint: str = ""
    commit_sha: str | None = None


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze a codebase",
    dependencies=[Depends(require_permission(Permission.RUN_INGESTION))],
)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze the codebase at the given path and return a dependency graph,
    detected architectural smells, and refactoring suggestions.
    """
    try:
        result = analyzer_service.run_analysis(
            path=req.path,
            language=req.language,
            include_tests=req.include_tests,
            enable_ai=req.enable_ai,
            ai_consent=req.ai_consent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    suggestions = refactor_service.generate_suggestions(result)

    return AnalyzeResponse(
        repo_id=str(result.repo_id),
        path=result.path,
        language=result.language,
        node_count=result.node_count,
        edge_count=result.edge_count,
        smells=result.smells,
        findings=getattr(result, "findings", []),
        cycles=getattr(result, "cycles", []),
        summary=getattr(result, "summary", {}),
        suggestions=suggestions,
        graph=result.graph.model_dump(),
        health=result.health.model_dump() if hasattr(result.health, "model_dump") else result.health,
        files_excluded=result.files_excluded,
        include_tests=result.include_tests,
        parser_version=result.parser_version,
        settings_hash=result.settings_hash,
        source_fingerprint=result.source_fingerprint,
        commit_sha=result.commit_sha,
    )
