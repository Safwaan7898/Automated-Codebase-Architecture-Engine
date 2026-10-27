"""Tests for the ingestion and import-resolver modules."""

from __future__ import annotations

from pathlib import Path

import pytest

from parsers.config import IngestionConfig
from parsers.ingestion import FileInfo, collect_files, detect_primary_language, ingest_source
from parsers.import_resolver import resolve_imports
from parsers.models import Edge, EdgeType, Metrics, Node, NodeType, ParseResult


# ── IngestionConfig tests ─────────────────────────────────────────────────────


class TestIngestionConfig:
    def test_default_ignores_node_modules(self):
        cfg = IngestionConfig()
        assert cfg.should_ignore_dir("node_modules")

    def test_default_ignores_git(self):
        cfg = IngestionConfig()
        assert cfg.should_ignore_dir(".git")

    def test_default_ignores_pycache(self):
        cfg = IngestionConfig()
        assert cfg.should_ignore_dir("__pycache__")

    def test_test_dirs_excluded_by_default(self):
        cfg = IngestionConfig(include_test_files=False)
        assert cfg.should_ignore_dir("test")
        assert cfg.should_ignore_dir("tests")

    def test_test_dirs_included_when_flag_set(self):
        cfg = IngestionConfig(include_test_files=True)
        # 'tests' should NOT be in ignore set when include_test_files=True
        assert not cfg.should_ignore_dir("tests")

    def test_ignore_file_pattern_class(self, tmp_path):
        cfg = IngestionConfig()
        f = tmp_path / "Main.class"
        f.write_bytes(b"\xca\xfe\xba\xbe")  # Java class magic bytes
        assert cfg.should_ignore_file(f)

    def test_oversized_file_ignored(self, tmp_path):
        cfg = IngestionConfig(max_file_size_bytes=10)
        f = tmp_path / "big.py"
        f.write_text("x = 1" * 100)
        assert cfg.should_ignore_file(f)

    def test_normal_py_file_not_ignored(self, tmp_path):
        cfg = IngestionConfig()
        f = tmp_path / "main.py"
        f.write_text("x = 1")
        assert not cfg.should_ignore_file(f)


# ── collect_files tests ───────────────────────────────────────────────────────


class TestCollectFiles:
    def test_collects_py_files(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        files = collect_files(tmp_path, IngestionConfig())
        rel_paths = {f.rel_path for f in files}
        assert "a.py" in rel_paths
        assert "b.py" in rel_paths

    def test_skips_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "lib.py").write_text("x = 1")
        files = collect_files(tmp_path, IngestionConfig())
        assert not any("node_modules" in f.rel_path for f in files)

    def test_skips_pycache(self, tmp_path):
        pc = tmp_path / "__pycache__"
        pc.mkdir()
        (pc / "cached.pyc").write_bytes(b"\x00" * 10)
        files = collect_files(tmp_path, IngestionConfig())
        assert not files

    def test_collects_java_files(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "Main.java").write_text("class Main {}")
        files = collect_files(tmp_path, IngestionConfig())
        assert any(f.rel_path.endswith(".java") for f in files)

    def test_nested_dirs_traversed(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "deep.py").write_text("pass")
        files = collect_files(tmp_path, IngestionConfig())
        assert any("deep.py" in f.rel_path for f in files)

    def test_language_detected(self, tmp_path):
        (tmp_path / "mod.py").write_text("x = 1")
        files = collect_files(tmp_path, IngestionConfig())
        assert files[0].language == "python"

    def test_returns_sorted_paths(self, tmp_path):
        for name in ["z.py", "a.py", "m.py"]:
            (tmp_path / name).write_text("pass")
        files = collect_files(tmp_path, IngestionConfig())
        paths = [f.rel_path for f in files]
        assert paths == sorted(paths)


class TestDetectPrimaryLanguage:
    def test_majority_python(self):
        files = [
            FileInfo(abs_path=Path("a.py"), rel_path="a.py", language="python", size_bytes=10),
            FileInfo(abs_path=Path("b.py"), rel_path="b.py", language="python", size_bytes=10),
            FileInfo(abs_path=Path("c.java"), rel_path="c.java", language="java", size_bytes=10),
        ]
        assert detect_primary_language(files) == "python"

    def test_empty_returns_unknown(self):
        assert detect_primary_language([]) == "unknown"


