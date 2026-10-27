"""Import resolution — mark edges as internal (resolved) or external.

After parsing all files in a repository we have a flat list of
``Edge(type=IMPORTS, resolved=False, target=<raw_import_string>)``.

This module post-processes those edges:
1.  Builds a lookup map of all known internal node IDs.
2.  For each unresolved import edge, attempts to find a matching internal node.
3.  Edges that match → ``resolved=True``.
4.  Edges that don't match → an *external* node is created (``is_external=True``)
    and the edge points to it (still ``resolved=False`` to flag it as external).
"""

from __future__ import annotations

import logging

from parsers.models import Edge, EdgeType, Metrics, Node, NodeType, ParseResult

logger = logging.getLogger(__name__)


def resolve_imports(
    file_results: list[ParseResult],
    language: str,
) -> tuple[list[Node], list[Edge]]:
    """Aggregate and resolve imports across all file results.

    Args:
        file_results: Per-file :class:`ParseResult` objects.
        language: ``'python'`` or ``'java'`` — controls resolution strategy.

    Returns:
        ``(nodes, edges)`` — deduplicated, with external nodes added and
        import edges resolved where possible.
    """
    # ── Collect all nodes and edges ───────────────────────────────────────────
    all_nodes: list[Node] = []
    all_edges: list[Edge] = []

    seen_node_ids: set[str] = set()

    for fr in file_results:
        for n in fr.nodes:
            if n.id not in seen_node_ids:
                all_nodes.append(n)
                seen_node_ids.add(n.id)
        all_edges.extend(fr.edges)

    # ── Build lookup maps ─────────────────────────────────────────────────────
    # Node id → node
    node_by_id: dict[str, Node] = {n.id: n for n in all_nodes}

    # Language-specific secondary lookup keys
    resolver = _PythonResolver() if language == "python" else _JavaResolver()
    resolver.build(all_nodes)

    # ── Resolve import edges ──────────────────────────────────────────────────
    external_nodes: dict[str, Node] = {}
    resolved_edges: list[Edge] = []

    for edge in all_edges:
        if edge.type != EdgeType.IMPORTS:
            resolved_edges.append(edge)
            continue

        raw_target = edge.target
        resolved_id = resolver.resolve(raw_target)

        if resolved_id and resolved_id in node_by_id:
            # Internal resolution
            resolved_edges.append(
                Edge(
                    source=edge.source,
                    target=resolved_id,
                    type=edge.type,
                    resolved=True,
                    line=edge.line,
                )
            )
        else:
            # External — create stub node if not already present
            ext_id = f"ext:{raw_target}"
            if ext_id not in external_nodes and ext_id not in node_by_id:
                external_nodes[ext_id] = Node(
                    id=ext_id,
                    type=NodeType.EXTERNAL,
                    name=raw_target.split(".")[-1],
                    path="",
                    language=language,
                    metrics=Metrics(),
                    is_external=True,
                )
            resolved_edges.append(
                Edge(
                    source=edge.source,
                    target=ext_id,
                    type=edge.type,
                    resolved=False,
                    line=edge.line,
                )
            )

    # Merge external nodes
    final_nodes = all_nodes + [n for n in external_nodes.values() if n.id not in node_by_id]
    final_nodes.sort(key=lambda n: n.id)
    resolved_edges.sort(key=lambda e: (e.source, e.target, e.line or 0))

    logger.info(
        "Import resolution: %d internal, %d external dependencies",
        sum(1 for e in resolved_edges if e.type == EdgeType.IMPORTS and e.resolved),
        len(external_nodes),
    )
    return final_nodes, resolved_edges


# ── Resolver strategies ────────────────────────────────────────────────────────


class _PythonResolver:
    """Resolve Python import strings to internal module/class ids."""

    def __init__(self) -> None:
        self._map: dict[str, str] = {}

    def build(self, nodes: list[Node]) -> None:
        for n in nodes:
            if n.is_external:
                continue
            # Direct id match
            self._map[n.id] = n.id
            # Short name match (last segment)
            short = n.name
            if short and short not in self._map:
                self._map[short] = n.id
            # For module nodes, also register with trailing segments
            if n.type in (NodeType.MODULE, NodeType.FILE):
                parts = n.id.split(".")
                for i in range(1, len(parts)):
                    suffix = ".".join(parts[i:])
                    if suffix not in self._map:
                        self._map[suffix] = n.id

    def resolve(self, raw: str) -> str | None:
        # Try exact, then strip trailing wildcard imports
        cleaned = raw.split(" import ")[0].strip() if " import " in raw else raw
        return self._map.get(cleaned) or self._map.get(raw)


class _JavaResolver:
    """Resolve Java FQN import strings to internal class/interface ids."""

    def __init__(self) -> None:
        self._map: dict[str, str] = {}
        self._short_map: dict[str, str] = {}

    def build(self, nodes: list[Node]) -> None:
        for n in nodes:
            if n.is_external:
                continue
            self._map[n.id] = n.id
            # Short class name
            if n.type in (NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM):
                short = n.name
                if short and short not in self._short_map:
                    self._short_map[short] = n.id
            # Package node
            if n.type == NodeType.PACKAGE:
                pkg_id = n.id.removeprefix("pkg:")
                self._map[pkg_id] = n.id

    def resolve(self, raw: str) -> str | None:
        # Try exact FQN first
        if raw in self._map:
            return self._map[raw]
        # Wildcard import: `com.example.*` → try to resolve package
        if raw.endswith(".*"):
            pkg = raw[:-2]
            pkg_key = f"pkg:{pkg}"
            if pkg_key in self._map:
                return pkg_key
            return self._map.get(pkg)
        # Try short name
        short = raw.split(".")[-1]
        return self._short_map.get(short)
