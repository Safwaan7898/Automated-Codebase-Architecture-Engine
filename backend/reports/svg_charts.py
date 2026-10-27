"""Server-side inline SVG chart generators for WeasyPrint & PDF reports.

Renders pixel-perfect, light-theme vector graphics without requiring client-side JS:
1. Health Scorecard Semicircular Speedometer Gauge
2. Sub-scores Horizontal Bars (Structure, Coupling, Security, Maintainability)
3. Layer Distribution Bar Chart
4. Architectural Smell Severity Donut Chart with Legend
5. Robert C. Martin Instability vs Abstractness Scatter Plot with Main Sequence Line
6. Top 10 Complexity Hotspots Bar Chart
7. Dependency Graph Topological Snapshot
8. Refactoring Simulation Before/After Comparison Chart
"""

from __future__ import annotations

import math
from typing import Any


def escape_xml(text: Any) -> str:
    """Escape special XML characters for safe SVG embedding."""
    if text is None:
        return ""
    s = str(text)
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")
    )


def generate_gauge_svg(score: float | None, grade: str | None, width: int = 280, height: int = 160) -> str:
    """Generate a semicircular speedometer gauge SVG.

    Shows 'Not enough data' when score is None or grade indicates insufficient data.
    """
    if score is None or grade in ("Not enough data", "insufficient_data", None):
        return f"""<svg width="{width}" height="{height}" viewBox="0 0 280 160" xmlns="http://www.w3.org/2000/svg">
  <rect width="280" height="160" rx="8" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1.5" />
  <path d="M 40 120 A 100 100 0 0 1 240 120" fill="none" stroke="#e2e8f0" stroke-width="18" stroke-linecap="round" />
  <text x="140" y="95" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="13" font-weight="700" fill="#64748b" text-anchor="middle">NOT ENOUGH DATA</text>
  <text x="140" y="115" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="10" fill="#94a3b8" text-anchor="middle">Analyze repository to compute health</text>
</svg>"""

    clamped_score = max(0.0, min(100.0, float(score)))
    # Angle from 180 (left) to 0 (right)
    # 0 score -> 180 deg, 100 score -> 0 deg
    angle_rad = math.pi * (1.0 - (clamped_score / 100.0))
    cx, cy = 140, 125

    # Needle tip coordinates
    needle_len = 72
    nx = cx + needle_len * math.cos(angle_rad)
    ny = cy - needle_len * math.sin(angle_rad)

    # Color selection based on score
    if clamped_score >= 80:
        score_color = "#16a34a"  # Green
        status_label = "EXCELLENT"
    elif clamped_score >= 60:
        score_color = "#2563eb"  # Blue
        status_label = "HEALTHY"
    elif clamped_score >= 40:
        score_color = "#d97706"  # Amber
        status_label = "CAUTION"
    else:
        score_color = "#dc2626"  # Red
        status_label = "CRITICAL"

    grade_display = grade or (
        "A" if clamped_score >= 85 else "B" if clamped_score >= 70 else "C" if clamped_score >= 50 else "D"
    )

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 280 160" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#ef4444" />
      <stop offset="45%" stop-color="#f59e0b" />
      <stop offset="75%" stop-color="#3b82f6" />
      <stop offset="100%" stop-color="#10b981" />
    </linearGradient>
  </defs>
  <!-- Background Arc -->
  <path d="M 40 125 A 100 100 0 0 1 240 125" fill="none" stroke="#e2e8f0" stroke-width="16" stroke-linecap="round" />
  <!-- Colored Gradient Arc -->
  <path d="M 40 125 A 100 100 0 0 1 240 125" fill="none" stroke="url(#gaugeGrad)" stroke-width="16" stroke-linecap="round" opacity="0.9" />
  <!-- Needle -->
  <line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#0f172a" stroke-width="3.5" stroke-linecap="round" />
  <circle cx="{cx}" cy="{cy}" r="7" fill="#0f172a" />
  <circle cx="{cx}" cy="{cy}" r="3" fill="#ffffff" />
  <!-- Score and Grade text -->
  <text x="{cx}" y="95" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="28" font-weight="900" fill="{score_color}" text-anchor="middle">{round(clamped_score)}<tspan font-size="14" font-weight="500" fill="#64748b">/100</tspan></text>
  <text x="{cx}" y="112" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="11" font-weight="700" fill="#0f172a" text-anchor="middle">GRADE {escape_xml(grade_display)} · {status_label}</text>
  <text x="40" y="145" font-family="monospace" font-size="9" fill="#94a3b8" text-anchor="middle">0</text>
  <text x="140" y="145" font-family="monospace" font-size="9" fill="#94a3b8" text-anchor="middle">50</text>
  <text x="240" y="145" font-family="monospace" font-size="9" fill="#94a3b8" text-anchor="middle">100</text>
