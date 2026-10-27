"""Unified Multi-Language Analyzer for mixed-language repositories.

Combines Tier 1 (Python, Java, JS/TS, Go) and Tier 2 (C#, C/C++, Rust, PHP, Ruby, Kotlin)
analyzers into a single cohesive dependency graph.
Tracks unsupported files by extension and count.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from parsers.fingerprint import (
    DEFAULT_RANDOM_SEED,
    PARSER_VERSION,
    compute_analysis_id,
    compute_settings_hash,
    compute_source_fingerprint,
    get_git_commit_sha,
)

from app.analyzers.base import BaseAnalyzer
from app.analyzers.go_analyzer import GoAnalyzer
from app.analyzers.java_analyzer import JavaAnalyzer
from app.analyzers.javascript_analyzer import JavaScriptAnalyzer
from app.analyzers.python_analyzer import PythonAnalyzer
from app.analyzers.treesitter_analyzer import TreeSitterAnalyzer
from app.analyzers.treesitter_common import detect_language
from app.core.logging import get_logger
from app.models.graph import (
    AnalysisResult,
    DependencyGraph,
    ExternalDependency,
    GraphEdge,
    GraphNode,
)
from app.models.refactor import Smell

logger = get_logger(__name__)

SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "venv",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "target",
        ".gradle",
        "bin",
        "obj",
        ".idea",
        ".vscode",
        "coverage",
        ".pytest_cache",
        ".tox",
        ".ruff_cache",
        ".reports_storage",
        "reports_output",
        "data",
        "scratch",
    }
)

TEST_DIR_NAMES = frozenset({"test", "tests", "fixtures", "samples", "examples", "docs", "__tests__"})


class MultiLanguageAnalyzer(BaseAnalyzer):
    """Analyzes mixed-language repositories into a single unified dependency graph."""

    def __init__(self) -> None:
        self._python = PythonAnalyzer()
        self._java = JavaAnalyzer()
        self._javascript = JavaScriptAnalyzer()
        self._go = GoAnalyzer()
        self._tier2_parsers: dict[str, TreeSitterAnalyzer] = {
            "rust": TreeSitterAnalyzer("rust"),
            "csharp": TreeSitterAnalyzer("csharp"),
            "c": TreeSitterAnalyzer("c"),
            "cpp": TreeSitterAnalyzer("cpp"),
            "php": TreeSitterAnalyzer("php"),
            "ruby": TreeSitterAnalyzer("ruby"),
            "kotlin": TreeSitterAnalyzer("kotlin"),
        }

    @property
    def language(self) -> str:
        return "multilang"

    def can_handle(self, path: Path) -> bool:
        return True

    def analyze(self, root: Path, include_tests: bool = False) -> AnalysisResult:
        root = root.resolve()
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        seen_nodes: set[str] = set()
        seen_edges: set[tuple[str, str]] = set()

        unsupported_counter: Counter[str] = Counter()
        detected_languages: set[str] = set()
        files_by_lang: dict[str, list[Path]] = {}
        files_excluded = 0

        # 1. Scan directory, detect language per file by extension or shebang
        for p in sorted(root.rglob("*"), key=lambda p: p.as_posix()):
            if not p.is_file():
                continue
            rel_parts = p.relative_to(root).parts
            if any(part in SKIP_DIRS for part in rel_parts):
                continue

            is_test = any(part.lower() in TEST_DIR_NAMES for part in rel_parts)
            if not include_tests and is_test:
                files_excluded += 1
                continue

            first_line = ""
            try:
                with p.open("r", encoding="utf-8", errors="replace") as f:
                    first_line = f.readline(128)
            except Exception as exc:
                logger.debug("Could not read first line of %s: %s", p, exc)

            lang = detect_language(p, first_line)
            if lang == "unknown":
                ext = p.suffix.lower() or p.name.lower()
                unsupported_counter[ext] += 1
            else:
                detected_languages.add(lang)
                files_by_lang.setdefault(lang, []).append(p)

        source_fingerprint, _ = compute_source_fingerprint(root)
        commit_sha = get_git_commit_sha(root)
        settings_hash = compute_settings_hash({"language": self.language, "include_tests": include_tests})
        repo_id = compute_analysis_id(
            source_fingerprint=source_fingerprint,
            parser_version=PARSER_VERSION,
            settings_hash=settings_hash,
            language=self.language,
            include_tests=include_tests,
        )

        all_smells: list[dict[str, Any]] = []
        all_ext_deps: list[ExternalDependency] = []

        # 2. Analyze files per detected language
        for lang in files_by_lang:
            sub_res: AnalysisResult | None = None
            try:
                if lang == "python":
                    sub_res = self._python.analyze(root, include_tests=include_tests)
                elif lang == "java":
                    sub_res = self._java.analyze(root, include_tests=include_tests)
                elif lang in ("javascript", "typescript"):
                    sub_res = self._javascript.analyze(root, include_tests=include_tests)
                elif lang == "go":
                    sub_res = self._go.analyze(root, include_tests=include_tests)
                elif lang in self._tier2_parsers:
                    sub_res = self._tier2_parsers[lang].analyze(root, include_tests=include_tests)
            except Exception as exc:
                logger.warning("Error running analyzer for language %s: %s", lang, exc)

            if sub_res:
                for n in sub_res.graph.nodes:
                    if n.id not in seen_nodes:
                        seen_nodes.add(n.id)
                        # Ensure language is assigned
                        if not n.language or n.language == "unknown":
                            n.language = lang
                        nodes.append(n)

                for e in sub_res.graph.edges:
                    if (e.source, e.target) not in seen_edges:
                        seen_edges.add((e.source, e.target))
                        if not hasattr(e, "confidence") or not e.confidence:
                            e.confidence = "resolved"
                        edges.append(e)

                all_smells.extend(sub_res.smells)
                all_ext_deps.extend(sub_res.external_dependencies)

        nodes.sort(key=lambda n: n.id)
        edges.sort(key=lambda e: (e.source, e.target))

        graph = DependencyGraph(nodes=nodes, edges=edges)
        result = AnalysisResult(
            repo_id=repo_id,
            path=root.name or "repository",
            language="multilang" if len(detected_languages) > 1 else (next(iter(detected_languages), "auto")),
            graph=graph,
            smells=all_smells,
            external_dependencies=all_ext_deps,
            commit_sha=commit_sha,
            parser_version=PARSER_VERSION,
            settings_hash=settings_hash,
            source_fingerprint=source_fingerprint,
            truncated=False,
            truncated_counts={"files_excluded": files_excluded} if files_excluded else {},
            random_seed=DEFAULT_RANDOM_SEED,
            files_excluded=files_excluded,
            include_tests=include_tests,
            unsupported_files=dict(sorted(unsupported_counter.items())),
            languages=sorted(detected_languages),
        )

        from diagnostics.scoring import compute_codebase_health

        result.health = compute_codebase_health(
            nodes=result.graph.nodes,
            edges=result.graph.edges,
            smells=result.smells,
        )
        return result

    def detect_smells(self, result: AnalysisResult) -> list[Smell]:
        return []
