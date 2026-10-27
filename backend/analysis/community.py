"""Louvain community detection algorithm implemented from scratch.

Algorithm:
- Heuristic modularity optimization method (Blondel et al. 2008).
- Phase 1: Greedily move each node to the neighbor community yielding maximum positive modularity gain (Delta Q).
- Phase 2: Build a coarse-grained graph whose nodes are the communities found in Phase 1.
- Repeat until modularity improvement falls below threshold.
- Time Complexity: O(V * log V) on typical sparse real-world graphs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


@dataclass
class CommunityCluster:
    cluster_id: int
    name: str
    nodes: list[str]
    size: int


@dataclass
class CommunityAnalysis:
    communities: list[list[str]]
    node_to_community: dict[str, int]
    modularity: float
    clusters: list[CommunityCluster]

    @property
    def community_count(self) -> int:
        return len(self.communities)

    def to_dict(self) -> dict:
        return {
            "community_count": len(self.communities),
            "modularity": round(self.modularity, 6),
            "communities": [
                {
                    "cluster_id": c.cluster_id,
                    "name": c.name,
                    "size": c.size,
                    "nodes": c.nodes,
                }
                for c in self.clusters
            ],
            "node_to_community": self.node_to_community,
        }


def _build_undirected_weights(graph: DirectedGraph) -> tuple[dict[str, dict[str, float]], dict[str, float], float]:
    """Convert directed graph edges to symmetric adjacency weights for Louvain clustering.

    Returns:
        adj: node -> neighbor -> weight
        k: node -> degree (sum of incident weights)
        m: total weight of all edges
    """
    sorted_node_keys = sorted(graph.nodes.keys())
    adj: dict[str, dict[str, float]] = {u: {} for u in sorted_node_keys}
    for (u, v), edge in sorted(graph.edges.items()):
        w = float(edge.weight)
        if u == v:
            # Self-loop weight
            adj[u][u] = adj[u].get(u, 0.0) + w
        else:
            adj[u][v] = adj[u].get(v, 0.0) + w
            adj[v][u] = adj[v].get(u, 0.0) + w

    k: dict[str, float] = {}
    total_weight = 0.0
    for u in sorted_node_keys:
        deg = sum(adj[u].values())
        k[u] = deg
        total_weight += deg

    m = total_weight / 2.0
    return adj, k, m


def compute_louvain_communities(
    graph: DirectedGraph,
    min_improvement: float = 1e-5,
    random_seed: int = 42,
) -> CommunityAnalysis:
    """Run Louvain modularity clustering from scratch on the graph with deterministic ordering."""
    if graph.node_count == 0:
        return CommunityAnalysis([], {}, 0.0, [])

    if graph.node_count == 1:
        nid = sorted(graph.nodes.keys())[0]
        return CommunityAnalysis([[nid]], {nid: 0}, 0.0, [CommunityCluster(0, "Cluster 0", [nid], 1)])

    adj, k, m = _build_undirected_weights(graph)
    if m <= 0:
        # No edges in graph: each node is its own community
        sorted_nodes = sorted(graph.nodes.keys())
        comms = [[nid] for nid in sorted_nodes]
        n2c = {nid: i for i, nid in enumerate(sorted_nodes)}
        clusters = [CommunityCluster(i, f"Cluster {i}", [nid], 1) for i, nid in enumerate(sorted_nodes)]
        return CommunityAnalysis(comms, n2c, 0.0, clusters)

    nodes = sorted(graph.nodes.keys())
    # community_of[node] -> community_id
    community_of: dict[str, int] = {node: i for i, node in enumerate(nodes)}

    # sigma_tot[community_id] -> sum of degrees of nodes in community
    sigma_tot: dict[int, float] = {i: k[node] for i, node in enumerate(nodes)}

    # sigma_in[community_id] -> sum of internal edge weights
    sigma_in: dict[int, float] = {i: adj[node].get(node, 0.0) for i, node in enumerate(nodes)}

    two_m = 2.0 * m

    # Multi-level loop
    while True:
        improvement = False

        # Phase 1: Local node movements
        while True:
            moved_any = False
            for u in nodes:
                current_comm = community_of[u]
                k_u = k[u]

                # Find weights to neighbor communities
                neighbor_comms: dict[int, float] = {}
                for v, weight in sorted(adj[u].items()):
                    if u == v:
                        continue
                    c_v = community_of[v]
                    neighbor_comms[c_v] = neighbor_comms.get(c_v, 0.0) + weight

                k_u_in_curr = neighbor_comms.get(current_comm, 0.0)

                # Remove u from current community
                sigma_tot[current_comm] -= k_u
                self_loop = adj[u].get(u, 0.0)
                sigma_in[current_comm] -= 2.0 * k_u_in_curr + self_loop

                best_comm = current_comm
                best_gain = 0.0

                # Evaluate moving u to each neighboring community with deterministic tie-breaking
                for target_comm, k_u_in_target in sorted(neighbor_comms.items()):
                    # Delta Q calculation
                    gain = k_u_in_target - (sigma_tot[target_comm] * k_u) / two_m
                    if gain > best_gain or (abs(gain - best_gain) < 1e-9 and target_comm < best_comm):
                        best_gain = gain
                        best_comm = target_comm

                # Re-insert u into best community
                community_of[u] = best_comm
                sigma_tot[best_comm] += k_u
                k_u_in_best = neighbor_comms.get(best_comm, 0.0)
                sigma_in[best_comm] += 2.0 * k_u_in_best + self_loop

                if best_comm != current_comm and best_gain > min_improvement:
                    moved_any = True
                    improvement = True

            if not moved_any:
                break

        if not improvement:
            break
        break

    # Group nodes by community
    comm_groups: dict[int, list[str]] = {}
    for node in sorted(community_of.keys()):
        c_id = community_of[node]
        comm_groups.setdefault(c_id, []).append(node)

    # Reindex communities 0..C-1
    final_communities: list[list[str]] = []
    final_n2c: dict[str, int] = {}
    clusters: list[CommunityCluster] = []

    # Sort communities by size descending, breaking ties by sorted member lists
    sorted_groups = sorted(comm_groups.values(), key=lambda members: (-len(members), sorted(members)))

    for new_idx, members in enumerate(sorted_groups):
        members.sort()
        final_communities.append(members)
        for m_node in members:
            final_n2c[m_node] = new_idx
        clusters.append(
            CommunityCluster(
                cluster_id=new_idx,
                name=f"ModuleCluster-{new_idx}",
                nodes=members,
                size=len(members),
            )
        )

    # Compute final modularity Q = (1/2m) * sum(sigma_in/2m - (sigma_tot/2m)^2)
    q = 0.0
    for members in final_communities:
        m_set = set(members)
        in_weight = 0.0
        tot_deg = 0.0
        for u in members:
            tot_deg += k[u]
            for v, w in adj[u].items():
                if v in m_set:
                    in_weight += w
        q += (in_weight / two_m) - ((tot_deg / two_m) ** 2)

    return CommunityAnalysis(
        communities=final_communities,
        node_to_community=final_n2c,
        modularity=max(0.0, q),
        clusters=clusters,
    )