</svg>"""


def generate_subscores_bars_svg(
    sub_scores: dict[str, float] | None = None,
    structure: float = 78.0,
    coupling: float = 72.0,
    security: float = 85.0,
    maintainability: float = 68.0,
    width: int = 340,
    height: int = 160,
) -> str:
    """Generate horizontal bar chart for architectural sub-scores."""
    if sub_scores:
        categories = []
        color_map = {
            "cycles": "#3b82f6",
            "coupling": "#10b981",
            "complexity": "#8b5cf6",
            "smells": "#f59e0b",
            "security": "#ec4899",
        }
        for k, v in sub_scores.items():
            color = color_map.get(k.lower(), "#3b82f6")
            name = k.replace("_", " ").title()
            categories.append((name, float(v), color))
    else:
        categories = [
            ("Structural Quality", structure, "#3b82f6"),
            ("Coupling & Modularity", coupling, "#10b981"),
            ("Security Hardening", security, "#8b5cf6"),
            ("Maintainability Index", maintainability, "#f59e0b"),
        ]

    bars_svg = []
    y_start = 18
    row_height = 27 if len(categories) > 4 else 34
    bar_max_width = 160

    for idx, (label, val, color) in enumerate(categories):
        clamped = max(0.0, min(100.0, float(val)))
        bar_w = (clamped / 100.0) * bar_max_width
        y = y_start + (idx * row_height)

        bars_svg.append(f"""
    <!-- {label} -->
    <text x="12" y="{y + 11}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="9" font-weight="600" fill="#334155">{escape_xml(label)}</text>
    <rect x="145" y="{y}" width="{bar_max_width}" height="13" rx="3" fill="#f1f5f9" />
    <rect x="145" y="{y}" width="{bar_w:.1f}" height="13" rx="3" fill="{color}" />
    <text x="{145 + bar_max_width + 8}" y="{y + 11}" font-family="monospace" font-size="9.5" font-weight="700" fill="#0f172a">{round(clamped)}%</text>
""")

    calc_height = max(height, y_start + len(categories) * row_height + 15)
    return f"""<svg width="{width}" height="{calc_height}" viewBox="0 0 {width} {calc_height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{calc_height}" rx="8" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1.5" />
  {"".join(bars_svg)}
</svg>"""


def generate_layer_distribution_svg(layers: list[dict[str, Any]], width: int = 520, height: int = 170) -> str:
    """Generate horizontal bar chart of codebase components per architectural layer."""
    if not layers:
        layers = [
            {"name": "Presentation", "count": 12, "percentage": 25.0},
            {"name": "Business / Domain", "count": 22, "percentage": 45.0},
            {"name": "Data Access", "count": 10, "percentage": 20.0},
            {"name": "Infrastructure", "count": 5, "percentage": 10.0},
        ]

    max_count = max((item.get("count", 0) for item in layers), default=1) or 1
    palette = ["#0284c7", "#10b981", "#8b5cf6", "#f59e0b", "#ec4899", "#64748b"]

    y_offset = 24
    row_height = 28
    bar_start_x = 140
    max_bar_width = 300

    items_svg = []
    for idx, layer in enumerate(layers[:5]):
        name = layer.get("name", f"Layer {idx + 1}")
        count = layer.get("count", 0)
        pct = layer.get("percentage", 0.0)
        color = palette[idx % len(palette)]
        w = (count / max_count) * max_bar_width if max_count else 0
        y = y_offset + (idx * row_height)

        items_svg.append(f"""
    <text x="14" y="{y + 12}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="10" font-weight="600" fill="#1e293b">{escape_xml(name)}</text>
    <rect x="{bar_start_x}" y="{y}" width="{max_bar_width}" height="16" rx="4" fill="#f1f5f9" />
    <rect x="{bar_start_x}" y="{y}" width="{max(6, w):.1f}" height="16" rx="4" fill="{color}" />
    <text x="{bar_start_x + w + 8}" y="{y + 12}" font-family="monospace" font-size="9.5" font-weight="700" fill="#334155">{count} ({pct:.1f}%)</text>
""")

    computed_height = max(height, y_offset + len(layers[:5]) * row_height + 15)

    return f"""<svg width="100%" height="{computed_height}" viewBox="0 0 {width} {computed_height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{computed_height}" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.2" />
  <text x="14" y="16" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="10" font-weight="700" fill="#64748b" letter-spacing="0.5">ARCHITECTURAL LAYER SPREAD</text>
  {"".join(items_svg)}
