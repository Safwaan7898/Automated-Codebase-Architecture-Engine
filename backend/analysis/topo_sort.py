"""Topological sort over the condensed DAG to produce architectural layers.

Algorithm:
1. Condense cyclic graph into a directed acyclic graph (DAG) by contracting SCCs.
2. Topological sort using Kahn's in-degree queue algorithm from scratch.
3. Compute architectural layer assignment (longest path from source / dependency depth).
- Time Complexity: O(V + E)
- Space Complexity: O(V + E)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from analysis.scc import find_strongly_connected_components

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


@dataclass
class CondensedNode:
    scc_id: int
    members: list[str]
    in_degree: int = 0
    layer: int = 0


@dataclass
class ArchitecturalLayers:
    layers: list[list[str]]
    """Ordered from top layer (0: presentation/entry) down to bottom layer (infrastructure/foundation)."""
    node_to_layer: dict[str, int]
    topological_order: list[str]
    is_dag: bool
    condensed_scc_count: int

    @property
    def total_layers(self) -> int:
        return len(self.layers)

    def to_dict(self) -> dict:
        return {
            "total_layers": len(self.layers),
            "layers": [{"layer_index": idx, "nodes": members} for idx, members in enumerate(self.layers)],
            "node_to_layer": self.node_to_layer,
            "topological_order": self.topological_order,
            "is_dag": self.is_dag,
            "condensed_scc_count": self.condensed_scc_count,
        }


def condense_graph(graph: DirectedGraph) -> tuple[dict[int, CondensedNode], dict[int, set[int]], dict[str, int]]:
    """Condense graph into a DAG by contracting each SCC into a single supernode.

    Returns:
        condensed_nodes: scc_id -> CondensedNode
        condensed_adj: scc_id -> set of successor scc_ids
        node_to_scc: original_node_id -> scc_id
    """
    sccs = find_strongly_connected_components(graph)
    node_to_scc: dict[str, int] = {}
    condensed_nodes: dict[int, CondensedNode] = {}
    condensed_adj: dict[int, set[int]] = {}

    for scc_id, members in enumerate(sccs):
        condensed_nodes[scc_id] = CondensedNode(scc_id=scc_id, members=members)
        condensed_adj[scc_id] = set()
        for node in members:
            node_to_scc[node] = scc_id

    # Add edges between distinct SCCs
    for u, v in graph.edges:
        scc_u = node_to_scc[u]
        scc_v = node_to_scc[v]
        if scc_u != scc_v:
            condensed_adj[scc_u].add(scc_v)

    # Compute in-degrees of condensed DAG
    for _scc_u, targets in condensed_adj.items():
        for scc_v in targets:
            condensed_nodes[scc_v].in_degree += 1

    return condensed_nodes, condensed_adj, node_to_scc


def compute_architectural_layers(graph: DirectedGraph) -> ArchitecturalLayers:
    """Perform topological sort on the condensed DAG and produce architectural layers."""
    if graph.node_count == 0:
        return ArchitecturalLayers(
            layers=[],
            node_to_layer={},
            topological_order=[],
            is_dag=True,
            condensed_scc_count=0,
        )

    condensed_nodes, condensed_adj, node_to_scc = condense_graph(graph)

    # Kahn's algorithm for topological sorting of condensed DAG
    in_degrees = {sid: cnode.in_degree for sid, cnode in condensed_nodes.items()}
    queue: deque[int] = deque([sid for sid, deg in in_degrees.items() if deg == 0])

    # Layer computation: layer of a node = 1 + max(layer of predecessors)
    scc_layer: dict[int, int] = dict.fromkeys(queue, 0)
    topo_sccs: list[int] = []

    while queue:
        u_scc = queue.popleft()
        topo_sccs.append(u_scc)
        current_layer = scc_layer[u_scc]

        for v_scc in condensed_adj[u_scc]:
            # Update layer of target
            scc_layer[v_scc] = max(scc_layer.get(v_scc, 0), current_layer + 1)
            in_degrees[v_scc] -= 1
            if in_degrees[v_scc] == 0:
                queue.append(v_scc)

    # Reconstruct topological ordering of individual nodes
    full_topo_order: list[str] = []
    for sid in topo_sccs:
        full_topo_order.extend(condensed_nodes[sid].members)

    # Group into architectural layers
    max_layer = max(scc_layer.values()) if scc_layer else 0
    layers: list[list[str]] = [[] for _ in range(max_layer + 1)]
    node_to_layer: dict[str, int] = {}

    for sid, l_idx in scc_layer.items():
        for member in condensed_nodes[sid].members:
            layers[l_idx].append(member)
            node_to_layer[member] = l_idx

    # Sort nodes in each layer deterministically
    for l_list in layers:
        l_list.sort()

    is_dag = len(condensed_nodes) == graph.node_count

    return ArchitecturalLayers(
        layers=layers,
        node_to_layer=node_to_layer,
        topological_order=full_topo_order,
        is_dag=is_dag,
        condensed_scc_count=len(condensed_nodes),
    )
