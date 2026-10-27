"""ArchLens Automated Reports Package.

One-click downloadable reports in PDF, HTML, and JSON covering:
1. Executive summary (health score 0-100, top 5 risks, trend vs previous scan)
2. Architecture overview (layers, clusters, rendered graph image)
3. Dependency analysis (cycles with paths, bottleneck classes, instability chart)
4. Security findings (grouped by severity, with CWE, file:line, snippet, fix)
5. Code quality (complexity distribution, dead code, smells)
6. Prioritized refactoring roadmap with effort estimates
7. Appendix (methodology and algorithms used)
"""

from reports.generator import ReportGenerator, default_report_generator
from reports.models import FullReport, ReportFormat
from reports.pdf import ReportRenderer
from reports.store import ReportStore, default_report_store

__all__ = [
    "FullReport",
    "ReportFormat",
    "ReportGenerator",
    "ReportRenderer",
    "ReportStore",
    "default_report_generator",
    "default_report_store",
]
