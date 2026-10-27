"""Ingestion orchestrator.

Coordinates:
1. Deduplication checks via source hash and git commit hash
2. Workspace directory creation and lifecycle
3. Source fetching (cloning, downloading, extracting, saving)
4. Language detection, breakdown, and capability checks
5. Parallel AST parsing and dependency resolution
6. Job event publication to WebSocket clients
7. Workspace read-only protection and TTL cleanup
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from parsers.config import IngestionConfig
from parsers.models import ProgressUpdate, RepositoryParseResult
from parsers.parallel_runner import parse_repository

from ingestion.config import IngestionLimits
from ingestion.exceptions import (
    IngestionError,
    SourceError,
)
from ingestion.job_store import JobStore, default_job_store
from ingestion.language_detector import scan_workspace
from ingestion.models import (
    IngestionSource,
    JobEvent,
    JobStatus,
    WorkspaceMetadata,
)
from ingestion.workspace import WorkspaceManager

logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    """Central engine running ingestion pipelines."""

    def __init__(
        self,
        job_store: JobStore | None = None,
        workspace_manager: WorkspaceManager | None = None,
        limits: IngestionLimits | None = None,
    ) -> None:
        self.job_store = job_store or default_job_store
        self.workspace_mgr = workspace_manager or WorkspaceManager()
        self.limits = limits or IngestionLimits.from_env()
        self._background_tasks: set[asyncio.Task[Any]] = set()

    async def start_ingestion(self, source: IngestionSource) -> str:
        """Start an ingestion pipeline asynchronously in the background.

        Returns the assigned job_id immediately.
        """
        job_id = str(uuid.uuid4())

        # Check deduplication cache
        cached = self.job_store.find_cached_job(source.source_hash)
        req_lang = getattr(source, "language", "auto")
        if cached and cached.metadata and cached.analysis:
            cached_lang = getattr(cached.analysis, "language", "").lower()
            if req_lang != "auto" and cached_lang and cached_lang != req_lang.lower():
                cached = None

        if cached and cached.metadata and (cached.result or cached.analysis):
            logger.info("Deduplication hit for source hash: %s (reusing job %s)", source.source_hash, cached.job_id)
            reused_job = self.job_store.create_job(job_id, source.source_hash)
            reused_job.metadata = cached.metadata
            reused_job.result = cached.result

            # Ensure analysis is also propagated
            cached_analysis = cached.analysis
            if cached_analysis is None:
                from app.services import analyzer_service
                cached_analysis = analyzer_service.get_cached_result(cached.job_id)

            reused_job.analysis = cached_analysis
            if cached_analysis is not None:
                from app.services import analyzer_service
                analysis_copy = cached_analysis.model_copy(deep=True)
                try:
                    analysis_copy.repo_id = uuid.UUID(job_id)
                except Exception:
                    pass
                analyzer_service._cache[job_id] = analysis_copy

            reused_job.status = JobStatus.COMPLETE
            reused_job.emit(
                JobEvent(
                    job_id=job_id,
                    status=JobStatus.COMPLETE,
                    stage="cached",
                    progress_pct=100.0,
                    message="Reused cached scan result.",
                    metadata=cached.metadata,
                )
            )
            return job_id

        # Create active job record
        self.job_store.create_job(job_id, source.source_hash)

        # Launch background task
        task = asyncio.create_task(self._run_pipeline(job_id, source))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return job_id

    async def run_sync(self, source: IngestionSource) -> tuple[WorkspaceMetadata, RepositoryParseResult | None]:
        """Run the ingestion pipeline synchronously (useful for tests or direct execution)."""
        job_id = str(uuid.uuid4())
        self.job_store.create_job(job_id, source.source_hash)
        return await self._run_pipeline(job_id, source)

    async def _run_pipeline(
        self,
        job_id: str,
        source: IngestionSource,
    ) -> tuple[WorkspaceMetadata, RepositoryParseResult | None]:
        record = self.job_store.get_job(job_id)
        assert record is not None

        async def report_progress(status: JobStatus, stage: str, pct: float, msg: str) -> None:
            record.emit(
                JobEvent(
                    job_id=job_id,
                    status=status,
                    stage=stage,
                    progress_pct=pct,
                    message=msg,
                )
            )

        workspace = self.workspace_mgr.create_workspace(job_id)
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=self.limits.workspace_ttl_s)

        metadata: WorkspaceMetadata | None = None

        try:
            # ── 1. Fetch source into workspace/src ────────────────────────────
            await report_progress(JobStatus.FETCHING, "starting", 0.0, f"Starting ingestion for {source.display_name}")
            extra_meta = await source.fetch(workspace.src_dir, self.limits, report_progress)

            # Check commit-based deduplication if git commit was discovered
            commit_hash = extra_meta.get("commit_hash")
            if commit_hash:
                self.job_store.record_commit(job_id, commit_hash)
                cached_commit = self.job_store.find_cached_by_commit(commit_hash)
                has_cached_result = cached_commit and (cached_commit.result or cached_commit.analysis)
                if has_cached_result and cached_commit.metadata and cached_commit.job_id != job_id:
                    logger.info("Deduplication hit for commit %s (reusing %s)", commit_hash, cached_commit.job_id)
                    record.metadata = cached_commit.metadata
                    record.result = cached_commit.result
                    record.analysis = cached_commit.analysis
                    record.status = JobStatus.COMPLETE
                    record.emit(
                        JobEvent(
                            job_id=job_id,
                            status=JobStatus.COMPLETE,
                            stage="cached_commit",
                            progress_pct=100.0,
                            message=f"Reused scan result from commit {commit_hash[:8]}.",
                            metadata=cached_commit.metadata,
                        )
                    )
                    self.workspace_mgr.delete_workspace(job_id)
                    return cached_commit.metadata, cached_commit.result

            # ── 2. Scan workspace for language breakdown ──────────────────────
            scan_msg = "Detecting languages and scanning files..."
            await report_progress(JobStatus.SCANNING, "language_detection", 30.0, scan_msg)
            scan_res = scan_workspace(workspace.src_dir, self.limits)

            metadata = WorkspaceMetadata(
                job_id=job_id,
                source_type=source.source_type,
                display_name=source.display_name,
                repo_name=source.repo_name,
                workspace_path=workspace.root,
                src_path=workspace.src_dir,
                language_breakdown=scan_res.language_breakdown,
                primary_language=scan_res.primary_language,
                file_count=scan_res.file_count,
                skipped_files=extra_meta.get("skipped_files", 0),
                skipped_by_dir=extra_meta.get("skipped_by_dir", {}),
                total_bytes=scan_res.total_bytes,
                supported=scan_res.supported,
                warnings=scan_res.warnings,
                commit_hash=commit_hash,
                branch=extra_meta.get("branch"),
                source_hash=source.source_hash,
                created_at=now,
                expires_at=expires,
            )

            if scan_res.file_count == 0:
                raise SourceError("No valid source files found in the ingested repository.")

            has_supported = any(
                lang.lower() in ("python", "java") for lang in scan_res.language_breakdown.keys()
            )
            if not has_supported:
                raise SourceError("No Python or Java files found in the ingested repository.")

            # ── 3. Parse AST if language is supported ─────────────────────────
            parse_result: RepositoryParseResult | None = None

            if scan_res.supported:
                parse_msg = f"Parsing {scan_res.primary_language} files in parallel..."
                await report_progress(JobStatus.PARSING, "ast_parsing", 50.0, parse_msg)

                async def parser_callback(update: ProgressUpdate) -> None:
                    if update.type == "progress":
                        # Map parser progress 0..100% to pipeline 50..90%
                        pipeline_pct = 50.0 + (update.percent * 0.4)
                        msg = (
                            f"Parsed {update.current}/{update.total} files "
                            f"({update.nodes_so_far} nodes, {update.edges_so_far} edges)"
                        )
                        await report_progress(JobStatus.PARSING, "parsing_files", pipeline_pct, msg)
                    elif update.type == "log":
                        await report_progress(JobStatus.PARSING, "parsing_log", 50.0, update.message)

                pconfig = IngestionConfig(
                    supported_languages=[scan_res.primary_language.lower()],
                    max_file_size_bytes=self.limits.max_file_size_bytes,
                    max_workers=self.limits.max_parse_workers,
                )

                parse_result = await parse_repository(
                    str(workspace.src_dir),
                    config=pconfig,
                    progress_callback=parser_callback,
                )
            else:
                logger.info(
                    "Skipping AST parsing for job %s: primary language '%s' is not yet supported.",
                    job_id,
                    scan_res.primary_language,
                )

            # ── 4. Graph Analysis Stage ───────────────────────────────────────
            analysis_result = None
            if scan_res.supported:
                await report_progress(
                    JobStatus.ANALYZING, "graph_analysis", 90.0, "Analyzing dependency structure and architecture..."
                )
                try:
                    from app.services import analyzer_service

                    analysis_result = analyzer_service.run_analysis(
                        path=str(workspace.src_dir),
                        language=scan_res.primary_language.lower(),
                        repo_id=job_id,
                        branch=metadata.branch,
                        commit_sha=metadata.commit_hash,
                        include_tests=getattr(source, "include_tests", False),
                        enable_ai=getattr(source, "enable_ai", False),
                        ai_consent=getattr(source, "ai_consent", False),
                        is_private_repo=bool(getattr(source, "access_token", None)),
                        source_type=getattr(source, "source_type", ""),
                    )
                    msg = (
                        f"Analyzed {analysis_result.node_count} components and "
                        f"{analysis_result.edge_count} dependency edges."
                    )
                    await report_progress(JobStatus.ANALYZING, "graph_analysis", 98.0, msg)
                except Exception as exc:
                    logger.warning("Analyzer service failed on job %s: %s", job_id, exc)

            # ── 5. Make workspace read-only for security ──────────────────────
            self.workspace_mgr.make_read_only(workspace.src_dir)

            # ── 6. Complete ───────────────────────────────────────────────────
            record.metadata = metadata
            record.result = parse_result
            record.analysis = analysis_result
            record.status = JobStatus.COMPLETE
            record.emit(
                JobEvent(
                    job_id=job_id,
                    status=JobStatus.COMPLETE,
                    stage="complete",
                    progress_pct=100.0,
                    message="Ingestion and analysis completed successfully.",
                    metadata=metadata,
                )
            )

            # Trigger background TTL cleanup
            self.workspace_mgr.cleanup_expired(self.limits.workspace_ttl_s)

            return metadata, parse_result

        except Exception as exc:
            error_msg = exc.user_message if isinstance(exc, IngestionError) else str(exc)
            logger.error("Ingestion job %s failed: %s", job_id, exc, exc_info=True)
            record.status = JobStatus.FAILED
            record.error = error_msg
            record.emit(
                JobEvent(
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    stage="error",
                    progress_pct=100.0,
                    message=f"Ingestion failed: {error_msg}",
                    error=error_msg,
                    metadata=metadata,
                )
            )
            # Clean up on failure so no orphaned temp files stay behind
            self.workspace_mgr.delete_workspace(job_id)
            return None, None


# Global default orchestrator instance
default_orchestrator = IngestionOrchestrator()