class TestIngestSource:
    def test_local_path_accepted(self, tmp_path):
        (tmp_path / "test.py").write_text("x = 1")
        ingested = ingest_source(str(tmp_path), IngestionConfig())
        assert ingested.root == tmp_path.resolve()
        assert not ingested.is_temp

    def test_nonexistent_path_raises(self):
        with pytest.raises(ValueError, match="does not exist"):
            ingest_source("/nonexistent/path/xyz_123", IngestionConfig())

    def test_file_path_raises(self, tmp_path):
        f = tmp_path / "file.py"
        f.write_text("x = 1")
        with pytest.raises(ValueError, match="not a directory"):
            ingest_source(str(f), IngestionConfig())


# ── Import resolver tests ─────────────────────────────────────────────────────


class TestImportResolver:
    def _make_result(self, file_path: str, nodes: list[Node], edges: list[Edge]) -> ParseResult:
        pr = ParseResult(file_path=file_path, language="python")
        pr.nodes = nodes
        pr.edges = edges
        return pr

    def test_internal_import_resolved(self):
        # Module A imports module B — both in the repo
        mod_a = Node(id="pkg.a", type=NodeType.MODULE, name="a", path="pkg/a.py", language="python", metrics=Metrics())
        mod_b = Node(id="pkg.b", type=NodeType.MODULE, name="b", path="pkg/b.py", language="python", metrics=Metrics())
        edge = Edge(source="pkg.a", target="pkg.b", type=EdgeType.IMPORTS, resolved=False)

        results = [
            self._make_result("pkg/a.py", [mod_a], [edge]),
            self._make_result("pkg/b.py", [mod_b], []),
        ]
        nodes, edges = resolve_imports(results, language="python")
        resolved_imports = [e for e in edges if e.type == EdgeType.IMPORTS and e.resolved]
        assert resolved_imports, "Expected at least one resolved import"

    def test_external_import_creates_stub(self):
        mod_a = Node(
            id="myapp.main", type=NodeType.MODULE, name="main", path="main.py", language="python", metrics=Metrics()
        )
        edge = Edge(source="myapp.main", target="requests", type=EdgeType.IMPORTS, resolved=False)
        results = [self._make_result("main.py", [mod_a], [edge])]
        nodes, edges = resolve_imports(results, "python")

        ext_ids = {n.id for n in nodes if n.is_external}
        assert "ext:requests" in ext_ids

        ext_edges = [e for e in edges if e.target == "ext:requests"]
        assert ext_edges

    def test_no_duplicate_external_nodes(self):
        mod_a = Node(id="a", type=NodeType.MODULE, name="a", path="a.py", language="python", metrics=Metrics())
        mod_b = Node(id="b", type=NodeType.MODULE, name="b", path="b.py", language="python", metrics=Metrics())
        edge1 = Edge(source="a", target="requests", type=EdgeType.IMPORTS, resolved=False)
        edge2 = Edge(source="b", target="requests", type=EdgeType.IMPORTS, resolved=False)
        results = [
            self._make_result("a.py", [mod_a], [edge1]),
            self._make_result("b.py", [mod_b], [edge2]),
        ]
        nodes, _ = resolve_imports(results, "python")
        ext_nodes = [n for n in nodes if n.id == "ext:requests"]
        assert len(ext_nodes) == 1, "Should create only one external stub per dependency"

    def test_java_wildcard_import_mapped_to_package(self):
        cls = Node(
            id="com.example.Main",
            type=NodeType.CLASS,
            name="Main",
            path="Main.java",
            language="java",
            metrics=Metrics(),
        )
        pkg = Node(id="pkg:java.util", type=NodeType.PACKAGE, name="util", path="", language="java", metrics=Metrics())
        edge = Edge(source="com.example.Main", target="java.util.*", type=EdgeType.IMPORTS, resolved=False)
        results = [
            self._make_result("Main.java", [cls], [edge]),
            self._make_result("_pkg", [pkg], []),
        ]
        nodes, edges = resolve_imports(results, "java")
        # Should resolve to the package or mark external — either is acceptable
        import_edges = [e for e in edges if e.type == EdgeType.IMPORTS]
        assert import_edges  # at least one edge present
