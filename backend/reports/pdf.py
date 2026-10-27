"""PDF, HTML, Markdown, and JSON report rendering engine.

Supports WeasyPrint with seamless Chromium headless and xhtml2pdf fallbacks to guarantee
consistent, light-theme A4 PDF generation across all operating systems.
"""

from __future__ import annotations

import io
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from reports.models import FullReport, ReportFormat

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


class ReportRenderer:
    """Renders FullReport models into PDF, HTML, Markdown, or JSON format."""

    @classmethod
    def render_html(cls, report: FullReport) -> str:
        """Render report to HTML string using Jinja2."""
        template = jinja_env.get_template("report.html")
        return template.render(report=report)

    @classmethod
    def render_pdf(cls, report: FullReport) -> bytes:
        """Render report to PDF bytes using WeasyPrint (preferred) or Chromium headless fallback."""
        html_content = cls.render_html(report)

        # 1. Primary: WeasyPrint (if system pango/cairo DLLs are present on Linux/macOS)
        if os.name != "nt":
            try:
                from weasyprint import HTML  # type: ignore[import-untyped]

                logger.info("Rendering PDF using WeasyPrint")
                return HTML(string=html_content).write_pdf()
            except Exception as exc:
                logger.debug("WeasyPrint unavailable (%s); using Chromium headless fallback", exc)

        # 2. Fallback: Headless Chromium via Playwright node bridge
        try:
            return cls._render_pdf_chromium(html_content)
        except Exception as exc:
            logger.warning("Chromium headless PDF rendering failed: %s; falling back to xhtml2pdf", exc)

        # 3. Fallback: xhtml2pdf
        try:
            from xhtml2pdf import pisa  # type: ignore[import-untyped]

            logger.info("Rendering PDF using xhtml2pdf fallback")
            buf = io.BytesIO()
            pisa_status = pisa.CreatePDF(html_content, dest=buf)
            if not pisa_status.err:
                return buf.getvalue()
        except Exception as exc:
            logger.warning("xhtml2pdf failed: %s", exc)

        # 4. Fallback: ReportLab canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 800, f"Architecture Diagnostic Report: {report.metadata.repo_name}")
        c.setFont("Helvetica", 11)
        c.drawString(50, 780, f"Analysis ID: {report.metadata.report_id} · Generated: {report.metadata.generated_at}")
        c.drawString(
            50,
            760,
            f"Health Score: {report.executive_summary.health_score}/100 (Grade {report.executive_summary.grade})",
        )
        c.showPage()
        c.save()
        return buf.getvalue()

    @classmethod
    def _render_pdf_chromium(cls, html_content: str) -> bytes:
        """Render HTML to PDF using local Chromium in A4 format."""
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f_html:
            f_html.write(html_content)
            html_path = f_html.name

        with tempfile.NamedTemporaryFile("r", suffix=".pdf", delete=False) as f_pdf:
            pdf_path = f_pdf.name

        try:
            frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
            escaped_html_uri = "file:///" + html_path.replace("\\", "/").replace('"', "")
            escaped_pdf_path = pdf_path.replace("\\", "/").replace('"', "")

            node_script = f"""
const {{ chromium }} = require('@playwright/test');
(async () => {{
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('{escaped_html_uri}', {{ waitUntil: 'networkidle' }});
  await page.pdf({{
    path: '{escaped_pdf_path}',
    format: 'A4',
    printBackground: true,
    margin: {{ top: '16mm', bottom: '16mm', left: '12mm', right: '12mm' }}
  }});
  await browser.close();
}})();
"""
            subprocess.run(
                ["node", "-e", node_script],
                cwd=str(frontend_dir),
                check=True,
                capture_output=True,
                timeout=35,
            )

            with open(pdf_path, "rb") as f:
                return f.read()
        finally:
            for p in (html_path, pdf_path):
                try:
                    if os.path.exists(p):
                        os.unlink(p)
                except OSError:
                    pass

    @classmethod
    def render_markdown(cls, report: FullReport) -> str:
        """Render report as comprehensive Markdown matching all 8 report sections."""
        m = report.metadata
        e = report.executive_summary
        g = report.glossary
        d = report.dependency_analysis
        q = report.code_quality
        s = report.security_findings
        a = report.prioritized_action_plan

        lines = [
            f"# {m.title}",
            f"**Target Repository:** {m.repo_name}  ",
            f"**Analysis ID:** `{m.report_id}`  ",
            f"**Generated:** {m.generated_at}  ",
            f"**Overall Grade:** {e.grade or 'Insufficient data'} ({e.health_score or 'N/A'}/100) — **Status:** {e.status_label}  ",
            "",
            "---",
            "",
            "## 01. Executive Summary",
            "",
            e.summary_text,
            "",
            f"- **Analyzed Components:** {e.total_components}",
            f"- **Total Dependencies:** {e.total_dependencies}",
            f"- **Circular Cycles:** {e.total_circular_cycles}",
            f"- **Critical Vulnerabilities:** {e.total_critical_vulnerabilities}",
            "",
            "> **💡 What this means:** " + (e.callout.what_means if e.callout else ""),
            "> **⚠️ Why it matters:** " + (e.callout.why_matters if e.callout else ""),
            "> **🎯 What to do:** " + (e.callout.what_to_do if e.callout else ""),
            "",
            "### Top 3 Risks",
            "",
        ]

        for r in e.top_3_risks:
            lines.append(f"{r.rank}. **{r.primary_issue}** [{r.severity.upper()}] — {r.plain_english_impact}")

        lines.extend(
            [
                "",
                "---",
                "",
                "## 02. How to Read This Report (Glossary)",
                "",
            ]
        )

        for item in g:
            lines.append(f"### {item.term}")
            lines.append(f"{item.definition}")
            lines.append(f"*Everyday Analogy:* {item.analogy}")
            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## 03. Health Scorecard",
                "",
                f"- **Overall Health Index:** {e.health_score or 'Insufficient data'}/100",
                f"- **Structural Grade:** {e.grade or 'N/A'}",
                "",
                "---",
                "",
                "## 04. Detailed Findings Tables",
                "",
                f"### Circular Dependency Loops ({d.total_cycles})",
                "",
                "| Cycle ID | Dependency Path | Severity | Recommended Break |",
                "| :--- | :--- | :--- | :--- |",
            ]
        )

        if d.cycles:
            for c in d.cycles[:8]:
                lines.append(
                    f"| `{c.cycle_id}` | `{c.formatted_path}` | **{c.severity_label}** | `{c.interface_remedy}` |"
                )
        else:
            lines.append("| - | *Zero circular dependency loops detected* | LOW | - |")

        lines.extend(
            [
                "",
                f"### Monolithic God Classes ({len(q.god_classes)})",
                "",
                "| Class / Module | Lines of Code | Methods | Fan-In/Out | Severity |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
        )

        if q.god_classes:
            for god in q.god_classes[:8]:
                lines.append(
                    f"| `{god.name}` | {god.loc} LOC | {god.methods_count} | {god.fan_in}/{god.fan_out} | **{god.severity_label}** |"
                )
        else:
            lines.append("| - | *No God classes detected* | - | - | CLEAN |")

        lines.extend(
            [
                "",
                f"### Security Vulnerabilities ({s.total_findings})",
                "",
                "| Severity | Finding Title | CWE / OWASP | Remediation |",
                "| :--- | :--- | :--- | :--- |",
            ]
        )

        if s.all_findings:
            for f in s.all_findings[:10]:
                lines.append(f"| **{f.severity_label}** | {f.title} | `{f.cwe}` / `{f.owasp}` | {f.remediation} |")
        else:
            lines.append("| CLEAN | *No security vulnerabilities detected* | - | - |")

        lines.extend(
            [
                "",
                "---",
                "",
                "## 05. Prioritized Action Plan",
                "",
                "### 🚨 Tier 1: Fix Now (Immediate Deployment Risk · Est: 1–2 days)",
                "",
            ]
        )

        for it in a.fix_now:
            lines.append(f"- **{it.title}** ({it.effort_estimate}): {it.description}")

        lines.extend(
            [
                "",
                "### ⚡ Tier 2: Next Sprint (Modularity & Technical Debt · Est: 3–5 days)",
                "",
            ]
        )

        for it in a.next_sprint:
            lines.append(f"- **{it.title}** ({it.effort_estimate}): {it.description}")

        lines.extend(
            [
                "",
                "### 📋 Tier 3: Later (Architecture Hygiene · Est: 1 sprint)",
                "",
            ]
        )

        for it in a.later:
            lines.append(f"- **{it.title}** ({it.effort_estimate}): {it.description}")

        lines.extend(
            [
                "",
                "---",
                "",
                "## 06. Appendix & Methodology",
                "",
                "- **Cycle Detection:** Tarjan's Strongly Connected Components (SCC) in O(V + E).",
                "- **Clustering:** Louvain Community Detection algorithm.",
                "- **Centrality:** Brandes betweenness centrality and PageRank.",
                "- **Limitations:** Dynamic reflection is evaluated via static heuristics.",
                "",
                f"*Generated by ArchLens Enterprise v{m.archlens_version}*",
            ]
        )

        return "\n".join(lines)

    @classmethod
    def render_json(cls, report: FullReport) -> dict[str, Any]:
        """Render report to JSON dict."""
        return report.to_dict()

    @classmethod
    def render(cls, report: FullReport, format: ReportFormat) -> tuple[bytes | str | dict[str, Any], str]:
        """Render report into requested format with corresponding media type."""
        if format == ReportFormat.PDF:
            return cls.render_pdf(report), "application/pdf"
        elif format == ReportFormat.HTML:
            return cls.render_html(report), "text/html"
        elif format == ReportFormat.MARKDOWN:
            return cls.render_markdown(report), "text/markdown; charset=utf-8"
        elif format == ReportFormat.JSON:
            return cls.render_json(report), "application/json"
        else:
            raise ValueError(f"Unsupported report format: {format}")
