"""Headless architecture graph renderer using Matplotlib.

Generates high-resolution topological images embedded directly into reports as base64 PNGs.
"""

from __future__ import annotations

import base64
import io
import math
from typing import TYPE_CHECKING, ClassVar

import matplotlib

# Use headless non-interactive Agg backend
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


class HeadlessGraphRenderer:
    """Renders DirectedGraph into polished base64-encoded PNG diagrams."""

    LAYER_PALETTE: ClassVar[dict[str, str]] = {
        "Presentation": "#38bdf8",  # Sky blue
        "Service": "#a855f7",  # Purple
        "Domain": "#10b981",  # Emerald
        "Data / Infrastructure": "#f59e0b",  # Amber
        "External": "#64748b",  # Slate
        "Default": "#60a5fa",  # Blue
    }

    @classmethod
    def render_graph_to_base64(
        cls,
        graph: DirectedGraph,
        max_nodes_to_draw: int = 80,
        dpi: int = 150,
        dark_mode: bool = True,
    ) -> str:
        """Render architecture graph to base64 PNG string."""
        fig, ax = plt.subplots(figsize=(10, 6.5), dpi=dpi)

        bg_color = "#0c0d14" if dark_mode else "#ffffff"
        text_color = "#f8fafc" if dark_mode else "#0f172a"
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)

        nodes = list(graph.nodes.values())[:max_nodes_to_draw]
        node_ids = {n.id for n in nodes}

        if not nodes:
            ax.text(0.5, 0.5, "Empty Architecture Graph", ha="center", va="center", color=text_color, fontsize=14)
            ax.axis("off")
            return cls._fig_to_base64(fig)

        # 1. Compute 2D coordinates (Layered or Circular Force Layout)
        positions: dict[str, tuple[float, float]] = {}
        layer_buckets: dict[str, list[str]] = {
            "Presentation": [],
            "Service": [],
            "Domain": [],
            "Data / Infrastructure": [],
            "Other": [],
        }

        for n in nodes:
            l_val = getattr(n, "layer", None) or n.extra.get("layer") or n.metrics.get("layer") or "Other"
            layer = l_val if l_val in layer_buckets else "Other"
            layer_buckets[layer].append(n.id)

        # Assign coordinates by layer
        layer_y_offsets = {
            "Presentation": 0.85,
            "Service": 0.60,
            "Domain": 0.35,
            "Data / Infrastructure": 0.12,
            "Other": 0.48,
        }

        for layer_name, nids in layer_buckets.items():
            if not nids:
                continue
            y = layer_y_offsets[layer_name]
            count = len(nids)
            for i, nid in enumerate(nids):
                # Spread evenly along X axis
                x = 0.1 + 0.8 * ((i + 0.5) / count)
                # Add small jitter so lines don't perfectly overlap
                jitter_y = (math.sin(i * 1.5) * 0.04) if count > 1 else 0
                positions[nid] = (x, y + jitter_y)

        # 2. Draw Edges
        cycles_count = 0
        for edge in graph.edges.values():
            if edge.source in node_ids and edge.target in node_ids:
                x1, y1 = positions[edge.source]
                x2, y2 = positions[edge.target]

                is_cycle = getattr(edge, "is_cycle", False)
                if is_cycle:
                    edge_color = "#ef4444"
                    line_style = "--"
                    alpha = 0.85
                    width = 1.6
                    cycles_count += 1
                else:
                    edge_color = "#475569" if dark_mode else "#cbd5e1"
                    line_style = "-"
                    alpha = 0.35
                    width = 0.8

                # Draw subtle curved arrow
                arrow = FancyArrowPatch(
                    (x1, y1),
                    (x2, y2),
                    connectionstyle="arc3,rad=0.08",
                    color=edge_color,
                    linestyle=line_style,
                    linewidth=width,
                    alpha=alpha,
                    arrowstyle="-|>",
                    mutation_scale=8,
                )
                ax.add_patch(arrow)

        # 3. Draw Nodes
        for n in nodes:
            x, y = positions[n.id]
            is_vulnerable = getattr(n, "is_vulnerable", False) or n.metrics.get("risk_score", 0) > 60

            # Centrality determines node size
            centrality = n.metrics.get("centrality", n.metrics.get("pagerank", 0.3))
            size = max(180, min(800, int(200 + float(centrality) * 600)))

            n_layer = getattr(n, "layer", None) or n.extra.get("layer") or n.metrics.get("layer") or "Default"
            node_color = "#ef4444" if is_vulnerable else cls.LAYER_PALETTE.get(n_layer, "#3b82f6")
            edge_color = "#ffffff" if is_vulnerable else ("#1e293b" if dark_mode else "#94a3b8")

            # Draw outer glow circle for high risk / vulnerable nodes
            if is_vulnerable:
                ax.scatter(x, y, s=size * 2.2, color="#ef4444", alpha=0.25, edgecolors="none")

            ax.scatter(x, y, s=size, color=node_color, edgecolors=edge_color, linewidth=1.5, zorder=5)

            # Node label (shortened basename)
            short_label = n.name if len(n.name) <= 18 else n.name[:16] + "…"
            ax.text(
                x,
                y - 0.035,
                short_label,
                fontsize=7.5,
                color=text_color,
                ha="center",
                va="top",
                fontfamily="monospace",
                fontweight="medium",
                zorder=6,
            )

        # 4. Draw Layer Header Bands
        for layer_name, y in [
            ("PRESENTATION LAYER", 0.94),
            ("SERVICE LAYER", 0.69),
            ("DOMAIN LAYER", 0.44),
            ("DATA & INFRASTRUCTURE", 0.20),
        ]:
            ax.axhline(
                y=y,
                color="#334155" if dark_mode else "#e2e8f0",
                linestyle=":",
                linewidth=0.7,
                alpha=0.5,
            )
            ax.text(
                0.02,
                y + 0.01,
                layer_name,
                fontsize=8,
                color="#94a3b8",
                fontfamily="monospace",
                fontweight="bold",
            )

        ax.set_xlim(0, 1.0)
        ax.set_ylim(0.05, 1.0)
        ax.axis("off")

        return cls._fig_to_base64(fig)

    @staticmethod
    def _fig_to_base64(fig: plt.Figure) -> str:
        """Convert matplotlib Figure to base64 data URI."""
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.1)
        plt.close(fig)
        buf.seek(0)
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"
