"""Go static analyzer using tree-sitter AST parsing.

Walks a directory tree, parses every .go file:
- Reads go.mod for canonical module root resolution
- Extracts Package, Module, Struct, Interface, and Function nodes
- Resolves internal package imports vs external/stdlib dependencies
- Computes per-file LOC and McCabe cyclomatic complexity
- Detects circular dependencies and god modules
"""

from __future__ import annotations

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
from app.analyzers.treesitter_common import compute_ast_complexity, get_tree_sitter_parser
from app.core.logging import get_logger
from app.models.graph import (
    AnalysisResult,
    DependencyGraph,
    ExternalDependency,
    GraphEdge,
    GraphNode,
    NodeType,
)
from app.models.refactor import Smell, SmellSeverity, SmellType

logger = get_logger(__name__)

GO_STDLIB_ROOTS = frozenset(
    {
        "archive",
        "bufio",
        "bytes",
        "compress",
        "container",
        "context",
        "crypto",
        "database",
        "debug",
        "encoding",
        "errors",
        "expvar",
        "flag",
        "fmt",
        "hash",
        "html",
        "image",
        "io",
        "log",
        "math",
        "mime",
        "net",
        "os",
        "path",
        "plugin",
        "reflect",
        "regexp",
        "runtime",
        "sort",
        "strconv",
        "strings",
        "sync",
        "syscall",
        "testing",
        "text",
        "time",
        "unicode",
        "unsafe",
    }
)


def _parse_go_mod(root: Path) -> str | None:
    """Read module path from go.mod if present."""
    go_mod = root / "go.mod"
    if not go_mod.exists():
        return None
    try:
        content = go_mod.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("module "):
                return line.split()[1]
    except Exception as exc:
        logger.debug("Failed reading go.mod from %s: %s", go_mod, exc)
    return None


