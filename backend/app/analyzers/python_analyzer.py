"""Python static analyzer using the built-in `ast` module.

Walks a directory tree, parses every .py file, extracts:
- Module nodes (one per file)
- Import edges (import / from … import)
- Class and top-level function definitions

Detects smells:
- God module  (> 500 lines)
- Missing type hints on public functions
- Circular imports (cycle detection via DFS)
"""

from __future__ import annotations

import ast
import sys
import warnings
from pathlib import Path

from diagnostics.scoring import compute_codebase_health

from app.analyzers.base import BaseAnalyzer
from app.core.logging import get_logger
from app.models.graph import AnalysisResult, DependencyGraph, ExternalDependency, GraphEdge, GraphNode, NodeType
from app.models.refactor import Smell, SmellSeverity, SmellType

logger = get_logger(__name__)

# Lines-of-code threshold for "god module" detection
GOD_MODULE_LOC_THRESHOLD = 500
MISSING_HINTS_LOC_THRESHOLD = 50  # only flag larger modules


def _compute_function_mccabe(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """
    Compute McCabe cyclomatic complexity per function:
    1 + if/elif/for/while/except/bool ops/comprehension ifs/match cases.
    """
    complexity = 1
    nodes_to_visit = list(func_node.body)
    while nodes_to_visit:
        curr = nodes_to_visit.pop()
        # Nested functions have their own McCabe complexity calculation
        if isinstance(curr, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue

        if isinstance(curr, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(curr, ast.BoolOp):
            complexity += max(0, len(curr.values) - 1)
        elif isinstance(curr, ast.comprehension):
            complexity += len(curr.ifs)
        elif hasattr(ast, "match_case") and isinstance(curr, ast.match_case):
            complexity += 1

        for child in ast.iter_child_nodes(curr):
            nodes_to_visit.append(child)

    return complexity


def _module_id(file_path: Path, root: Path) -> str:
    """Convert an absolute file path to a dot-separated repo-relative module identifier."""
    try:
        rel = file_path.relative_to(root)
    except ValueError:
        rel = file_path
    parts = list(rel.parts)
    # Strip any drive letters, root markers, or temp clone prefixes
    parts = [p for p in parts if p not in ("/", "\\") and not p.endswith(":")]
    parts = [p for p in parts if not p.startswith("archlens_clone_") and not p.startswith("archlens_workspace_")]
    if parts and parts[-1] == "__init__.py":
        parts = parts[:-1]
    elif parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    return ".".join(parts) if parts else "root"


def _classify_external_dep(name: str) -> str:
    """Classify an external dependency name as 'stdlib', 'third_party', or 'unresolved'."""
    clean = name.strip()
    if clean.startswith("."):
        return "unresolved"
    root = clean.split(".")[0]
    if not root or not root.isidentifier():
        return "unresolved"
    stdlib_names = getattr(sys, "stdlib_module_names", set()) | set(sys.builtin_module_names)
    if root in stdlib_names:
        return "stdlib"
    return "third_party"


def _get_path_suffixes(rel_parts: list[str]) -> list[str]:
    """Given path parts (e.g. ['backend', 'app', 'services', 'x']), return all dotted suffixes.

    Example: ['backend.app.services.x', 'app.services.x', 'services.x', 'x']
    """
    return [".".join(rel_parts[i:]) for i in range(len(rel_parts)) if rel_parts[i:]]


def _resolve_candidate(
    candidate_key: str,
    current_mod: str,
    suffix_map: dict[str, list[str]],
    ambiguity_tracker: list[int],
) -> str | None:
    """Resolve candidate dotted name against suffix map with deterministic tie-breaking.

    If multiple distinct candidates match:
    - Ambiguity counter is incremented.
    - Tie-breaking: matches in the same top-level directory come first, then lexicographic.
    """
    candidates = suffix_map.get(candidate_key)
    if not candidates:
        return None

    unique_candidates = sorted(set(candidates))
    if len(unique_candidates) == 1:
        return unique_candidates[0]

    # Ambiguity detected
    ambiguity_tracker[0] += 1

    curr_top = current_mod.split(".")[0] if current_mod != "root" else ""
    same_top = [c for c in unique_candidates if c.split(".")[0] == curr_top]
    if same_top:
        return sorted(same_top)[0]

    return unique_candidates[0]


def _resolve_import_entries(
    module: str | None,
    names: list[str],
    level: int,
    current_mod: str,
    is_init: bool,
    suffix_to_modules: dict[str, list[str]],
    suffix_to_symbols: dict[str, list[str]],
    ambiguity_tracker: list[int],
) -> list[tuple[str | None, str | None]]:
    """Resolve import statement to list of (internal_target_id, external_dep_name).

    Uses longest match across indexed dotted-name suffixes and symbols.
    """
    results: list[tuple[str | None, str | None]] = []

    if level > 0:
        # Relative import
        parts = current_mod.split(".") if current_mod != "root" else []
        pkg_parts = parts if is_init else (parts[:-1] if len(parts) > 1 else [])
        up_levels = level - 1
        if up_levels > len(pkg_parts):
            raw = f"{'.' * level}{module or (names[0] if names else '')}"
            return [(None, raw.split(".")[0] or raw)]

        base_parts = pkg_parts[: len(pkg_parts) - up_levels] if up_levels > 0 else pkg_parts
        base_pkg = ".".join(base_parts)

        if module:
            target_prefix = f"{base_pkg}.{module}" if base_pkg else module
            for name in names:
                candidate_sub = f"{target_prefix}.{name}"
                matched = (
                    _resolve_candidate(candidate_sub, current_mod, suffix_to_symbols, ambiguity_tracker)
                    or _resolve_candidate(candidate_sub, current_mod, suffix_to_modules, ambiguity_tracker)
                    or _resolve_candidate(target_prefix, current_mod, suffix_to_symbols, ambiguity_tracker)
                    or _resolve_candidate(target_prefix, current_mod, suffix_to_modules, ambiguity_tracker)
                )
                if matched:
                    results.append((matched, None))
                else:
                    results.append((None, candidate_sub.split(".")[0]))
        else:
            for name in names:
                candidate = f"{base_pkg}.{name}" if base_pkg else name
                matched = (
                    _resolve_candidate(candidate, current_mod, suffix_to_symbols, ambiguity_tracker)
                    or _resolve_candidate(candidate, current_mod, suffix_to_modules, ambiguity_tracker)
                    or (base_pkg and _resolve_candidate(base_pkg, current_mod, suffix_to_modules, ambiguity_tracker))
                )
                if matched:
                    results.append((matched, None))
                else:
                    results.append((None, candidate.split(".")[0]))
        return results

    # Absolute import (level == 0)
    if module:
        mod_parts = module.split(".")
        for name in names:
            candidate_full = f"{module}.{name}"
            # 1. Longest match: check full candidate symbol or module
            matched = (
                _resolve_candidate(candidate_full, current_mod, suffix_to_symbols, ambiguity_tracker)
                or _resolve_candidate(candidate_full, current_mod, suffix_to_modules, ambiguity_tracker)
                or _resolve_candidate(module, current_mod, suffix_to_symbols, ambiguity_tracker)
                or _resolve_candidate(module, current_mod, suffix_to_modules, ambiguity_tracker)
            )
            if matched:
                results.append((matched, None))
                continue

            # 2. Descending prefixes for longest match
            found_prefix = False
            for i in range(len(mod_parts) - 1, 0, -1):
                prefix = ".".join(mod_parts[:i])
                prefix_matched = _resolve_candidate(prefix, current_mod, suffix_to_modules, ambiguity_tracker)
                if prefix_matched:
                    results.append((prefix_matched, None))
                    found_prefix = True
                    break

            if not found_prefix:
                root_pkg = mod_parts[0]
                results.append((None, root_pkg))
    else:
        for name in names:
            name_parts = name.split(".")
            found_name = False
            for i in range(len(name_parts), 0, -1):
                prefix = ".".join(name_parts[:i])
                matched = _resolve_candidate(
                    prefix, current_mod, suffix_to_symbols, ambiguity_tracker
                ) or _resolve_candidate(prefix, current_mod, suffix_to_modules, ambiguity_tracker)
                if matched:
                    results.append((matched, None))
                    found_name = True
                    break
            if not found_name:
                root_pkg = name_parts[0]
                results.append((None, root_pkg))

    return results


class PythonAnalyzer(BaseAnalyzer):
    """Analyzes Python codebases via ast parsing."""

    @property
    def language(self) -> str:
        return "python"

    def can_handle(self, path: Path) -> bool:
        py_files = list(path.rglob("*.py"))
        return bool(py_files)

    def analyze(self, root: Path, include_tests: bool = False) -> AnalysisResult:
        root = root.resolve()
        nodes: list[GraphNode] = []
        seen_nodes: set[str] = set()

        base_skip_dirs = {
            "node_modules",
            ".git",
            "venv",
            ".venv",
            "build",
            "dist",
            "__pycache__",
            ".tox",
            ".idea",
            ".vscode",
            ".reports_storage",
            "reports_output",
            "data",
            "scratch",
        }
        test_scope_dirs = {
            "tests",
            "test",
            "fixtures",
            "samples",
            "examples",
            "docs",
            "migrations",
        }
        raw_py_files = sorted(root.rglob("*.py"), key=lambda p: p.as_posix())
        py_files: list[Path] = []
        max_file_size = 5 * 1024 * 1024  # 5 MB size limit
        files_excluded = 0

        for p in raw_py_files:
            try:
                rel = p.relative_to(root)
                rel_parts = rel.parts
            except ValueError:
                rel_parts = p.parts
            rel_dirs = set(rel_parts[:-1])

            if any(part in base_skip_dirs for part in rel_dirs):
                continue
            if not include_tests:
                if (
                    any(part in test_scope_dirs for part in rel_dirs)
                    or p.name.startswith("test_")
                    or p.name.endswith("_test.py")
                ):
                    files_excluded += 1
                    continue
            try:
                if p.stat().st_size > max_file_size:
                    logger.warning("Skipping oversized python file (%d bytes): %s", p.stat().st_size, p)
                    continue
            except OSError:
                continue
            py_files.append(p)

        logger.info(
            "Python analyzer: processing %d .py files (excluded: %d, include_tests: %s) in %s",
            len(py_files),
            files_excluded,
            include_tests,
            root,
        )

        parsed_trees: dict[Path, tuple[str, list[str], str, ast.AST]] = {}
        internal_modules: set[str] = set()
        suffix_to_modules: dict[str, list[str]] = {}
        suffix_to_symbols: dict[str, list[str]] = {}
        is_init_by_mod: dict[str, bool] = {}

        # ── Pass 1: Parse AST, index dotted-name suffixes and symbols ────────
        for py_file in py_files:
            try:
                rel = py_file.relative_to(root)
            except ValueError:
                rel = py_file
            raw_parts = [p for p in rel.parts if p not in ("/", "\\") and not p.endswith(":")]
            raw_parts = [
                p for p in raw_parts if not p.startswith("archlens_clone_") and not p.startswith("archlens_workspace_")
            ]
            is_init = bool(raw_parts and raw_parts[-1] == "__init__.py")

            if is_init:
                mod_parts = list(raw_parts[:-1])
            elif raw_parts and raw_parts[-1].endswith(".py"):
                mod_parts = [*raw_parts[:-1], raw_parts[-1][:-3]]
            else:
                mod_parts = list(raw_parts)

            mod_id = ".".join(mod_parts) if mod_parts else "root"
            source = py_file.read_text(encoding="utf-8", errors="replace")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                try:
                    tree = ast.parse(source, filename=str(py_file))
                except SyntaxError as exc:
                    logger.warning("Syntax error in %s: %s", py_file, exc)
                    continue

            parsed_trees[py_file] = (mod_id, mod_parts, source, tree)
            internal_modules.add(mod_id)
            is_init_by_mod[mod_id] = is_init

            # Index every dotted-name suffix of the file's path
            for s in _get_path_suffixes(mod_parts):
                if mod_id not in suffix_to_modules.setdefault(s, []):
                    suffix_to_modules[s].append(mod_id)

            # Index symbols (classes and functions) and their suffixes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_id = f"{mod_id}.{node.name}"
                    for s in _get_path_suffixes([*mod_parts, node.name]):
                        if mod_id not in suffix_to_symbols.setdefault(s, []):
                            suffix_to_symbols[s].append(mod_id)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for s in _get_path_suffixes([*mod_parts, node.name]):
                        if mod_id not in suffix_to_symbols.setdefault(s, []):
                            suffix_to_symbols[s].append(mod_id)

        # ── Pass 2: Build nodes and resolve internal edges vs external deps ──
        internal_edge_weights: dict[tuple[str, str], float] = {}
        external_deps_by_mod: dict[str, dict[str, str]] = {}
        ambiguity_tracker = [0]

        for py_file, (mod_id, _mod_parts, source, tree) in parsed_trees.items():
            loc = source.count("\n") + 1
            # McCabe cyclomatic complexity per function (1 + branch points)
            module_funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            func_complexities = [_compute_function_mccabe(fn) for fn in module_funcs]
            if func_complexities:
                mean_cc = round(sum(func_complexities) / len(func_complexities), 2)
                max_cc = max(func_complexities)
            else:
                mean_cc = 1.0
                max_cc = 1

            rel_file_path = py_file.relative_to(root).as_posix()
            if mod_id not in seen_nodes:
                nodes.append(
                    GraphNode(
                        id=mod_id,
                        label=mod_id.split(".")[-1],
                        type=NodeType.MODULE,
                        language="python",
                        file_path=rel_file_path,
                        loc=loc,
                        cyclomatic_complexity=mean_cc,
                        max_complexity=max_cc,
                        mean_complexity=mean_cc,
                    )
                )
                seen_nodes.add(mod_id)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_id = f"{mod_id}.{node.name}"
                    if class_id not in seen_nodes:
                        class_funcs = [
                            n
                            for n in ast.walk(node)
                            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not node
                        ]
                        class_complexities = [_compute_function_mccabe(fn) for fn in class_funcs]
                        if class_complexities:
                            c_mean = round(sum(class_complexities) / len(class_complexities), 2)
                            c_max = max(class_complexities)
                        else:
                            c_mean = 1.0
                            c_max = 1
                        class_loc = (
                            node.end_lineno - node.lineno + 1 if hasattr(node, "end_lineno") and node.end_lineno else 0
                        )
                        nodes.append(
                            GraphNode(
                                id=class_id,
                                label=node.name,
                                type=NodeType.CLASS,
                                language="python",
                                file_path=rel_file_path,
                                loc=class_loc,
                                cyclomatic_complexity=c_mean,
                                max_complexity=c_max,
                                mean_complexity=c_mean,
                            )
                        )
                        seen_nodes.add(class_id)

            # Resolve imports in this file
            is_init = is_init_by_mod.get(mod_id, False)
            mod_ext_deps = external_deps_by_mod.setdefault(mod_id, {})

            for node in ast.walk(tree):
                resolved_entries: list[tuple[str | None, str | None]] = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                    resolved_entries = _resolve_import_entries(
                        None, names, 0, mod_id, is_init, suffix_to_modules, suffix_to_symbols, ambiguity_tracker
                    )
                elif isinstance(node, ast.ImportFrom):
                    names = [alias.name for alias in node.names]
                    resolved_entries = _resolve_import_entries(
                        node.module,
                        names,
                        node.level or 0,
                        mod_id,
                        is_init,
                        suffix_to_modules,
                        suffix_to_symbols,
                        ambiguity_tracker,
                    )

                for target_mod, ext_dep in resolved_entries:
                    if target_mod and target_mod in internal_modules:
                        # Self-loop guard
                        if target_mod != mod_id:
                            edge_key = (mod_id, target_mod)
                            internal_edge_weights[edge_key] = internal_edge_weights.get(edge_key, 0.0) + 1.0
                    elif ext_dep:
                        category = _classify_external_dep(ext_dep)
                        mod_ext_deps[ext_dep] = category

        # Attach external dependencies to nodes
        for node in nodes:
            if node.id in external_deps_by_mod:
                deps_dict = external_deps_by_mod[node.id]
                node.external_dependencies = [
                    ExternalDependency(name=name, category=cat) for name, cat in sorted(deps_dict.items())
                ]

        # Sort nodes deterministically by ID
        nodes.sort(key=lambda n: n.id)

        # Build deduplicated edges with weights in deterministic order
        edges = [
            GraphEdge(source=src, target=dst, weight=w, edge_type="import")
            for (src, dst), w in sorted(internal_edge_weights.items())
        ]
        edges.sort(key=lambda e: (e.source, e.target))

        # Aggregate codebase-wide external dependencies
        global_ext_deps: dict[str, str] = {}
        for deps_dict in external_deps_by_mod.values():
            global_ext_deps.update(deps_dict)

        codebase_external_deps = [
            ExternalDependency(name=name, category=cat) for name, cat in sorted(global_ext_deps.items())
        ]

        # Mark cycle edges using Tarjan SCC
        from analysis.graph import DirectedGraph
        from analysis.scc import detect_circular_dependencies

        directed_g = DirectedGraph()
        for n in nodes:
            directed_g.add_node(n.id)
        for e in edges:
            directed_g.add_edge(e.source, e.target, weight=e.weight)

        scc_cycles = detect_circular_dependencies(directed_g)
        cycle_edges = set()
        for c in scc_cycles:
            for s, d in getattr(c, "edges", []):
                cycle_edges.add((s, d))

        for e in edges:
            if (e.source, e.target) in cycle_edges:
                e.is_cycle = True

        # Compute Louvain communities deterministically
        from analysis.community import compute_louvain_communities

        comm_res = compute_louvain_communities(directed_g)
        for n in nodes:
            n.community = comm_res.node_to_community.get(n.id, 0)

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
            {
                "language": "python",
                "include_tests": include_tests,
                "god_module_loc": GOD_MODULE_LOC_THRESHOLD,
                "missing_hints": MISSING_HINTS_LOC_THRESHOLD,
            }
        )
        repo_id = compute_analysis_id(
            source_fingerprint=source_fingerprint,
            parser_version=PARSER_VERSION,
            settings_hash=settings_hash,
            language="python",
            include_tests=include_tests,
        )

        # Clean path: never leak machine-specific absolute path or temporary clone directory
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

        graph = DependencyGraph(nodes=nodes, edges=edges)
        result = AnalysisResult(
            repo_id=repo_id,
            path=clean_path,
            language=self.language,
            graph=graph,
            smells=[],
            external_dependencies=codebase_external_deps,
            commit_sha=commit_sha,
            parser_version=PARSER_VERSION,
            settings_hash=settings_hash,
            source_fingerprint=source_fingerprint,
            truncated=False,
            truncated_counts={"files_excluded": files_excluded} if files_excluded else {},
            random_seed=DEFAULT_RANDOM_SEED,
            ambiguous_imports=ambiguity_tracker[0],
            files_excluded=files_excluded,
            include_tests=include_tests,
        )
        result.smells = [s.model_dump(mode="json") for s in self.detect_smells(result)]
        result.health = compute_codebase_health(
            nodes=result.graph.nodes,
            edges=result.graph.edges,
            smells=result.smells,
            cycles=len(scc_cycles),
        )
        return result

    def detect_smells(self, result: AnalysisResult) -> list[Smell]:
        smells: list[Smell] = []
        adjacency: dict[str, set[str]] = {}

        for edge in result.graph.edges:
            adjacency.setdefault(edge.source, set()).add(edge.target)

        # Iterate over sorted nodes for deterministic smell detection
        for node in sorted(result.graph.nodes, key=lambda n: n.id):
            if node.type != NodeType.MODULE:
                continue

            # ── God module ──────────────────────────────────────────────────
            if node.loc and node.loc > GOD_MODULE_LOC_THRESHOLD:
                smells.append(
                    Smell(
                        type=SmellType.GOD_MODULE,
                        file=node.file_path or node.id,
                        severity=SmellSeverity.HIGH,
                        description=(
                            f"Module '{node.label}' has {node.loc} lines "
                            f"(threshold: {GOD_MODULE_LOC_THRESHOLD}). "
                            "Consider splitting into smaller modules."
                        ),
                        suggestion="Extract cohesive responsibilities into separate modules.",
                    )
                )

        # ── Circular import detection (DFS) ─────────────────────────────────
        visited: set[str] = set()
        rec_stack: set[str] = set()
        reported_cycles: set[frozenset[str]] = set()

        def dfs(node_id: str, path: list[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            for neighbor in sorted(adjacency.get(node_id, set())):
                if neighbor not in visited:
                    dfs(neighbor, [*path, neighbor])
                elif neighbor in rec_stack:
                    cycle = frozenset([node_id, neighbor])
                    if cycle not in reported_cycles:
                        reported_cycles.add(cycle)
                        smells.append(
                            Smell(
                                type=SmellType.CIRCULAR_IMPORT,
                                file=node_id,
                                severity=SmellSeverity.CRITICAL,
                                description=f"Circular import detected between '{node_id}' and '{neighbor}'.",
                                suggestion="Introduce an abstraction layer or restructure dependencies.",
                            )
                        )
            rec_stack.discard(node_id)

        module_ids = sorted([n.id for n in result.graph.nodes if n.type == NodeType.MODULE])
        for mid in module_ids:
            if mid not in visited:
                dfs(mid, [mid])

        smells.sort(key=lambda s: (s.severity.value, s.type.value, s.file, s.description))
        return smells
