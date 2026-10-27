"""Report storage and history management for ArchLens."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from reports.models import FullReport

logger = logging.getLogger(__name__)


import os


def _get_default_reports_dir() -> Path:
    try:
        from app.core.config import settings

        return settings.reports_storage_dir
    except Exception:
        env_dir = os.environ.get("ARCHLENS_DATA_DIR")
        if env_dir:
            p = Path(env_dir).resolve() / ".reports_storage"
        else:
            p = (Path(__file__).resolve().parent.parent / "data" / ".reports_storage").resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p


class ReportStore:
    """Stores generated reports in-memory and persists metadata to disk."""

    def __init__(self, storage_dir: Path | None = None) -> None:
        self.storage_dir = storage_dir or _get_default_reports_dir()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._reports: dict[str, FullReport] = {}

    def save_report(self, report: FullReport) -> str:
        """Save report to memory and disk."""
        rid = report.metadata.report_id
        self._reports[rid] = report

        # Persist JSON on disk
        file_path = self.storage_dir / f"{rid}.json"
        try:
            file_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to persist report %s to disk: %s", rid, exc)

        return rid

    def get_report(self, report_id: str) -> FullReport | None:
        """Retrieve report by ID."""
        if report_id in self._reports:
            return self._reports[report_id]

        file_path = self.storage_dir / f"{report_id}.json"
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                report = FullReport.model_validate(data)
                self._reports[report_id] = report
                return report
            except Exception:
                return None

        return None

    def list_reports(self) -> list[dict[str, Any]]:
        """Return history list of all saved reports."""
        items: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for r in self._reports.values():
            rid = r.metadata.report_id
            seen_ids.add(rid)
            items.append(
                {
                    "report_id": rid,
                    "repo_name": r.metadata.repo_name,
                    "health_score": r.executive_summary.health_score,
                    "grade": r.executive_summary.grade,
                    "components": r.executive_summary.total_components,
                    "dependencies": r.executive_summary.total_dependencies,
                    "critical_vulnerabilities": r.executive_summary.total_critical_vulnerabilities,
                    "cycles": r.executive_summary.total_circular_cycles,
                    "generated_at": r.metadata.generated_at,
                }
            )

        # Also scan disk for any previously saved reports
        for f in self.storage_dir.glob("REP-*.json"):
            rid = f.stem
            if rid not in seen_ids:
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    meta = data.get("metadata", {})
                    exec_s = data.get("executive_summary", {})
                    real_rid = meta.get("report_id", rid)
                    if real_rid not in seen_ids:
                        seen_ids.add(real_rid)
                        items.append(
                            {
                                "report_id": real_rid,
                                "repo_name": meta.get("repo_name", "Codebase"),
                                "health_score": exec_s.get("health_score", 0.0),
                                "grade": exec_s.get("grade", "N/A"),
                                "components": exec_s.get("total_components", 0),
                                "dependencies": exec_s.get("total_dependencies", 0),
                                "critical_vulnerabilities": exec_s.get("total_critical_vulnerabilities", 0),
                                "cycles": exec_s.get("total_circular_cycles", 0),
                                "generated_at": meta.get("generated_at", ""),
                            }
                        )
                except (json.JSONDecodeError, OSError) as exc:
                    logger.debug("Failed reading cached report from %s: %s", f, exc)
                    continue

        # Sort newest first
        items.sort(key=lambda x: str(x.get("generated_at", "")), reverse=True)
        return items


default_report_store = ReportStore()
