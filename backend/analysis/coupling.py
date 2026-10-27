"""Coupling and instability metrics (Robert C. Martin).

Metrics:
- Ca (Afferent Coupling / Fan-In): Number of external entities depending on this entity.
- Ce (Efferent Coupling / Fan-Out): Number of external entities this entity depends upon.
- Instability: I = Ce / (Ca + Ce)
  * I = 0: maximally stable (resists change, heavily depended on)
  * I = 1: maximally unstable (easily changeable, depends on many others)
  * If Ca + Ce == 0: I = 0.0 (isolated)
- Abstractness A: ratio of abstract classes/interfaces to total classes.
- Distance from Main Sequence D: |A + I - 1| (0 is on the balanced main sequence).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph


@dataclass
class NodeCoupling:
    node_id: str
    fan_in: int  # Ca (incoming dependencies)
    fan_out: int  # Ce (outgoing dependencies)
    instability: float  # I in [0.0, 1.0]

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "fan_in": self.fan_in,
            "fan_out": self.fan_out,
            "instability": round(self.instability, 4),
        }


@dataclass
class PackageCoupling:
    package_name: str
    classes: list[str]
    ca: int
    ce: int
    instability: float
    abstractness: float
    distance_from_main_sequence: float

    @property
    def distance(self) -> float:
        return self.distance_from_main_sequence

    def to_dict(self) -> dict:
        return {
            "package_name": self.package_name,
            "class_count": len(self.classes),
            "ca": self.ca,
            "ce": self.ce,
            "instability": round(self.instability, 4),
            "abstractness": round(self.abstractness, 4),
            "distance": round(self.distance_from_main_sequence, 4),
        }


@dataclass
class CouplingAnalysis:
    nodes: list[NodeCoupling]
    packages: list[PackageCoupling]
    mean_instability: float

    def to_dict(self) -> dict:
        return {
            "mean_instability": round(self.mean_instability, 4),
            "node_couplings": [n.to_dict() for n in self.nodes],
            "package_couplings": [p.to_dict() for p in self.packages],
        }


def compute_coupling_metrics(graph: DirectedGraph) -> CouplingAnalysis:
    """Compute fan-in, fan-out, and Martin's instability metric I = Ce / (Ca + Ce)."""
    node_couplings: list[NodeCoupling] = []
    total_instability = 0.0

    for nid in graph.nodes:
        ca = graph.in_degree(nid)
        ce = graph.out_degree(nid)
        denom = ca + ce
        instability = (ce / denom) if denom > 0 else 0.0

        nc = NodeCoupling(
            node_id=nid,
            fan_in=ca,
            fan_out=ce,
            instability=instability,
        )
        node_couplings.append(nc)
        total_instability += instability

    # Package / module grouping
    pkg_map: dict[str, list[str]] = {}
    for nid, node in graph.nodes.items():
        # Derive package/directory from node path or ID
        if "/" in node.path or "\\" in node.path:
            clean_p = node.path.replace("\\", "/")
            pkg = clean_p.rsplit("/", 1)[0]
        elif ":" in nid:
            pkg = nid.split(":", 1)[1].rsplit(".", 1)[0] if "." in nid else nid.split(":", 1)[0]
        else:
            pkg = nid.rsplit(".", 1)[0] if "." in nid else "default"
        pkg_map.setdefault(pkg, []).append(nid)

    package_couplings: list[PackageCoupling] = []
    for pkg_name, members in pkg_map.items():
        member_set = set(members)
        # Ca: edges from outside pkg into pkg
        ca = 0
        # Ce: edges from inside pkg to outside pkg
        ce = 0
        abstract_count = 0

        for u in members:
            u_node = graph.nodes[u]
            if u_node.node_type in ("interface", "abstract_class") or "abstract" in u_node.annotations:
                abstract_count += 1

            for v in graph.successors(u):
                if v not in member_set:
                    ce += 1
            for v in graph.predecessors(u):
                if v not in member_set:
                    ca += 1

        denom = ca + ce
        i_metric = (ce / denom) if denom > 0 else 0.0
        a_metric = (abstract_count / len(members)) if members else 0.0
        d_metric = abs(a_metric + i_metric - 1.0)

        package_couplings.append(
            PackageCoupling(
                package_name=pkg_name,
                classes=members,
                ca=ca,
                ce=ce,
                instability=i_metric,
                abstractness=a_metric,
                distance_from_main_sequence=d_metric,
            )
        )

    mean_inst = (total_instability / len(node_couplings)) if node_couplings else 0.0

    return CouplingAnalysis(
        nodes=node_couplings,
        packages=package_couplings,
        mean_instability=mean_inst,
    )