</svg>"""


def generate_smell_donut_svg(breakdown: dict[str, int], width: int = 240, height: int = 170) -> str:
    """Generate SVG donut chart showing architectural smell severity distribution."""
    critical = breakdown.get("CRITICAL", breakdown.get("critical", 0))
    high = breakdown.get("HIGH", breakdown.get("high", 0))
    medium = breakdown.get("MEDIUM", breakdown.get("medium", 0))
    low = breakdown.get("LOW", breakdown.get("low", 0))
    total = critical + high + medium + low

    if total == 0:
        return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.2" />
  <circle cx="80" cy="85" r="50" fill="none" stroke="#e2e8f0" stroke-width="18" />
  <text x="80" y="85" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="11" font-weight="700" fill="#10b981" text-anchor="middle">CLEAN</text>
  <text x="80" y="98" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="9" fill="#64748b" text-anchor="middle">0 smells</text>
  <text x="150" y="70" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="10" fill="#16a34a" font-weight="600">✓ No architectural</text>
  <text x="150" y="85" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="10" fill="#16a34a" font-weight="600">smells detected</text>
</svg>"""

    cx, cy = 80, 85
    r = 50
    circumference = 2 * math.pi * r

    slices = [
        ("CRITICAL", critical, "#dc2626"),
        ("HIGH", high, "#ea580c"),
        ("MEDIUM", medium, "#d97706"),
        ("LOW", low, "#3b82f6"),
    ]

    paths = []
    current_offset = 0.0

    for _name, count, color in slices:
        if count <= 0:
            continue
        slice_len = (count / total) * circumference
        gap_len = circumference - slice_len
        paths.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="18" '
            f'stroke-dasharray="{slice_len:.2f} {gap_len:.2f}" stroke-dashoffset="{-current_offset:.2f}" />'
        )
        current_offset += slice_len

    legend_svg = []
    ly = 45
    for name, count, color in slices:
        legend_svg.append(f"""
    <rect x="155" y="{ly - 8}" width="9" height="9" rx="2" fill="{color}" />
    <text x="170" y="{ly}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="9.5" font-weight="600" fill="#334155">{name}: <tspan font-weight="700" fill="#0f172a">{count}</tspan></text>
""")
        ly += 22

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.2" />
  <!-- Donut slices -->
  <g transform="rotate(-90 {cx} {cy})">
    {"".join(paths)}
  </g>
  <!-- Center count -->
  <text x="{cx}" y="{cy - 2}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="17" font-weight="800" fill="#0f172a" text-anchor="middle">{total}</text>
  <text x="{cx}" y="{cy + 12}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="8.5" font-weight="600" fill="#64748b" text-anchor="middle" letter-spacing="0.5">SMELLS</text>
  <!-- Legend -->
  {"".join(legend_svg)}
</svg>"""


def generate_instability_abstractness_matplotlib(metrics: list[dict[str, Any]]) -> str:
    """Generate high-resolution Instability (I) vs Abstractness (A) scatter plot via matplotlib."""
    if not metrics:
        return ""
    try:
        import io
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams["svg.hashsalt"] = "archlens"
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6.2, 3.2), dpi=200)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")

        # Zones
        ax.fill([0, 0.4, 0], [0, 0, 0.4], color="#fee2e2", alpha=0.55, label="Zone of Pain (Rigid)")
        ax.fill([1, 0.6, 1], [1, 1, 0.6], color="#fef3c7", alpha=0.55, label="Zone of Uselessness")

        # Main sequence line: A + I = 1
        ax.plot([0, 1], [1, 0], color="#10b981", linestyle="--", linewidth=1.5, label="Main Sequence (A + I = 1)")

        i_vals = [max(0.0, min(1.0, float(m.get("instability", 0.5)))) for m in metrics[:20]]
        a_vals = [max(0.0, min(1.0, float(m.get("abstractness", 0.5)))) for m in metrics[:20]]
        names = [str(m.get("package_name", "")).split(".")[-1] or "pkg" for m in metrics[:20]]

        colors = ["#dc2626" if abs(a + i - 1.0) > 0.4 else "#2563eb" for i, a in zip(i_vals, a_vals)]
        ax.scatter(i_vals, a_vals, c=colors, s=36, edgecolors="#ffffff", linewidth=1.0, zorder=5)

        for i, a, name in zip(i_vals, a_vals, names):
            ax.annotate(name, (i, a), xytext=(4, 4), textcoords="offset points", fontsize=7.5, color="#334155")

        ax.set_xlim(-0.03, 1.03)
        ax.set_ylim(-0.03, 1.03)
        ax.set_xlabel("Instability (I = Ce / (Ca + Ce))", fontsize=8, color="#475569")
        ax.set_ylabel("Abstractness (A)", fontsize=8, color="#475569")
        ax.set_title("Package Metrics: Instability vs. Abstractness", fontsize=9, fontweight="bold", color="#1e293b", pad=8)
        ax.tick_params(colors="#64748b", labelsize=7.5)
        ax.grid(True, linestyle=":", alpha=0.4, color="#cbd5e1")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=7, frameon=False)

        plt.tight_layout()
        buf = io.StringIO()
        fig.savefig(buf, format="svg", bbox_inches="tight", metadata={"Date": None})
        plt.close(fig)
        return buf.getvalue()
    except Exception:
        return generate_instability_abstractness_svg(metrics)


def generate_instability_abstractness_svg(metrics: list[dict[str, Any]], width: int = 520, height: int = 240) -> str:
    """Generate Robert C. Martin's Package Metric Plot: Instability (I) vs Abstractness (A).

    Draws the Main Sequence line (A + I = 1), Zone of Pain (bottom-left), and Zone of Uselessness (top-right).
    """
    # Graph area dimensions
    gx, gy = 55, 30
    gw, gh = 420, 160

    # Main sequence line: (0, 1) -> (1, 0)
    # in SVG coordinates: (gx, gy) to (gx + gw, gy + gh)
    points_svg = []
    sample_metrics = (
        metrics
        if metrics
        else [
            {"package_name": "app.core", "instability": 0.2, "abstractness": 0.75},
            {"package_name": "app.api", "instability": 0.85, "abstractness": 0.1},
            {"package_name": "app.services", "instability": 0.55, "abstractness": 0.45},
            {"package_name": "app.models", "instability": 0.1, "abstractness": 0.8},
            {"package_name": "app.utils", "instability": 0.9, "abstractness": 0.05},
        ]
    )

    for item in sample_metrics[:15]:
        pkg = item.get("package_name", "pkg")
        short_name = pkg.split(".")[-1]
        i_val = max(0.0, min(1.0, float(item.get("instability", 0.5))))
        a_val = max(0.0, min(1.0, float(item.get("abstractness", 0.5))))

        px = gx + i_val * gw
        py = gy + (1.0 - a_val) * gh

        # Distance from main sequence: D = |A + I - 1|
        d_val = abs(a_val + i_val - 1.0)
        pt_color = "#dc2626" if d_val > 0.4 else "#2563eb"

        points_svg.append(f"""
    <circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{pt_color}" stroke="#ffffff" stroke-width="1.5" />
    <text x="{px + 6:.1f}" y="{py + 3:.1f}" font-family="monospace" font-size="8" fill="#334155" font-weight="600">{escape_xml(short_name)}</text>
