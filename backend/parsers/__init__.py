"""
ArchLens parser layer — public re-exports.

Usage:
    from parsers import parse_repository, IngestionConfig, Node, Edge, NodeType, EdgeType
"""

from parsers.config import IngestionConfig
from parsers.models import (
    Edge,
    EdgeType,
    Metrics,
    Node,
    NodeType,
    ParseResult,
    ProgressUpdate,
    RepositoryParseResult,
)
from parsers.parallel_runner import parse_repository

__all__ = [
    "Edge",
    "EdgeType",
    "IngestionConfig",
    "Metrics",
    "Node",
    "NodeType",
    "ParseResult",
    "ProgressUpdate",
    "RepositoryParseResult",
    "parse_repository",
]
