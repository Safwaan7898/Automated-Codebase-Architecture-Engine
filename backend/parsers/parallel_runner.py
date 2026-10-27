"""Parallel file parsing with WebSocket-compatible progress streaming.

The main entry point is :func:`parse_repository`, which:

1. Ingests the source (GitHub URL or local path).
2. Collects all parseable files respecting :class:`~parsers.config.IngestionConfig`.
3. Dispatches to language-specific parsers using a ``ThreadPoolExecutor``.
4. Reports progress via an async callback (suitable for WebSocket streaming).
5. Runs import resolution across the full result set.
6. Returns a :class:`~parsers.models.RepositoryParseResult`.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from parsers.cache import FileParseCache, default_file_parse_cache, hash_file_content
from parsers.config import IngestionConfig
from parsers.import_resolver import resolve_imports
from parsers.ingestion import (
    FileInfo,
    IngestedRepo,
    cleanup_ingested,
    collect_files,
    detect_primary_language,
    ingest_source,
)
from parsers.models import ParseResult, ProgressUpdate, RepositoryParseResult
from parsers.registry import get_parser

logger = logging.getLogger(__name__)

# Type alias for progress callback
ProgressCallback = Callable[[ProgressUpdate], Awaitable[None]]


# ── Public API ────────────────────────────────────────────────────────────────


async def parse_repository(
    source: str,
    config: IngestionConfig | None = None,
    *,
    progress_callback: ProgressCallback | None = None,
    cache: FileParseCache | None = default_file_parse_cache,
) -> RepositoryParseResult:
    """Parse an entire repository, streaming progress to *progress_callback*.

    Args:
        source:            Local path or GitHub URL.
        config:            Ingestion settings (defaults to :class:`IngestionConfig`).
        progress_callback: Async callable receiving :class:`ProgressUpdate` messages.
        cache:             Optional :class:`FileParseCache` for incremental parsing by file SHA-256.

    Returns:
        :class:`RepositoryParseResult` with all nodes, edges, and summary stats.
    """
    if config is None:
        config = IngestionConfig()

    repo_id = str(uuid.uuid4())
    t_start = time.monotonic()

    # ── 1. Ingest ──────────────────────────────────────────────────────────────
    await _notify(progress_callback, ProgressUpdate(type="log", message=f"Ingesting source: {source}"))
    ingested: IngestedRepo = await asyncio.to_thread(ingest_source, source, config)

    from parsers.fingerprint import (
        DEFAULT_RANDOM_SEED,
        PARSER_VERSION,
        compute_settings_hash,
        compute_source_fingerprint,
        get_git_commit_sha,
    )

    # Compute deterministic source fingerprint and provenance
    source_fingerprint, _ = await asyncio.to_thread(compute_source_fingerprint, ingested.root)
    commit_sha = getattr(ingested, "commit_sha", None)
    if not commit_sha:
        commit_sha = await asyncio.to_thread(get_git_commit_sha, ingested.root)
    settings_hash = compute_settings_hash({"max_files": config.max_files, "languages": config.supported_languages})
    repo_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"archlens:{source_fingerprint}"))

    # Sanitize source name: never leak temporary clone paths or machine-specific directories
    clean_source = source
    if "archlens_clone_" in source or Path(source).is_absolute():
        clean_source = ingested.root.name or "repository"

    # ── 2. Collect files ───────────────────────────────────────────────────────
    files: list[FileInfo] = await asyncio.to_thread(collect_files, ingested.root, config)
    raw_total = len(files)
    primary_language = detect_primary_language(files)

    errors_global: list[str] = []
    truncated = False
    truncated_counts: dict[str, int] = {}

    # Enforce max files limit for huge repos deterministically
    if raw_total > config.max_files:
        msg = f"Repository file count ({raw_total}) exceeds limit ({config.max_files}); truncated."
        logger.warning(msg)
        errors_global.append(msg)
        truncated = True
        truncated_counts = {
            "max_files": config.max_files,
            "total_files": raw_total,
            "skipped_files": raw_total - config.max_files,
        }
        files = files[: config.max_files]

    total = len(files)

    await _notify(
        progress_callback,
        ProgressUpdate(
            type="log",
            message=f"Found {total} files (primary language: {primary_language})",
        ),
    )

    if total == 0:
        cleanup_ingested(ingested)
        return RepositoryParseResult(
            repo_id=repo_id,
            source=clean_source,
            language=primary_language,
            duration_ms=(time.monotonic() - t_start) * 1000,
            errors=errors_global,
            source_fingerprint=source_fingerprint,
            commit_sha=commit_sha,
            parser_version=PARSER_VERSION,
            settings_hash=settings_hash,
            truncated=truncated,
            truncated_counts=truncated_counts,
            random_seed=DEFAULT_RANDOM_SEED,
        )

    # ── 3. Parse in parallel with incremental cache and timeout ─────────────────
    file_results: list[ParseResult] = []
    nodes_so_far = 0
    edges_so_far = 0

    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        # Submit all tasks
        future_to_file: dict[Any, FileInfo] = {
            executor.submit(_parse_one, fi, ingested.root, cache): fi for fi in files
        }

        completed = 0
        remaining_timeout = max(5.0, float(config.parse_timeout_s))

        try:
            for future in as_completed(future_to_file, timeout=remaining_timeout):
                fi = future_to_file[future]
                completed += 1
                pct = (completed / total) * 100.0

                try:
                    pr: ParseResult = future.result()
                except Exception as exc:  # noqa: BLE001
                    err = f"Worker error for {fi.rel_path}: {exc}"
                    logger.warning(err)
                    errors_global.append(err)
                    pr = ParseResult(file_path=fi.rel_path, language=fi.language, errors=[err])

                file_results.append(pr)
                nodes_so_far += pr.node_count
                edges_so_far += pr.edge_count

                if pr.errors:
                    for e in pr.errors:
                        logger.debug("Parse warning [%s]: %s", fi.rel_path, e)

                await _notify(
                    progress_callback,
                    ProgressUpdate(
                        type="progress",
                        current=completed,
                        total=total,
                        percent=pct,
                        file=fi.rel_path,
                        nodes_so_far=nodes_so_far,
                        edges_so_far=edges_so_far,
                    ),
                )
        except TimeoutError:
            timeout_msg = (
                f"Parsing timed out after {config.parse_timeout_s} seconds ({completed}/{total} files completed)."
            )
            logger.warning(timeout_msg)
            errors_global.append(timeout_msg)
            truncated = True
            truncated_counts["timed_out"] = 1
            truncated_counts["completed_files"] = completed
            truncated_counts["total_files"] = total
            # Cancel any uncompleted futures
            for fut in future_to_file:
                fut.cancel()

    # Deterministic order: sort file_results by relative file path before building graph
    file_results.sort(key=lambda pr: pr.file_path)

    # ── 4. Resolve imports ─────────────────────────────────────────────────────
    await _notify(progress_callback, ProgressUpdate(type="log", message="Resolving imports…"))
    resolved_nodes, resolved_edges = await asyncio.to_thread(resolve_imports, file_results, primary_language)

    # ── 5. Collect all parse errors ────────────────────────────────────────────
    all_errors = errors_global + [f"{fr.file_path}: {e}" for fr in file_results for e in fr.errors]

    duration_ms = (time.monotonic() - t_start) * 1000

    result = RepositoryParseResult(
        repo_id=repo_id,
        source=clean_source,
        language=primary_language,
        nodes=resolved_nodes,
        edges=resolved_edges,
        file_results=file_results,
        errors=all_errors,
        duration_ms=duration_ms,
        files_parsed=len([fr for fr in file_results if not fr.errors or fr.node_count > 0]),
        files_skipped=len([fr for fr in file_results if fr.errors and fr.node_count == 0]),
        source_fingerprint=source_fingerprint,
        commit_sha=commit_sha,
        parser_version=PARSER_VERSION,
        settings_hash=settings_hash,
        truncated=truncated,
        truncated_counts=truncated_counts,
        random_seed=DEFAULT_RANDOM_SEED,
    )

    logger.info(result.summary())
    await _notify(
        progress_callback,
        ProgressUpdate(
            type="log",
            message=f"Done — {result.node_count} nodes, {result.edge_count} edges in {duration_ms:.0f} ms",
        ),
    )

    try:
        cleanup_ingested(ingested)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cleanup error: %s", exc)

    return result


# ── Private helpers ───────────────────────────────────────────────────────────


def _parse_one(fi: FileInfo, root: Any, cache: FileParseCache | None = None) -> ParseResult:
    """Thread worker: parse a single file using the appropriate parser, leveraging cache."""
    fhash: str | None = None
    if cache is not None:
        try:
            fhash = hash_file_content(fi.abs_path)
            cached_res = cache.get(fhash, fi.rel_path)
            if cached_res is not None:
                return cached_res
        except Exception as exc:
            logger.debug("Failed hashing %s for cache: %s", fi.abs_path, exc)

    parser = get_parser(fi.language)
    if parser is None:
        pr = ParseResult(file_path=fi.rel_path, language=fi.language)
        pr.errors.append(f"No parser registered for language '{fi.language}'")
        return pr

    pr = parser.safe_parse_file(fi.abs_path, fi.rel_path)

    if cache is not None and fhash is not None and not pr.errors:
        try:
            cache.set(fhash, pr)
        except Exception as exc:
            logger.debug("Failed caching %s: %s", fi.abs_path, exc)

    return pr


async def _notify(callback: ProgressCallback | None, update: ProgressUpdate) -> None:
    """Send a progress update if a callback is registered."""
    if callback is not None:
        try:
            await callback(update)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Progress callback error: %s", exc)
