"""Unit tests for the Python and Java analyzers."""

from __future__ import annotations

from pathlib import Path

from app.analyzers.java_analyzer import JavaAnalyzer
from app.analyzers.python_analyzer import PythonAnalyzer
from app.models.refactor import SmellType

# ── Python Analyzer Tests ─────────────────────────────────────────────────────


class TestPythonAnalyzer:
    def setup_method(self) -> None:
        self.analyzer = PythonAnalyzer()

    def test_language_property(self) -> None:
        assert self.analyzer.language == "python"

    def test_can_handle_py_dir(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("x = 1")
        assert self.analyzer.can_handle(tmp_path) is True

    def test_cannot_handle_empty_dir(self, tmp_path: Path) -> None:
        assert self.analyzer.can_handle(tmp_path) is False

    def test_cannot_handle_java_only_dir(self, tmp_path: Path) -> None:
        (tmp_path / "Main.java").write_text("class Main {}")
        assert self.analyzer.can_handle(tmp_path) is False

    def test_analyze_single_file(self, tmp_path: Path) -> None:
        (tmp_path / "hello.py").write_text("import os\nimport sys\n\nx = 1\n")
        result = self.analyzer.analyze(tmp_path)
        assert result.language == "python"
        assert result.node_count >= 1
        node_ids = [n.id for n in result.graph.nodes]
        assert "hello" in node_ids

    def test_analyze_import_edges(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("import b\n")
        (tmp_path / "b.py").write_text("x = 1\n")
        result = self.analyzer.analyze(tmp_path)
        edge_sources = {e.source for e in result.graph.edges}
        assert "a" in edge_sources

    def test_circular_import_smell(self, tmp_path: Path) -> None:
        (tmp_path / "alpha.py").write_text("import beta\n")
        (tmp_path / "beta.py").write_text("import alpha\n")
        result = self.analyzer.analyze(tmp_path)
        smell_types = [s["type"] for s in result.smells]
        assert SmellType.CIRCULAR_IMPORT in smell_types

    def test_god_module_smell(self, tmp_path: Path) -> None:
        big_source = "\n".join(f"x_{i} = {i}" for i in range(600))
        (tmp_path / "big_module.py").write_text(big_source)
        result = self.analyzer.analyze(tmp_path)
        smell_types = [s["type"] for s in result.smells]
        assert SmellType.GOD_MODULE in smell_types

    def test_no_smells_for_tiny_file(self, tmp_path: Path) -> None:
        (tmp_path / "small.py").write_text("x = 1\n")
        result = self.analyzer.analyze(tmp_path)
        assert result.smells == []

    def test_handles_syntax_error_gracefully(self, tmp_path: Path) -> None:
        (tmp_path / "broken.py").write_text("def foo(\n")
        (tmp_path / "good.py").write_text("x = 1\n")
        # Should not raise — broken.py is skipped
        result = self.analyzer.analyze(tmp_path)
        assert result.language == "python"

    def test_result_has_uuid(self, tmp_path: Path) -> None:
        (tmp_path / "m.py").write_text("pass\n")
        result = self.analyzer.analyze(tmp_path)
        assert result.repo_id is not None

    def test_class_nodes_extracted(self, tmp_path: Path) -> None:
        (tmp_path / "models.py").write_text("class User:\n    pass\n\nclass Post:\n    pass\n")
        result = self.analyzer.analyze(tmp_path)
        node_labels = [n.label for n in result.graph.nodes]
        assert "User" in node_labels
        assert "Post" in node_labels


# ── Java Analyzer Tests ───────────────────────────────────────────────────────


class TestJavaAnalyzer:
    def setup_method(self) -> None:
        self.analyzer = JavaAnalyzer()

    def test_language_property(self) -> None:
        assert self.analyzer.language == "java"

    def test_can_handle_java_dir(self, tmp_path: Path) -> None:
        (tmp_path / "Main.java").write_text("class Main {}")
        assert self.analyzer.can_handle(tmp_path) is True

    def test_cannot_handle_empty_dir(self, tmp_path: Path) -> None:
        assert self.analyzer.can_handle(tmp_path) is False

    def test_analyze_returns_result(self, tmp_path: Path) -> None:
        src = "package com.example;\npublic class HelloWorld {}\n"
        (tmp_path / "HelloWorld.java").write_text(src)
        result = self.analyzer.analyze(tmp_path)
        assert result.language == "java"
        assert result.repo_id is not None

    def test_analyze_extracts_class_node(self, tmp_path: Path) -> None:
        src = "package com.example;\npublic class Greeter {}\n"
        (tmp_path / "Greeter.java").write_text(src)
        result = self.analyzer.analyze(tmp_path)
        node_labels = [n.label for n in result.graph.nodes]
        assert "Greeter" in node_labels

    def test_analyze_extracts_import_edge(self, tmp_path: Path) -> None:
        src = "package com.example;\nimport java.util.List;\npublic class MyService {}\n"
        (tmp_path / "MyService.java").write_text(src)
        result = self.analyzer.analyze(tmp_path)
        edge_targets = {e.target for e in result.graph.edges}
        assert "java.util.List" in edge_targets
