"""FastAPI endpoints for downloadable reports (PDF, HTML, JSON) and report history."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analysis.facade import build_graph_from_dict
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from reports.generator import default_report_generator
from reports.models import ReportFormat
from reports.pdf import ReportRenderer
from reports.store import default_report_store

from app.auth.dependencies import require_permission
from app.auth.models import Permission
from app.auth.store import auth_store
from app.services import analyzer_service

router = APIRouter(prefix="/api/reports", tags=["reports"])
direct_reports_router = APIRouter(prefix="/reports", tags=["reports"])


class GenerateReportRequest(BaseModel):
    analysis_id: str | None = Field(None, description="Optional analysis ID to load from SQLite analysis store")
    repo_path: str = Field(".", description="Path to repository on disk")
    repo_name: str | None = Field(None, description="Optional display name for codebase")
    format: ReportFormat = Field(ReportFormat.PDF, description="Output format: 'pdf', 'html', or 'json'")
    graph: dict[str, Any] | None = Field(None, description="Optional pre-parsed graph dictionary")
    query_osv: bool = Field(True, description="Query OSV.dev for CVEs")


@router.post(
    "/generate",
    summary="Generate a comprehensive architecture, security, and refactoring report (PDF, HTML, JSON)",
    dependencies=[Depends(require_permission(Permission.GENERATE_REPORTS))],
)
def generate_report(
    req: GenerateReportRequest,
    current_user: dict[str, Any] = Depends(require_permission(Permission.GENERATE_REPORTS)),
) -> Response:
    """Generate and return a downloadable report."""
    resolved_path = Path(req.repo_path).resolve()
    repo_name = req.repo_name or resolved_path.name or "Codebase"
    analysis_res = None

    # 1. Build graph (from analysis_id, request payload, or analyze repository)
    if req.analysis_id:
        analysis_res = analyzer_service.get_cached_result(req.analysis_id)
        if analysis_res is not None:
            graph = build_graph_from_dict(analysis_res.graph.model_dump())
            repo_name = req.repo_name or Path(analysis_res.path).name or "Codebase"
            resolved_path = Path(analysis_res.path).resolve()
        else:
            raise HTTPException(status_code=404, detail=f"Analysis '{req.analysis_id}' not found")
    elif req.graph:
        graph = build_graph_from_dict(req.graph)
    elif resolved_path.exists() and resolved_path.is_dir():
        try:
            analysis_res = analyzer_service.run_analysis(str(resolved_path), language="auto")
            graph = build_graph_from_dict(analysis_res.graph.model_dump())
        except Exception:
            # Fallback to empty directed graph
            from analysis.graph import DirectedGraph

            graph = DirectedGraph()
    else:
        from analysis.graph import DirectedGraph

        graph = DirectedGraph()

    report_score = analysis_res.health.score if (analysis_res and analysis_res.health.score is not None) else None
    report_grade = analysis_res.health.grade if analysis_res else None
    report_sub_scores = analysis_res.health.sub_scores if analysis_res else {}
    report_status = analysis_res.health.status if analysis_res else "ok"
    report_sha = analysis_res.commit_sha if analysis_res else None
    report_fingerprint = analysis_res.source_fingerprint if analysis_res else None
    report_parser_version = getattr(analysis_res, "parser_version", "1.0.0") if analysis_res else "1.0.0"
    report_truncated = getattr(analysis_res, "truncated", False) if analysis_res else False
    report_files_analyzed = analysis_res.node_count if analysis_res else graph.node_count
    report_ext_deps_count = len(analysis_res.external_dependencies) if analysis_res else 0
    report_files_skipped = (
        analysis_res.truncated_counts.get("files_skipped", 0)
        if analysis_res and hasattr(analysis_res, "truncated_counts") and analysis_res.truncated_counts
        else 0
    )

    # 2. Generate full report model
    report = default_report_generator.generate_report(
        graph=graph,
        repo_path=str(resolved_path),
        repo_name=repo_name,
        language="auto",
        query_osv=req.query_osv,
        health_score=report_score,
        health_grade=report_grade,
        analysis_id=req.analysis_id,
        commit_sha=report_sha,
        source_fingerprint=report_fingerprint,
        parser_version=report_parser_version,
        files_analyzed=report_files_analyzed,
        files_skipped=report_files_skipped,
        truncated=report_truncated,
        external_dependencies_count=report_ext_deps_count,
        health_sub_scores=report_sub_scores,
        health_status=report_status,
    )

    # 3. Save to report store for history tracking
    report_id = default_report_store.save_report(report)

    # 4. Audit trail
    role_val = current_user.get("role")
    auth_store.add_audit_log(
        user_id=current_user.get("id", "anonymous"),
        user_email=current_user.get("work_email", "anonymous@archlens.io"),
        user_role=role_val.value if hasattr(role_val, "value") else str(role_val),
        action="report_generate",
        resource_type="report",
        resource_id=report_id,
        details={"format": req.format.value, "repo_name": repo_name},
    )

    # 5. Render to requested format
    content, media_type = ReportRenderer.render(report, req.format)
    safe_name = repo_name.lower().replace(" ", "-").replace("/", "-")
    filename = f"archlens-report-{safe_name}-{report_id}.{req.format.value}"

    if req.format == ReportFormat.PDF:
        return Response(
            content=content,  # type: ignore[arg-type]
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Report-Id": report_id,
            },
        )
    elif req.format == ReportFormat.HTML:
        return Response(
            content=content,  # type: ignore[arg-type]
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Report-Id": report_id,
            },
        )
    else:
        return Response(
            content=json.dumps(content, indent=2),  # type: ignore[arg-type]
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Report-Id": report_id,
            },
        )


@router.post(
    "/export-security",
    summary="Export specialized security vulnerability and CVE audit report",
    dependencies=[Depends(require_permission(Permission.EXPORT_SECURITY_REPORTS))],
)
def export_security_report(
    req: GenerateReportRequest,
    current_user: dict[str, Any] = Depends(require_permission(Permission.EXPORT_SECURITY_REPORTS)),
) -> Response:
    """Generate and export a security findings report. Restriced to Security Analysts and Admins."""
    req.format = ReportFormat.JSON
    if req.query_osv is not False:
        req.query_osv = True
    response = generate_report(req, current_user=current_user)

    role_val = current_user.get("role")
    auth_store.add_audit_log(
        user_id=current_user.get("id", "anonymous"),
        user_email=current_user.get("work_email", "anonymous@archlens.io"),
        user_role=role_val.value if hasattr(role_val, "value") else str(role_val),
        action="security_report_export",
        resource_type="report",
        resource_id=response.headers.get("X-Report-Id"),
        details={"format": "json"},
    )
    return response


@router.get(
    "/history",
    summary="List previously generated reports",
    dependencies=[Depends(require_permission(Permission.VIEW_REPORTS))],
)
def get_report_history() -> dict[str, Any]:
    """Retrieve history of all generated reports."""
    reports = default_report_store.list_reports()
    return {
        "total_reports": len(reports),
        "reports": reports,
    }


@router.get(
    "/{report_id}",
    summary="Get report details by ID",
    dependencies=[Depends(require_permission(Permission.VIEW_REPORTS))],
)
def get_report(report_id: str) -> dict[str, Any]:
    """Get report JSON model by ID."""
    report = default_report_store.get_report(report_id)
    if not report:
        analysis_res = analyzer_service.get_cached_result(report_id)
        if analysis_res is not None:
            graph = build_graph_from_dict(analysis_res.graph.model_dump())
            repo_path = Path(analysis_res.path)
            repo_name = (
                repo_path.name
                if repo_path.name and repo_path.name.lower() not in ("repository", "codebase", "none")
                else "sample-repo"
            )
            report = default_report_generator.generate_report(
                graph=graph,
                repo_path=analysis_res.path,
                repo_name=repo_name,
                language=analysis_res.language,
                query_osv=False,
                health_score=analysis_res.health.score,
                health_grade=analysis_res.health.grade,
                analysis_id=report_id,
                commit_sha=analysis_res.commit_sha,
                source_fingerprint=analysis_res.source_fingerprint,
                parser_version=analysis_res.parser_version,
                files_analyzed=analysis_res.node_count,
                truncated=analysis_res.truncated,
                external_dependencies_count=len(analysis_res.external_dependencies),
                health_sub_scores=analysis_res.health.sub_scores,
                health_status=analysis_res.health.status,
            )
            report.metadata.report_id = report_id
            default_report_store.save_report(report)
        else:
            raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
    return report.to_dict()


@router.get(
    "/{report_id}/download",
    summary="Download existing report as PDF, HTML, or JSON",
    dependencies=[Depends(require_permission(Permission.VIEW_REPORTS))],
)
def download_report(
    report_id: str,
    format: ReportFormat = Query(ReportFormat.PDF, description="Desired download format"),
) -> Response:
    """Download previously generated report."""
    report = default_report_store.get_report(report_id)
    if not report:
        analysis_res = analyzer_service.get_cached_result(report_id)
        if analysis_res is not None:
            graph = build_graph_from_dict(analysis_res.graph.model_dump())
            repo_path = Path(analysis_res.path)
            repo_name = (
                repo_path.name
                if repo_path.name and repo_path.name.lower() not in ("repository", "codebase", "none")
                else "sample-repo"
            )
            report = default_report_generator.generate_report(
                graph=graph,
                repo_path=analysis_res.path,
                repo_name=repo_name,
                language=analysis_res.language,
                query_osv=False,
                health_score=analysis_res.health.score,
                health_grade=analysis_res.health.grade,
                analysis_id=report_id,
                commit_sha=analysis_res.commit_sha,
                source_fingerprint=analysis_res.source_fingerprint,
                parser_version=analysis_res.parser_version,
                files_analyzed=analysis_res.node_count,
                truncated=analysis_res.truncated,
                external_dependencies_count=len(analysis_res.external_dependencies),
                health_sub_scores=analysis_res.health.sub_scores,
                health_status=analysis_res.health.status,
            )
            report.metadata.report_id = report_id
            default_report_store.save_report(report)
        else:
            raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")

    content, media_type = ReportRenderer.render(report, format)
    safe_name = report.metadata.repo_name.lower().replace(" ", "-").replace("/", "-")
    ext = "md" if format == ReportFormat.MARKDOWN else format.value
    filename = f"archlens-report-{safe_name}-{report_id}.{ext}"

    if format == ReportFormat.JSON:
        body = json.dumps(content, indent=2)
    else:
        body = content  # type: ignore[assignment]

    return Response(
        content=body,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Id": report_id,
        },
    )


@router.get("/{report_id}/pdf", summary="Download server-generated PDF report")
@direct_reports_router.get("/{report_id}/pdf", summary="Download server-generated PDF report")
def get_pdf_report(report_id: str) -> Response:
    """GET /reports/{analysis_id}/pdf endpoint."""
    return download_report(report_id=report_id, format=ReportFormat.PDF)


@router.get("/{report_id}/markdown", summary="Download server-generated Markdown report")
@direct_reports_router.get("/{report_id}/markdown", summary="Download server-generated Markdown report")
def get_markdown_report(report_id: str) -> Response:
    """GET /reports/{analysis_id}/markdown endpoint."""
    return download_report(report_id=report_id, format=ReportFormat.MARKDOWN)


@router.get("/{report_id}/json", summary="Download server-generated JSON report")
@direct_reports_router.get("/{report_id}/json", summary="Download server-generated JSON report")
def get_json_report(report_id: str) -> Response:
    """GET /reports/{analysis_id}/json endpoint."""
    return download_report(report_id=report_id, format=ReportFormat.JSON)


class ReportNarrativeRequest(BaseModel):
    analysis_id: str | None = Field(None, description="Optional analysis ID to load context")
    report_data: dict[str, Any] = Field(default_factory=dict, description="Metrics dictionary")
    is_private_repo: bool = False
    source_type: str = ""


@router.post(
    "/narrative",
    summary="Generate plain-English narrative for architectural reports (in-app and PDF)",
)
@direct_reports_router.post(
    "/narrative",
    summary="Generate plain-English narrative for architectural reports (in-app and PDF)",
)
async def api_generate_report_narrative(
    req: ReportNarrativeRequest,
) -> Any:
    """Generate in-app and PDF executive narrative (what this means / why it matters / what to do)."""
    from ai.features import generate_report_narrative

    from app.services import analyzer_service

    data = dict(req.report_data)
    if req.analysis_id and not data.get("health_score"):
        res = analyzer_service.get_cached_result(req.analysis_id)
        if res:
            data.setdefault("health_score", res.health.score if res.health.score is not None else 75.0)
            data.setdefault("grade", res.health.grade or "B")
            data.setdefault("repo_name", Path(res.path).name or "Codebase")
            data.setdefault("node_count", res.node_count)
            data.setdefault("edge_count", res.edge_count)
            data.setdefault("cycles_count", len(res.cycles))
            data.setdefault("smells_count", len(res.smells))

    narrative = await generate_report_narrative(
        report_data=data,
        is_private_repo=req.is_private_repo,
        source_type=req.source_type,
    )
    return narrative.model_dump()
