"""Pytest test verifying deterministic PDF generation, text extraction, and section completeness."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader

from analysis.facade import build_graph_from_dict
from app.services import analyzer_service
from reports.generator import default_report_generator
from reports.pdf import ReportRenderer

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_repo"


def test_pdf_generation_content_and_sections() -> None:
    """Generate PDF for fixture repo, extract text, and assert title, date, repo name, grade, and all section headings."""
    assert FIXTURE_DIR.exists(), f"Fixture directory not found: {FIXTURE_DIR}"

    analyzer_service._cache.clear()
    analyzer_service._cache_by_key.clear()

    analysis_res = analyzer_service.run_analysis(str(FIXTURE_DIR), language="python")
    graph = build_graph_from_dict(analysis_res.graph.model_dump())

    report = default_report_generator.generate_report(
        graph=graph,
        repo_path=str(FIXTURE_DIR),
        repo_name="mini_repo",
        language="python",
        query_osv=False,
        health_score=analysis_res.health.score,
        health_grade=analysis_res.health.grade,
        analysis_id=str(analysis_res.repo_id),
        commit_sha=analysis_res.commit_sha,
        source_fingerprint=analysis_res.source_fingerprint,
        parser_version=analysis_res.parser_version,
        files_analyzed=analysis_res.node_count,
        health_sub_scores=analysis_res.health.sub_scores,
        health_status=analysis_res.health.status,
    )

    pdf_bytes = ReportRenderer.render_pdf(report)
    assert len(pdf_bytes) > 1000, "PDF rendering produced empty or invalid byte sequence"

    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 5, f"Expected at least 5 pages, got {len(reader.pages)}"

    raw_text = " ".join(page.extract_text() for page in reader.pages)
    norm = " ".join(raw_text.split()).upper()

    # Required assertions from prompt
    assert "ARCHITECTURE DIAGNOSTIC REPORT" in norm, "Report title missing"
    assert "MINI_REPO" in norm, "Repo name missing"
    assert (analysis_res.health.grade or "A").upper() in norm, "Health grade missing"
    assert report.metadata.generated_at[:10] in norm, "Generation date missing"

    # Section headings verification
    expected_sections = [
        "EXECUTIVE SUMMARY",
        "HOW TO READ THIS REPORT",
        "HEALTH SCORECARD",
        "ARCHITECTURAL VISUALS",
        "DETAILED FINDINGS TABLES",
        "PRIORITIZED ACTION PLAN",
        "APPENDIX",
        "SCAN DETAILS",
    ]
    for sec in expected_sections:
        assert sec in norm, f"Section heading '{sec}' missing from extracted PDF text"


def test_report_generation_reproducible_for_same_analysis_id() -> None:
    """Generating report twice for the same analysis id produces identical content except generation timestamp."""
    analyzer_service._cache.clear()
    analyzer_service._cache_by_key.clear()

    analysis_res = analyzer_service.run_analysis(str(FIXTURE_DIR), language="python")
    graph = build_graph_from_dict(analysis_res.graph.model_dump())

    def _build():
        return default_report_generator.generate_report(
            graph=graph,
            repo_path=str(FIXTURE_DIR),
            repo_name="mini_repo",
            language="python",
            query_osv=False,
            health_score=analysis_res.health.score,
            health_grade=analysis_res.health.grade,
            analysis_id=str(analysis_res.repo_id),
            commit_sha=analysis_res.commit_sha,
            source_fingerprint=analysis_res.source_fingerprint,
            parser_version=analysis_res.parser_version,
            files_analyzed=analysis_res.node_count,
            health_sub_scores=analysis_res.health.sub_scores,
            health_status=analysis_res.health.status,
        )

    r1 = _build()
    r2 = _build()

    d1 = r1.model_dump()
    d2 = r2.model_dump()

    # Strip only generation timestamp
    d1["metadata"]["generated_at"] = ""
    d2["metadata"]["generated_at"] = ""

    j1 = json.dumps(d1, sort_keys=True)
    j2 = json.dumps(d2, sort_keys=True)

    assert j1 == j2, "Report contents diverged between two runs for the same analysis ID"
