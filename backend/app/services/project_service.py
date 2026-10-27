"""Service for managing multi-project workspaces, grouping analysis records, and comparing runs."""

from __future__ import annotations

import hashlib
import logging
from typing import Any
from urllib.parse import urlparse

from app.storage.analysis_store import AnalysisRecord, AnalysisStore, default_analysis_store

logger = logging.getLogger(__name__)


def compute_project_id(repo_url: str, branch: str | None) -> str:
    """Derive deterministic project identifier from repo URL and branch."""
    norm_url = (repo_url or "unknown").strip().rstrip("/").lower()
    if norm_url.endswith(".git"):
        norm_url = norm_url[:-4]
    norm_branch = (branch or "main").strip().lower()
    raw = f"{norm_url}::{norm_branch}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def derive_project_name(repo_url: str, branch: str | None) -> str:
    """Format human-readable project display name."""
    url = (repo_url or "Project").strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    # Handle git URLs or paths
    if "://" in url:
        path = urlparse(url).path.strip("/")
        base = path.split("/")[-1].removesuffix(".git") or path
    else:
        parts = url.replace("\\", "/").split("/")
        base = parts[-1] or (parts[-2] if len(parts) > 1 else url)

    b = branch or "main"
    return f"{base} ({b})"


class ProjectService:
    """Manages multi-project groupings, history metrics, and comparisons."""

    def __init__(self, store: AnalysisStore | None = None) -> None:
        self.store = store or default_analysis_store

    def list_projects(self, search: str | None = None, sort_by: str = "last_analyzed") -> list[dict[str, Any]]:
        """List all projects grouped by repo_url and branch."""
        records = self.store.list_records()
        groups: dict[str, list[AnalysisRecord]] = {}

        for rec in records:
            pid = compute_project_id(rec.repo_url, rec.branch)
            groups.setdefault(pid, []).append(rec)

        projects: list[dict[str, Any]] = []

        for pid, rec_list in groups.items():
            # Sort newest first
            rec_list.sort(key=lambda r: r.created_at, reverse=True)
            latest_rec = rec_list[0]
            latest_res = self.store.get_result(latest_rec.id)

            repo_url = latest_rec.repo_url
            branch = latest_rec.branch or "main"
            name = derive_project_name(repo_url, branch)

            score = 0.0
            grade = "N/A"
            cycles_count = 0
            smells_count = 0
            languages: dict[str, int] = {}
            total_nodes = 0
            total_edges = 0

            if latest_res:
                score = (
                    round(latest_res.health.score, 1)
                    if latest_res.health and latest_res.health.score is not None
                    else 0.0
                )
                grade = latest_res.health.grade if latest_res.health and latest_res.health.grade else "N/A"
                if latest_res.graph:
                    cycles_count = sum(1 for e in latest_res.graph.edges if e.is_cycle)
                    total_nodes = len(latest_res.graph.nodes)
                    total_edges = len(latest_res.graph.edges)
                    for n in latest_res.graph.nodes:
                        lang = n.language or "unknown"
                        languages[lang] = languages.get(lang, 0) + 1
                if latest_res.smells:
                    smells_count = len(latest_res.smells)

            # Build history items
            history: list[dict[str, Any]] = []
            for r in rec_list[:20]:
                res = self.store.get_result(r.id)
                h_score = round(res.health.score, 1) if res and res.health and res.health.score is not None else 0.0
                h_cycles = sum(1 for e in res.graph.edges if e.is_cycle) if res and res.graph else 0
                h_smells = len(res.smells) if res and res.smells else 0
                history.append(
                    {
                        "analysis_id": r.id,
                        "created_at": r.created_at,
                        "commit_sha": r.commit_sha or r.id[:8],
                        "status": r.status,
                        "score": h_score,
                        "cycles": h_cycles,
                        "smells": h_smells,
                        "node_count": len(res.graph.nodes) if res and res.graph else 0,
                        "edge_count": len(res.graph.edges) if res and res.graph else 0,
                    }
                )

            proj = {
                "project_id": pid,
                "name": name,
                "repo_url": repo_url,
                "branch": branch,
                "last_analyzed": latest_rec.created_at,
                "analysis_count": len(rec_list),
                "latest_analysis_id": latest_rec.id,
                "score": score,
                "grade": grade,
                "cycles": cycles_count,
                "smells": smells_count,
                "risk_score": round(max(0.0, (100.0 - score) + smells_count * 2.0 + cycles_count * 5.0), 1),
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "languages": languages,
                "history": history,
            }

            if search:
                s = search.lower()
                if s not in name.lower() and s not in repo_url.lower() and s not in branch.lower():
                    continue

            projects.append(proj)

        # Sorting
        if sort_by == "score":
            projects.sort(key=lambda p: p["score"], reverse=True)
        elif sort_by == "risk":
            projects.sort(key=lambda p: p.get("risk_score", 0.0), reverse=True)
        elif sort_by == "name":
            projects.sort(key=lambda p: p["name"].lower())
        elif sort_by == "smells":
            projects.sort(key=lambda p: p["smells"], reverse=True)
        else:  # last_analyzed default
            projects.sort(key=lambda p: p["last_analyzed"], reverse=True)

        return projects

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        """Get details and full historical metrics for a specific project."""
        projects = self.list_projects()
        for p in projects:
            if p["project_id"] == project_id:
                return p
        return None

    def delete_project(self, project_id: str) -> int:
        """Delete all analysis records and workspace data associated with a project."""
        records = self.store.list_records()
        deleted_count = 0

        for rec in records:
            pid = compute_project_id(rec.repo_url, rec.branch)
            if pid == project_id:
                if self.store.delete(rec.id):
                    deleted_count += 1

        logger.info("Deleted %d analysis records for project_id=%s", deleted_count, project_id)
        return deleted_count

    def compare_analyses(self, base_id: str, target_id: str) -> dict[str, Any]:
        """Perform deterministic structural comparison between two analysis runs."""
        base_res = self.store.get_result(base_id)
        target_res = self.store.get_result(target_id)

        if not base_res:
            raise ValueError(f"Base analysis record '{base_id}' not found")
        if not target_res:
            raise ValueError(f"Target analysis record '{target_id}' not found")

        # Extract node sets
        base_nodes = {n.id: n for n in (base_res.graph.nodes if base_res.graph else [])}
        target_nodes = {n.id: n for n in (target_res.graph.nodes if target_res.graph else [])}

        base_ids = set(base_nodes.keys())
        target_ids = set(target_nodes.keys())

        added_modules = sorted(target_ids - base_ids)
        removed_modules = sorted(base_ids - target_ids)
        common_ids = base_ids & target_ids

        modified_modules: list[dict[str, Any]] = []
        for mid in sorted(common_ids):
            bn = base_nodes[mid]
            tn = target_nodes[mid]
            bloc = bn.loc or 0
            tloc = tn.loc or 0
            bcc = bn.cyclomatic_complexity or 0
            tcc = tn.cyclomatic_complexity or 0
            if bloc != tloc or bcc != tcc:
                modified_modules.append(
                    {
                        "id": mid,
                        "loc_before": bloc,
                        "loc_after": tloc,
                        "loc_delta": tloc - bloc,
                        "complexity_before": bcc,
                        "complexity_after": tcc,
                        "complexity_delta": tcc - bcc,
                    }
                )

        # Edges
        def edge_key(e: Any) -> tuple[str, str]:
            s = e.source if isinstance(e.source, str) else getattr(e.source, "id", str(e.source))
            t = e.target if isinstance(e.target, str) else getattr(e.target, "id", str(e.target))
            return s, t

        base_edges = {edge_key(e) for e in (base_res.graph.edges if base_res.graph else [])}
        target_edges = {edge_key(e) for e in (target_res.graph.edges if target_res.graph else [])}

        added_edges = [{"source": s, "target": t} for s, t in sorted(target_edges - base_edges)]
        removed_edges = [{"source": s, "target": t} for s, t in sorted(base_edges - target_edges)]

        # Cycles
        base_cycles = sum(1 for e in (base_res.graph.edges if base_res.graph else []) if e.is_cycle)
        target_cycles = sum(1 for e in (target_res.graph.edges if target_res.graph else []) if e.is_cycle)

        # Health Scores
        base_score = round(base_res.health.score, 1) if base_res.health and base_res.health.score is not None else 0.0
        target_score = (
            round(target_res.health.score, 1) if target_res.health and target_res.health.score is not None else 0.0
        )
        score_delta = round(target_score - base_score, 1)

        # Smells
        base_smells = len(base_res.smells) if base_res.smells else 0
        target_smells = len(target_res.smells) if target_res.smells else 0
        smells_delta = target_smells - base_smells

        # Deterministic summary
        deterministic_summary = (
            f"Comparison from {base_id[:8]} to {target_id[:8]}: "
            f"Health score changed by {score_delta:+0.1f} ({base_score} -> {target_score}). "
            f"Added {len(added_modules)} modules, removed {len(removed_modules)}, modified {len(modified_modules)}. "
            f"Cycles: {base_cycles} -> {target_cycles} ({target_cycles - base_cycles:+d}). "
            f"Smells: {base_smells} -> {target_smells} ({smells_delta:+d})."
        )

        return {
            "base_id": base_id,
            "target_id": target_id,
            "base_score": base_score,
            "target_score": target_score,
            "score_delta": score_delta,
            "base_grade": base_res.health.grade if base_res.health else "N/A",
            "target_grade": target_res.health.grade if target_res.health else "N/A",
            "added_modules": added_modules,
            "removed_modules": removed_modules,
            "modified_modules": modified_modules,
            "added_edges": added_edges,
            "removed_edges": removed_edges,
            "base_cycles": base_cycles,
            "target_cycles": target_cycles,
            "cycles_delta": target_cycles - base_cycles,
            "base_smells": base_smells,
            "target_smells": target_smells,
            "smells_delta": smells_delta,
            "summary": deterministic_summary,
            "is_ai_generated": False,
        }


default_project_service = ProjectService()
