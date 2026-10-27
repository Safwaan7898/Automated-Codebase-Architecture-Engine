"""Java static analyzer using the `javalang` pure-Python parser.

Walks a directory tree, parses every .java file, extracts:
- Class / interface nodes
- Import edges
- Inheritance edges (extends / implements)

Detects smells:
- Large class       (> 300 lines)
- Deep inheritance  (> 3 levels, heuristic via class name tracking)
"""

from __future__ import annotations

from pathlib import Path

from app.analyzers.base import BaseAnalyzer
from app.core.logging import get_logger
from app.models.graph import AnalysisResult, DependencyGraph, ExternalDependency, GraphEdge, GraphNode, NodeType
from app.models.refactor import Smell, SmellSeverity, SmellType

logger = get_logger(__name__)

LARGE_CLASS_LOC_THRESHOLD = 300
DEEP_INHERITANCE_THRESHOLD = 3

try:
    import javalang  # type: ignore[import-untyped]

    _JAVALANG_AVAILABLE = True
except ImportError:
    _JAVALANG_AVAILABLE = False
    logger.warning("javalang not installed — Java analysis will return empty graphs.")


class JavaAnalyzer(BaseAnalyzer):
    """Analyzes Java codebases via javalang AST parsing."""

    @property
    def language(self) -> str:
        return "java"

    def can_handle(self, path: Path) -> bool:
        java_files = list(path.rglob("*.java"))
        return bool(java_files)

    def analyze(self, root: Path, include_tests: bool = False) -> AnalysisResult:
        root = root.resolve()
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        seen_nodes: set[str] = set()
        seen_edges: set[tuple[str, str]] = set()

        # Track inheritance depth by class name
        parent_map: dict[str, str] = {}

        skip_dirs = {
            "node_modules",
            ".git",
            "target",
            "build",
            "dist",
            ".gradle",
            "bin",
            ".idea",
            ".vscode",
            "data",
            "scratch",
        }
        test_dirs = {"test", "tests", "fixtures", "samples", "examples", "docs"}
        raw_java_files = sorted(root.rglob("*.java"), key=lambda p: p.as_posix())
        java_files: list[Path] = []
        max_file_size = 5 * 1024 * 1024  # 5 MB size limit
        files_excluded = 0

        for p in raw_java_files:
            try:
                rel = p.relative_to(root)
                rel_parts = rel.parts
            except ValueError:
                rel_parts = p.parts
            rel_dirs = set(rel_parts[:-1])

            if any(part in skip_dirs for part in rel_dirs):
                continue
            if not include_tests:
                if any(part in test_dirs for part in rel_dirs) or p.name.endswith(
                    ("Test.java", "Tests.java", "IT.java", "TestCase.java")
                ):
                    files_excluded += 1
                    continue
            try:
                if p.stat().st_size > max_file_size:
                    logger.warning("Skipping oversized java file (%d bytes): %s", p.stat().st_size, p)
                    continue
            except OSError:
                continue
            java_files.append(p)

        logger.info(
            "Java analyzer: processing %d .java files (excluded: %d, include_tests: %s) in %s",
            len(java_files),
            files_excluded,
            include_tests,
            root,
        )

        from parsers.fingerprint import (
            DEFAULT_RANDOM_SEED,
            PARSER_VERSION,
            compute_analysis_id,
            compute_settings_hash,
            compute_source_fingerprint,
            get_git_commit_sha,
        )

        source_fingerprint, _ = compute_source_fingerprint(root)
        commit_sha = get_git_commit_sha(root)
        settings_hash = compute_settings_hash(
            {"language": "java", "include_tests": include_tests, "large_class_loc": LARGE_CLASS_LOC_THRESHOLD}
        )
        repo_id = compute_analysis_id(
            source_fingerprint=source_fingerprint,
            parser_version=PARSER_VERSION,
            settings_hash=settings_hash,
            language="java",
            include_tests=include_tests,
        )

        # Clean path: never leak machine-specific absolute path or temporary clone directory
        clean_path = root.name if ("archlens_clone_" in str(root) or root.is_absolute()) else root.as_posix()
        if not clean_path:
            clean_path = "."

        if not _JAVALANG_AVAILABLE:
            return AnalysisResult(
                repo_id=repo_id,
                path=clean_path,
                language=self.language,
                graph=DependencyGraph(nodes=[], edges=[]),
                smells=[],
                commit_sha=commit_sha,
                parser_version=PARSER_VERSION,
                settings_hash=settings_hash,
                source_fingerprint=source_fingerprint,
                truncated=False,
                truncated_counts={},
                random_seed=DEFAULT_RANDOM_SEED,
            )

        for java_file in java_files:
            source = java_file.read_text(encoding="utf-8", errors="replace")
            loc = source.count("\n") + 1

            try:
                tree = javalang.parse.parse(source)
            except Exception as exc:  # javalang raises various parse errors
                logger.warning("Parse error in %s: %s", java_file, exc)
                continue

            # Determine package prefix
            package = tree.package.name if tree.package else ""
            rel_path = java_file.relative_to(root).as_posix()

            # ── Import edges ────────────────────────────────────────────────
            import_targets: list[str] = []
            for imp in tree.imports or []:
                if imp.path:
                    import_targets.append(imp.path)

            # ── Class / interface nodes ─────────────────────────────────────
            for _path, node in tree:
                if not isinstance(node, javalang.tree.ClassDeclaration | javalang.tree.InterfaceDeclaration):
                    continue

                fqn = f"{package}.{node.name}" if package else node.name
                node_type = NodeType.CLASS if isinstance(node, javalang.tree.ClassDeclaration) else NodeType.INTERFACE

                if fqn not in seen_nodes:
                    nodes.append(
                        GraphNode(
                            id=fqn,
                            label=node.name,
                            type=node_type,
                            language="java",
                            file_path=rel_path,
                            loc=loc,
                            cyclomatic_complexity=1.0,
                            max_complexity=1,
                            mean_complexity=1.0,
                        )
                    )
                    seen_nodes.add(fqn)

                # ── Inheritance edges ───────────────────────────────────────
                if isinstance(node, javalang.tree.ClassDeclaration) and node.extends:
                    parent_name = node.extends.name
                    parent_fqn = f"{package}.{parent_name}" if package else parent_name
                    parent_map[fqn] = parent_fqn
                    if parent_fqn != fqn:
                        key = (fqn, parent_fqn)
                        if key not in seen_edges:
                            edges.append(GraphEdge(source=fqn, target=parent_fqn, edge_type="inherit", weight=1.0))
                            seen_edges.add(key)

                # ── Interface implementation edges ──────────────────────────
                if isinstance(node, javalang.tree.ClassDeclaration) and node.implements:
                    for iface in node.implements:
                        iface_fqn = f"{package}.{iface.name}" if package else iface.name
                        if iface_fqn != fqn:
                            key = (fqn, iface_fqn)
                            if key not in seen_edges:
                                edges.append(GraphEdge(source=fqn, target=iface_fqn, edge_type="implement", weight=1.0))
                                seen_edges.add(key)

                # ── Import edges for this class ─────────────────────────────
                ext_deps_for_node: dict[str, str] = {}
                for imp_target in sorted(import_targets):
                    if imp_target == fqn:
                        continue
                    cat = "stdlib" if imp_target.startswith(("java.", "javax.")) else "third_party"
                    ext_deps_for_node[imp_target] = cat

                    key = (fqn, imp_target)
                    if key not in seen_edges:
                        edges.append(GraphEdge(source=fqn, target=imp_target, edge_type="import", weight=1.0))
                        seen_edges.add(key)

                current_node = next((n for n in nodes if n.id == fqn), None)
                if current_node:
                    current_node.external_dependencies = [
                        ExternalDependency(name=k, category=v) for k, v in sorted(ext_deps_for_node.items())
                    ]

        # Compute Louvain communities
        from analysis.community import compute_louvain_communities
        from analysis.graph import DirectedGraph

        directed_g = DirectedGraph()
        for n in nodes:
            directed_g.add_node(n.id)
        for e in edges:
            directed_g.add_edge(e.source, e.target, weight=e.weight)

        comm_res = compute_louvain_communities(directed_g)
        for n in nodes:
            n.community = comm_res.node_to_community.get(n.id, 0)

        # Normalize clean_path
        repo_leaf_name = root.name
        if repo_leaf_name.startswith("archlens_clone_") or repo_leaf_name.startswith("archlens_workspace_"):
            parts = repo_leaf_name.split("_")
            repo_leaf_name = parts[-1]
        if not repo_leaf_name or repo_leaf_name.lower() in ("repository", "codebase", "temp", "tmp", "src"):
            if root.parent and root.parent.name and root.parent.name.lower() not in ("workspaces", "temp", "tmp"):
                repo_leaf_name = root.parent.name
            else:
                repo_leaf_name = "Codebase"

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
        inheritance_map: dict[str, str] = {}

        for edge in result.graph.edges:
            if edge.edge_type == "inherit":
                inheritance_map[edge.source] = edge.target

        for node in sorted(result.graph.nodes, key=lambda n: n.id):
            # ── Large class ─────────────────────────────────────────────────
            if node.loc and node.loc > LARGE_CLASS_LOC_THRESHOLD:
                smells.append(
                    Smell(
                        type=SmellType.LARGE_CLASS,
                        file=node.file_path or node.id,
                        severity=SmellSeverity.HIGH,
                        description=(
                            f"Class '{node.label}' has {node.loc} lines "
                            f"(threshold: {LARGE_CLASS_LOC_THRESHOLD}). "
                            "Consider decomposing into smaller classes."
                        ),
                        suggestion="Apply Single Responsibility Principle; extract cohesive methods.",
                    )
                )

            # ── Deep inheritance ─────────────────────────────────────────────
            depth = 0
            current = node.id
            visited: set[str] = set()
            while current in inheritance_map and current not in visited:
                visited.add(current)
                current = inheritance_map[current]
                depth += 1
            if depth > DEEP_INHERITANCE_THRESHOLD:
                smells.append(
                    Smell(
                        type=SmellType.DEEP_INHERITANCE,
                        file=node.file_path or node.id,
                        severity=SmellSeverity.MEDIUM,
                        description=(
                            f"Class '{node.label}' has inheritance depth of {depth} "
                            f"(threshold: {DEEP_INHERITANCE_THRESHOLD}). "
                            "Deep hierarchies make code fragile."
                        ),
                        suggestion="Prefer composition over deep inheritance chains.",
                    )
                )

        smells.sort(key=lambda s: (s.severity.value, s.type.value, s.file, s.description))
        return smells
