"""Tarjan's Strongly Connected Components algorithm for circular dependency detection.

Algorithm:
- Tarjan's linear-time DFS using index, lowlink, and an explicit/recursion stack.
- Time Complexity: O(V + E)
- Space Complexity: O(V)

Circular Dependency:
- Any SCC with >= 2 nodes constitutes an architectural cycle (circular dependency).
- Any SCC with 1 node that has a self-loop is a self-cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


@dataclass
class CircularDependency:
    cycle_id: str
    nodes: list[str]
    size: int
    edges: list[tuple[str, str]]
    is_self_loop: bool = False

    def to_dict(self) -> dict:
        return {
            "cycle_id": self.cycle_id,
            "nodes": self.nodes,
            "size": self.size,
            "edges": [{"source": u, "target": v} for u, v in self.edges],
            "is_self_loop": self.is_self_loop,
        }


def find_strongly_connected_components(graph: DirectedGraph) -> list[list[str]]:
    """Compute all strongly connected components using Tarjan's algorithm from scratch.

    Returns a list of components, where each component is a list of node IDs.
    """
    index = 0
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    sccs: list[list[str]] = []

    # Iterative / recursion helper
    # To prevent recursion limit issues on very deep graphs, we use an iterative DFS with call frames.
    for root in sorted(graph.nodes.keys()):
        if root in indices:
            continue

        # DFS call stack frame: (node, neighbor_iterator)
        call_stack = [(root, iter(sorted(graph.successors(root))))]
        indices[root] = index
        lowlink[root] = index
        index += 1
        stack.append(root)
        on_stack.add(root)

        while call_stack:
            v, neighbors = call_stack[-1]
            try:
                w = next(neighbors)
                if w not in indices:
                    indices[w] = index
                    lowlink[w] = index
                    index += 1
                    stack.append(w)
                    on_stack.add(w)
                    call_stack.append((w, iter(sorted(graph.successors(w)))))
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], indices[w])
            except StopIteration:
                call_stack.pop()
                if call_stack:
                    parent, _ = call_stack[-1]
                    lowlink[parent] = min(lowlink[parent], lowlink[v])

                if lowlink[v] == indices[v]:
                    component: list[str] = []
                    while True:
                        w = stack.pop()
                        on_stack.remove(w)
                        component.append(w)
                        if w == v:
                            break
                    component.sort()
                    sccs.append(component)

    return sccs


def detect_circular_dependencies(graph: DirectedGraph) -> list[CircularDependency]:
    """Detect circular dependency cycles from Tarjan's SCC results.

    Returns only non-trivial cycles (size >= 2, or self-loops) with deterministic ordering.
    """
    all_sccs = find_strongly_connected_components(graph)
    raw_cycles: list[CircularDependency] = []

    for scc in all_sccs:
        scc_set = set(scc)
        if len(scc) > 1:
            # Multi-node circular dependency
            cycle_edges: list[tuple[str, str]] = []
            for u in sorted(scc):
                for v in sorted(graph.successors(u)):
                    if v in scc_set:
                        cycle_edges.append((u, v))
            cycle_edges.sort()

            raw_cycles.append(
                CircularDependency(
                    cycle_id="",
                    nodes=sorted(scc),
                    size=len(scc),
                    edges=cycle_edges,
                    is_self_loop=False,
                )
            )
        elif len(scc) == 1:
            u = scc[0]
            # Check for self-loop
            if u in graph.successors(u):
                raw_cycles.append(
                    CircularDependency(
                        cycle_id="",
                        nodes=[u],
                        size=1,
                        edges=[(u, u)],
                        is_self_loop=True,
                    )
                )

    # Sort largest cycles first, breaking ties deterministically by sorted node IDs
    raw_cycles.sort(key=lambda c: (-c.size, c.nodes))

    # Assign stable cycle_id after sorting
    for i, c in enumerate(raw_cycles):
        c.cycle_id = f"cycle_{i + 1}"

    return raw_cycles
