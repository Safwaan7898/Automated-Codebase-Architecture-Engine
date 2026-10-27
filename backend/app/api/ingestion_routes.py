"""API endpoints for the universal ingestion layer.

Endpoints:
- POST /ingest: Start an ingestion job (Git URL, Archive URL, Snippet, Local Path)
- POST /ingest/archive: Upload an archive file (.zip, .tar.gz, etc.)
- POST /ingest/folder: Multipart upload for folder hierarchies preserving paths
- GET /jobs/{job_id}: Query job status, events, and results
- WS /ws/jobs/{job_id}: Real-time WebSocket streaming of pipeline progress
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Literal

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field

from app.auth.dependencies import require_permission
from app.auth.models import Permission
from app.auth.store import auth_store
from ingestion.exceptions import (
    EmptyArchiveError,
    IngestionError,
    LimitExceeded,
    LocalPathDisabledError,
    SecurityError,
    SourceError,
)
from ingestion.job_store import default_job_store
from ingestion.orchestrator import default_orchestrator
from ingestion.sources import (
    ArchiveUploadSource,
    ArchiveUrlSource,
    FolderUploadSource,
    GitSource,
    LocalPathSource,
    SnippetSource,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ingestion"])


# ── Request / Response Schemas ───────────────────────────────────────────────


class IngestGitRequest(BaseModel):
    source_type: Literal["git"] = "git"
    url: str = Field(..., description="HTTPS Git repository URL")
    branch: str | None = Field(None, description="Optional branch or tag name")
    commit: str | None = Field(None, description="Optional specific commit hash")
    subpath: str | None = Field(None, description="Optional subpath for monorepos")
    access_token: str | None = Field(None, description="Optional personal access token for private repositories")
    include_tests: bool = Field(False, description="Whether to include test/sample/fixture files in scope")
    enable_ai: bool = Field(False, description="Enable AI assistance with user consent")
    ai_consent: bool = Field(False, description="Explicit user consent for AI analysis")


class IngestArchiveUrlRequest(BaseModel):
    source_type: Literal["archive_url"] = "archive_url"
    url: str = Field(..., description="HTTPS URL of the archive to download")
    include_tests: bool = Field(False, description="Whether to include test/sample/fixture files in scope")
    enable_ai: bool = Field(False, description="Enable AI assistance with user consent")
    ai_consent: bool = Field(False, description="Explicit user consent for AI analysis")


class IngestSnippetRequest(BaseModel):
    source_type: Literal["snippet"] = "snippet"
    code: str = Field(..., description="Pasted code snippet")
    language: str = Field(..., description="Programming language (e.g. python, java)")
    filename: str | None = Field(None, description="Optional filename")
    include_tests: bool = Field(False, description="Whether to include test/sample/fixture files in scope")
    enable_ai: bool = Field(False, description="Enable AI assistance with user consent")
    ai_consent: bool = Field(False, description="Explicit user consent for AI analysis")


class IngestLocalRequest(BaseModel):
    source_type: Literal["local"] = "local"
    path: str = Field(..., description="Server filesystem path (requires ARCHLENS_ALLOW_LOCAL_PATHS=true)")
    include_tests: bool = Field(False, description="Whether to include test/sample/fixture files in scope")
    enable_ai: bool = Field(False, description="Enable AI assistance with user consent")
    ai_consent: bool = Field(False, description="Explicit user consent for AI analysis")


class IngestResponse(BaseModel):
    job_id: str
    status: str
    message: str


# ── Error handler helper ─────────────────────────────────────────────────────


def _map_ingestion_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, LimitExceeded):
        return HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=exc.user_message)
    if isinstance(exc, EmptyArchiveError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.user_message)
    if isinstance(exc, SecurityError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.user_message)
    if isinstance(exc, SourceError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.user_message)
    if isinstance(exc, IngestionError):
        return HTTPException(status_code=exc.status_code, detail=exc.user_message)
    return HTTPException(status_code=500, detail=str(exc))


# ── Routes ───────────────────────────────────────────────────────────────────


@router.get(
    "/ingest/config",
    summary="Get ingestion limits and allowed formats for clients",
)
async def get_ingest_config() -> dict[str, Any]:
    limits = default_orchestrator.limits
    return {
        "max_upload_size_mb": limits.max_compressed_bytes // (1024 * 1024),
        "max_upload_size_bytes": limits.max_compressed_bytes,
        "allowed_extensions": [".zip", ".tar.gz", ".tgz", ".tar", ".tar.bz2"],
        "supported_languages": ["python", "java"],
        "allow_local_ingestion": limits.allow_local_paths,
    }


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start an ingestion job from a JSON payload (Git, Archive URL, Snippet, Local)",
    dependencies=[Depends(require_permission(Permission.RUN_INGESTION))],
)
async def start_ingest_json(
    request: IngestGitRequest | IngestArchiveUrlRequest | IngestSnippetRequest | IngestLocalRequest,
    current_user: dict[str, Any] = Depends(require_permission(Permission.RUN_INGESTION)),
) -> IngestResponse:
    try:
        if request.source_type == "git":
            src = GitSource(
                url=request.url,
                branch=request.branch,
                commit=request.commit,
                subpath=request.subpath,
                access_token=request.access_token,
            )
        elif request.source_type == "archive_url":
            src = ArchiveUrlSource(url=request.url)
        elif request.source_type == "snippet":
            src = SnippetSource(
                code=request.code,
                language=request.language,
                filename=request.filename,
            )
        elif request.source_type == "local":
            if not default_orchestrator.limits.allow_local_paths:
                raise LocalPathDisabledError()
            src = LocalPathSource(path=request.path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source type: {request.source_type}")

        src.include_tests = getattr(request, "include_tests", False)
        src.enable_ai = getattr(request, "enable_ai", False)
        src.ai_consent = getattr(request, "ai_consent", False)
        job_id = await default_orchestrator.start_ingestion(src)

        # Audit log entry
        role_val = current_user.get("role")
        auth_store.add_audit_log(
            user_id=current_user.get("id", "anonymous"),
            user_email=current_user.get("work_email", "anonymous@archlens.io"),
            user_role=role_val.value if hasattr(role_val, "value") else str(role_val),
            action="ingestion_start",
            resource_type="job",
            resource_id=job_id,
            details={"source_type": request.source_type},
        )

        return IngestResponse(
            job_id=job_id,
            status="pending",
            message="Ingestion job scheduled successfully.",
        )
    except Exception as exc:
        raise _map_ingestion_error(exc) from exc


@router.post(
    "/ingest/archive",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload an archive file (.zip, .tar, .tar.gz, etc.)",
    dependencies=[Depends(require_permission(Permission.RUN_INGESTION))],
)
async def upload_archive(
    archive: UploadFile = File(..., description="Archive file"),
    language: str = Form("auto", description="Language option ('auto', 'python', 'java')"),
    include_tests: bool = Form(False, description="Include test/sample/fixture files in scope"),
    enable_ai: bool = Form(False, description="Enable AI assistance with user consent"),
    ai_consent: bool = Form(False, description="Explicit user consent for AI analysis"),
) -> IngestResponse:
    temp_path: Path | None = None
    try:
        limits = default_orchestrator.limits
        filename = archive.filename or "archive.zip"
        lower_name = filename.lower()
        allowed_exts = (".zip", ".tar.gz", ".tgz", ".tar", ".tar.bz2")
        if not any(lower_name.endswith(ext) for ext in allowed_exts):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported archive format: '{filename}'. Expected .zip, .tar.gz, .tgz, or .tar",
            )

        # Stream chunk-by-chunk to disk to protect memory
        temp_file = tempfile.NamedTemporaryFile(delete=False, prefix="archlens_stream_")
        temp_path = Path(temp_file.name)
        total_bytes = 0
        chunk_size = 1024 * 1024  # 1 MB chunks

        while True:
            chunk = await archive.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > limits.max_compressed_bytes:
                archive_mb = total_bytes / (1024 * 1024)
                limit_mb = limits.max_compressed_bytes / (1024 * 1024)
                temp_file.close()
                temp_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Archive is {archive_mb:.1f} MB; the limit is {limit_mb:.0f} MB.",
                )
            temp_file.write(chunk)
        temp_file.close()

        if total_bytes == 0:
            temp_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded archive is empty.",
            )

        src = ArchiveUploadSource(
            archive_data=temp_path,
            filename=filename,
            language=language,
            include_tests=include_tests,
        )
        src.enable_ai = enable_ai
        src.ai_consent = ai_consent
        job_id = await default_orchestrator.start_ingestion(src)
        return IngestResponse(
            job_id=job_id,
            status="pending",
            message="Archive upload accepted and queued for processing.",
        )
    except Exception as exc:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise _map_ingestion_error(exc) from exc


@router.post(
    "/ingest/folder",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a folder preserving nested relative paths",
    dependencies=[Depends(require_permission(Permission.RUN_INGESTION))],
)
async def upload_folder(
    files: list[UploadFile] = File(...),
    paths: list[str] = Form(..., description="List of relative file paths matching the uploaded files"),
    folder_name: str = Form("uploaded_folder"),
    include_tests: bool = Form(False, description="Include test/sample/fixture files in scope"),
    enable_ai: bool = Form(False, description="Enable AI assistance with user consent"),
    ai_consent: bool = Form(False, description="Explicit user consent for AI analysis"),
) -> IngestResponse:
    try:
        if len(files) != len(paths):
            raise HTTPException(
                status_code=400,
                detail=f"Mismatch: received {len(files)} files but {len(paths)} paths.",
            )

        file_tuples: list[tuple[str, bytes]] = []
        for file_obj, rel_path in zip(files, paths, strict=False):
            content = await file_obj.read()
            file_tuples.append((rel_path, content))

        src = FolderUploadSource(files=file_tuples, folder_name=folder_name)
        src.include_tests = include_tests
        src.enable_ai = enable_ai
        src.ai_consent = ai_consent
        job_id = await default_orchestrator.start_ingestion(src)
        return IngestResponse(
            job_id=job_id,
            status="pending",
            message="Folder upload accepted and queued for processing.",
        )
    except Exception as exc:
        raise _map_ingestion_error(exc) from exc


@router.get(
    "/jobs/{job_id}",
    summary="Query status and results of an ingestion job",
    dependencies=[Depends(require_permission(Permission.VIEW_GRAPH))],
)
async def get_job_status(job_id: str) -> dict[str, Any]:
    job = default_job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    res: dict[str, Any] = {
        "job_id": job.job_id,
        "status": str(job.status),
        "source_hash": job.source_hash,
        "created_at": job.created_at.isoformat(),
        "error": job.error,
        "metadata": job.metadata.to_dict() if job.metadata else None,
    }

    if job.analysis is not None:
        res["result"] = job.analysis.model_dump()
        res["analysis_id"] = job.job_id
        res["repo_id"] = job.job_id
    else:
        from app.services import analyzer_service

        cached_analysis = analyzer_service.get_cached_result(job_id)
        if cached_analysis is not None:
            job.analysis = cached_analysis
            res["result"] = cached_analysis.model_dump()
            res["analysis_id"] = job.job_id
            res["repo_id"] = job.job_id

    if job.result is not None:
        res["raw_parser"] = job.result.to_dict() if hasattr(job.result, "to_dict") else job.result

    return res


# ── WebSocket Endpoints ───────────────────────────────────────────────────────


@router.websocket("/ws/jobs/{job_id}")
@router.websocket("/jobs/{job_id}/ws")
async def ws_job_events(websocket: WebSocket, job_id: str) -> None:
    """Stream live ingestion and parsing progress events over WebSocket."""
    job = default_job_store.get_job(job_id)
    if not job:
        await websocket.close(code=4004, reason=f"Job '{job_id}' not found")
        return

    await websocket.accept()

    try:
        async for event in default_job_store.stream_events(job_id):
            await websocket.send_json(event.to_dict())
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected from job %s", job_id)
    except Exception as exc:
        logger.warning("Error streaming events for job %s: %s", job_id, exc)
