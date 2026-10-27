"""JavaScript / TypeScript static analyzer using regex-based AST extraction.

Walks a directory tree, parses every .js, .jsx, .ts, .tsx, .mjs, .cjs file, extracts:
- Module, class, and function nodes
- Import / require edges
- Class inheritance edges (extends)

Detects smells:
- Large class / module (> 300 lines)
- Circular dependencies
"""

from __future__ import annotations

import re
from pathlib import Path

from parsers.fingerprint import (
    DEFAULT_RANDOM_SEED,
    PARSER_VERSION,
    compute_analysis_id,
    compute_settings_hash,
    compute_source_fingerprint,
    get_git_commit_sha,
)

from app.analyzers.base import BaseAnalyzer
from app.core.logging import get_logger
from app.models.graph import (
    AnalysisResult,
    DependencyGraph,
    GraphEdge,
    GraphNode,
    NodeType,
)
from app.models.refactor import Smell, SmellSeverity, SmellType

logger = get_logger(__name__)

LARGE_CLASS_LOC_THRESHOLD = 300
JS_EXTENSIONS = frozenset({".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"})


class JavaScriptAnalyzer(BaseAnalyzer):
    """Analyzes JavaScript and TypeScript codebases."""

    @property
    def language(self) -> str:
        return "javascript"

    def can_handle(self, path: Path) -> bool:
        if path.is_file():
            return path.suffix.lower() in JS_EXTENSIONS
        return any(
            p.suffix.lower() in JS_EXTENSIONS
            for p in path.rglob("*")
            if not any(part.startswith((".", "node_modules", "dist", "build")) for part in p.parts)
        )

    def analyze(self, root: Path, include_tests: bool = False) -> AnalysisResult:
        root = root.resolve()
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        seen_nodes: set[str] = set()
        seen_edges: set[tuple[str, str]] = set()

        skip_dirs = {
            "node_modules",
            "venv",
            ".venv",
            ".git",
            "dist",
            "build",
            ".next",
            ".nuxt",
            ".output",
            "coverage",
            ".turbo",
            "data",
            "scratch",
        }
        test_dirs = {"test", "tests", "__tests__", "spec", "specs", "fixtures", "samples", "examples", "docs"}

        all_files = sorted(
            [
                p
                for p in root.rglob("*")
                if p.is_file() and p.suffix.lower() in JS_EXTENSIONS and not any(d in p.parts for d in skip_dirs)
            ],
            key=lambda p: p.as_posix(),
        )

        in_scope_files: list[Path] = []
        files_excluded = 0
        for f in all_files:
            rel_parts = f.relative_to(root).parts
            is_test_or_fixture = any(part.lower() in test_dirs for part in rel_parts) or any(
                p.endswith((".test.js", ".test.ts", ".spec.js", ".spec.ts", ".test.jsx", ".test.tsx"))
                for p in (f.name.lower(),)
            )
            if not include_tests and is_test_or_fixture:
                files_excluded += 1
            else:
                in_scope_files.append(f)

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

        # Regex patterns for imports, classes, functions
        import_pattern = re.compile(
            r"""(?:import\s+(?:(?:\{[^}]*\}|[A-Za-z0-9_$,\s*]+)\s+from\s+)?['"]([^'"]+)['"]|require\(['"]([^'"]+)['"]\))"""
        )
        class_pattern = re.compile(r"""class\s+([A-Za-z0-9_$]+)(?:\s+extends\s+([A-Za-z0-9_$]+))?""")
        branch_pattern = re.compile(r"""\b(?:if|else\s+if|for|while|catch|case)\b|&&|\|\||\?""")

        file_to_mod_id: dict[Path, str] = {}
        for js_file in in_scope_files:
            rel_path = js_file.relative_to(root).as_posix()
            mod_id = rel_path.replace("/", ".").rstrip(".js").rstrip(".ts").rstrip(".jsx").rstrip(".tsx")
            file_to_mod_id[js_file] = mod_id

        for js_file in in_scope_files:
            rel_path = js_file.relative_to(root).as_posix()
            source = js_file.read_text(encoding="utf-8", errors="replace")
            lines = source.splitlines()
            loc = len(lines)

            # Compute cyclomatic complexity
            branches = len(branch_pattern.findall(source))
            complexity = float(max(1, branches + 1))

            mod_id = file_to_mod_id[js_file]
            classes_in_file = class_pattern.findall(source)

            if classes_in_file:
                for cls_name, base_cls in classes_in_file:
                    cls_id = f"{mod_id}.{cls_name}"
                    node_lang = "typescript" if js_file.suffix.lower() in (".ts", ".tsx") else "javascript"
                    if cls_id not in seen_nodes:
                        seen_nodes.add(cls_id)
                        nodes.append(
                            GraphNode(
                                id=cls_id,
                                label=cls_name,
                                type=NodeType.CLASS,
                                language=node_lang,
                                file_path=rel_path,
                                loc=loc,
                                cyclomatic_complexity=complexity,
                                max_complexity=int(complexity),
                                mean_complexity=complexity,
                            )
                        )
                    if base_cls:
                        base_id = f"{mod_id}.{base_cls}"
                        if (cls_id, base_id) not in seen_edges:
                            seen_edges.add((cls_id, base_id))
                            edges.append(GraphEdge(source=cls_id, target=base_id, edge_type="inherit", weight=1.0))
            else:
                if mod_id not in seen_nodes:
                    seen_nodes.add(mod_id)
                    node_lang = "typescript" if js_file.suffix.lower() in (".ts", ".tsx") else "javascript"
                    nodes.append(
                        GraphNode(
                            id=mod_id,
                            label=js_file.stem,
                            type=NodeType.MODULE,
                            language=node_lang,
                            file_path=rel_path,
                            loc=loc,
                            cyclomatic_complexity=complexity,
                            max_complexity=int(complexity),
                            mean_complexity=complexity,
                        )
                    )

            # Extract imports
            for match in import_pattern.finditer(source):
                imp_target = match.group(1) or match.group(2)
                if not imp_target:
                    continue

                # Relative import resolution
                target_node_id = None
                if imp_target.startswith("."):
                    target_file = (js_file.parent / imp_target).resolve()
                    # Check candidates
                    for cand_ext in ("", ".js", ".ts", ".jsx", ".tsx", "/index.js", "/index.ts"):
                        cand = Path(str(target_file) + cand_ext)
                        if cand in file_to_mod_id:
                            target_node_id = file_to_mod_id[cand]
                            break
                else:
                    target_node_id = imp_target

                if target_node_id:
                    src_id = mod_id
                    if (src_id, target_node_id) not in seen_edges and src_id != target_node_id:
                        seen_edges.add((src_id, target_node_id))
                        edges.append(GraphEdge(source=src_id, target=target_node_id, edge_type="import", weight=1.0))

        repo_leaf_name = root.name or "repository"
        clean_path = repo_leaf_name

        nodes.sort(key=lambda n: n.id)
        edges.sort(key=lambda e: (e.source, e.target))

        graph = DependencyGraph(nodes=nodes, edges=edges)
        result = AnalysisResult(
            repo_id=repo_id,
            path=clean_path,
            language=self.language,
            graph=graph,
            smells=[],
            commit_sha=commit_sha,
            parser_version=PARSER_VERSION,
            settings_hash=settings_hash,
            source_fingerprint=source_fingerprint,
            truncated=False,
            truncated_counts={"files_excluded": files_excluded} if files_excluded else {},
            random_seed=DEFAULT_RANDOM_SEED,
            files_excluded=files_excluded,
            include_tests=include_tests,
        )
        result.smells = [s.model_dump(mode="json") for s in self.detect_smells(result)]

        from diagnostics.scoring import compute_codebase_health

        result.health = compute_codebase_health(
            nodes=result.graph.nodes,
            edges=result.graph.edges,
            smells=result.smells,
        )
        return result

    def detect_smells(self, result: AnalysisResult) -> list[Smell]:
        smells: list[Smell] = []

        for node in sorted(result.graph.nodes, key=lambda n: n.id):
            if node.loc and node.loc > LARGE_CLASS_LOC_THRESHOLD:
                smells.append(
                    Smell(
                        type=SmellType.LARGE_CLASS,
                        file=node.file_path or node.id,
                        severity=SmellSeverity.HIGH,
                        description=(
                            f"Component '{node.label}' has {node.loc} lines "
                            f"(threshold: {LARGE_CLASS_LOC_THRESHOLD}). "
                            "Consider decomposing into smaller modules."
                        ),
                        suggestion="Apply Single Responsibility Principle; extract cohesive functions.",
                    )
                )

        # Detect circular dependencies
        try:
            from analysis.facade import build_graph_from_dict
            from analysis.scc import detect_circular_dependencies

            g_dict = {
                "nodes": [{"id": n.id} for n in result.graph.nodes],
                "edges": [{"source": e.source, "target": e.target} for e in result.graph.edges],
            }
            dir_g = build_graph_from_dict(g_dict)
            scc_cycles = detect_circular_dependencies(dir_g)
            for c in scc_cycles:
                cycle_str = " -> ".join(c.nodes)
                smells.append(
                    Smell(
                        type=SmellType.CIRCULAR_IMPORT,
                        file=c.nodes[0],
                        severity=SmellSeverity.CRITICAL,
                        description=f"Circular dependency cycle detected: {cycle_str}",
                        suggestion="Break cycle using dependency inversion or extracting shared interfaces.",
                    )
                )
        except Exception as exc:
            logger.warning("Could not compute circular smells for JS: %s", exc)

        return smells