""")

    return f"""<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.2" />
  <text x="14" y="18" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="10" font-weight="700" fill="#64748b" letter-spacing="0.5">MARTIN INSTABILITY (I) VS ABSTRACTNESS (A) & MAIN SEQUENCE</text>

  <!-- Zones -->
  <!-- Zone of Pain (Low I, Low A) -->
  <polygon points="{gx},{gy + gh} {gx + gw * 0.4},{gy + gh} {gx},{gy + gh * 0.6}" fill="#fee2e2" opacity="0.6" />
  <text x="{gx + 8}" y="{gy + gh - 8}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="8" font-weight="700" fill="#b91c1c">ZONE OF PAIN (Rigid)</text>

  <!-- Zone of Uselessness (High I, High A) -->
  <polygon points="{gx + gw},{gy} {gx + gw * 0.6},{gy} {gx + gw},{gy + gh * 0.4}" fill="#fef3c7" opacity="0.6" />
  <text x="{gx + gw - 8}" y="{gy + 14}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="8" font-weight="700" fill="#b45309" text-anchor="end">ZONE OF USELESSNESS</text>

  <!-- Axes -->
  <line x1="{gx}" y1="{gy + gh}" x2="{gx + gw}" y2="{gy + gh}" stroke="#94a3b8" stroke-width="1.5" />
  <line x1="{gx}" y1="{gy}" x2="{gx}" y2="{gy + gh}" stroke="#94a3b8" stroke-width="1.5" />

  <!-- Grid lines -->
  <line x1="{gx + gw / 2}" y1="{gy}" x2="{gx + gw / 2}" y2="{gy + gh}" stroke="#f1f5f9" stroke-width="1" stroke-dasharray="3 3" />
  <line x1="{gx}" y1="{gy + gh / 2}" x2="{gx + gw}" y2="{gy + gh / 2}" stroke="#f1f5f9" stroke-width="1" stroke-dasharray="3 3" />

  <!-- Main Sequence Line (A + I = 1) -->
  <line x1="{gx}" y1="{gy}" x2="{gx + gw}" y2="{gy + gh}" stroke="#10b981" stroke-width="2" stroke-dasharray="4 4" />
  <text x="{gx + gw * 0.52}" y="{gy + gh * 0.46}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="8.5" font-weight="700" fill="#059669">Main Sequence Line (A + I = 1)</text>

  <!-- Plotted points -->
  {"".join(points_svg)}

  <!-- Axis Labels -->
  <text x="{gx + gw / 2}" y="{gy + gh + 22}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="9" font-weight="600" fill="#475569" text-anchor="middle">Instability (I = Ce / (Ca + Ce)) → [0: Stable / Rigid → 1: Volatile / Flexible]</text>
  <text x="14" y="{gy + gh / 2}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="9" font-weight="600" fill="#475569" transform="rotate(-90 14 {gy + gh / 2})" text-anchor="middle">Abstractness (A) ↑</text>
  <text x="{gx}" y="{gy + gh + 14}" font-family="monospace" font-size="8" fill="#94a3b8">0.0</text>
  <text x="{gx + gw}" y="{gy + gh + 14}" font-family="monospace" font-size="8" fill="#94a3b8" text-anchor="end">1.0</text>
  <text x="{gx - 6}" y="{gy + 8}" font-family="monospace" font-size="8" fill="#94a3b8" text-anchor="end">1.0</text>
