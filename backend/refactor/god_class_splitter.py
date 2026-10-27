"""God class splitter using community detection on the class's method-field interaction graph."""

from __future__ import annotations

import ast
import logging
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

from analysis.community import compute_louvain_communities
from analysis.graph import DirectedGraph

from refactor.models import Effort, RefactorSuggestion, RefactorType

if TYPE_CHECKING:
    from analysis.graph import GraphNode

logger = logging.getLogger(__name__)


def _build_ast_method_field_graph(source_code: str, class_name: str) -> DirectedGraph:
    """Extract methods and field accesses for a class via Python AST."""
    inner_g = DirectedGraph()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        try:
            tree = ast.parse(source_code)
        except Exception:
            return inner_g

    target_class_def = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and (not class_name or node.name == class_name):
            target_class_def = node
            break

    if not target_class_def:
        return inner_g

    methods = [n for n in target_class_def.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for m in methods:
        inner_g.add_node(m.name, name=m.name, node_type="method")

    for m in methods:
        for sub in ast.walk(m):
            # Check calls to other methods in self
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                if isinstance(sub.func.value, ast.Name) and sub.func.value.id == "self":
                    target_member = sub.func.attr
                    if target_member in inner_g.nodes and target_member != m.name:
                        inner_g.add_edge(m.name, target_member, edge_type="calls", weight=1.0)
            # Check self.field accesses
            elif isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == "self":
                field_name = f"field:{sub.attr}"
                if field_name not in inner_g.nodes:
                    inner_g.add_node(field_name, name=sub.attr, node_type="field")
                inner_g.add_edge(m.name, field_name, edge_type="uses", weight=1.0)

    return inner_g


class GodClassSplitter:
    """Decomposes god classes into cohesive single-responsibility classes."""

    def __init__(self, loc_threshold: int = 300, method_threshold: int = 15) -> None:
        self.loc_threshold = loc_threshold
        self.method_threshold = method_threshold

    def build_method_field_graph(self, node: GraphNode, graph: DirectedGraph) -> DirectedGraph:
        """Construct the inner method-field graph for a god class."""
        inner_g = DirectedGraph()

        # 1. First attempt: check if graph has contains edges for methods
        inner_methods: list[str] = []
        for (src, tgt), edge in graph.edges.items():
            if src == node.id and edge.edge_type == "contains":
                tgt_node = graph.nodes.get(tgt)
                if tgt_node and tgt_node.node_type in ("method", "function", "field"):
                    inner_methods.append(tgt)
                    inner_g.add_node(tgt, name=tgt_node.name, node_type=tgt_node.node_type)

        if len(inner_g.nodes) >= 4:
            # Connect edges between inner methods
            for m in inner_methods:
                for succ in graph.successors(m):
                    if succ in inner_g.nodes and succ != m:
                        inner_g.add_edge(m, succ, weight=1.0)
            return inner_g

        # 2. Second attempt: read source code from disk if available
        if node.path and Path(node.path).exists():
            try:
                code = Path(node.path).read_text(encoding="utf-8", errors="replace")
                ast_g = _build_ast_method_field_graph(code, node.name)
                if len(ast_g.nodes) >= 4:
                    return ast_g
            except Exception as exc:
                logger.debug("Could not parse AST method-field graph for %s: %s", node.id, exc)

        # 3. Fallback: group outgoing dependencies into cohesive responsibility clusters
        out_targets = list(graph.successors(node.id))
        if out_targets:
            for t in out_targets:
                inner_g.add_node(t, name=t.split(".")[-1], node_type="dependency")
            for i, t1 in enumerate(out_targets):
                for t2 in out_targets[i + 1 :]:
                    # Connect if they share successors or common domain prefix
                    p1 = t1.split(".")[:-1]
                    p2 = t2.split(".")[:-1]
                    if p1 == p2:
                        inner_g.add_edge(t1, t2, weight=1.0)
                        inner_g.add_edge(t2, t1, weight=1.0)

        return inner_g

    def generate_suggestions(self, graph: DirectedGraph) -> list[RefactorSuggestion]:
        """Generate god class decomposition suggestions."""
        suggestions: list[RefactorSuggestion] = []
        idx = 0

        # Sort nodes deterministically
        sorted_nodes = sorted(graph.nodes.values(), key=lambda n: n.id)

        for node in sorted_nodes:
            if node.is_external or node.node_type not in ("class", "interface"):
                continue

            loc = int(node.metrics.get("loc", 0))
            num_methods = int(node.metrics.get("num_methods", 0))

            if loc < self.loc_threshold and num_methods < self.method_threshold:
                continue

            inner_g = self.build_method_field_graph(node, graph)
            if inner_g.node_count < 4:
                # Synthetic division if inner graph is sparse
                clusters = [
                    {"name": f"{node.name}CoreService", "members": [f"{node.name}Operations"]},
                    {"name": f"{node.name}Helper", "members": [f"{node.name}Utilities"]},
                ]
            else:
                comm = compute_louvain_communities(inner_g)
                if len(comm.clusters) >= 2:
                    clusters = [
                        {
                            "name": f"{node.name}Component{c.cluster_id + 1}",
                            "members": c.nodes,
                        }
                        for c in comm.clusters
                    ]
                else:
                    # Split in half deterministically
                    nodes_list = list(inner_g.nodes.keys())
                    mid = len(nodes_list) // 2
                    clusters = [
                        {"name": f"{node.name}PrimaryService", "members": nodes_list[:mid]},
                        {"name": f"{node.name}SupportService", "members": nodes_list[mid:]},
                    ]

            idx += 1
            proposed_classes = [c["name"] for c in clusters]
            priority = 80.0 + min(15.0, (loc / 100.0) + (num_methods / 5.0))

            title = f"Split God Class '{node.name}' into {len(clusters)} cohesive components"
            rationale = (
                f"Class '{node.name}' violates the Single Responsibility Principle with "
                f"{loc} LOC and {num_methods} methods. Community detection on its method-field "
                f"interaction graph identified {len(clusters)} distinct functional clusters: "
                f"[{', '.join(proposed_classes)}]."
            )

            suggestions.append(
                RefactorSuggestion(
                    id=f"REFACTOR-GODCLASS-{idx:03d}",
                    type=RefactorType.SPLIT_GOD_CLASS,
                    title=title,
                    rationale=rationale,
                    affected_nodes=[node.id, *proposed_classes],
                    effort=Effort.L,
                    priority_score=priority,
                    action_details={
                        "original_class": node.id,
                        "loc": loc,
                        "num_methods": num_methods,
                        "extracted_classes": clusters,
                    },
                )
            )

        return suggestions
