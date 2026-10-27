"""Dead code candidate detection.

Identifies nodes with zero in-degree that are not legitimate application entry points.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analysis.graph import DirectedGraph, GraphNode


@dataclass
class DeadCodeCandidate:
    node_id: str
    name: str
    node_type: str
    path: str
    loc: int
    confidence: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type,
            "path": self.path,
            "loc": self.loc,
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
        }


@dataclass
class DeadCodeAnalysis:
    total_candidates: int
    total_wasted_loc: int
    candidates: list[DeadCodeCandidate]

    def to_dict(self) -> dict:
        return {
            "total_candidates": self.total_candidates,
            "total_wasted_loc": self.total_wasted_loc,
            "candidates": [c.to_dict() for c in self.candidates],
        }


# Entrypoint patterns
ENTRY_FILENAMES = {
    "main.py",
    "app.py",
    "wsgi.py",
    "asgi.py",
    "manage.py",
    "cli.py",
    "setup.py",
    "main.java",
    "application.java",
    "app.java",
}

ENTRY_NAME_PATTERNS = [
    re.compile(r"^main$", re.IGNORECASE),
    re.compile(r"^run$", re.IGNORECASE),
    re.compile(r"^cli$", re.IGNORECASE),
    re.compile(r"^test_", re.IGNORECASE),
    re.compile(r".*test$", re.IGNORECASE),
    re.compile(r".*tests$", re.IGNORECASE),
]

ENTRY_ANNOTATIONS = {
    "springbootapplication",
    "restcontroller",
    "controller",
    "endpoint",
    "getmapping",
    "postmapping",
    "putmapping",
    "deletemapping",
    "requestmapping",
    "configuration",
    "bean",
    "test",
    "override",
    "eventlistener",
    "app.get",
    "app.post",
    "app.put",
    "app.delete",
    "router.get",
    "router.post",
}


def is_entry_point(node: GraphNode) -> bool:
    """Determine whether a node is an intentional entry point or test."""
    path_lower = node.path.replace("\\", "/").lower()

    # 1. External nodes are dependencies, not internal dead code
    if node.is_external:
        return True

    # 2. Check filename
    filename = path_lower.rsplit("/", 1)[-1] if "/" in path_lower else path_lower
    if filename in ENTRY_FILENAMES:
        return True

    # 3. Check test files/directories
    if "test" in path_lower or "tests" in path_lower:
        return True

    # 4. Check function/class names
    if any(pattern.match(node.name) for pattern in ENTRY_NAME_PATTERNS):
        return True

    # 5. Check annotations / decorators
    for ann in node.annotations:
        ann_clean = ann.lower().lstrip("@")
        if any(entry_ann in ann_clean for entry_ann in ENTRY_ANNOTATIONS):
            return True

    # 6. Check node type: Interfaces or base types might be extension points
    if node.node_type in ("interface", "package", "file", "module"):
        return True

    return False


def find_dead_code_candidates(graph: DirectedGraph) -> DeadCodeAnalysis:
    """Find nodes with zero in-degree that are not designated entry points."""
    candidates: list[DeadCodeCandidate] = []
    total_loc = 0

    for nid, node in sorted(graph.nodes.items(), key=lambda x: x[0]):
        # Check in-degree
        if graph.in_degree(nid) == 0:
            if not is_entry_point(node):
                loc = int(node.metrics.get("loc", 0))
                total_loc += loc

                # Confidence calculation: higher if it has out-degree (actively depends on others but is never called)
                out_deg = graph.out_degree(nid)
                confidence = 0.95 if out_deg > 0 else 0.80

                reason = f"Node '{node.name}' has 0 incoming dependencies (fan-in = 0) and is not an entrypoint."

                candidates.append(
                    DeadCodeCandidate(
                        node_id=nid,
                        name=node.name,
                        node_type=node.node_type,
                        path=node.path,
                        loc=loc,
                        confidence=confidence,
                        reason=reason,
                    )
                )

    # Sort candidates by LOC descending, breaking ties by node ID
    candidates.sort(key=lambda c: (-c.loc, c.node_id))

    return DeadCodeAnalysis(
        total_candidates=len(candidates),
        total_wasted_loc=total_loc,
        candidates=candidates,
    )
