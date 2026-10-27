"""Centrality metrics: Betweenness Centrality and PageRank from scratch.

Algorithms:
1. Betweenness Centrality: Brandes' algorithm O(V * E) for unweighted directed graphs.
2. PageRank: Power iteration with dangling node redistribution O(k * (V + E)).
3. Identification of bottleneck and god classes.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


@dataclass
class NodeCentralityResult:
    node_id: str
    betweenness: float
    pagerank: float
    is_bottleneck: bool = False
    is_god_class: bool = False


@dataclass
class CentralityAnalysis:
    betweenness: dict[str, float]
    pagerank: dict[str, float]
    bottlenecks: list[str]
    god_classes: list[str]
    node_results: list[NodeCentralityResult]

    def to_dict(self) -> dict:
        return {
            "bottlenecks": self.bottlenecks,
            "god_classes": self.god_classes,
            "betweenness": {k: round(v, 6) for k, v in self.betweenness.items()},
            "pagerank": {k: round(v, 6) for k, v in self.pagerank.items()},
            "nodes": [
                {
                    "node_id": nr.node_id,
                    "betweenness": round(nr.betweenness, 6),
                    "pagerank": round(nr.pagerank, 6),
                    "is_bottleneck": nr.is_bottleneck,
                    "is_god_class": nr.is_god_class,
                }
                for nr in self.node_results
            ],
        }


def compute_betweenness_centrality(
    graph: DirectedGraph,
    normalized: bool = True,
) -> dict[str, float]:
    """Compute betweenness centrality for all nodes using Ulrik Brandes' algorithm.

    Time Complexity: O(V * E)
    Space Complexity: O(V + E)
    """
    n = graph.node_count
    cb = dict.fromkeys(graph.nodes, 0.0)
    if n <= 2:
        return cb

    nodes = sorted(graph.nodes.keys())

    for s in nodes:
        # S is the stack of visited nodes in reverse order of BFS discovery
        S: list[str] = []
        # P[w] = list of predecessors of w on shortest paths from s
        P: dict[str, list[str]] = {w: [] for w in nodes}
        # sigma[w] = number of shortest paths from s to w
        sigma: dict[str, float] = dict.fromkeys(nodes, 0.0)
        sigma[s] = 1.0
        # d[w] = distance from s to w
        d: dict[str, int] = dict.fromkeys(nodes, -1)
        d[s] = 0

        # BFS queue
        Q: deque[str] = deque([s])

        while Q:
            v = Q.popleft()
            S.append(v)
            for w in sorted(graph.successors(v)):
                # Path discovery
                if d[w] < 0:
                    Q.append(w)
                    d[w] = d[v] + 1
                # Path counting
                if d[w] == d[v] + 1:
                    sigma[w] += sigma[v]
                    P[w].append(v)

        # Accumulation: dependency delta of s on each vertex v
        delta: dict[str, float] = dict.fromkeys(nodes, 0.0)
        while S:
            w = S.pop()
            for v in sorted(P[w]):
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                cb[w] += delta[w]

    # Normalization for directed graph: divide by (n-1)*(n-2)
    if normalized and n > 2:
        scale = 1.0 / ((n - 1) * (n - 2))
        for v in sorted(cb.keys()):
            cb[v] = round(cb[v] * scale, 8)

    return cb


def compute_pagerank(
    graph: DirectedGraph,
    alpha: float = 0.85,
    max_iter: int = 100,
    tol: float = 1e-7,
) -> dict[str, float]:
    """Compute PageRank using power iteration from scratch with deterministic sorting.

    Handles dangling nodes (nodes with 0 out-degree) by redistributing their
    mass uniformly across all nodes.
    Time Complexity: O(k * (V + E))
    """
    n = graph.node_count
    if n == 0:
        return {}

    nodes = sorted(graph.nodes.keys())
    initial_score = 1.0 / n
    p = dict.fromkeys(nodes, initial_score)

    dangling_nodes = [node for node in nodes if graph.out_degree(node) == 0]

    for _ in range(max_iter):
        p_last = p.copy()
        # Sum of mass from dangling nodes
        dangling_sum = alpha * sum(p_last[node] for node in dangling_nodes)
        base_score = (1.0 - alpha + dangling_sum) / n

        p = dict.fromkeys(nodes, base_score)

        for u in nodes:
            out_deg = graph.out_degree(u)
            if out_deg > 0:
                share = (alpha * p_last[u]) / out_deg
                for v in sorted(graph.successors(u)):
                    p[v] += share

        # Check convergence (L1 norm)
        err = sum(abs(p[node] - p_last[node]) for node in nodes)
        if err < tol:
            break

    # Normalize so sum(p) == 1.0 with consistent rounding
    total = sum(p.values())
    if total > 0:
        p = {k: round(v / total, 8) for k, v in sorted(p.items())}

    return p


def analyze_centrality(graph: DirectedGraph) -> CentralityAnalysis:
    """Run both betweenness and PageRank, identifying bottlenecks and god classes."""
    bw = compute_betweenness_centrality(graph)
    pr = compute_pagerank(graph)

    n = graph.node_count
    if n == 0:
        return CentralityAnalysis({}, {}, [], [], [])

    # Thresholds for bottlenecks: betweenness > mean + 1.5 * stddev
    bw_vals = [bw[k] for k in sorted(bw.keys())]
    bw_mean = sum(bw_vals) / n
    bw_variance = sum((x - bw_mean) ** 2 for x in bw_vals) / n
    bw_std = math.sqrt(bw_variance)
    bw_threshold = bw_mean + (1.5 * bw_std) if bw_std > 0 else bw_mean

    # Thresholds for god classes: high PageRank (> 2 * mean)
    pr_mean = 1.0 / n
    pr_threshold = 2.0 * pr_mean

    bottlenecks: list[str] = []
    god_classes: list[str] = []
    results: list[NodeCentralityResult] = []

    for nid in sorted(graph.nodes.keys()):
        is_bn = bw[nid] > bw_threshold and bw[nid] > 0
        is_god = pr[nid] > pr_threshold
        if is_bn:
            bottlenecks.append(nid)
        if is_god:
            god_classes.append(nid)

        results.append(
            NodeCentralityResult(
                node_id=nid,
                betweenness=bw[nid],
                pagerank=pr[nid],
                is_bottleneck=is_bn,
                is_god_class=is_god,
            )
        )

    # Sort bottlenecks and god classes by score descending, breaking ties by node ID
    bottlenecks.sort(key=lambda nid: (-round(bw[nid], 6), nid))
    god_classes.sort(key=lambda nid: (-round(pr[nid], 6), nid))
    results.sort(key=lambda nr: (-round(nr.pagerank, 6), -round(nr.betweenness, 6), nr.node_id))

    return CentralityAnalysis(
        betweenness=bw,
        pagerank=pr,
        bottlenecks=bottlenecks,
        god_classes=god_classes,
        node_results=results,
    )
