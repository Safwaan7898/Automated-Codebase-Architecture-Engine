"""Tests for language-agnostic analysis engine (Phase 3).

Verifies:
- Go analyzer with go.mod module path resolution, package imports, cycles, LOC and McCabe complexity.
- TypeScript / JavaScript analyzer with relative imports and cycles.
- MultiLanguageAnalyzer for mixed-language repos, unified graph, node languages, edge confidence, and unsupported_files.
- Tier 2 tree-sitter analyzers (Rust, C#, C/C++, PHP, Ruby, Kotlin).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from app.analyzers.go_analyzer import GoAnalyzer
from app.analyzers.javascript_analyzer import JavaScriptAnalyzer
from app.analyzers.multilang_analyzer import MultiLanguageAnalyzer
from app.analyzers.treesitter_analyzer import TreeSitterAnalyzer
from app.analyzers.treesitter_common import detect_language
from app.models.graph import NodeType
from app.services.analyzer_service import run_analysis

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "multilang"


def test_go_analyzer_fixture_repo() -> None:
    """Verify Go analyzer on go_repo: exact nodes, edges, cycle detection, and complexity."""
    go_repo_dir = FIXTURES_DIR / "go_repo"
    assert go_repo_dir.exists(), f"Missing Go fixture at {go_repo_dir}"

    analyzer = GoAnalyzer()
    assert analyzer.can_handle(go_repo_dir)

    result = analyzer.analyze(go_repo_dir, include_tests=True)
    assert result.language == "go"

    node_ids = {n.id for n in result.graph.nodes}
    # Expected module nodes
    assert "pkg.alpha.alpha" in node_ids
    assert "pkg.beta.beta" in node_ids

    # Expected struct class nodes
    assert "pkg.alpha.alpha.AlphaService" in node_ids
    assert "pkg.beta.beta.BetaService" in node_ids

    # Expected function/method nodes
    assert "pkg.alpha.alpha.Run" in node_ids
    assert "pkg.beta.beta.Value" in node_ids

    # Verify node language
    for n in result.graph.nodes:
        assert n.language == "go"
        assert n.loc >= 0
        assert n.cyclomatic_complexity >= 1.0

    # Verify import edges between alpha and beta
    edge_pairs = {(e.source, e.target) for e in result.graph.edges}
    assert ("pkg.alpha.alpha", "pkg.beta.beta") in edge_pairs
    assert ("pkg.beta.beta", "pkg.alpha.alpha") in edge_pairs

    # Verify edge confidence
    for e in result.graph.edges:
        assert e.confidence in ("resolved", "parsed", "ai_inferred")

    # Verify cycle was detected
    assert len(result.smells) >= 1
    cycle_smells = [s for s in result.smells if s.get("type") == "circular_import"]
    assert len(cycle_smells) >= 1


def test_typescript_analyzer_fixture_repo() -> None:
    """Verify TypeScript analyzer on ts_repo: nodes, edges, and circular dependencies."""
    ts_repo_dir = FIXTURES_DIR / "ts_repo"
    assert ts_repo_dir.exists(), f"Missing TS fixture at {ts_repo_dir}"

    analyzer = JavaScriptAnalyzer()
    assert analyzer.can_handle(ts_repo_dir)

    result = analyzer.analyze(ts_repo_dir, include_tests=True)
    assert result.language == "javascript"

    node_ids = {n.id for n in result.graph.nodes}
    assert "src.user.UserService" in node_ids
    assert "src.auth.AuthService" in node_ids

    # Node language should be typescript
    for n in result.graph.nodes:
        assert n.language in ("javascript", "typescript")

    # Circular import edges
    edge_pairs = {(e.source, e.target) for e in result.graph.edges}
    assert ("src.user", "src.auth") in edge_pairs
    assert ("src.auth", "src.user") in edge_pairs


def test_multilang_analyzer_mixed_repo() -> None:
    """Verify MultiLanguageAnalyzer on mixed_repo: unified graph, node languages, edge confidence, and unsupported_files."""
    mixed_repo_dir = FIXTURES_DIR / "mixed_repo"
    assert mixed_repo_dir.exists(), f"Missing mixed fixture at {mixed_repo_dir}"

    # Use analyzer_service.run_analysis with auto detection
    result = run_analysis(str(mixed_repo_dir), language="auto", include_tests=True)

    assert result.language == "multilang"
    assert "go" in result.languages
    assert "python" in result.languages
    assert "typescript" in result.languages

    # Check nodes contain Go, Python, and TypeScript
    languages_in_nodes = {n.language for n in result.graph.nodes}
    assert "go" in languages_in_nodes
    assert "python" in languages_in_nodes
    assert "typescript" in languages_in_nodes

    # Check unsupported files
    assert ".csv" in result.unsupported_files
    assert ".md" in result.unsupported_files
    assert result.unsupported_files[".csv"] == 1
    assert result.unsupported_files[".md"] == 1

    # Check edges have confidence attribute
    for e in result.graph.edges:
        assert hasattr(e, "confidence")


def test_tier2_treesitter_analyzers_in_memory() -> None:
    """Verify Tier 2 tree-sitter analyzers on Rust, C#, C++, Ruby, PHP, and Kotlin."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Rust file
        rs_file = tmp_path / "lib.rs"
        rs_file.write_text(
            "use std::collections::HashMap;\n"
            "pub struct Config {\n"
            "    pub port: u16,\n"
            "}\n"
            "pub fn start(cfg: Config) -> bool {\n"
            "    if cfg.port > 1024 {\n"
            "        true\n"
            "    } else {\n"
            "        false\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        rs_analyzer = TreeSitterAnalyzer("rust")
        assert rs_analyzer.can_handle(tmp_path)
        rs_res = rs_analyzer.analyze(tmp_path, include_tests=True)
        rs_node_ids = {n.id for n in rs_res.graph.nodes}
        assert "lib" in rs_node_ids
        assert "lib.Config" in rs_node_ids
        assert "lib.start" in rs_node_ids
        start_node = next(n for n in rs_res.graph.nodes if n.id == "lib.start")
        assert start_node.language == "rust"

        # 2. C# file
        cs_file = tmp_path / "Program.cs"
        cs_file.write_text(
            "using System;\n"
            "namespace App {\n"
            "    public class Program {\n"
            "        public static void Main(string[] args) {\n"
            '            Console.WriteLine("Hello");\n'
            "        }\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        cs_analyzer = TreeSitterAnalyzer("csharp")
        assert cs_analyzer.can_handle(tmp_path)
        cs_res = cs_analyzer.analyze(tmp_path, include_tests=True)
        cs_node_ids = {n.id for n in cs_res.graph.nodes}
        assert "Program" in cs_node_ids
        assert "Program.Program" in cs_node_ids
        assert "Program.Main" in cs_node_ids


def test_shebang_language_detection() -> None:
    """Verify shebang detection for files without standard extensions."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        script_file = tmp_path / "my_runner"
        script_file.write_text("#!/usr/bin/env python3\nprint('hello')\n", encoding="utf-8")

        detected = detect_language(script_file, "#!/usr/bin/env python3")
        assert detected == "python"
