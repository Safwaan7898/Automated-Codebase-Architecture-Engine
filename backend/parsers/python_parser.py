"""Tree-sitter based Python parser.

Extracts:
  - Modules (one node per file) → :attr:`NodeType.MODULE`
  - Imports (absolute and relative) → :attr:`EdgeType.IMPORTS`
  - Classes with bases → :attr:`NodeType.CLASS` + :attr:`EdgeType.EXTENDS`
  - Functions / methods → :attr:`NodeType.FUNCTION` / :attr:`NodeType.METHOD`
  - Call sites → :attr:`EdgeType.CALLS`
  - Decorators → :attr:`EdgeType.ANNOTATED_BY`
  - Cyclomatic complexity and LOC per function/method
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from parsers.base import LanguageParser
from parsers.models import Edge, EdgeType, Metrics, Node, NodeType, ParseResult

logger = logging.getLogger(__name__)

# ── tree-sitter setup ─────────────────────────────────────────────────────────

try:
    import tree_sitter_python as _tspy
    from tree_sitter import Language

    _PY_LANGUAGE = Language(_tspy.language())
    _TS_AVAILABLE = True
except Exception as _ts_err:  # noqa: BLE001
    logger.warning("tree-sitter-python not available: %s — Python parser will produce empty results", _ts_err)
    _TS_AVAILABLE = False
    _PY_LANGUAGE = None  # type: ignore[assignment]

# ── McCabe complexity node types (Python grammar) ─────────────────────────────

_PY_BRANCH_TYPES: frozenset[str] = frozenset(
    {
        "if_statement",
        "elif_clause",
        "while_statement",
        "for_statement",
        "except_clause",
        "with_statement",
        "conditional_expression",  # `x if y else z`
        "case_clause",  # match / case (Python 3.10+)
    }
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _text(node: Any) -> str:
    if node is None:
        return ""
    raw = getattr(node, "text", None)
    if raw is None:
        return ""
    return raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)


def _field(node: Any, field_name: str) -> Any:
    try:
        return node.child_by_field_name(field_name)
    except Exception:  # noqa: BLE001
        return None


def _find_first(node: Any, *types: str) -> Any | None:
    for child in node.children or []:
        if child.type in types:
            return child
    return None


def _children_by_type(node: Any, *types: str) -> list[Any]:
    return [c for c in (node.children or []) if c.type in types]


def _iter_tree(node: Any):
    yield node
    for child in node.children or []:
        yield from _iter_tree(child)


def _count_complexity(node: Any) -> int:
    """Count McCabe complexity contributions in a Python AST subtree."""
    count = 0
    for n in _iter_tree(node):
        if n.type in _PY_BRANCH_TYPES:
            count += 1
        elif n.type == "boolean_operator":
            # `and` / `or` each add 1
            op = _field(n, "operator") or _find_first(n, "and", "or")
            op_text = _text(op).strip()
            if op_text in ("and", "or"):
                count += 1
    return count


def _module_id_from_path(rel_path: str) -> str:
    """Convert a relative file path to a dotted module id.

    Examples:
        ``flask/app.py``       → ``flask.app``
        ``__init__.py``        → ``__init__``
        ``src/utils/__init__.py`` → ``src.utils``
    """
    parts = rel_path.replace("\\", "/").split("/")
    if parts and parts[-1].endswith(".py"):
        stem = parts[-1][:-3]
        if stem == "__init__":
            parts = parts[:-1]
        else:
            parts[-1] = stem
    return ".".join(parts) if parts else rel_path


def _resolve_relative_import(current_module: str, level: int, module: str) -> str:
    """Resolve a relative import ``from . import X`` → absolute module id."""
    parts = current_module.split(".")
    # Go up `level` package levels
    base_parts = parts[: max(0, len(parts) - level)]
    if module:
        return ".".join([*base_parts, module]) if base_parts else module
    return ".".join(base_parts) if base_parts else ""


# ── Python AST Visitor ────────────────────────────────────────────────────────


class _PythonVisitor:
    """Stateful visitor that walks a tree-sitter Python parse tree."""

    def __init__(self, rel_path: str, module_id: str) -> None:
        self.rel_path = rel_path
        self.module_id = module_id
        self.nodes: list[Node] = []
        self.edges: list[Edge] = []
        self.errors: list[str] = []

        self._class_stack: list[str] = []  # dotted FQNs of enclosing classes

    # ── Entry point ───────────────────────────────────────────────────────────

    def visit_module(self, root: Any) -> None:
        """Walk the top-level module node."""
        for child in root.children or []:
            self._dispatch_top_level(child)

    def _dispatch_top_level(self, node: Any) -> None:
        t = node.type
        if t == "import_statement":
            self._visit_import(node)
        elif t == "import_from_statement":
            self._visit_import_from(node)
        elif t == "class_definition":
            self._visit_class(node)
        elif t == "function_definition":
            self._visit_function(node, parent_id=self.module_id)
        elif t == "decorated_definition":
            self._visit_decorated(node, parent_id=self.module_id)
        elif t == "expression_statement":
            pass  # skip top-level assignments for now
        elif t in ("if_statement", "while_statement", "for_statement", "try_statement", "with_statement"):
            # Recurse into block-level nodes for nested defs
            for child in node.children or []:
                self._dispatch_top_level(child)

    # ── Imports ───────────────────────────────────────────────────────────────

    def _visit_import(self, node: Any) -> None:
        """``import X, Y as Z``"""
        for child in node.children or []:
            if child.type == "dotted_name":
                mod_name = _text(child)
                self.edges.append(
                    Edge(
                        source=self.module_id,
                        target=mod_name,
                        type=EdgeType.IMPORTS,
                        resolved=False,
                        line=node.start_point[0] + 1,
                    )
                )
            elif child.type == "aliased_import":
                # `import X as Y` — the aliased_import has a dotted_name child
                dn = _find_first(child, "dotted_name")
                if dn:
                    self.edges.append(
                        Edge(
                            source=self.module_id,
                            target=_text(dn),
                            type=EdgeType.IMPORTS,
                            resolved=False,
                            line=node.start_point[0] + 1,
                        )
                    )

    def _visit_import_from(self, node: Any) -> None:
        """``from [.+]X import Y, Z``"""
        # Count leading dots (relative import level)
        level = 0
        module_part = ""
        for child in node.children or []:
            if child.type == "import_prefix":
                level = len(_text(child))  # number of dots
            elif child.type in ("dotted_name", "relative_import"):
                module_part = _text(child)

        # Determine base module
        if level > 0:
            base = _resolve_relative_import(self.module_id, level, module_part)
        else:
            base = module_part

        if base:
            self.edges.append(
                Edge(
                    source=self.module_id,
                    target=base,
                    type=EdgeType.IMPORTS,
                    resolved=False,
                    line=node.start_point[0] + 1,
                )
            )

    # ── Class ─────────────────────────────────────────────────────────────────

    def _visit_class(
        self,
        node: Any,
        parent_id: str | None = None,
        decorators: list[str] | None = None,
    ) -> None:
        name_node = _field(node, "name") or _find_first(node, "identifier")
        if not name_node:
            return
        short_name = _text(name_node)

        # Build FQN
        if self._class_stack:
            fqn = f"{self._class_stack[-1]}.{short_name}"
        else:
            fqn = f"{self.module_id}.{short_name}"

        annotations = decorators or []

        # LOC
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        loc = end_line - start_line + 1

        class_node = Node(
            id=fqn,
            type=NodeType.CLASS,
            name=short_name,
            path=self.rel_path,
            language="python",
            metrics=Metrics(loc=loc),
            annotations=annotations,
        )
        self.nodes.append(class_node)

        # Module → class containment
        source_id = parent_id or self.module_id
        self.edges.append(Edge(source=source_id, target=fqn, type=EdgeType.CONTAINS, resolved=True))

        # Decorator edges
        for ann in annotations:
            self.edges.append(Edge(source=fqn, target=ann, type=EdgeType.ANNOTATED_BY, resolved=False))

        # Base classes (extends)
        args_node = _field(node, "superclasses") or _find_first(node, "argument_list")
        if args_node:
            for base_child in args_node.children or []:
                if base_child.type in ("identifier", "attribute"):
                    base_name = _text(base_child)
                    self.edges.append(Edge(source=fqn, target=base_name, type=EdgeType.EXTENDS, resolved=False))

        # Visit class body
        body = _field(node, "body")
        if body:
            self._class_stack.append(fqn)
            method_count = 0
            for member in body.children or []:
                mt = member.type
                if mt == "function_definition":
                    method_count += 1
                    self._visit_function(member, parent_id=fqn)
                elif mt == "decorated_definition":
                    method_count += 1
                    self._visit_decorated(member, parent_id=fqn)
                elif mt == "class_definition":
                    self._visit_class(member, parent_id=fqn)
            class_node.metrics.num_methods = method_count
            self._class_stack.pop()

    # ── Function / method ─────────────────────────────────────────────────────

    def _visit_function(
        self,
        node: Any,
        parent_id: str,
        decorators: list[str] | None = None,
    ) -> None:
        name_node = _field(node, "name") or _find_first(node, "identifier")
        if not name_node:
            return
        short_name = _text(name_node)

        if self._class_stack:
            fqn = f"{self._class_stack[-1]}.{short_name}"
            node_type = NodeType.METHOD
        else:
            fqn = f"{self.module_id}.{short_name}"
            node_type = NodeType.FUNCTION

        annotations = decorators or []

        # LOC
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        loc = end_line - start_line + 1

        # Parameters
        params_node = _field(node, "parameters")
        num_params = 0
        if params_node:
            num_params = sum(
                1
                for c in (params_node.children or [])
                if c.type
                in (
                    "identifier",
                    "typed_parameter",
                    "default_parameter",
                    "typed_default_parameter",
                    "list_splat_pattern",
                    "dictionary_splat_pattern",
                )
            )
            # Subtract 'self' / 'cls' for methods
            if self._class_stack and num_params > 0:
                num_params = max(0, num_params - 1)

        # Complexity
        body = _field(node, "body")
        complexity = 1 + (_count_complexity(body) if body else 0)

        fn_node = Node(
            id=fqn,
            type=node_type,
            name=short_name,
            path=self.rel_path,
            language="python",
            metrics=Metrics(
                loc=loc,
                cyclomatic_complexity=complexity,
                num_parameters=num_params,
            ),
            annotations=annotations,
        )
        self.nodes.append(fn_node)

        # Parent → function containment
        self.edges.append(Edge(source=parent_id, target=fqn, type=EdgeType.CONTAINS, resolved=True))

        # Decorator edges
        for ann in annotations:
            self.edges.append(Edge(source=fqn, target=ann, type=EdgeType.ANNOTATED_BY, resolved=False))

        # Call sites inside the body
        if body:
            self._extract_calls(body, fqn)

        # Nested functions / classes
        if body:
            for child in body.children or []:
                if child.type == "function_definition":
                    self._visit_function(child, parent_id=fqn)
                elif child.type == "class_definition":
                    self._visit_class(child, parent_id=fqn)
                elif child.type == "decorated_definition":
                    self._visit_decorated(child, parent_id=fqn)

    # ── Decorated definitions ─────────────────────────────────────────────────

    def _visit_decorated(self, node: Any, parent_id: str) -> None:
        """Handle ``@decorator\ndef/class ...``"""
        decorators: list[str] = []
        inner: Any = None

        for child in node.children or []:
            if child.type == "decorator":
                # decorator body is the child after '@'
                dec_name = ""
                for dc in child.children or []:
                    if dc.type in ("identifier", "attribute", "call"):
                        # strip call args — keep only the name
                        if dc.type == "call":
                            fn = _field(dc, "function") or _find_first(dc, "identifier", "attribute")
                            dec_name = _text(fn) if fn else _text(dc)
                        else:
                            dec_name = _text(dc)
                        break
                if dec_name:
                    decorators.append(dec_name)
            elif child.type == "function_definition":
                inner = ("function", child)
            elif child.type == "class_definition":
                inner = ("class", child)
            elif child.type == "async_function_definition":
                inner = ("function", child)

        if inner is None:
            return
        kind, inner_node = inner
        if kind == "function":
            self._visit_function(inner_node, parent_id=parent_id, decorators=decorators)
        else:
            self._visit_class(inner_node, parent_id=parent_id, decorators=decorators)

    # ── Call extraction ───────────────────────────────────────────────────────

    def _extract_calls(self, body: Any, caller_id: str) -> None:
        """Extract call expressions from a function body subtree."""
        for n in _iter_tree(body):
            if n.type == "call":
                fn_node = _field(n, "function")
                if fn_node is None:
                    continue
                if fn_node.type == "identifier":
                    callee = _text(fn_node)
                    self.edges.append(
                        Edge(
                            source=caller_id,
                            target=callee,
                            type=EdgeType.CALLS,
                            resolved=False,
                            line=n.start_point[0] + 1,
                        )
                    )
                elif fn_node.type == "attribute":
                    attr = _field(fn_node, "attribute") or _find_first(fn_node, "identifier")
                    if attr:
                        self.edges.append(
                            Edge(
                                source=caller_id,
                                target=_text(attr),
                                type=EdgeType.CALLS,
                                resolved=False,
                                line=n.start_point[0] + 1,
                            )
                        )


# ── Public parser class ───────────────────────────────────────────────────────


class PythonParser(LanguageParser):
    """Tree-sitter backed Python parser implementing :class:`LanguageParser`."""

    def __init__(self) -> None:
        if not _TS_AVAILABLE:
            raise RuntimeError("tree-sitter-python is not installed. Run: pip install tree-sitter tree-sitter-python")
        from tree_sitter import Parser as _P

        self._parser: Any = _P(_PY_LANGUAGE)

    @property
    def language(self) -> str:
        return "python"

    @property
    def file_extensions(self) -> frozenset[str]:
        return frozenset({".py", ".pyw"})

    def parse_file(self, abs_path: Path, rel_path: str, source: str) -> ParseResult:
        result = ParseResult(file_path=rel_path, language="python")

        source_lines = source.splitlines()
        module_id = _module_id_from_path(rel_path)

        # Module-level node
        module_node = Node(
            id=module_id,
            type=NodeType.MODULE,
            name=abs_path.stem,
            path=rel_path,
            language="python",
            metrics=Metrics(loc=len(source_lines)),
        )
        result.nodes.append(module_node)

        if not source.strip():
            return result

        try:
            tree = self._parser.parse(source.encode("utf-8", errors="replace"))
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"tree-sitter parse error: {exc}")
            return result

        if tree.root_node.has_error:
            result.errors.append("Python syntax error detected in file; partial results may be incomplete.")

        visitor = _PythonVisitor(rel_path=rel_path, module_id=module_id)
        try:
            visitor.visit_module(tree.root_node)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"Visitor error: {exc}")

        result.nodes.extend(visitor.nodes)
        result.edges.extend(visitor.edges)
        result.errors.extend(visitor.errors)

        return result
