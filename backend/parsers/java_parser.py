"""Tree-sitter based Java parser.

Extracts:
  - Package declarations → :attr:`NodeType.PACKAGE`
  - Classes / interfaces / enums → :attr:`NodeType.CLASS` / :attr:`NodeType.INTERFACE` / :attr:`NodeType.ENUM`
  - Methods and constructors → :attr:`NodeType.METHOD`
  - Import statements → :attr:`EdgeType.IMPORTS`
  - Inheritance (extends) → :attr:`EdgeType.EXTENDS`
  - Interface implementation → :attr:`EdgeType.IMPLEMENTS`
  - Method call sites → :attr:`EdgeType.CALLS`
  - Field types → :attr:`EdgeType.USES`
  - Annotations → :attr:`EdgeType.ANNOTATED_BY`
  - Cyclomatic complexity and LOC per method
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
    import tree_sitter_java as _tsjava
    from tree_sitter import Language

    _JAVA_LANGUAGE = Language(_tsjava.language())
    _TS_AVAILABLE = True
except Exception as _ts_err:  # noqa: BLE001
    logger.warning("tree-sitter-java not available: %s — Java parser will produce empty results", _ts_err)
    _TS_AVAILABLE = False
    _JAVA_LANGUAGE = None  # type: ignore[assignment]

# ── McCabe complexity node types (Java grammar) ───────────────────────────────

_JAVA_BRANCH_TYPES: frozenset[str] = frozenset(
    {
        "if_statement",
        "while_statement",
        "for_statement",
        "enhanced_for_statement",
        "do_statement",
        "catch_clause",
        "conditional_expression",  # ternary
        "assert_statement",
    }
)

# ── Helper functions ──────────────────────────────────────────────────────────


def _text(node: Any) -> str:
    """Safely decode node.text bytes to str."""
    if node is None:
        return ""
    raw = getattr(node, "text", None)
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)


def _field(node: Any, field_name: str) -> Any:
    """Return named field or None."""
    try:
        return node.child_by_field_name(field_name)
    except Exception:  # noqa: BLE001
        return None


def _children_of_type(node: Any, *types: str) -> list[Any]:
    return [c for c in (node.children or []) if c.type in types]


def _find_first(node: Any, *types: str) -> Any | None:
    for child in node.children or []:
        if child.type in types:
            return child
    return None


def _iter_tree(node: Any):
    """Depth-first generator over all nodes in a subtree."""
    yield node
    for child in node.children or []:
        yield from _iter_tree(child)


def _count_complexity(node: Any) -> int:
    """Count McCabe complexity contributors in *node*'s subtree."""
    count = 0
    for n in _iter_tree(node):
        if n.type in _JAVA_BRANCH_TYPES:
            count += 1
        elif n.type == "switch_label":
            # Count 'case X:' but not 'default:'
            first = n.children[0] if n.children else None
            if first and _text(first).strip() == "case":
                count += 1
        elif n.type == "binary_expression":
            op = _field(n, "operator")
            if _text(op) in ("&&", "||"):
                count += 1
    return count


def _extract_annotations(modifiers_node: Any) -> list[str]:
    """Pull annotation names from a modifiers node."""
    if modifiers_node is None:
        return []
    result: list[str] = []
    for child in modifiers_node.children or []:
        if child.type in ("marker_annotation", "annotation"):
            name_node = _field(child, "name") or _find_first(child, "identifier")
            if name_node:
                result.append(_text(name_node))
    return result


def _scoped_name(node: Any) -> str:
    """Extract a potentially dotted name from scoped_identifier or identifier."""
    if node is None:
        return ""
    if node.type == "identifier":
        return _text(node)
    # scoped_identifier has 'scope' and 'name' fields
    scope = _field(node, "scope")
    name = _field(node, "name")
    if scope and name:
        return f"{_scoped_name(scope)}.{_text(name)}"
    return _text(node)


# ── Java AST Visitor ─────────────────────────────────────────────────────────