class GoAnalyzer(BaseAnalyzer):
    """Analyzes Go codebases with full module and package import resolution."""

    @property
    def language(self) -> str:
        return "go"

    def can_handle(self, path: Path) -> bool:
        if path.is_file():
            return path.suffix.lower() == ".go"
        return any(
            p.suffix.lower() == ".go"
            for p in path.rglob("*")
            if not any(part.startswith((".", "vendor", "node_modules", "venv")) for part in p.parts)
        )

    def analyze(self, root: Path, include_tests: bool = False) -> AnalysisResult:
        root = root.resolve()
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        seen_nodes: set[str] = set()
        seen_edges: set[tuple[str, str]] = set()

        skip_dirs = {
            ".git",
            "vendor",
            "node_modules",
            "venv",
            ".venv",
            "bin",
            "dist",
            "build",
            ".idea",
            ".vscode",
            "data",
            "scratch",
        }
        test_dirs = {"test", "tests", "fixtures", "samples", "examples", "docs"}

        all_go_files = sorted(
            [p for p in root.rglob("*.go") if p.is_file() and not any(d in p.parts for d in skip_dirs)],
            key=lambda p: p.as_posix(),
        )

        in_scope_files: list[Path] = []
        files_excluded = 0
        for f in all_go_files:
            rel_parts = f.relative_to(root).parts
            is_test = any(part.lower() in test_dirs for part in rel_parts) or f.name.endswith("_test.go")
            if not include_tests and is_test:
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

        module_path = _parse_go_mod(root)
        ts_parser = get_tree_sitter_parser("go")

        # Map file -> package name, module id, imports, structs, functions
        file_to_info: dict[Path, dict[str, Any]] = {}
        pkg_to_files: dict[str, list[Path]] = {}

        for go_file in in_scope_files:
            rel_posix = go_file.relative_to(root).as_posix()
            mod_id = rel_posix.replace("/", ".").rstrip(".go")
            raw_bytes = go_file.read_bytes()
            source_text = raw_bytes.decode("utf-8", errors="replace")
            lines = source_text.splitlines()
            loc = len(lines)

            pkg_name = "main"
            imports: list[str] = []
            types: list[tuple[str, str]] = []  # (name, kind: struct/interface)
            functions: list[str] = []
            complexity = 1

            if ts_parser:
                tree = ts_parser.parse(raw_bytes)
                complexity = compute_ast_complexity(tree.root_node, "go")

                def walk_ast(
                    n: Any,
                    b: bytes = raw_bytes,
                    imp_list: list[str] = imports,
                    typ_list: list[tuple[str, str]] = types,
                    fn_list: list[str] = functions,
                ) -> None:
                    nonlocal pkg_name
                    if n.type == "package_clause":
                        for c in n.children:
                            if c.type == "package_identifier":
                                pkg_name = b[c.start_byte : c.end_byte].decode("utf-8", errors="replace")
                    elif n.type == "import_spec":
                        for c in n.children:
                            if c.type in ("interpreted_string_literal", "raw_string_literal"):
                                imp_val = b[c.start_byte : c.end_byte].decode("utf-8", errors="replace").strip('"`')
                                imp_list.append(imp_val)
                    elif n.type == "type_spec":
                        t_name = ""
                        t_kind = "class"
                        for c in n.children:
                            if c.type == "type_identifier":
                                t_name = b[c.start_byte : c.end_byte].decode("utf-8", errors="replace")
                            elif c.type == "struct_type":
                                t_kind = "struct"
                            elif c.type == "interface_type":
                                t_kind = "interface"
                        if t_name:
                            typ_list.append((t_name, t_kind))
                    elif n.type in ("function_declaration", "method_declaration"):
                        for c in n.children:
                            if c.type in ("identifier", "field_identifier"):
                                fn_name = b[c.start_byte : c.end_byte].decode("utf-8", errors="replace")
                                fn_list.append(fn_name)
                                break
                    for child in n.children:
                        walk_ast(child, b, imp_list, typ_list, fn_list)

                walk_ast(tree.root_node)

            file_info = {
                "rel_path": rel_posix,
                "mod_id": mod_id,
                "pkg_name": pkg_name,
                "loc": loc,
                "complexity": complexity,
                "imports": imports,
                "types": types,
                "functions": functions,
            }
            file_to_info[go_file] = file_info

            # Directory-based package identifier
            dir_rel = go_file.parent.relative_to(root).as_posix()
            pkg_key = dir_rel if dir_rel != "." else pkg_name
            pkg_to_files.setdefault(pkg_key, []).append(go_file)

        # ── Build Nodes ───────────────────────────────────────────────────────
        for go_file, info in file_to_info.items():
            mod_id = info["mod_id"]
            if mod_id not in seen_nodes:
                seen_nodes.add(mod_id)
                nodes.append(
                    GraphNode(
                        id=mod_id,
                        label=go_file.stem,
                        type=NodeType.MODULE,
                        language="go",
                        file_path=info["rel_path"],
                        loc=info["loc"],
                        cyclomatic_complexity=float(info["complexity"]),
                        max_complexity=info["complexity"],
                        mean_complexity=float(info["complexity"]),
                    )
                )

            for t_name, t_kind in info["types"]:
                type_id = f"{mod_id}.{t_name}"
                if type_id not in seen_nodes:
                    seen_nodes.add(type_id)
                    n_type = NodeType.INTERFACE if t_kind == "interface" else NodeType.CLASS
                    nodes.append(
                        GraphNode(
                            id=type_id,
                            label=t_name,
                            type=n_type,
                            language="go",
                            file_path=info["rel_path"],
                            loc=0,
                            cyclomatic_complexity=1.0,
                            max_complexity=1,
                            mean_complexity=1.0,
                        )
                    )

            for fn_name in info["functions"]:
                fn_id = f"{mod_id}.{fn_name}"
                if fn_id not in seen_nodes:
                    seen_nodes.add(fn_id)
                    nodes.append(
                        GraphNode(
                            id=fn_id,
                            label=fn_name,
                            type=NodeType.FUNCTION,
                            language="go",
                            file_path=info["rel_path"],
                            loc=0,
                            cyclomatic_complexity=1.0,
                            max_complexity=1,
                            mean_complexity=1.0,
                        )
                    )

        # ── Resolve Imports & Build Edges ─────────────────────────────────────
        external_deps_set: set[str] = set()

        for go_file, info in file_to_info.items():
            src_id = info["mod_id"]
            for imp in info["imports"]:
                target_node_id: str | None = None
                is_internal = False

                # 1. Resolve internal imports matching module_path
                if module_path and imp.startswith(module_path):
                    rel_subpkg = imp[len(module_path) :].lstrip("/")
                    # Find files in that package directory
                    matching = pkg_to_files.get(rel_subpkg, [])
                    if matching:
                        # Connect to primary file or first file in package
                        target_node_id = file_to_info[matching[0]]["mod_id"]
                        is_internal = True

                # 2. Check relative import
                elif imp.startswith("."):
                    target_dir = (go_file.parent / imp).resolve()
                    try:
                        rel_dir = target_dir.relative_to(root).as_posix()
                        matching = pkg_to_files.get(rel_dir, [])
                        if matching:
                            target_node_id = file_to_info[matching[0]]["mod_id"]
                            is_internal = True
                    except ValueError:
                        pass

                # 3. Check direct directory matching (e.g. import "pkg/util")
                elif imp in pkg_to_files:
                    matching = pkg_to_files[imp]
                    if matching:
                        target_node_id = file_to_info[matching[0]]["mod_id"]
                        is_internal = True

                if is_internal and target_node_id:
                    if (src_id, target_node_id) not in seen_edges and src_id != target_node_id:
                        seen_edges.add((src_id, target_node_id))
                        edges.append(
                            GraphEdge(
                                source=src_id,
                                target=target_node_id,
                                edge_type="import",
                                confidence="resolved",
                                weight=1.0,
                            )
                        )
                else:
                    external_deps_set.add(imp)

        # External dependencies classification
        ext_deps: list[ExternalDependency] = []
        for imp in sorted(external_deps_set):
            root_pkg = imp.split("/")[0]
            cat = "stdlib" if root_pkg in GO_STDLIB_ROOTS else "third_party"
            ext_deps.append(ExternalDependency(name=imp, category=cat))

        nodes.sort(key=lambda n: n.id)
        edges.sort(key=lambda e: (e.source, e.target))

        graph = DependencyGraph(nodes=nodes, edges=edges)
        result = AnalysisResult(
            repo_id=repo_id,
            path=root.name or "repository",
            language=self.language,
            graph=graph,
            smells=[],
            external_dependencies=ext_deps,
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
        adjacency: dict[str, set[str]] = {}
        for edge in result.graph.edges:
            adjacency.setdefault(edge.source, set()).add(edge.target)

        # God module detection (> 500 lines)
        for node in result.graph.nodes:
            if node.type == NodeType.MODULE and node.loc > 500:
                smells.append(
                    Smell(
                        type=SmellType.GOD_MODULE,
                        file=node.file_path or node.id,
                        severity=SmellSeverity.HIGH,
                        description=f"Go module '{node.label}' has {node.loc} lines (threshold: 500).",
                        suggestion="Decompose package or extract cohesive structs into separate files.",
                    )
                )

        # Circular import detection (DFS)
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
                                description=f"Circular dependency detected between '{node_id}' and '{neighbor}'.",
                                suggestion=(
                                    "Refactor package structure or extract shared types into an interfaces package."
                                ),
                            )
                        )
            rec_stack.discard(node_id)

        for n in result.graph.nodes:
            if n.type == NodeType.MODULE and n.id not in visited:
                dfs(n.id, [n.id])

        smells.sort(key=lambda s: (s.severity.value, s.type.value, s.file, s.description))
        return smells
