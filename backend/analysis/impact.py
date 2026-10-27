"""Impact analysis (blast radius) via Dijkstra and BFS.

Determines which components in the codebase are affected if node X changes.
Direction of impact:
If A depends on B (edge A -> B: 'calls' or 'imports'), then modifying B directly
or transitively impacts A. Hence, blast radius traverses reverse edges (predecessors).
"""

from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


@dataclass
class ImpactedNode:
    node_id: str
    depth: int
    distance: float
    path: list[str]
    is_direct: bool


@dataclass
class BlastRadiusResult:
    target_node: str
    total_impacted_count: int
    blast_radius_pct: float
    direct_impact_count: int
    transitive_impact_count: int
    max_depth: int
    impacted_nodes: list[ImpactedNode]

    def to_dict(self) -> dict:
        return {
            "target_node": self.target_node,
            "total_impacted_count": self.total_impacted_count,
            "blast_radius_pct": round(self.blast_radius_pct, 2),
            "direct_impact_count": self.direct_impact_count,
            "transitive_impact_count": self.transitive_impact_count,
            "max_depth": self.max_depth,
            "impacted_nodes": [
                {
                    "node_id": node.node_id,
                    "depth": node.depth,
                    "distance": round(node.distance, 4),
                    "is_direct": node.is_direct,
                    "path": node.path,
                }
                for node in self.impacted_nodes
            ],
        }


def compute_blast_radius_bfs(
    graph: DirectedGraph,
    target_node: str,
    max_depth: int = 100,
    direction: str = "reverse",
) -> BlastRadiusResult:
    """Compute blast radius using BFS (unweighted shortest hop distance).

    Args:
        graph: Architectural directed graph.
        target_node: The node being changed or refactored.
        max_depth: Maximum hops to traverse.
        direction: 'reverse' (default: find who depends on target) or 'forward' (who target depends on).
    """
    if target_node not in graph.nodes:
        return BlastRadiusResult(
            target_node=target_node,
            total_impacted_count=0,
            blast_radius_pct=0.0,
            direct_impact_count=0,
            transitive_impact_count=0,
            max_depth=0,
            impacted_nodes=[],
        )

    # Queue contains (current_node, current_depth, path_from_target)
    queue: deque[tuple[str, int, list[str]]] = deque([(target_node, 0, [target_node])])
    visited: set[str] = {target_node}
    impacted: list[ImpactedNode] = []
    direct_count = 0
    max_d_seen = 0

    while queue:
        curr, depth, path = queue.popleft()

        if curr != target_node:
            is_dir = depth == 1
            if is_dir:
                direct_count += 1
            max_d_seen = max(max_d_seen, depth)

            impacted.append(
                ImpactedNode(
                    node_id=curr,
                    depth=depth,
                    distance=float(depth),
                    path=path,
                    is_direct=is_dir,
                )
            )

        if depth >= max_depth:
            continue

        neighbors = graph.predecessors(curr) if direction == "reverse" else graph.successors(curr)
        for nbr in neighbors:
            if nbr not in visited:
                visited.add(nbr)
                queue.append((nbr, depth + 1, [*path, nbr]))

    total_nodes = graph.node_count
    total_impacted = len(impacted)
    pct = (total_impacted / total_nodes * 100.0) if total_nodes > 0 else 0.0

    return BlastRadiusResult(
        target_node=target_node,
        total_impacted_count=total_impacted,
        blast_radius_pct=pct,
        direct_impact_count=direct_count,
        transitive_impact_count=total_impacted - direct_count,
        max_depth=max_d_seen,
        impacted_nodes=impacted,
    )


def compute_blast_radius_dijkstra(
    graph: DirectedGraph,
    target_node: str,
    direction: str = "reverse",
) -> BlastRadiusResult:
    """Compute blast radius using Dijkstra's algorithm for weighted shortest paths.

    Time Complexity: O(E + V log V)
    """
    if target_node not in graph.nodes:
        return BlastRadiusResult(
            target_node=target_node,
            total_impacted_count=0,
            blast_radius_pct=0.0,
            direct_impact_count=0,
            transitive_impact_count=0,
            max_depth=0,
            impacted_nodes=[],
        )

    # dist[node] -> shortest distance
    dist: dict[str, float] = {target_node: 0.0}
    # parent[node] -> predecessor in shortest path tree
    parent: dict[str, str | None] = {target_node: None}
    # depth[node] -> hop count
    depth_map: dict[str, int] = {target_node: 0}

    # Priority queue: (current_distance, node_id)
    pq: list[tuple[float, str]] = [(0.0, target_node)]

    while pq:
        d_curr, u = heapq.heappop(pq)
        if d_curr > dist[u]:
            continue

        neighbors = graph.predecessors(u) if direction == "reverse" else graph.successors(u)
        for v in neighbors:
            edge_weight = graph.edge_weight(v, u) if direction == "reverse" else graph.edge_weight(u, v)
            cost = max(0.1, edge_weight)
            new_dist = d_curr + cost

            if v not in dist or new_dist < dist[v]:
                dist[v] = new_dist
                parent[v] = u
                depth_map[v] = depth_map[u] + 1
                heapq.heappush(pq, (new_dist, v))

    impacted: list[ImpactedNode] = []
    direct_count = 0
    max_d_seen = 0

    for node_id, distance in dist.items():
        if node_id == target_node:
            continue

        # Reconstruct path
        path: list[str] = []
        curr_p: str | None = node_id
        while curr_p is not None:
            path.append(curr_p)
            curr_p = parent.get(curr_p)
        path.reverse()

        d_hops = depth_map[node_id]
        is_dir = d_hops == 1
        if is_dir:
            direct_count += 1
        max_d_seen = max(max_d_seen, d_hops)

        impacted.append(
            ImpactedNode(
                node_id=node_id,
                depth=d_hops,
                distance=distance,
                path=path,
                is_direct=is_dir,
            )
        )

    # Sort impacted nodes by distance ascending
    impacted.sort(key=lambda item: item.distance)

    total_nodes = graph.node_count
    total_impacted = len(impacted)
    pct = (total_impacted / total_nodes * 100.0) if total_nodes > 0 else 0.0

    return BlastRadiusResult(
        target_node=target_node,
        total_impacted_count=total_impacted,
        blast_radius_pct=pct,
        direct_impact_count=direct_count,
        transitive_impact_count=total_impacted - direct_count,
        max_depth=max_d_seen,
        impacted_nodes=impacted,
    )