class _JavaVisitor:
    """Stateful visitor that walks a tree-sitter Java parse tree."""

    def __init__(self, rel_path: str, source_lines: list[str]) -> None:
        self.rel_path = rel_path
        self.source_lines = source_lines
        self.nodes: list[Node] = []
        self.edges: list[Edge] = []
        self.errors: list[str] = []

        self._package: str = ""
        self._imports: list[tuple[str, int]] = []  # (fqn, line)
        self._class_stack: list[str] = []  # FQNs of enclosing classes

    # ── Entry point ───────────────────────────────────────────────────────────

    def visit(self, root_node: Any) -> None:
        """Walk the compilation unit root."""
        for child in root_node.children or []:
            t = child.type
            if t == "package_declaration":
                self._visit_package(child)
            elif t == "import_declaration":
                self._visit_import(child)
            elif t == "class_declaration":
                self._visit_class(child)
            elif t == "interface_declaration":
                self._visit_interface(child)
            elif t == "enum_declaration":
                self._visit_enum(child)
            # top-level annotated declarations (Java 16+)
            elif t == "record_declaration":
                self._visit_class(child)  # treat records like classes

    # ── Package ───────────────────────────────────────────────────────────────

    def _visit_package(self, node: Any) -> None:
        name_node = _find_first(node, "scoped_identifier", "identifier")
        self._package = _scoped_name(name_node) if name_node else ""
        if self._package:
            self.nodes.append(
                Node(
                    id=f"pkg:{self._package}",
                    type=NodeType.PACKAGE,
                    name=self._package.split(".")[-1],
                    path=self.rel_path,
                    language="java",
                    metrics=Metrics(loc=0),
                )
            )

    # ── Imports ───────────────────────────────────────────────────────────────

    def _visit_import(self, node: Any) -> None:
        name_node = _find_first(node, "scoped_identifier", "identifier")
        fqn = _scoped_name(name_node) if name_node else ""
        if fqn:
            line = node.start_point[0] + 1
            self._imports.append((fqn, line))

    # ── Class ─────────────────────────────────────────────────────────────────

    def _visit_class(self, node: Any, parent_fqn: str | None = None) -> None:
        name_node = _field(node, "name") or _find_first(node, "identifier")
        if not name_node:
            return
        short_name = _text(name_node)

        # Determine FQN
        if parent_fqn:
            fqn = f"{parent_fqn}.{short_name}"
        elif self._package:
            fqn = f"{self._package}.{short_name}"
        else:
            fqn = short_name

        # Annotations
        mods = _find_first(node, "modifiers")
        annotations = _extract_annotations(mods)

        # LOC
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        loc = end_line - start_line + 1

        class_node = Node(
            id=fqn,
            type=NodeType.CLASS,
            name=short_name,
            path=self.rel_path,
            language="java",
            metrics=Metrics(loc=loc),
            annotations=annotations,
        )
        self.nodes.append(class_node)

        # File → class containment
        self.edges.append(Edge(source=f"file:{self.rel_path}", target=fqn, type=EdgeType.CONTAINS, resolved=True))

        # Annotation edges
        for ann in annotations:
            self.edges.append(Edge(source=fqn, target=ann, type=EdgeType.ANNOTATED_BY, resolved=False))

        # superclass (extends)
        superclass = _field(node, "superclass")
        if superclass:
            for sc_child in _iter_tree(superclass):
                if sc_child.type == "type_identifier":
                    sc_name = _text(sc_child)
                    self.edges.append(Edge(source=fqn, target=sc_name, type=EdgeType.EXTENDS, resolved=False))
                    break

        # interfaces (implements)
        interfaces_node = _field(node, "interfaces") or _find_first(node, "super_interfaces")
        if interfaces_node:
            for ifc_child in _iter_tree(interfaces_node):
                if ifc_child.type == "type_identifier":
                    self.edges.append(
                        Edge(source=fqn, target=_text(ifc_child), type=EdgeType.IMPLEMENTS, resolved=False)
                    )

        # Visit class body
        body = _field(node, "body") or _find_first(node, "class_body")
        if body:
            self._class_stack.append(fqn)
            self._visit_class_body(body, fqn)
            self._class_stack.pop()

        # Emit import edges now that we have the class FQN as source
        for imp_fqn, imp_line in self._imports:
            self.edges.append(Edge(source=fqn, target=imp_fqn, type=EdgeType.IMPORTS, resolved=False, line=imp_line))

    # ── Class body ────────────────────────────────────────────────────────────

    def _visit_class_body(self, body: Any, class_fqn: str) -> None:
        field_count = 0
        method_count = 0

        for member in body.children or []:
            t = member.type
            if t == "field_declaration":
                field_count += 1
                self._visit_field(member, class_fqn)
            elif t in ("method_declaration", "constructor_declaration"):
                method_count += 1
                self._visit_method(member, class_fqn)
            elif t == "class_declaration":
                self._visit_class(member, parent_fqn=class_fqn)
            elif t == "interface_declaration":
                self._visit_interface(member, parent_fqn=class_fqn)
            elif t == "enum_declaration":
                self._visit_enum(member, parent_fqn=class_fqn)

        # Update metrics on the class node
        for n in self.nodes:
            if n.id == class_fqn:
                n.metrics.num_fields = field_count
                n.metrics.num_methods = method_count
                break

    # ── Field ─────────────────────────────────────────────────────────────────

    def _visit_field(self, node: Any, class_fqn: str) -> None:
        type_node = _field(node, "type")
        if type_node is None:
            return
        # Collect all type_identifier children (generics may have multiple)
        for type_child in _iter_tree(type_node):
            if type_child.type == "type_identifier":
                type_name = _text(type_child)
                self.edges.append(Edge(source=class_fqn, target=type_name, type=EdgeType.USES, resolved=False))

    # ── Method ────────────────────────────────────────────────────────────────

    def _visit_method(self, node: Any, class_fqn: str) -> None:
        is_ctor = node.type == "constructor_declaration"
        name_node = _field(node, "name") or _find_first(node, "identifier")
        if not name_node:
            return
        method_name = _text(name_node)
        method_id = f"{class_fqn}#{method_name}"

        # Annotations
        mods = _find_first(node, "modifiers")
        annotations = _extract_annotations(mods)

        # LOC
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        loc = end_line - start_line + 1

        # Parameters
        params_node = _field(node, "parameters") or _find_first(node, "formal_parameters")
        num_params = 0
        if params_node:
            num_params = len([c for c in (params_node.children or []) if c.type == "formal_parameter"])

        # Cyclomatic complexity
        body = _field(node, "body") or _find_first(node, "block")
        complexity = 1 + (_count_complexity(body) if body else 0)

        self.nodes.append(
            Node(
                id=method_id,
                type=NodeType.METHOD,
                name=method_name,
                path=self.rel_path,
                language="java",
                metrics=Metrics(loc=loc, cyclomatic_complexity=complexity, num_parameters=num_params),
                annotations=annotations,
                extra={"is_constructor": is_ctor},
            )
        )
        self.edges.append(Edge(source=class_fqn, target=method_id, type=EdgeType.CONTAINS, resolved=True))

        # Annotation edges
        for ann in annotations:
            self.edges.append(Edge(source=method_id, target=ann, type=EdgeType.ANNOTATED_BY, resolved=False))

        # Call sites inside the method body
        if body:
            self._extract_calls(body, method_id)

    # ── Interface ─────────────────────────────────────────────────────────────

    def _visit_interface(self, node: Any, parent_fqn: str | None = None) -> None:
        name_node = _field(node, "name") or _find_first(node, "identifier")
        if not name_node:
            return
        short_name = _text(name_node)
        if parent_fqn:
            fqn = f"{parent_fqn}.{short_name}"
        elif self._package:
            fqn = f"{self._package}.{short_name}"
        else:
            fqn = short_name

        mods = _find_first(node, "modifiers")
        annotations = _extract_annotations(mods)
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1

        self.nodes.append(
            Node(
                id=fqn,
                type=NodeType.INTERFACE,
                name=short_name,
                path=self.rel_path,
                language="java",
                metrics=Metrics(loc=end_line - start_line + 1),
                annotations=annotations,
            )
        )
        self.edges.append(Edge(source=f"file:{self.rel_path}", target=fqn, type=EdgeType.CONTAINS, resolved=True))

        # extends (interface extension)
        extends_node = _field(node, "extends_interfaces") or _find_first(node, "extends_interfaces")
        if extends_node:
            for ec in _iter_tree(extends_node):
                if ec.type == "type_identifier":
                    self.edges.append(Edge(source=fqn, target=_text(ec), type=EdgeType.EXTENDS, resolved=False))

        # Interface body → method signatures
        body = _field(node, "body") or _find_first(node, "interface_body")
        if body:
            method_count = 0
            for member in body.children or []:
                if member.type in ("method_declaration", "interface_method_declaration"):
                    method_count += 1
                    self._visit_method(member, fqn)
            for n in self.nodes:
                if n.id == fqn:
                    n.metrics.num_methods = method_count
                    break

        for imp_fqn, imp_line in self._imports:
            self.edges.append(Edge(source=fqn, target=imp_fqn, type=EdgeType.IMPORTS, resolved=False, line=imp_line))

    # ── Enum ──────────────────────────────────────────────────────────────────

    def _visit_enum(self, node: Any, parent_fqn: str | None = None) -> None:
        name_node = _field(node, "name") or _find_first(node, "identifier")
        if not name_node:
            return
        short_name = _text(name_node)
        if parent_fqn:
            fqn = f"{parent_fqn}.{short_name}"
        elif self._package:
            fqn = f"{self._package}.{short_name}"
        else:
            fqn = short_name

        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1

        self.nodes.append(
            Node(
                id=fqn,
                type=NodeType.ENUM,
                name=short_name,
                path=self.rel_path,
                language="java",
                metrics=Metrics(loc=end_line - start_line + 1),
            )
        )
        self.edges.append(Edge(source=f"file:{self.rel_path}", target=fqn, type=EdgeType.CONTAINS, resolved=True))
        for imp_fqn, imp_line in self._imports:
            self.edges.append(Edge(source=fqn, target=imp_fqn, type=EdgeType.IMPORTS, resolved=False, line=imp_line))

    # ── Call extraction ───────────────────────────────────────────────────────

    def _extract_calls(self, body: Any, caller_id: str) -> None:
        for n in _iter_tree(body):
            if n.type == "method_invocation":
                name_node = _field(n, "name") or _find_first(n, "identifier")
                if name_node:
                    callee = _text(name_node)
                    self.edges.append(
                        Edge(
                            source=caller_id,
                            target=callee,
                            type=EdgeType.CALLS,
                            resolved=False,
                            line=n.start_point[0] + 1,
                        )
                    )
            elif n.type == "object_creation_expression":
                type_node = _field(n, "type") or _find_first(n, "type_identifier")
                if type_node and type_node.type == "type_identifier":
                    self.edges.append(
                        Edge(
                            source=caller_id,
                            target=_text(type_node),
                            type=EdgeType.CALLS,
                            resolved=False,
                            line=n.start_point[0] + 1,
                        )
                    )


