"""Analyzer registry and service layer.

Keeps a registry of all available analyzers and routes analysis requests
to the appropriate one based on language auto-detection or explicit selection.
Persists results in SQLite AnalysisStore and keeps an in-process cache.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.analyzers.base import BaseAnalyzer
from app.analyzers.go_analyzer import GoAnalyzer
from app.analyzers.java_analyzer import JavaAnalyzer
from app.analyzers.javascript_analyzer import JavaScriptAnalyzer
from app.analyzers.multilang_analyzer import MultiLanguageAnalyzer
from app.analyzers.python_analyzer import PythonAnalyzer
from app.analyzers.treesitter_analyzer import TreeSitterAnalyzer
from app.analyzers.treesitter_common import detect_language
from app.core.logging import get_logger
from app.models.graph import AnalysisResult
from app.storage.analysis_store import AnalysisRecord, default_analysis_store

logger = get_logger(__name__)

# In-process result cache: repo_id -> AnalysisResult and cache_key -> AnalysisResult
_cache: dict[str, AnalysisResult] = {}
_cache_by_key: dict[str, AnalysisResult] = {}

# Registered analyzers (order matters for auto-detection)
_ANALYZERS: list[BaseAnalyzer] = [
    PythonAnalyzer(),
    JavaAnalyzer(),
    JavaScriptAnalyzer(),
    GoAnalyzer(),
    TreeSitterAnalyzer("rust"),
    TreeSitterAnalyzer("csharp"),
    TreeSitterAnalyzer("c"),
    TreeSitterAnalyzer("cpp"),
    TreeSitterAnalyzer("php"),
    TreeSitterAnalyzer("ruby"),
    TreeSitterAnalyzer("kotlin"),
]


def _get_analyzer(language: str, path: Path) -> BaseAnalyzer | None:
    norm_lang = language.lower().strip()
    if norm_lang in ("multilang", "mixed"):
        return MultiLanguageAnalyzer()

    if norm_lang == "auto":
        # Check if multiple languages exist in path
        if path.is_dir():
            found_langs: set[str] = set()
            for p in path.rglob("*"):
                if p.is_file() and not any(
                    part.startswith((".", "node_modules", "venv", "target", "vendor")) for part in p.parts
                ):
                    lang = detect_language(p)
                    if lang != "unknown":
                        found_langs.add(lang)
                        if len(found_langs) > 1:
                            logger.info(
                                "Auto-detected mixed languages %s for path %s -> MultiLanguageAnalyzer",
                                found_langs,
                                path,
                            )
                            return MultiLanguageAnalyzer()

        for analyzer in _ANALYZERS:
            if analyzer.can_handle(path):
                logger.info("Auto-detected language: %s for path %s", analyzer.language, path)
                return analyzer
        return None

    if norm_lang in ("javascript", "typescript", "js", "ts"):
        return JavaScriptAnalyzer()
    if norm_lang in ("go", "golang"):
        return GoAnalyzer()
    if norm_lang in ("c#", "cs", "csharp"):
        return TreeSitterAnalyzer("csharp")
    if norm_lang in ("c++", "cpp"):
        return TreeSitterAnalyzer("cpp")
    if norm_lang in ("c",):
        return TreeSitterAnalyzer("c")
    if norm_lang in ("rust", "rs"):
        return TreeSitterAnalyzer("rust")
    if norm_lang in ("php",):
        return TreeSitterAnalyzer("php")
    if norm_lang in ("ruby", "rb"):
        return TreeSitterAnalyzer("ruby")
    if norm_lang in ("kotlin", "kt"):
        return TreeSitterAnalyzer("kotlin")

    for analyzer in _ANALYZERS:
        if analyzer.language == norm_lang:
            return analyzer
    return None


def run_analysis(
    path: str,
    language: str = "auto",
    repo_id: str | None = None,
    branch: str | None = None,
    commit_sha: str | None = None,
    include_tests: bool = False,
    enable_ai: bool = False,
    ai_consent: bool = False,
    is_private_repo: bool = False,
    source_type: str = "local",
) -> AnalysisResult:
    """Run analysis on the given path (local filesystem directory or remote Git URL).

    Args:
        path: File system path or Git repository URL (e.g. https://github.com/...).
        language: 'python', 'java', or 'auto'.
        repo_id: Optional predetermined analysis ID (UUID string).
        branch: Optional Git branch name.
        commit_sha: Optional Git commit hash.

    Returns:
        AnalysisResult with a stable repo_id (cached in memory and persisted in SQLite).

    Raises:
        ValueError: If the path is invalid or cloning fails.
    """
    clean_path = path.strip()
    resolved: Path | None = None
    ingested_repo = None

    # 1. Handle remote Git repositories (HTTP/HTTPS/SSH)
    is_remote = (
        clean_path.startswith(("http://", "https://", "git@", "ssh://"))
        or "github.com/" in clean_path
        or clean_path.endswith(".git")
    )
    if is_remote:
        try:
            from parsers.config import IngestionConfig
            from parsers.ingestion import ingest_source

            logger.info("Ingesting remote repository URL: %s", clean_path)
            ingested_repo = ingest_source(clean_path, IngestionConfig())
            resolved = ingested_repo.root
        except Exception as exc:
            logger.error("Failed to clone remote repository %s: %s", clean_path, exc)
            raise ValueError(f"Failed to clone repository '{clean_path}': {exc}") from exc

    # 2. Handle local paths
    if resolved is None:
        p = Path(clean_path).resolve()
        if not p.exists():
            # Check relative to repo workspace root and parent directories
            workspace_root = Path(__file__).resolve().parent.parent.parent.parent
            candidates = [
                (Path.cwd().parent / clean_path).resolve(),
                (workspace_root / clean_path).resolve(),
                (Path.cwd() / clean_path).resolve(),
            ]
            for candidate in candidates:
                if candidate.exists():
                    p = candidate
                    break

        if not p.exists():
            raise ValueError(f"Path does not exist: {clean_path}")
        if not p.is_dir():
            raise ValueError(f"Path is not a directory: {clean_path}")
        resolved = p

    analyzer = _get_analyzer(language, resolved)
    if analyzer is None:
        # Fallback to PythonAnalyzer if any python files exist
        py_analyzer = PythonAnalyzer()
        if py_analyzer.can_handle(resolved):
            analyzer = py_analyzer
        else:
            # Fallback to JavaAnalyzer if java files exist
            java_analyzer = JavaAnalyzer()
            if java_analyzer.can_handle(resolved):
                analyzer = java_analyzer
            else:
                js_analyzer = JavaScriptAnalyzer()
                if js_analyzer.can_handle(resolved):
                    analyzer = js_analyzer
                else:
                    go_analyzer = GoAnalyzer()
                    if go_analyzer.can_handle(resolved):
                        analyzer = go_analyzer
                    else:
                        for ts_analyzer in _ANALYZERS:
                            if isinstance(ts_analyzer, TreeSitterAnalyzer) and ts_analyzer.can_handle(resolved):
                                analyzer = ts_analyzer
                                break

    if analyzer is None:
        raise ValueError(
            f"No compatible static analyzer found for codebase at '{clean_path}'. "
            "Supported languages: Python, Java, JavaScript/TypeScript, Go, Rust, C#, C/C++, PHP, Ruby, Kotlin."
        )

    # 3. Check deterministic cache by (source_fingerprint, parser_version, settings_hash)
    from parsers.fingerprint import (
        PARSER_VERSION,
        compute_cache_key,
        compute_settings_hash,
        compute_source_fingerprint,
        get_git_commit_sha,
    )

    source_fingerprint, _ = compute_source_fingerprint(resolved)
    if not commit_sha:
        if ingested_repo and getattr(ingested_repo, "commit_sha", None):
            commit_sha = ingested_repo.commit_sha
        else:
            commit_sha = get_git_commit_sha(resolved)
    settings_hash = compute_settings_hash({"language": analyzer.language, "include_tests": include_tests})
    cache_key = compute_cache_key(
        source_fingerprint=source_fingerprint,
        parser_version=PARSER_VERSION,
        settings_hash=settings_hash,
        language=analyzer.language,
        include_tests=include_tests,
    )

    cached_result: AnalysisResult | None = None
    if cache_key in _cache_by_key:
        cached_result = _cache_by_key[cache_key]
    else:
        cached_result = default_analysis_store.get_result_by_cache_key(cache_key)

    if cached_result is not None:
        logger.info("Deterministic cache hit for cache_key: %s", cache_key)
        res_copy = cached_result.model_copy(deep=True)
        if commit_sha and not res_copy.commit_sha:
            res_copy.commit_sha = commit_sha
        if repo_id:
            try:
                res_copy.repo_id = UUID(repo_id)
            except (ValueError, TypeError):
                pass
            try:
                record = AnalysisRecord(
                    id=str(res_copy.repo_id),
                    repo_url=clean_path,
                    branch=branch,
                    commit_sha=res_copy.commit_sha,
                    created_at=datetime.now(UTC).isoformat(),
                    status="completed",
                    result_json=res_copy.model_dump_json(),
                    cache_key=cache_key,
                )
                default_analysis_store.save(record)
            except Exception as exc:
                logger.warning("Failed to persist cached AnalysisRecord for %s: %s", res_copy.repo_id, exc)
        _cache[str(res_copy.repo_id)] = res_copy
        _cache_by_key[cache_key] = res_copy
        return res_copy

    logger.info("Running %s analyzer on %s (include_tests=%s)", analyzer.language, resolved, include_tests)
    result = analyzer.analyze(resolved, include_tests=include_tests)
    if commit_sha:
        result.commit_sha = commit_sha

    # Run AST security rules & diagnostics
    try:
        from diagnostics.engine import default_diagnostics_engine

        diag_report = default_diagnostics_engine.analyze_directory(resolved)
        findings_dicts = [f.to_dict() for f in diag_report.findings]
        result.findings = findings_dicts
        result.summary = diag_report.summary

        # Map findings and risk scores to graph nodes
        for node in result.graph.nodes:
            node_file = (node.file_path or "").replace("\\", "/")
            node_findings = [
                f
                for f in findings_dicts
                if (f.get("file_path") and f.get("file_path").replace("\\", "/") == node_file)
                or f.get("node_id") == node.id
            ]
            node.findings = node_findings
            if node.id in diag_report.risk_scores:
                node.risk_score = diag_report.risk_scores[node.id].risk_score
            node.is_vulnerable = any(str(f.get("severity", "")).lower() in ("critical", "high") for f in node_findings)
    except Exception as exc:
        logger.warning("Diagnostics execution failed during run_analysis: %s", exc)

    # Extract circular cycles for result.cycles
    try:
        from analysis.facade import build_graph_from_dict
        from analysis.scc import detect_circular_dependencies

        g_dict = {
            "nodes": [{"id": n.id} for n in result.graph.nodes],
            "edges": [{"source": e.source, "target": e.target} for e in result.graph.edges],
        }
        dir_g = build_graph_from_dict(g_dict)
        scc_cycles = detect_circular_dependencies(dir_g)
        result.cycles = [c.nodes for c in scc_cycles]
    except Exception as exc:
        logger.warning("Cycle extraction failed during run_analysis: %s", exc)

    # Generate refactoring suggestions from dependency graph
    try:
        from analysis.facade import build_graph_from_dict
        from refactor.engine import default_refactor_engine

        dir_g = build_graph_from_dict(
            {
                "nodes": [n.model_dump() for n in result.graph.nodes],
                "edges": [e.model_dump() for e in result.graph.edges],
            }
        )
        plan = default_refactor_engine.generate_plan(
            graph=dir_g,
            repo_root=resolved,
            enable_llm=False,
        )
        result.refactor_suggestions = [s.to_dict() for s in plan.suggestions]
    except Exception as exc:
        logger.warning("Refactor plan generation failed during run_analysis: %s", exc)

    # Infer edges for unsupported-language files via AI if consent given & AI enabled
    if (enable_ai or ai_consent) and result.unsupported_files and resolved.is_dir():
        try:
            import asyncio
            import concurrent.futures

            from ai import GLOBAL_AI_SERVICE
            from ai.features import infer_unsupported_language_edges

            from app.models.graph import GraphEdge, GraphNode, NodeType

            if GLOBAL_AI_SERVICE.is_enabled:
                valid_targets = {n.id for n in result.graph.nodes}
                existing_edge_keys = {(e.source, e.target) for e in result.graph.edges}
                unsupported_exts = set(result.unsupported_files.keys())

                candidate_files: list[Path] = []
                for p in resolved.rglob("*"):
                    if p.is_file() and p.suffix.lower() in unsupported_exts:
                        if not any(
                            part.startswith((".", "node_modules", "venv", "target", "vendor", "__pycache__"))
                            for part in p.parts
                        ):
                            candidate_files.append(p)
                            if len(candidate_files) >= 10:
                                break

                def _run_coro(coro: Any) -> Any:
                    try:
                        asyncio.get_running_loop()
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                            return pool.submit(asyncio.run, coro).result()
                    except RuntimeError:
                        return asyncio.run(coro)

                for fpath in candidate_files:
                    try:
                        rel_str = str(fpath.relative_to(resolved)).replace("\\", "/")
                        content = fpath.read_text(encoding="utf-8", errors="ignore")
                        inferred = _run_coro(
                            infer_unsupported_language_edges(
                                file_path=rel_str,
                                content=content,
                                valid_targets=valid_targets,
                                is_private_repo=is_private_repo,
                                source_type=source_type,
                            )
                        )
                        for inf in inferred:
                            if inf.target in valid_targets and (inf.source, inf.target) not in existing_edge_keys:
                                if not any(n.id == inf.source for n in result.graph.nodes):
                                    result.graph.nodes.append(
                                        GraphNode(
                                            id=inf.source,
                                            label=fpath.name,
                                            type=NodeType.MODULE,
                                            language=fpath.suffix.lstrip(".").lower() or "unknown",
                                            file_path=rel_str,
                                            metadata={"is_ai_inferred": True},
                                        )
                                    )
                                result.graph.edges.append(
                                    GraphEdge(
                                        source=inf.source,
                                        target=inf.target,
                                        edge_type=inf.edge_type,
                                        confidence="ai_inferred",
                                    )
                                )
                                existing_edge_keys.add((inf.source, inf.target))
                    except Exception as f_exc:
                        logger.debug("Failed inferring edges for %s: %s", fpath, f_exc)
        except Exception as exc:
            logger.warning("Unsupported language edge inference failed during analysis: %s", exc)

    # Use specified repo_id if provided
    if repo_id:
        try:
            result.repo_id = UUID(repo_id)
        except (ValueError, TypeError):
            pass

    # Store in memory cache
    repo_id_str = str(result.repo_id)
    _cache[repo_id_str] = result
    _cache_by_key[cache_key] = result

    # Persist in SQLite analysis store
    try:
        record = AnalysisRecord(
            id=repo_id_str,
            repo_url=clean_path,
            branch=branch,
            commit_sha=result.commit_sha,
            created_at=datetime.now(UTC).isoformat(),
            status="completed",
            result_json=result.model_dump_json(),
            cache_key=cache_key,
        )
        default_analysis_store.save(record)
    except Exception as exc:
        logging.getLogger(__name__).warning("Failed to persist AnalysisRecord for %s: %s", repo_id_str, exc)

    logger.info(
        "Analysis complete: repo_id=%s nodes=%d edges=%d smells=%d",
        repo_id_str,
        result.node_count,
        result.edge_count,
        len(result.smells),
    )
    return result


def get_cached_result(repo_id: str) -> AnalysisResult | None:
    """Return a previously cached analysis result by repo_id (from cache, SQLite, or ingestion jobs)."""
    if repo_id in _cache:
        return _cache[repo_id]
    result = default_analysis_store.get_result(repo_id)
    if result is not None:
        _cache[repo_id] = result
        return result

    # Check ingestion job store
    try:
        from ingestion.orchestrator import default_job_store

        job = default_job_store.get_job(repo_id)
        if job:
            if job.analysis is not None:
                _cache[repo_id] = job.analysis
                return job.analysis
            if job.source_hash:
                cached_orig = default_job_store.find_cached_job(job.source_hash)
                if cached_orig and cached_orig.analysis is not None:
                    _cache[repo_id] = cached_orig.analysis
                    return cached_orig.analysis
    except Exception as exc:
        logger.debug("Failed checking job store for %s: %s", repo_id, exc)

    return None


def list_cached_ids() -> list[str]:
    """Return all cached and persisted repo_ids ordered newest first."""
    persisted_ids = default_analysis_store.list_ids()
    for k in _cache:
        if k not in persisted_ids:
            persisted_ids.append(k)
    try:
        from ingestion.orchestrator import default_job_store

        for jid, job in default_job_store.jobs.items():
            if (job.analysis is not None or job.result is not None) and jid not in persisted_ids:
                persisted_ids.append(jid)
    except Exception as exc:
        logger.debug("Failed listing cached job ids: %s", exc)
    return persisted_ids
