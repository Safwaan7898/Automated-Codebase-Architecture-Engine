"""Tests for ReportGenerator and ReportRenderer."""

from __future__ import annotations


import pytest

from analysis.graph import DirectedGraph
from reports.generator import ReportGenerator, default_report_generator
from reports.models import FullReport, ReportFormat
from reports.pdf import ReportRenderer
from reports.renderer import HeadlessGraphRenderer


@pytest.fixture
def sample_graph() -> DirectedGraph:
    """Create a sample graph with cycles, layers, and metrics."""
    g = DirectedGraph()

    g.add_node(
        "app.controller.UserController",
        name="UserController",
        node_type="class",
        path="src/app/controller.py",
        metrics={"loc": 120, "cyclomatic_complexity": 5, "layer": "Presentation"},
    )
    g.add_node(
        "app.service.UserService",
        name="UserService",
        node_type="class",
        path="src/app/service.py",
        metrics={"loc": 450, "cyclomatic_complexity": 25, "layer": "Service"},
    )
    g.add_node(
        "app.repository.UserRepository",
        name="UserRepository",
        node_type="class",
        path="src/app/repository.py",
        metrics={"loc": 200, "cyclomatic_complexity": 8, "layer": "Data / Infrastructure"},
    )

    # Add cycle between controller and service
    g.add_edge("app.controller.UserController", "app.service.UserService", edge_type="call")
    g.add_edge("app.service.UserService", "app.controller.UserController", edge_type="call")
    g.add_edge("app.service.UserService", "app.repository.UserRepository", edge_type="call")

    return g


class TestReportGenerator:
    """Test full report generation logic across all 7 sections."""

    def test_generator_all_7_sections_present(self, sample_graph: DirectedGraph):
        gen = ReportGenerator()
        report = gen.generate_report(
            graph=sample_graph,
            repo_path=".",
            repo_name="SampleTestApp",
            language="Python",
            query_osv=False,
        )

        assert isinstance(report, FullReport)

        # 1. Executive summary
        exec_s = report.executive_summary
        assert 0.0 <= exec_s.health_score <= 100.0
        assert exec_s.grade in ["A", "B", "C", "D", "F"]
        assert isinstance(exec_s.top_5_risks, list)
        assert len(exec_s.top_5_risks) <= 5
        assert exec_s.trend is not None
        assert exec_s.total_components == 3

        # 2. Architecture overview
        arch = report.architecture_overview
        assert len(arch.layers) >= 1
        assert len(arch.clusters) >= 1
        assert arch.graph_image_base64.startswith("data:image/png;base64,")

        # 3. Dependency analysis
        dep = report.dependency_analysis
        assert len(dep.cycles) >= 1  # Cycle UserController <-> UserService
        assert len(dep.cycles[0].path) >= 2
        assert len(dep.instability_chart) >= 1
        for item in dep.instability_chart:
            assert 0.0 <= item.instability <= 1.0

        # 4. Security findings
        sec = report.security_findings
        assert isinstance(sec.findings_by_severity, dict)
        assert "critical" in sec.findings_by_severity
        assert "high" in sec.findings_by_severity

        # 5. Code quality
        cq = report.code_quality
        assert "Low (1-5)" in cq.complexity_distribution
        assert "Moderate (6-10)" in cq.complexity_distribution
        assert "High (11-20)" in cq.complexity_distribution
        assert "Critical (21+)" in cq.complexity_distribution

        # 6. Prioritized refactoring roadmap
        roadmap = report.refactoring_roadmap
        assert isinstance(roadmap.items, list)
        for item in roadmap.items:
            assert item.effort in ["S", "M", "L"]
            assert len(item.affected_nodes) >= 1

        # 7. Appendix
        app = report.appendix
        assert "methodology" in app
        assert "algorithms" in app
        assert len(app["methodology"]) >= 3
        assert len(app["algorithms"]) >= 4

    def test_headless_graph_renderer(self, sample_graph: DirectedGraph):
        renderer = HeadlessGraphRenderer()
        img_b64 = renderer.render_graph_to_base64(sample_graph, max_nodes_to_draw=50)
        assert img_b64.startswith("data:image/png;base64,")
        assert len(img_b64) > 1000

    def test_pdf_html_json_rendering(self, sample_graph: DirectedGraph):
        report = default_report_generator.generate_report(
            graph=sample_graph,
            repo_path=".",
            repo_name="RenderingTestApp",
            query_osv=False,
        )

        # JSON rendering
        json_data, media_type = ReportRenderer.render(report, ReportFormat.JSON)
        assert media_type == "application/json"
        assert isinstance(json_data, dict)
        assert json_data["executive_summary"]["health_score"] >= 0

        # HTML rendering
        html_str, media_type = ReportRenderer.render(report, ReportFormat.HTML)
        assert media_type == "text/html"
        assert isinstance(html_str, str)
        assert "<!DOCTYPE html>" in html_str
        assert "RenderingTestApp" in html_str
        assert "Executive Summary" in html_str

        # PDF rendering (WeasyPrint or graceful xhtml2pdf fallback)
        pdf_bytes, media_type = ReportRenderer.render(report, ReportFormat.PDF)
        assert media_type == "application/pdf"
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 5000