</svg>"""


def generate_top_hotspots_bar_svg(hotspots: list[dict[str, Any]], width: int = 520, height: int = 240) -> str:
    """Generate horizontal bar chart ranking top 10 architectural hotspots / bottlenecks."""
    if not hotspots:
        hotspots = [
            {"name": "app.core.orchestrator", "risk_score": 88.5, "impact_level": "Critical"},
            {"name": "app.api.dependencies", "risk_score": 79.2, "impact_level": "High"},
            {"name": "app.models.entity", "risk_score": 71.0, "impact_level": "High"},
            {"name": "app.services.auth", "risk_score": 64.8, "impact_level": "Moderate"},
            {"name": "app.database.session", "risk_score": 58.0, "impact_level": "Moderate"},
        ]

    items = hotspots[:8]
    max_score = 100.0
    bar_start_x = 190
    max_w = 260
    row_height = 24
    y_start = 28

    bars_svg = []
    for idx, h in enumerate(items):
        name = h.get("name") or h.get("node_id", f"node_{idx}")
        score = float(h.get("risk_score", 50.0))
        level = h.get("impact_level", "Moderate")

        if score >= 75:
            color = "#dc2626"
        elif score >= 60:
            color = "#ea580c"
        else:
            color = "#f59e0b"

        w = (score / max_score) * max_w
        y = y_start + (idx * row_height)

        # Truncate name if too long
        display_name = name if len(name) <= 24 else name[:11] + "…" + name[-12:]

        bars_svg.append(f"""
    <text x="14" y="{y + 11}" font-family="monospace" font-size="9" font-weight="600" fill="#1e293b">{escape_xml(display_name)}</text>
    <rect x="{bar_start_x}" y="{y}" width="{max_w}" height="14" rx="3" fill="#f1f5f9" />
    <rect x="{bar_start_x}" y="{y}" width="{max(6, w):.1f}" height="14" rx="3" fill="{color}" />
    <text x="{bar_start_x + w + 8}" y="{y + 11}" font-family="monospace" font-size="9" font-weight="700" fill="#0f172a">{score:.1f} <tspan font-family="sans-serif" font-size="7.5" fill="#64748b">[{level}]</tspan></text>
""")

    computed_height = max(height, y_start + len(items) * row_height + 15)

    return f"""<svg width="100%" height="{computed_height}" viewBox="0 0 {width} {computed_height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{computed_height}" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.2" />
  <text x="14" y="18" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="10" font-weight="700" fill="#64748b" letter-spacing="0.5">TOP ARCHITECTURAL HOTSPOTS (COMPLEXITY & BLAST RADIUS)</text>
  {"".join(bars_svg)}
</svg>"""


def generate_graph_snapshot_svg(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]], width: int = 520, height: int = 220
) -> str:
    """Generate a clean topological snapshot of the dependency graph with directed edges and cluster coloring."""
    if not nodes:
        return f"""<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="8" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1.2" />
  <text x="{width / 2}" y="{height / 2}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="12" fill="#64748b" text-anchor="middle">No graph components to display</text>
