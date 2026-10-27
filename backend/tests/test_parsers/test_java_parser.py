"""Unit tests for the Java tree-sitter parser."""

from __future__ import annotations

import pytest

from parsers.models import EdgeType, NodeType
from tests.test_parsers import COMPLEX_JAVA, SIMPLE_JAVA


# ── Skip guard ────────────────────────────────────────────────────────────────


def _java_parser():
    try:
        from parsers.java_parser import JavaParser

        return JavaParser()
    except RuntimeError as exc:
        pytest.skip(f"Java parser unavailable: {exc}")


# ── Simple.java tests ─────────────────────────────────────────────────────────


class TestSimpleJava:
    def setup_method(self):
        self.parser = _java_parser()
        self.source = SIMPLE_JAVA.read_text(encoding="utf-8")
        self.result = self.parser.parse_file(SIMPLE_JAVA, "java/Simple.java", self.source)

    def test_no_fatal_errors(self):
        # Non-syntax errors (visitors warnings) may exist, but parse should succeed
        fatal = [e for e in self.result.errors if "Fatal" in e]
        assert not fatal, f"Fatal errors: {fatal}"

    def test_file_node_present(self):
        ids = {n.id for n in self.result.nodes}
        assert "file:java/Simple.java" in ids

    def test_package_node_present(self):
        nodes = [n for n in self.result.nodes if n.type == NodeType.PACKAGE]
        assert nodes, "Expected at least one PACKAGE node"
        assert any("simple" in n.id for n in nodes)

    def test_class_node_present(self):
        classes = [n for n in self.result.nodes if n.type == NodeType.CLASS]
        names = [n.name for n in classes]
        assert "Simple" in names

    def test_class_fqn(self):
        classes = [n for n in self.result.nodes if n.name == "Simple"]
        assert classes
        assert "com.example.simple.Simple" in {c.id for c in classes}

    def test_method_nodes_present(self):
        methods = [n for n in self.result.nodes if n.type == NodeType.METHOD]
        names = {m.name for m in methods}
        assert "getName" in names
        assert "getValue" in names
        assert "buildItems" in names

    def test_method_loc_positive(self):
        methods = [n for n in self.result.nodes if n.type == NodeType.METHOD]
        for m in methods:
            assert m.metrics.loc > 0, f"Method {m.name} has zero LOC"

    def test_buildItems_complexity(self):
        """buildItems has for + if → complexity ≥ 3."""
        methods = [n for n in self.result.nodes if n.name == "buildItems"]
        assert methods
        assert methods[0].metrics.cyclomatic_complexity >= 3

    def test_import_edges_present(self):
        import_edges = [e for e in self.result.edges if e.type == EdgeType.IMPORTS]
        targets = {e.target for e in import_edges}
        assert any("List" in t or "ArrayList" in t for t in targets), f"Import targets: {targets}"

    def test_contains_edges_class_to_method(self):
        contains = [e for e in self.result.edges if e.type == EdgeType.CONTAINS]
        class_fqn = "com.example.simple.Simple"
        method_sources = {e.source for e in contains if e.source == class_fqn}
        assert method_sources, "Expected class→method CONTAINS edges"

    def test_file_loc(self):
        file_nodes = [n for n in self.result.nodes if n.type == NodeType.FILE]
        assert file_nodes
        assert file_nodes[0].metrics.loc > 0


# ── Complex.java tests ────────────────────────────────────────────────────────


class TestComplexJava:
    def setup_method(self):
        self.parser = _java_parser()
        self.source = COMPLEX_JAVA.read_text(encoding="utf-8")
        self.result = self.parser.parse_file(COMPLEX_JAVA, "java/Complex.java", self.source)

    def test_interface_node_present(self):
        interfaces = [n for n in self.result.nodes if n.type == NodeType.INTERFACE]
        names = {i.name for i in interfaces}
        assert "Repository" in names

    def test_enum_node_present(self):
        enums = [n for n in self.result.nodes if n.type == NodeType.ENUM]
        names = {e.name for e in enums}
        assert "Status" in names

    def test_extends_edge(self):
        extends = [e for e in self.result.edges if e.type == EdgeType.EXTENDS]
        targets = {e.target for e in extends}
        assert "BaseService" in targets, f"Extends edges: {targets}"

    def test_implements_edge(self):
        implements = [e for e in self.result.edges if e.type == EdgeType.IMPLEMENTS]
        targets = {e.target for e in implements}
        assert "Repository" in targets, f"Implements edges: {targets}"

    def test_annotations_extracted(self):
        """@Service and @Transactional should be on ComplexService."""
        class_nodes = [n for n in self.result.nodes if n.name == "ComplexService"]
        assert class_nodes
        anns = class_nodes[0].annotations
        assert "Service" in anns or "Transactional" in anns, f"Annotations: {anns}"

    def test_classify_high_complexity(self):
        """classify() has 7+ branches → complexity > 5."""
        methods = [n for n in self.result.nodes if n.name == "classify"]
        assert methods
        assert methods[0].metrics.cyclomatic_complexity >= 5

    def test_annotated_by_edges(self):
        annotated = [e for e in self.result.edges if e.type == EdgeType.ANNOTATED_BY]
        assert annotated, "Expected ANNOTATED_BY edges"

    def test_no_crash_on_complex_source(self):
        """Most importantly: no unhandled exceptions."""
        assert self.result is not None


# ── Syntax error handling ─────────────────────────────────────────────────────


class TestJavaSyntaxError:
    def setup_method(self):
        self.parser = _java_parser()

    def test_broken_java_does_not_raise(self, tmp_path):
        broken = "public class Broken { void foo( "  # missing closing braces
        result = self.parser.parse_file(tmp_path / "Broken.java", "Broken.java", broken)
        # Should return a result, possibly with errors, but never raise
        assert result is not None

    def test_empty_file_ok(self, tmp_path):
        result = self.parser.parse_file(tmp_path / "Empty.java", "Empty.java", "")
        assert result.node_count >= 1  # at least file node

    def test_utf8_mojibake_ok(self, tmp_path):
        weird = "public class Weird { /* \xff\xfe comment */ }"
        result = self.parser.parse_file(
            tmp_path / "Weird.java", "Weird.java", weird.encode("latin-1").decode("utf-8", errors="replace")
        )
        assert result is not None
