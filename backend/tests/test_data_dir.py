"""Test that ARCHLENS_DATA_DIR guarantees working directory independence."""

import os
from pathlib import Path
import pytest
from app.storage.analysis_store import AnalysisRecord, AnalysisStore
from reports.models import FullReport, ReportMetadata, ExecutiveSummary
from reports.store import ReportStore


def test_app_sees_same_data_from_different_working_directories(tmp_path: Path, monkeypatch) -> None:
    # 1. Define shared absolute data directory
    shared_data_dir = (tmp_path / "shared_data").resolve()
    shared_data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ARCHLENS_DATA_DIR", str(shared_data_dir))

    # Working directories
    work_dir_1 = tmp_path / "work_dir_1"
    work_dir_2 = tmp_path / "work_dir_2"
    work_dir_1.mkdir()
    work_dir_2.mkdir()

    # 2. In working directory 1: save an analysis and a report
    monkeypatch.chdir(work_dir_1)

    store_1 = AnalysisStore()
    assert store_1.db_path.parent == shared_data_dir

    from datetime import datetime, timezone

    rec_1 = AnalysisRecord(
        id="test-run-id-1234",
        repo_url="https://github.com/example/repo",
        branch="main",
        commit_sha="abcdef1234567890abcdef1234567890abcdef12",
        created_at=datetime.now(timezone.utc).isoformat(),
        status="complete",
        result_json='{"node_count": 42}',
        cache_key="test_cache_key_1",
    )
    store_1.save(rec_1)

    report_store_1 = ReportStore()
    assert report_store_1.storage_dir == shared_data_dir / ".reports_storage"

    from reports.generator import default_report_generator
    from analysis.facade import build_graph_from_dict

    g = build_graph_from_dict({"nodes": [{"id": "m1", "label": "m1", "path": "m1.py"}], "edges": []})
    test_report = default_report_generator.generate_report(
        graph=g,
        repo_path=str(work_dir_1),
        repo_name="dir_test",
        language="python",
        query_osv=False,
        analysis_id="REP-TEST-DIR-INDEPENDENCE",
    )
    test_report.metadata.report_id = "REP-TEST-DIR-INDEPENDENCE"
    test_report.executive_summary.health_score = 95.0
    report_store_1.save_report(test_report)

    # 3. In working directory 2: read from store without knowing dir 1
    monkeypatch.chdir(work_dir_2)

    store_2 = AnalysisStore()
    assert store_2.db_path.parent == shared_data_dir
    fetched_rec = store_2.get("test-run-id-1234")
    assert fetched_rec is not None
    assert fetched_rec.id == "test-run-id-1234"
    assert fetched_rec.cache_key == "test_cache_key_1"
    assert fetched_rec.status == "complete"

    report_store_2 = ReportStore()
    assert report_store_2.storage_dir == shared_data_dir / ".reports_storage"
    fetched_report = report_store_2.get_report("REP-TEST-DIR-INDEPENDENCE")
    assert fetched_report is not None
    assert fetched_report.metadata.report_id == "REP-TEST-DIR-INDEPENDENCE"
    assert fetched_report.executive_summary.health_score == 95.0