</svg>"""

    # Layout nodes in clusters / layers
    sample_nodes = nodes[:12]
    node_coords: dict[str, tuple[float, float]] = {}

    for idx, n in enumerate(sample_nodes):
        nid = n.get("id") or str(idx)
        # Arrange in a dual-wave layout across the width
        col = idx % 4
        row = idx // 4
        x = 60 + col * 125 + (15 if row % 2 == 1 else 0)
        y = 50 + row * 60
        node_coords[nid] = (x, y)

    edges_svg = []
    for e in edges[:18]:
        s = e.get("source")
        t = e.get("target")
        is_cycle = e.get("is_cycle", False)
        if s in node_coords and t in node_coords and s != t:
            x1, y1 = node_coords[s]
            x2, y2 = node_coords[t]
            stroke_col = "#dc2626" if is_cycle else "#94a3b8"
            dash = 'stroke-dasharray="3 3"' if is_cycle else ""
            edges_svg.append(f"""
    <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke_col}" stroke-width="1.3" opacity="0.6" {dash} marker-end="url(#arrow)" />
""")

    nodes_svg = []
    for idx, n in enumerate(sample_nodes):
        nid = n.get("id") or str(idx)
        x, y = node_coords[nid]
        name = n.get("name") or nid.split(".")[-1]
        display_name = name if len(name) <= 12 else name[:10] + "…"
        is_vuln = n.get("is_vulnerable", False)
        box_color = "#fef2f2" if is_vuln else "#f0fdf4"
        stroke_color = "#ef4444" if is_vuln else "#0284c7"

        nodes_svg.append(f"""
    <g transform="translate({x - 42}, {y - 14})">
      <rect width="84" height="28" rx="6" fill="{box_color}" stroke="{stroke_color}" stroke-width="1.5" />
      <text x="42" y="17" font-family="monospace" font-size="8.5" font-weight="700" fill="#0f172a" text-anchor="middle">{escape_xml(display_name)}</text>
    </g>
""")

    return f"""<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="16" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#64748b" />
    </marker>
  </defs>
  <rect width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.2" />
  <text x="14" y="18" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="10" font-weight="700" fill="#64748b" letter-spacing="0.5">DEPENDENCY TOPOLOGY SNAPSHOT</text>

  <!-- Directed edges -->
  {"".join(edges_svg)}

  <!-- Nodes -->
  {"".join(nodes_svg)}
</svg>"""


def generate_simulation_comparison_svg(
    before: dict[str, Any], after: dict[str, Any], width: int = 520, height: int = 150
) -> str:
    """Generate side-by-side metric comparison bars showing simulated refactoring impact."""
    metrics = [
        ("Circular Cycles", before.get("cycles", 4), after.get("cycles", 0), "lower"),
        ("Max Coupling", before.get("coupling", 18), after.get("coupling", 6), "lower"),
        ("God Classes", before.get("god_classes", 3), after.get("god_classes", 0), "lower"),
        ("Overall Health", before.get("health", 62), after.get("health", 88), "higher"),
    ]

    cols_svg = []
    card_w = 115
    start_x = 18

    for idx, (title, b_val, a_val, direction) in enumerate(metrics):
        cx = start_x + idx * (card_w + 12)
        is_improved = (a_val < b_val) if direction == "lower" else (a_val > b_val)
        status_color = "#16a34a" if is_improved else "#dc2626"
        delta_sign = "-" if a_val < b_val else "+"
        delta_val = abs(a_val - b_val)

        cols_svg.append(f"""
    <g transform="translate({cx}, 36)">
      <rect width="{card_w}" height="95" rx="6" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1" />
      <text x="{card_w / 2}" y="18" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="9" font-weight="700" fill="#475569" text-anchor="middle">{escape_xml(title)}</text>
      <text x="{card_w / 2}" y="42" font-family="monospace" font-size="15" font-weight="800" fill="#64748b" text-anchor="middle">{b_val} → <tspan fill="{status_color}">{a_val}</tspan></text>
      <rect x="18" y="54" width="{card_w - 36}" height="20" rx="4" fill="{status_color}" opacity="0.12" />
      <text x="{card_w / 2}" y="68" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="8.5" font-weight="700" fill="{status_color}" text-anchor="middle">{delta_sign}{delta_val} ({"Optimized" if is_improved else "Neutral"})</text>
    </g>
""")

    return f"""<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.2" />
  <text x="14" y="18" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="10" font-weight="700" fill="#64748b" letter-spacing="0.5">REFACTORING SIMULATION: BEFORE VS AFTER PROJECTION</text>
  {"".join(cols_svg)}
</svg>"""


def generate_dsm_svg(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    width: int = 520,
    height: int = 300,
) -> str:
    """Generate Dependency Structure Matrix (DSM) SVG with cycles highlighted in red."""
    if not nodes:
        return f"""<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="8" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1.2" />
  <text x="{width / 2}" y="{height / 2}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="12" fill="#64748b" text-anchor="middle">No modules available for Dependency Structure Matrix</text>
</svg>"""

    sample_nodes = nodes[:10]
    n = len(sample_nodes)
    node_ids = [item.get("id") or str(idx) for idx, item in enumerate(sample_nodes)]
    id_to_idx = {nid: idx for idx, nid in enumerate(node_ids)}

    # Build adjacency matrix and cycle detection
    matrix = [[0] * n for _ in range(n)]
    cycle_matrix = [[False] * n for _ in range(n)]

    for e in edges:
        s = e.get("source")
        t = e.get("target")
        is_cycle = e.get("is_cycle", False)
        if s in id_to_idx and t in id_to_idx:
            si, ti = id_to_idx[s], id_to_idx[t]
            matrix[si][ti] += 1
            if is_cycle:
                cycle_matrix[si][ti] = True

    # Identify mutual feedback cycles
    for i in range(n):
        for j in range(i + 1, n):
            if matrix[i][j] > 0 and matrix[j][i] > 0:
                cycle_matrix[i][j] = True
                cycle_matrix[j][i] = True

    # Coordinates
    margin_x = 130
    margin_y = 50
    cell_size = min(22, int((width - margin_x - 30) / max(1, n)))
    grid_w = n * cell_size

    cells_svg = []
    # Header numbers
    for j in range(n):
        col_x = margin_x + j * cell_size + cell_size / 2
        cells_svg.append(
            f'<text x="{col_x}" y="{margin_y - 8}" font-family="monospace" font-size="9" font-weight="700" fill="#64748b" text-anchor="middle">{j + 1}</text>'
        )

    for i in range(n):
        row_y = margin_y + i * cell_size
        name = sample_nodes[i].get("name") or sample_nodes[i].get("label") or node_ids[i].split(".")[-1]
        disp_name = name if len(name) <= 16 else name[:14] + "…"
        cells_svg.append(
            f'<text x="{margin_x - 10}" y="{row_y + cell_size / 2 + 3}" font-family="monospace" font-size="8.5" font-weight="600" fill="#1e293b" text-anchor="end">{i + 1}. {escape_xml(disp_name)}</text>'
        )

        for j in range(n):
            cell_x = margin_x + j * cell_size
            if i == j:
                # Diagonal self
                cells_svg.append(
                    f'<rect x="{cell_x}" y="{row_y}" width="{cell_size}" height="{cell_size}" fill="#f1f5f9" stroke="#cbd5e1" stroke-width="0.8" />'
                    f'<line x1="{cell_x}" y1="{row_y}" x2="{cell_x + cell_size}" y2="{row_y + cell_size}" stroke="#94a3b8" stroke-width="1" />'
                )
            elif cycle_matrix[i][j]:
                # Cycle edge
                cells_svg.append(
                    f'<rect x="{cell_x}" y="{row_y}" width="{cell_size}" height="{cell_size}" fill="#fee2e2" stroke="#ef4444" stroke-width="1.2" />'
                    f'<text x="{cell_x + cell_size / 2}" y="{row_y + cell_size / 2 + 3.5}" font-family="monospace" font-size="9" font-weight="800" fill="#b91c1c" text-anchor="middle">{matrix[i][j] or 1}</text>'
                )
            elif matrix[i][j] > 0:
                # Normal dependency
                cells_svg.append(
                    f'<rect x="{cell_x}" y="{row_y}" width="{cell_size}" height="{cell_size}" fill="#eff6ff" stroke="#93c5fd" stroke-width="0.8" />'
                    f'<text x="{cell_x + cell_size / 2}" y="{row_y + cell_size / 2 + 3.5}" font-family="monospace" font-size="8.5" font-weight="700" fill="#1d4ed8" text-anchor="middle">{matrix[i][j]}</text>'
                )
            else:
                cells_svg.append(
                    f'<rect x="{cell_x}" y="{row_y}" width="{cell_size}" height="{cell_size}" fill="#ffffff" stroke="#e2e8f0" stroke-width="0.6" />'
                )

    computed_h = max(height, margin_y + n * cell_size + 30)

    return f"""<svg width="100%" height="{computed_h}" viewBox="0 0 {width} {computed_h}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{computed_h}" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.2" />
  <text x="14" y="20" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="10" font-weight="700" fill="#64748b" letter-spacing="0.5">DEPENDENCY STRUCTURE MATRIX (DSM) · ROW DEPENDS ON COLUMN</text>
  {"".join(cells_svg)}
</svg>"""


def generate_treemap_svg(
    nodes: list[dict[str, Any]],
    width: int = 520,
    height: int = 240,
) -> str:
    """Generate Treemap SVG sized by LOC and colored by cyclomatic complexity."""
    if not nodes:
        return f"""<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="8" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1.2" />
  <text x="{width / 2}" y="{height / 2}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="12" fill="#64748b" text-anchor="middle">No nodes available for Treemap</text>
</svg>"""

    sample = sorted(nodes[:12], key=lambda x: int(x.get("loc", 100)), reverse=True)
    total_loc = sum(max(20, int(item.get("loc", 100))) for item in sample) or 1000

    gw = width - 28
    gh = height - 45
    start_x = 14
    start_y = 32

    # Squarified slice approximation
    rects_svg = []
    curr_x = start_x
    curr_w = gw

    # Layout into 2 rows of items
    row1 = sample[: len(sample) // 2 + 1]
    row2 = sample[len(sample) // 2 + 1 :]

    for r_idx, row_items in enumerate([row1, row2]):
        if not row_items:
            continue
        r_y = start_y + (r_idx * (gh / 2))
        r_h = gh / 2 - 2
        r_total_loc = sum(max(20, int(item.get("loc", 100))) for item in row_items) or 1
        x_cursor = start_x

        for item in row_items:
            loc = max(20, int(item.get("loc", 100)))
            w_item = (loc / r_total_loc) * gw - 2
            complexity = float(item.get("complexity", item.get("metrics", {}).get("complexity", 10.0)))

            if complexity >= 25:
                fill_color = "#ef4444"
                text_col = "#ffffff"
            elif complexity >= 12:
                fill_color = "#f59e0b"
                text_col = "#0f172a"
            else:
                fill_color = "#10b981"
                text_col = "#ffffff"

            name = item.get("name") or item.get("label") or item.get("id", "mod").split(".")[-1]
            disp = name if len(name) <= 12 else name[:10] + "…"

            rects_svg.append(f"""
    <g transform="translate({x_cursor:.1f}, {r_y:.1f})">
      <rect width="{max(10, w_item):.1f}" height="{r_h:.1f}" rx="4" fill="{fill_color}" opacity="0.9" stroke="#ffffff" stroke-width="1.5" />
      <text x="6" y="16" font-family="monospace" font-size="8.5" font-weight="700" fill="{text_col}">{escape_xml(disp)}</text>
      <text x="6" y="{r_h - 6}" font-family="-apple-system, sans-serif" font-size="7.5" fill="{text_col}" opacity="0.85">{loc} LOC · CC: {complexity:.0f}</text>
    </g>
""")
            x_cursor += max(10, w_item) + 2

    return f"""<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.2" />
  <text x="14" y="20" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="10" font-weight="700" fill="#64748b" letter-spacing="0.5">LOC TREEMAP (SIZED BY LINES OF CODE, COLORED BY COMPLEXITY)</text>
  {"".join(rects_svg)}
</svg>"""


def generate_blast_radius_svg(
    root_id: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    width: int = 520,
    height: int = 240,
) -> str:
    """Generate Blast Radius BFS Depth Rings SVG visualization."""
    if not nodes:
        return f"""<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="8" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1.2" />
  <text x="{width / 2}" y="{height / 2}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="12" fill="#64748b" text-anchor="middle">No components to compute blast radius</text>
</svg>"""

    # Compute BFS depth rings
    from collections import deque
    adj_rev: dict[str, list[str]] = {}
    for e in edges:
        s, t = e.get("source"), e.get("target")
        if s and t:
            adj_rev.setdefault(t, []).append(s)

    target_id = root_id or (nodes[0].get("id") if nodes else "root")
    depths: dict[str, int] = {target_id: 0}
    q = deque([target_id])
    while q:
        curr = q.popleft()
        d = depths[curr]
        if d >= 2:
            continue
        for neighbor in adj_rev.get(curr, []):
            if neighbor not in depths:
                depths[neighbor] = d + 1
                q.append(neighbor)

    cx = width / 2
    cy = height / 2 + 10

    ring1_count = sum(1 for d in depths.values() if d == 1)
    ring2_count = sum(1 for d in depths.values() if d == 2)
    target_name = target_id.split(".")[-1]

    return f"""<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.2" />
  <text x="14" y="20" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="10" font-weight="700" fill="#64748b" letter-spacing="0.5">BLAST RADIUS IMPACT RINGS (TARGET: {escape_xml(target_name).upper()})</text>

  <!-- Ring 2: Transitive Dependents -->
  <circle cx="{cx}" cy="{cy}" r="88" fill="#fef2f2" stroke="#fca5a5" stroke-width="1.5" stroke-dasharray="4 4" />
  <text x="{cx}" y="{cy - 92}" font-family="-apple-system, sans-serif" font-size="8.5" font-weight="700" fill="#dc2626" text-anchor="middle">Level 2 Transitive Dependents ({ring2_count})</text>

  <!-- Ring 1: Direct Dependents -->
  <circle cx="{cx}" cy="{cy}" r="52" fill="#fff7ed" stroke="#fdba74" stroke-width="1.5" />
  <text x="{cx}" y="{cy - 56}" font-family="-apple-system, sans-serif" font-size="8.5" font-weight="700" fill="#ea580c" text-anchor="middle">Level 1 Direct ({ring1_count})</text>

  <!-- Epicenter -->
  <circle cx="{cx}" cy="{cy}" r="22" fill="#1e293b" stroke="#0ea5e9" stroke-width="2.5" />
  <text x="{cx}" y="{cy + 4}" font-family="monospace" font-size="9" font-weight="800" fill="#ffffff" text-anchor="middle">{escape_xml(target_name[:8])}</text>
  <text x="{cx}" y="{cy + 115}" font-family="-apple-system, sans-serif" font-size="9" font-weight="600" fill="#64748b" text-anchor="middle">Total Impacted Modules: {len(depths) - 1} of {len(nodes)} ({(len(depths) - 1) / max(1, len(nodes)) * 100:.1f}%)</text>
</svg>"""

