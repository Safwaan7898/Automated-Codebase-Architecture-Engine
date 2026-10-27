"""Benchmark test on a 10,000-node graph measuring runtime and scalability."""

from __future__ import annotations

import time


from analysis.centrality import compute_pagerank
from analysis.coupling import compute_coupling_metrics
from analysis.dead_code import find_dead_code_candidates
from analysis.graph import DirectedGraph
from analysis.impact import compute_blast_radius_bfs
from analysis.scc import find_strongly_connected_components
from analysis.topo_sort import compute_architectural_layers


def generate_benchmark_graph(num_nodes: int = 10_000) -> DirectedGraph:
    """Generate a realistic synthetic dependency graph with 10k nodes."""
    g = DirectedGraph()

    # Add 10,000 nodes across 50 packages
    for i in range(num_nodes):
        pkg_id = i % 50
        g.add_node(
            node_id=f"Node_{i}",
            name=f"Class_{i}",
            path=f"com/company/pkg_{pkg_id}/Class_{i}.java",
            node_type="class",
            metrics={"loc": 10 + (i % 500)},
        )

    # Add ~25,000 directed edges:
    # 1. Hierarchical backbone (chain and trees)
    for i in range(num_nodes - 1):
        # Forward dependency
        g.add_edge(f"Node_{i}", f"Node_{i + 1}")

    # 2. Package-internal clustering edges
    for i in range(0, num_nodes - 20, 10):
        g.add_edge(f"Node_{i}", f"Node_{i + 5}")
        g.add_edge(f"Node_{i + 5}", f"Node_{i + 10}")

    # 3. Intentional small cycles in specific clusters
    for i in range(0, 500, 25):
        g.add_edge(f"Node_{i + 2}", f"Node_{i}")

    return g


class TestBenchmark10kNodes:
    def test_benchmark_algorithms_10k_nodes(self) -> None:
        t0 = time.monotonic()
        g = generate_benchmark_graph(10_000)
        t_gen = time.monotonic() - t0
        assert g.node_count == 10_000
        assert g.edge_count > 10_000

        timings: dict[str, float] = {}

        # 1. Tarjan's SCC
        t0 = time.monotonic()
        sccs = find_strongly_connected_components(g)
        timings["Tarjan SCC"] = time.monotonic() - t0
        assert len(sccs) > 0
        # SCC on 10k nodes must run in under 2.0s
        assert timings["Tarjan SCC"] < 2.0

        # 2. Topological Sort & Layers
        t0 = time.monotonic()
        layers = compute_architectural_layers(g)
        timings["TopoSort & Layers"] = time.monotonic() - t0
        assert layers.total_layers > 0
        assert timings["TopoSort & Layers"] < 2.0

        # 3. PageRank (15 iterations for large graph)
        t0 = time.monotonic()
        pr = compute_pagerank(g, max_iter=15, tol=1e-4)
        timings["PageRank"] = time.monotonic() - t0
        assert len(pr) == 10_000
        assert timings["PageRank"] < 3.0

        # 4. Coupling Metrics (Ca, Ce, Instability)
        t0 = time.monotonic()
        cpl = compute_coupling_metrics(g)
        timings["Coupling Metrics"] = time.monotonic() - t0
        assert len(cpl.nodes) == 10_000
        assert timings["Coupling Metrics"] < 2.0

        # 5. Dead Code Detection
        t0 = time.monotonic()
        dc = find_dead_code_candidates(g)
        timings["Dead Code"] = time.monotonic() - t0
        assert dc.total_candidates >= 0
        assert timings["Dead Code"] < 1.0

        # 6. Impact Analysis (BFS Blast Radius)
        t0 = time.monotonic()
        blast = compute_blast_radius_bfs(g, target_node="Node_5000")
        timings["Impact Analysis (BFS)"] = time.monotonic() - t0
        assert blast.total_impacted_count >= 0
        assert timings["Impact Analysis (BFS)"] < 1.0

        print("\n--- 10,000 Node Benchmark Results ---")
        print(f"Graph Construction (10k nodes, {g.edge_count} edges): {t_gen:.4f}s")
        for algo, duration in timings.items():
            print(f"{algo}: {duration:.4f}s")
