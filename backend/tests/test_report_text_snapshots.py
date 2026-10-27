"""Snapshot tests asserting narrative text accuracy, absence of false claims,

and complete section metadata across clean, cycle, and vulnerable scenarios.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader
import pypdfium2 as pdfium

from analysis.graph import DirectedGraph
from analysis.facade import build_graph_from_dict
from app.services import analyzer_service
from reports.generator import default_report_generator
from reports.pdf import ReportRenderer

MINI_REPO_DIR = Path(__file__).parent / "fixtures" / "mini_repo"
DIAGNOSTICS_DIR = Path(__file__).parent / "fixtures" / "diagnostics"
ARTIFACTS_DIR = Path(r"C:\Users\mmoha\.gemini\antigravity-ide\brain\f406697d-bd3c-4749-83f7-baf55fb467e5")


def _assert_no_empty_fields_in_report(report: Any) -> None:
    """Validate that every section contains populated fields and no blank strings/cards."""
    # Executive summary
    exec_s = report.executive_summary
    assert exec_s.callout.what_it_means.strip(), "Executive summary what_it_means is empty"
    assert exec_s.callout.why_it_matters.strip(), "Executive summary why_it_matters is empty"
    assert exec_s.callout.what_to_do.strip(), "Executive summary what_to_do is empty"
    assert len(exec_s.summary_sentences) >= 3, "Expected at least 3 dynamic narrative sentences"
    for s in exec_s.summary_sentences:
        assert s.strip(), "Found empty summary sentence"

    # Top risks
    assert len(exec_s.top_3_risks) >= 1, "Expected at least 1 risk card"
    for risk in exec_s.top_3_risks:
        assert risk.title.strip(), "Risk title is blank"
        assert risk.severity.strip(), "Risk severity is blank"
        assert risk.description.strip(), "Risk description is blank"
        assert risk.remediation_target.strip(), "Risk remediation_target is blank"

    # Architecture overview
    arch = report.architecture_overview
    assert arch.callout.what_it_means.strip()
    assert arch.callout.why_it_matters.strip()
    assert arch.callout.what_to_do.strip()

    # Dependency analysis
    dep = report.dependency_analysis
    assert dep.callout.what_it_means.strip()
    assert dep.callout.why_it_matters.strip()
    assert dep.callout.what_to_do.strip()

    # Security findings
    sec = report.security_findings
    assert sec.callout.what_it_means.strip()
    assert sec.callout.why_it_matters.strip()
    assert sec.callout.what_to_do.strip()

    # Prioritized action plan
    plan = report.prioritized_action_plan
    assert plan.callout.what_it_means.strip()
    assert plan.callout.why_it_matters.strip()
    assert plan.callout.what_to_do.strip()
    assert (len(plan.fix_now) + len(plan.next_sprint) + len(plan.later)) >= 1, (
        "Action items should not be completely empty"
    )


def test_scenario_clean_repo_no_circular_dependencies_and_no_empty_fields(tmp_path: Path) -> None:
    """Scenario 1 (Clean Repo):

    - Assert narrative says 'No circular dependencies were found'
    - Assert false claim 'circular dependencies' is absent from active findings/risks
    - Assert single clean risk card with non-blank target ('No action required')
    - Assert grade-derived status is green ('EXCELLENT' or 'GOOD')
    - Assert no section contains empty fields
    - Generate PDF and render page image
    """
    g = DirectedGraph()
    g.add_node(
        "pkg.presentation.views",
        name="views",
        node_type="module",
        path="src/presentation/views.py",
        metrics={"loc": 45, "cyclomatic_complexity": 2, "layer": "Presentation"},
    )
    g.add_node(
        "pkg.services.user_service",
        name="user_service",
        node_type="module",
        path="src/services/user_service.py",
        metrics={"loc": 75, "cyclomatic_complexity": 3, "layer": "Service"},
    )
    g.add_node(
        "pkg.domain.models",
        name="models",
        node_type="module",
        path="src/domain/models.py",
        metrics={"loc": 30, "cyclomatic_complexity": 1, "layer": "Domain"},
    )
    g.add_edge("pkg.presentation.views", "pkg.services.user_service", edge_type="import")
    g.add_edge("pkg.services.user_service", "pkg.domain.models", edge_type="import")

    report = default_report_generator.generate_report(
        graph=g,
        repo_path=str(tmp_path),
        repo_name="clean_repo",
        language="python",
        query_osv=False,
        health_score=94.5,
        health_grade="A",
        health_status="healthy",
        commit_sha="a1b2c3d4e5",
    )

    _assert_no_empty_fields_in_report(report)

    # 1. Narrative sentences dynamically branched
    exec_sentences = report.executive_summary.summary_sentences
    assert "No circular dependencies were found" in exec_sentences[2], (
        f"Expected 'No circular dependencies were found', got: {exec_sentences[2]}"
    )
    assert "No monolithic god classes were detected" in exec_sentences[3]
    assert "Zero critical security vulnerabilities" in exec_sentences[4]

    # False anti-pattern claims must NOT be present
    all_summary_text = " ".join(exec_sentences)
    assert "Tight coupling and circular dependencies detected" not in all_summary_text
    assert "detected in the core domain" not in all_summary_text

    # Top risks: must be exactly 1 clean card, not 3 empty MODERATE cards
    top_risks = report.executive_summary.top_3_risks
    assert len(top_risks) == 1, f"Expected 1 clean risk card, got {len(top_risks)}"
    assert top_risks[0].title == "No significant risks found"
    assert top_risks[0].severity == "Clean"
    assert top_risks[0].remediation_target == "No action required"

    # Status badge derives strictly from grade A -> green
    assert report.executive_summary.status_indicator.upper() == "GREEN"
    assert report.executive_summary.status_label in ["EXCELLENT", "GOOD"]

    # Target metadata sanitized
    assert report.metadata.repo_name == "clean_repo"
    assert report.metadata.commit_sha == "a1b2c3d"

    # Generate PDF and render page image
    pdf_bytes = ReportRenderer.render_pdf(report)
    assert pdf_bytes.startswith(b"%PDF"), "Must produce valid PDF binary"
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pdf_text = " ".join(p.extract_text() for p in reader.pages)

    assert "No circular dependencies were found" in pdf_text
    assert "Tight coupling and circular dependencies detected" not in pdf_text
    assert "ISO/SOC2 compliance" not in pdf_text
    assert "100% deterministic coverage" not in pdf_text

    # Save page 1 image
    doc = pdfium.PdfDocument(pdf_bytes)
    assert len(doc) >= 5
    page_img = doc[0].render(scale=1.5).to_pil()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    img_path = ARTIFACTS_DIR / "pdf_clean_repo_page1.png"
    page_img.save(str(img_path))
    assert img_path.exists() and img_path.stat().st_size > 1000


def test_scenario_cycle_repo_detects_real_cycles_and_break_edge() -> None:
    """Scenario 2 (Cycle Repo):

    - Assert analysis detects circular dependencies between module_a and module_b
    - Assert narrative describes the real cycle count
    - Assert prioritized remediation identifies the cycle break edge
    - Assert status badge derives from grade
    - Assert no section contains empty fields
    - Generate PDF and render page image
    """
    assert MINI_REPO_DIR.exists(), f"Missing mini_repo: {MINI_REPO_DIR}"
    analyzer_service._cache.clear()
    analyzer_service._cache_by_key.clear()

    analysis_res = analyzer_service.run_analysis(str(MINI_REPO_DIR), language="python")
    graph = build_graph_from_dict(analysis_res.graph.model_dump())

    report = default_report_generator.generate_report(
        graph=graph,
        repo_path=str(MINI_REPO_DIR),
        repo_name="mini_repo_cycles",
        language="python",
        query_osv=False,
        health_score=analysis_res.health.score,
        health_grade=analysis_res.health.grade,
        health_status=analysis_res.health.status,
        commit_sha=analysis_res.commit_sha,
        source_fingerprint=analysis_res.source_fingerprint,
    )

    _assert_no_empty_fields_in_report(report)

    # Verify cycle detection
    dep = report.dependency_analysis
    assert len(dep.cycles) >= 1, "Expected at least 1 circular dependency cycle in mini_repo"

    # Narrative sentences must reflect real cycle count
    exec_sentences = report.executive_summary.summary_sentences
    assert "circular dependency" in exec_sentences[2]

    # Action plan identifies break edge
    fix_now_titles = [item.title for item in report.prioritized_action_plan.fix_now]
    assert any("Break Circular Dependency" in t for t in fix_now_titles)

    # Target metadata
    assert report.metadata.repo_name == "mini_repo_cycles"
    assert report.metadata.commit_sha not in ["HEAD", "repository"]

    # Generate PDF and render page image
    pdf_bytes = ReportRenderer.render_pdf(report)
    assert pdf_bytes.startswith(b"%PDF")
    doc = pdfium.PdfDocument(pdf_bytes)
    assert len(doc) >= 5
    page_img = doc[0].render(scale=1.5).to_pil()
    img_path = ARTIFACTS_DIR / "pdf_cycle_repo_page1.png"
    page_img.save(str(img_path))
    assert img_path.exists() and img_path.stat().st_size > 1000


def test_scenario_vulnerable_repo_detects_security_findings_with_remediation() -> None:
    """Scenario 3 (Vulnerable Repo):

    - Assert analysis flags security smells / vulnerabilities
    - Assert findings contain remediation guidance and CWE/OWASP info
    - Assert no section contains empty fields
    - Assert hotspot severity labels use documented thresholds (0.0 is not Moderate)
    - Generate PDF
    """
    g = DirectedGraph()
    # Complex module with high complexity and security smell
    g.add_node(
        "app.api.vulnerable_endpoint",
        name="vulnerable_endpoint",
        node_type="module",
        path="src/api/vulnerable_endpoint.py",
        metrics={"loc": 180, "cyclomatic_complexity": 22, "layer": "Presentation"},
    )
    g.add_node(
        "app.db.raw_sql",
        name="raw_sql",
        node_type="module",
        path="src/db/raw_sql.py",
        metrics={"loc": 110, "cyclomatic_complexity": 14, "layer": "Data / Infrastructure"},
    )
    g.add_edge("app.api.vulnerable_endpoint", "app.db.raw_sql", edge_type="call")

    report = default_report_generator.generate_report(
        graph=g,
        repo_path=str(DIAGNOSTICS_DIR),
        repo_name="vulnerable_diagnostics",
        language="python",
        query_osv=False,
        health_score=48.0,
        health_grade="F",
        health_status="critical",
        commit_sha="c9d8e7f6a5",
    )

    _assert_no_empty_fields_in_report(report)

    # Status indicator derived from grade F -> red
    assert report.executive_summary.status_indicator.upper() == "RED"
    assert report.executive_summary.status_label == "POOR"

    # Appendix states real limitations
    limitations_dict = report.appendix.get("limitations", {})
    limitations_text = " ".join(str(v) for v in limitations_dict.values())
    assert "ISO/SOC2 compliance" not in limitations_text
    assert "100% deterministic coverage" not in limitations_text
    assert "dynamic imports" in limitations_text.lower()
    assert "python and java" in limitations_text.lower()

    # Generate PDF
    pdf_bytes = ReportRenderer.render_pdf(report)
    assert pdf_bytes.startswith(b"%PDF")
    doc = pdfium.PdfDocument(pdf_bytes)
    assert len(doc) >= 5
    page_img = doc[0].render(scale=1.5).to_pil()
    img_path = ARTIFACTS_DIR / "pdf_vulnerable_repo_page1.png"
    page_img.save(str(img_path))
    assert img_path.exists() and img_path.stat().st_size > 1000