# ── Public parser class ───────────────────────────────────────────────────────


class JavaParser(LanguageParser):
    """Tree-sitter backed Java parser implementing :class:`LanguageParser`."""

    def __init__(self) -> None:
        if not _TS_AVAILABLE:
            raise RuntimeError("tree-sitter-java is not installed. Run: pip install tree-sitter tree-sitter-java")
        from tree_sitter import Parser as _P

        self._parser: Any = _P(_JAVA_LANGUAGE)

    @property
    def language(self) -> str:
        return "java"

    @property
    def file_extensions(self) -> frozenset[str]:
        return frozenset({".java"})

    def parse_file(self, abs_path: Path, rel_path: str, source: str) -> ParseResult:
        result = ParseResult(file_path=rel_path, language="java")

        # Add file-level node
        source_lines = source.splitlines()
        file_node = Node(
            id=f"file:{rel_path}",
            type=NodeType.FILE,
            name=abs_path.name,
            path=rel_path,
            language="java",
            metrics=Metrics(loc=len(source_lines)),
        )
        result.nodes.append(file_node)

        if not source.strip():
            return result

        try:
            tree = self._parser.parse(source.encode("utf-8", errors="replace"))
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"tree-sitter parse error: {exc}")
            return result

        if tree.root_node.has_error:
            # Still try to extract what we can — do not abort
            result.errors.append("Java syntax error detected in file; partial results may be incomplete.")

        visitor = _JavaVisitor(rel_path=rel_path, source_lines=source_lines)
        try:
            visitor.visit(tree.root_node)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"Visitor error: {exc}")

        result.nodes.extend(visitor.nodes)
        result.edges.extend(visitor.edges)
        result.errors.extend(visitor.errors)

        return result
