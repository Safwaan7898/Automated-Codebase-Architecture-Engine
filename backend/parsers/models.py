"""Normalized data models for the ArchLens parser layer.

Every language parser produces ``Node`` and ``Edge`` objects using these
types. The schema is deliberately language-agnostic so the rest of the
backend (graph rendering, refactoring engine) never needs to know whether
the source was Java or Python.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# ── Node types ────────────────────────────────────────────────────────────────


class NodeType(StrEnum):
    FILE = "file"
    PACKAGE = "package"
    MODULE = "module"
    CLASS = "class"
    INTERFACE = "interface"
    ENUM = "enum"
    FUNCTION = "function"
    METHOD = "method"
    EXTERNAL = "external"  # unresolved / third-party dependency


# ── Edge types ────────────────────────────────────────────────────────────────


class EdgeType(StrEnum):
    IMPORTS = "imports"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    CALLS = "calls"
    USES = "uses"  # field/variable type dependency
    CONTAINS = "contains"  # parent → child (class → method, file → class)
    ANNOTATED_BY = "annotated_by"


# ── Metrics ───────────────────────────────────────────────────────────────────


@dataclass
class Metrics:
    """Code-quality metrics attached to any node."""

    loc: int = 0
    """Lines of code (inclusive of blank lines inside the construct)."""

    cyclomatic_complexity: int = 1
    """McCabe's cyclomatic complexity (1 = no branches)."""

    num_methods: int = 0
    """Number of methods / functions directly inside this node."""

    num_fields: int = 0
    """Number of fields / attributes directly inside this node."""

    num_parameters: int = 0
    """Parameter count (for function/method nodes)."""

    depth: int = 0
    """Nesting depth of the node in the AST (0 = top-level)."""


# ── Node ──────────────────────────────────────────────────────────────────────


@dataclass
class Node:
    """A vertex in the architecture graph."""

    id: str
    """Globally unique identifier.
    Conventions:
      - File:      ``file:<relative/path.java>``
      - Package:   ``pkg:com.example.web``
      - Class/Interface/Enum: ``<fqn>``  e.g. ``com.example.web.UserController``
      - Method:    ``<class_fqn>#<method_name>``
      - Function:  ``<module>.<function_name>``
      - External:  ``ext:<import_path>``
    """

    type: NodeType
    name: str
    """Short unqualified name (e.g. ``UserController``, ``run``)."""

    path: str
    """Relative file path from the repository root."""

    language: str
    """``'java'`` or ``'python'``."""

    metrics: Metrics = field(default_factory=Metrics)
    is_external: bool = False
    annotations: list[str] = field(default_factory=list)
    """Decoration / annotation names (e.g. ``['Override', 'Transactional']``)."""

    extra: dict[str, Any] = field(default_factory=dict)
    """Arbitrary language-specific extras (e.g. return type, access modifier)."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": str(self.type),
            "name": self.name,
            "path": self.path,
            "language": self.language,
            "is_external": self.is_external,
            "annotations": self.annotations,
            "metrics": {
                "loc": self.metrics.loc,
                "cyclomatic_complexity": self.metrics.cyclomatic_complexity,
                "num_methods": self.metrics.num_methods,
                "num_fields": self.metrics.num_fields,
                "num_parameters": self.metrics.num_parameters,
                "depth": self.metrics.depth,
            },
            **self.extra,
        }


# ── Edge ──────────────────────────────────────────────────────────────────────


@dataclass
class Edge:
    """A directed relationship between two nodes."""

    source: str
    target: str
    type: EdgeType
    resolved: bool = True
    """True if *target* refers to an internal node; False if external/unknown."""

    confidence: str = "resolved"
    """'resolved' | 'parsed' | 'ai_inferred'."""

    line: int | None = None
    """Source line where the relationship was detected."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": str(self.type),
            "resolved": self.resolved,
            "confidence": self.confidence,
            "line": self.line,
        }


# ── Per-file parse result ─────────────────────────────────────────────────────


@dataclass
class ParseResult:
    """Output of parsing a single file."""

    file_path: str
    """Relative path from repo root."""

    language: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    """Non-fatal parse warnings / syntax errors for this file."""

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


# ── Repository-level result ───────────────────────────────────────────────────


@dataclass
class RepositoryParseResult:
    """Aggregated result for an entire repository."""

    repo_id: str
    source: str
    """Original source path / URL."""

    language: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    file_results: list[ParseResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    files_parsed: int = 0
    files_skipped: int = 0
    source_fingerprint: str = ""
    commit_sha: str | None = None
    parser_version: str = "1.0.0"
    settings_hash: str = ""
    truncated: bool = False
    truncated_counts: dict[str, int] = field(default_factory=dict)
    random_seed: int = 42

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def summary(self) -> str:
        return (
            f"Repo: {self.source}\n"
            f"  Language : {self.language}\n"
            f"  Files    : {self.files_parsed} parsed, {self.files_skipped} skipped\n"
            f"  Nodes    : {self.node_count}\n"
            f"  Edges    : {self.edge_count}\n"
            f"  Errors   : {self.error_count}\n"
            f"  Duration : {self.duration_ms:.0f} ms"
        )


# ── WebSocket progress ────────────────────────────────────────────────────────


@dataclass
class ProgressUpdate:
    """Streamed over WebSocket during parallel parsing."""

    type: str = "progress"
    current: int = 0
    total: int = 0
    percent: float = 0.0
    file: str = ""
    nodes_so_far: int = 0
    edges_so_far: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "current": self.current,
            "total": self.total,
            "percent": round(self.percent, 1),
            "file": self.file,
            "nodes_so_far": self.nodes_so_far,
            "edges_so_far": self.edges_so_far,
            "message": self.message,
        }
