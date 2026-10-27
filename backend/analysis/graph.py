"""Graph data structure for ArchLens analysis.

Provides a fast, pure-Python directed graph representation:
- Adjacency lists (forward edges)
- Predecessor lists (reverse edges)
- Edge weights and types
- Node attributes and metrics
- Bidirectional conversion to/from NetworkX (used for cross-checking)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import networkx as nx


@dataclass
class GraphNode:
    id: str
    name: str = ""
    node_type: str = "class"
    path: str = ""
    language: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    annotations: list[str] = field(default_factory=list)
    is_external: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    edge_type: str = "calls"
    weight: float = 1.0
    extra: dict[str, Any] = field(default_factory=dict)


class DirectedGraph:
    """Directed graph tailored for software dependency analysis."""

    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}
        # node_id -> dict[neighbor_id, weight]
        self._succ: dict[str, dict[str, float]] = {}
        # node_id -> dict[predecessor_id, weight]
        self._pred: dict[str, dict[str, float]] = {}
        # (source, target) -> GraphEdge
        self.edges: dict[tuple[str, str], GraphEdge] = {}

    def add_node(
        self,
        node_id: str,
        name: str | None = None,
        node_type: str = "class",
        path: str = "",
        language: str = "",
        metrics: dict[str, Any] | None = None,
        annotations: list[str] | None = None,
        is_external: bool = False,
        **extra: Any,
    ) -> GraphNode:
        if node_id not in self.nodes:
            node = GraphNode(
                id=node_id,
                name=name or node_id,
                node_type=node_type,
                path=path,
                language=language,
                metrics=metrics or {},
                annotations=annotations or [],
                is_external=is_external,
                extra=extra,
            )
            self.nodes[node_id] = node
            self._succ[node_id] = {}
            self._pred[node_id] = {}
            return node
        return self.nodes[node_id]

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str = "calls",
        weight: float = 1.0,
        allow_self_loops: bool = True,
        **extra: Any,
    ) -> GraphEdge | None:
        if not allow_self_loops and source == target:
            return None

        if source not in self.nodes:
            self.add_node(source)
        if target not in self.nodes:
            self.add_node(target)

        if (source, target) in self.edges:
            existing = self.edges[(source, target)]
            existing.weight += weight
            self._succ[source][target] = existing.weight
            self._pred[target][source] = existing.weight
            return existing

        edge = GraphEdge(
            source=source,
            target=target,
            edge_type=edge_type,
            weight=weight,
            extra=extra,
        )
        self.edges[(source, target)] = edge
        self._succ[source][target] = weight
        self._pred[target][source] = weight
        return edge

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def remove_edge(self, source: str, target: str) -> None:
        """Remove a directed edge (source, target) if it exists."""
        self.edges.pop((source, target), None)
        if source in self._succ:
            self._succ[source].pop(target, None)
        if target in self._pred:
            self._pred[target].pop(source, None)

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all incident edges."""
        if node_id not in self.nodes:
            return
        for target in list(self._succ.get(node_id, {}).keys()):
            self.remove_edge(node_id, target)
        for source in list(self._pred.get(node_id, {}).keys()):
            self.remove_edge(source, node_id)
        self._succ.pop(node_id, None)
        self._pred.pop(node_id, None)
        self.nodes.pop(node_id, None)

    def successors(self, node_id: str) -> list[str]:
        """Outgoing neighbor IDs (nodes this node calls/depends on)."""
        return list(self._succ.get(node_id, {}).keys())

    def predecessors(self, node_id: str) -> list[str]:
        """Incoming neighbor IDs (nodes that call/depend on this node)."""
        return list(self._pred.get(node_id, {}).keys())

    def out_degree(self, node_id: str) -> int:
        return len(self._succ.get(node_id, {}))

    def in_degree(self, node_id: str) -> int:
        return len(self._pred.get(node_id, {}))

    def edge_weight(self, source: str, target: str, default: float = 1.0) -> float:
        return self._succ.get(source, {}).get(target, default)

    def to_networkx(self) -> nx.DiGraph:
        """Convert to a NetworkX DiGraph for cross-checking algorithm outputs."""
        G = nx.DiGraph()
        for nid, node in self.nodes.items():
            G.add_node(
                nid,
                name=node.name,
                node_type=node.node_type,
                path=node.path,
                language=node.language,
                is_external=node.is_external,
                metrics=node.metrics,
            )
        for (u, v), edge in self.edges.items():
            G.add_edge(u, v, weight=edge.weight, edge_type=edge.edge_type)
        return G

    @classmethod
    def from_networkx(cls, G: nx.DiGraph) -> DirectedGraph:
        """Construct from a NetworkX DiGraph."""
        dg = cls()
        for nid, data in G.nodes(data=True):
            dg.add_node(
                node_id=str(nid),
                name=data.get("name", str(nid)),
                node_type=data.get("node_type", "class"),
                path=data.get("path", ""),
                language=data.get("language", ""),
                metrics=data.get("metrics", {}),
                is_external=data.get("is_external", False),
            )
        for u, v, data in G.edges(data=True):
            dg.add_edge(
                source=str(u),
                target=str(v),
                edge_type=data.get("edge_type", "calls"),
                weight=float(data.get("weight", 1.0)),
            )
        return dg
