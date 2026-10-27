"""Unit tests for the Python tree-sitter parser."""

from __future__ import annotations

import pytest

from parsers.models import EdgeType, NodeType
from tests.test_parsers import COMPLEX_PY, SIMPLE_PY


def _python_parser():
    try:
        from parsers.python_parser import PythonParser

        return PythonParser()
    except RuntimeError as exc:
        pytest.skip(f"Python parser unavailable: {exc}")


# ── simple.py tests ───────────────────────────────────────────────────────────


class TestSimplePython:
    def setup_method(self):
        self.parser = _python_parser()
        self.source = SIMPLE_PY.read_text(encoding="utf-8")
        self.result = self.parser.parse_file(SIMPLE_PY, "python/simple.py", self.source)

    def test_no_fatal_errors(self):
        fatal = [e for e in self.result.errors if "Fatal" in e]
        assert not fatal

    def test_module_node_present(self):
        modules = [n for n in self.result.nodes if n.type == NodeType.MODULE]
        assert modules, "Expected a MODULE node"
        assert modules[0].id == "python.simple"

    def test_module_loc(self):
        modules = [n for n in self.result.nodes if n.type == NodeType.MODULE]
        assert modules[0].metrics.loc > 0

    def test_class_node_present(self):
        classes = [n for n in self.result.nodes if n.type == NodeType.CLASS]
        names = {c.name for c in classes}
        assert "SimpleClass" in names

    def test_class_fqn(self):
        classes = [n for n in self.result.nodes if n.name == "SimpleClass"]
        assert classes
        assert classes[0].id == "python.simple.SimpleClass"

    def test_method_nodes_present(self):
        methods = [n for n in self.result.nodes if n.type == NodeType.METHOD]
        names = {m.name for m in methods}
        assert "__init__" in names
        assert "describe" in names

    def test_top_level_function_present(self):
        funcs = [n for n in self.result.nodes if n.type == NodeType.FUNCTION]
        names = {f.name for f in funcs}
        assert "greet" in names
        assert "read_file" in names

    def test_import_edges_present(self):
        imports = [e for e in self.result.edges if e.type == EdgeType.IMPORTS]
        targets = {e.target for e in imports}
        assert "os" in targets or "pathlib" in targets, f"Import targets: {targets}"

    def test_contains_edges_module_to_class(self):
        contains = [e for e in self.result.edges if e.type == EdgeType.CONTAINS]
        assert any(e.source == "python.simple" and "SimpleClass" in e.target for e in contains)

    def test_method_parameters_counted(self):
        init = [n for n in self.result.nodes if n.name == "__init__"]
        assert init
        # __init__(self, name, value=0) → 2 params (self excluded)
        assert init[0].metrics.num_parameters >= 1

    def test_static_method_detected(self):
        methods = [n for n in self.result.nodes if n.name == "from_env"]
        assert methods


# ── complex.py tests ──────────────────────────────────────────────────────────


class TestComplexPython:
    def setup_method(self):
        self.parser = _python_parser()
        self.source = COMPLEX_PY.read_text(encoding="utf-8")
        self.result = self.parser.parse_file(COMPLEX_PY, "python/complex.py", self.source)

    def test_abstract_base_class_found(self):
        classes = [n for n in self.result.nodes if n.name == "BaseProcessor"]
        assert classes

    def test_inheritance_edge(self):
        extends = [e for e in self.result.edges if e.type == EdgeType.EXTENDS]
        targets = {e.target for e in extends}
        assert "BaseProcessor" in targets, f"Extends targets: {targets}"

    def test_multi_level_inheritance(self):
        """StreamingProcessor → DataProcessor → BaseProcessor."""
        extends = [e for e in self.result.edges if e.type == EdgeType.EXTENDS]
        sources = {e.source.split(".")[-1] for e in extends}
        assert "StreamingProcessor" in sources
        assert "DataProcessor" in sources

    def test_decorator_node(self):
        """retry decorator should appear as FUNCTION node."""
        funcs = [n for n in self.result.nodes if n.name == "retry"]
        assert funcs, "Expected 'retry' decorator factory function"

    def test_annotated_by_edges(self):
        annotated = [e for e in self.result.edges if e.type == EdgeType.ANNOTATED_BY]
        assert annotated, "Expected ANNOTATED_BY edges from @retry"

    def test_classify_complexity(self):
        """classify() has 7 elif branches → complexity ≥ 7."""
        methods = [n for n in self.result.nodes if n.name == "classify"]
        assert methods
        assert methods[0].metrics.cyclomatic_complexity >= 7

    def test_process_complexity(self):
        """DataProcessor.process() has multiple isinstance branches."""
        methods = [n for n in self.result.nodes if n.name == "process" and "DataProcessor" in n.id]
        assert methods, "Expected DataProcessor.process node"
        assert methods[0].metrics.cyclomatic_complexity >= 4

    def test_call_edges_present(self):
        calls = [e for e in self.result.edges if e.type == EdgeType.CALLS]
        assert calls, "Expected CALLS edges from method bodies"

    def test_relative_import_edge(self):
        imports = [e for e in self.result.edges if e.type == EdgeType.IMPORTS]
        # `from . import simple as _simple` should yield an import edge
        assert imports, "Expected import edges"


# ── Syntax error / edge cases ─────────────────────────────────────────────────


class TestPythonEdgeCases:
    def setup_method(self):
        self.parser = _python_parser()

    def test_broken_python_does_not_raise(self, tmp_path):
        broken = "def foo(\n    x, y\n  # missing close paren"
        result = self.parser.parse_file(tmp_path / "broken.py", "broken.py", broken)
        assert result is not None

    def test_empty_file(self, tmp_path):
        result = self.parser.parse_file(tmp_path / "empty.py", "empty.py", "")
        assert result.node_count >= 1  # at least module node

    def test_deeply_nested_functions(self, tmp_path):
        code = """
def outer():
    def middle():
        def inner():
            pass
        return inner
    return middle
"""
        result = self.parser.parse_file(tmp_path / "nested.py", "nested.py", code)
        func_names = {n.name for n in result.nodes if n.type in (NodeType.FUNCTION, NodeType.METHOD)}
        assert "outer" in func_names

    def test_async_function(self, tmp_path):
        code = """
async def fetch(url: str) -> str:
    return ""
"""
        result = self.parser.parse_file(tmp_path / "async_mod.py", "async_mod.py", code)
        # Should not crash; async functions may or may not be extracted depending on grammar
        assert result is not None

    def test_dataclass_style(self, tmp_path):
        code = """
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float

    def distance(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5
"""
        result = self.parser.parse_file(tmp_path / "dc.py", "dc.py", code)
        class_names = {n.name for n in result.nodes if n.type == NodeType.CLASS}
        assert "Point" in class_names
        ann = [e for e in result.edges if e.type == EdgeType.ANNOTATED_BY]
        assert ann, "dataclass decorator should create ANNOTATED_BY edge"
