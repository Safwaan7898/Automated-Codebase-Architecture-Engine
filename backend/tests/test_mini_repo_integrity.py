"""Tests for data integrity, graph builder, import resolution, and external dependencies."""

from pathlib import Path
import pytest

from app.analyzers.python_analyzer import PythonAnalyzer
from app.models.refactor import SmellType
from analysis.graph import DirectedGraph


class TestMiniRepoDataIntegrity:
    @pytest.fixture
    def mini_repo_path(self) -> Path:
        return Path(__file__).parent / "fixtures" / "mini_repo"

    def test_mini_repo_graph_structure(self, mini_repo_path: Path) -> None:
        analyzer = PythonAnalyzer()
        result = analyzer.analyze(mini_repo_path)

        # 1. Assert exact 4 internal module nodes
        node_ids = {n.id for n in result.graph.nodes if n.type == "module"}
        assert node_ids == {"module_a", "module_b", "module_c", "module_d"}
        assert len(result.graph.nodes) == 4

        # 2. Assert exact internal edges
        edge_pairs = {(e.source, e.target) for e in result.graph.edges}
        assert edge_pairs == {
            ("module_a", "module_b"),
            ("module_b", "module_a"),
            ("module_c", "module_a"),
            ("module_d", "module_c"),
        }
        assert len(result.graph.edges) == 4

        # 3. Assert self-loop guard: no edge has source == target
        for edge in result.graph.edges:
            assert edge.source != edge.target

        # 4. Assert one 2-module import cycle between module_a and module_b
        smell_types = [s["type"] for s in result.smells]
        assert SmellType.CIRCULAR_IMPORT in smell_types

        # 5. Assert external dependencies: 3 external imports (1 stdlib, 2 third-party)
        ext_dep_names = {d.name: d.category for d in result.external_dependencies}
        assert "os" in ext_dep_names
        assert ext_dep_names["os"] == "stdlib"
        assert "requests" in ext_dep_names
        assert ext_dep_names["requests"] == "third_party"
        assert "pydantic" in ext_dep_names
        assert ext_dep_names["pydantic"] == "third_party"
        assert len(result.external_dependencies) == 3

        # 6. Assert exact LOC and McCabe cyclomatic complexity per module
        node_map = {n.id: n for n in result.graph.nodes}
        assert node_map["module_a"].loc == 10
        assert node_map["module_a"].mean_complexity == 2.0
        assert node_map["module_a"].max_complexity == 2

        assert node_map["module_b"].loc == 10
        assert node_map["module_b"].mean_complexity == 3.0
        assert node_map["module_b"].max_complexity == 3

        assert node_map["module_c"].loc == 6
        assert node_map["module_c"].mean_complexity == 1.0
        assert node_map["module_c"].max_complexity == 1

        assert node_map["module_d"].loc == 6
        assert node_map["module_d"].mean_complexity == 1.0
        assert node_map["module_d"].max_complexity == 1

        # 7. Assert health score computed deterministically
        assert result.health.status == "ok"
        assert result.health.score is not None
        assert result.health.grade is not None
        assert "cycles" in result.health.sub_scores
        assert "coupling" in result.health.sub_scores
        assert "complexity" in result.health.sub_scores
        assert "smells" in result.health.sub_scores
        assert "security" in result.health.sub_scores

    def test_insufficient_data_guard(self) -> None:
        from diagnostics.scoring import compute_codebase_health

        res = compute_codebase_health(nodes=[], edges=[])
        assert res.status == "insufficient_data"
        assert res.score is None
        assert res.grade is None

    def test_directed_graph_add_edge_self_loop_and_parallel_weights(self) -> None:
        g = DirectedGraph()
        # Self loop should be rejected when guarded
        res = g.add_edge("nodeA", "nodeA", allow_self_loops=False)
        assert res is None
        assert g.edge_count == 0

        # Adding edge
        edge1 = g.add_edge("nodeA", "nodeB", weight=1.0)
        assert edge1 is not None
        assert edge1.weight == 1.0
        assert g.edge_count == 1

        # Adding parallel edge should accumulate weight
        edge2 = g.add_edge("nodeA", "nodeB", weight=2.5)
        assert edge2 is not None
        assert edge2.weight == 3.5
        assert g.edge_count == 1
        assert g.edge_weight("nodeA", "nodeB") == 3.5

    def test_relative_and_init_package_imports(self, tmp_path: Path) -> None:
        # Create a package hierarchy:
        # mypkg/
        #   __init__.py (imports .sub_a)
        #   sub_a.py (imports ..mypkg)
        #   sub_b.py (from .sub_a import helper)
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("from . import sub_a\n")
        (pkg / "sub_a.py").write_text("x = 10\n")
        (pkg / "sub_b.py").write_text("from .sub_a import x\n")

        analyzer = PythonAnalyzer()
        res = analyzer.analyze(tmp_path)

        edge_pairs = {(e.source, e.target) for e in res.graph.edges}
        assert ("mypkg", "mypkg.sub_a") in edge_pairs
        assert ("mypkg.sub_b", "mypkg.sub_a") in edge_pairs

    def test_include_tests_distinct_ids_and_valid_scores(self, tmp_path: Path) -> None:
        """The same fixture with include_tests true/false produces distinct ids and a valid score for both."""
        src_file = tmp_path / "app.py"
        src_file.write_text("def run():\n    return 42\n")
        test_file = tmp_path / "test_app.py"
        test_file.write_text("import app\ndef test_run():\n    assert app.run() == 42\n")

        analyzer = PythonAnalyzer()

        # Run with include_tests=False
        res_false = analyzer.analyze(tmp_path, include_tests=False)
        assert res_false.include_tests is False
        assert res_false.node_count >= 1
        assert res_false.health.status == "ok"
        assert res_false.health.score is not None
        assert res_false.health.grade is not None

        # Run with include_tests=True
        res_true = analyzer.analyze(tmp_path, include_tests=True)
        assert res_true.include_tests is True
        assert res_true.node_count > res_false.node_count
        assert res_true.health.status == "ok"
        assert res_true.health.score is not None
        assert res_true.health.grade is not None

        # Distinct IDs guaranteed by full cache key
        assert res_false.repo_id != res_true.repo_id
        assert str(res_false.repo_id) != str(res_true.repo_id)

        # Persistence verification: ensure analyzer_service persists both without overwriting
        from app.services import analyzer_service
        from app.storage.analysis_store import default_analysis_store

        run1 = analyzer_service.run_analysis(str(tmp_path), language="python", include_tests=False)
        run2 = analyzer_service.run_analysis(str(tmp_path), language="python", include_tests=True)

        assert run1.repo_id != run2.repo_id
        rec1 = default_analysis_store.get(str(run1.repo_id))
        rec2 = default_analysis_store.get(str(run2.repo_id))
        assert rec1 is not None
        assert rec2 is not None
        assert rec1.id != rec2.id
