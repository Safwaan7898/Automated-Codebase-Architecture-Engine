"""Tree-sitter static analyzer for Tier 2 languages (C#, C/C++, Rust, PHP, Ruby, Kotlin).

Extracts structure (file, module, class, struct, interface, function) and syntactic
imports with edge confidence='parsed'. Calculates LOC and McCabe cyclomatic complexity.
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
from app.analyzers.treesitter_common import (
    compute_ast_complexity,
    detect_language,
    get_tree_sitter_parser,
)
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

# Ast node queries per language
AST_RULES: dict[str, dict[str, Any]] = {
    "rust": {
        "class_types": {"struct_item", "enum_item", "trait_item", "impl_item"},
        "func_types": {"function_item"},
        "import_types": {"use_declaration", "mod_item"},
    },
    "csharp": {
        "class_types": {"class_declaration", "interface_declaration", "struct_declaration", "record_declaration"},
        "func_types": {"method_declaration", "local_function_statement"},
        "import_types": {"using_directive"},
    },
    "c": {
        "class_types": {"struct_specifier", "union_specifier", "enum_specifier"},
        "func_types": {"function_definition"},
        "import_types": {"preproc_include"},
    },
    "cpp": {
        "class_types": {"class_specifier", "struct_specifier", "union_specifier"},
        "func_types": {"function_definition"},
        "import_types": {"preproc_include"},
    },
    "php": {
        "class_types": {"class_declaration", "interface_declaration", "trait_declaration"},
        "func_types": {"function_definition", "method_declaration"},
        "import_types": {"namespace_use_declaration", "require_expression", "include_expression"},
    },
    "ruby": {
        "class_types": {"class", "module"},
        "func_types": {"method", "singleton_method"},
        "import_types": {"call"},  # require, require_relative
    },
    "kotlin": {
        "class_types": {"class_declaration", "object_declaration"},
        "func_types": {"function_declaration"},
        "import_types": {"import_header"},
    },
}


class TreeSitterAnalyzer(BaseAnalyzer):
    """Analyzes Tier 2 languages using tree-sitter AST queries."""

    def __init__(self, target_language: str = "rust") -> None:
        self._target_language = target_language.lower()

    @property
    def language(self) -> str:
        return self._target_language

    def can_handle(self, path: Path) -> bool:
        if path.is_file():
            return detect_language(path) == self._target_language
        return any(
            detect_language(p) == self._target_language
            for p in path.rglob("*")
            if not any(part.startswith((".", "node_modules", "target", "vendor")) for part in p.parts)
        )

    def analyze(self, root: Path, include_tests: bool = False) -> AnalysisResult:
        root = root.resolve()
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        seen_nodes: set[str] = set()
        seen_edges: set[tuple[str, str]] = set()

        skip_dirs = {
            ".git",
            "node_modules",
            "venv",
            ".venv",
            "target",
            "bin",
            "obj",
            "vendor",
            ".idea",
            ".vscode",
            "data",
            "scratch",
        }
        test_dirs = {"test", "tests", "fixtures", "samples", "examples", "docs"}

        all_files = sorted(
            [
                p
                for p in root.rglob("*")
                if p.is_file()
                and detect_language(p) == self._target_language
                and not any(d in p.parts for d in skip_dirs)
            ],
            key=lambda p: p.as_posix(),
        )

        in_scope_files: list[Path] = []
        files_excluded = 0
        for f in all_files:
            rel_parts = f.relative_to(root).parts
            is_test = any(part.lower() in test_dirs for part in rel_parts)
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

        ts_parser = get_tree_sitter_parser(self._target_language)
        rules = AST_RULES.get(self._target_language, {})
        class_types = rules.get("class_types", set())
        func_types = rules.get("func_types", set())
        import_types = rules.get("import_types", set())

        file_to_mod_id: dict[Path, str] = {}
        for f in in_scope_files:
            rel_path = f.relative_to(root).as_posix()
            mod_id = rel_path.replace("/", ".").replace("\\", ".")
            ext = f.suffix
            if ext and mod_id.endswith(ext.replace("/", ".")):
                mod_id = mod_id[: -len(ext)]
            file_to_mod_id[f] = mod_id

        # ── Parse each file ───────────────────────────────────────────────────
        for f in in_scope_files:
            rel_posix = f.relative_to(root).as_posix()
            mod_id = file_to_mod_id[f]
            raw_bytes = f.read_bytes()
            lines = raw_bytes.splitlines()
            loc = len(lines)

            complexity = 1
            classes: list[str] = []
            functions: list[str] = []
            imports: list[str] = []

            if ts_parser:
                try:
                    tree = ts_parser.parse(raw_bytes)
                    complexity = compute_ast_complexity(tree.root_node, self._target_language)

                    def walk(
                        n: Any,
                        b: bytes = raw_bytes,
                        cls_list: list[str] = classes,
                        fn_list: list[str] = functions,
                        imp_list: list[str] = imports,
                    ) -> None:
                        if n.type in class_types:
                            # Extract identifier
                            for child in n.children:
                                if child.type in ("identifier", "type_identifier", "name"):
                                    c_name = b[child.start_byte : child.end_byte].decode("utf-8", errors="replace")
                                    cls_list.append(c_name)
                                    break
                        elif n.type in func_types:
                            for child in n.children:
                                if child.type in ("identifier", "field_identifier", "name"):
                                    fn_name = b[child.start_byte : child.end_byte].decode("utf-8", errors="replace")
                                    fn_list.append(fn_name)
                                    break
                        elif n.type in import_types:
                            imp_text = b[n.start_byte : n.end_byte].decode("utf-8", errors="replace").strip()
                            imp_list.append(imp_text)

                        for child in n.children:
                            walk(child, b, cls_list, fn_list, imp_list)

                    walk(tree.root_node)
                except Exception as exc:
                    logger.debug("Tree-sitter parse error for %s: %s", rel_posix, exc)

            # Add module node
            if mod_id not in seen_nodes:
                seen_nodes.add(mod_id)
                nodes.append(
                    GraphNode(
                        id=mod_id,
                        label=f.stem,
                        type=NodeType.MODULE,
                        language=self._target_language,
                        file_path=rel_posix,
                        loc=loc,
                        cyclomatic_complexity=float(complexity),
                        max_complexity=complexity,
                        mean_complexity=float(complexity),
                    )
                )

            # Add class nodes
            for c_name in set(classes):
                cid = f"{mod_id}.{c_name}"
                if cid not in seen_nodes:
                    seen_nodes.add(cid)
                    nodes.append(
                        GraphNode(
                            id=cid,
                            label=c_name,
                            type=NodeType.CLASS,
                            language=self._target_language,
                            file_path=rel_posix,
                            loc=0,
                            cyclomatic_complexity=1.0,
                            max_complexity=1,
                            mean_complexity=1.0,
                        )
                    )

            # Add function nodes
            for fn_name in set(functions):
                fid = f"{mod_id}.{fn_name}"
                if fid not in seen_nodes:
                    seen_nodes.add(fid)
                    nodes.append(
                        GraphNode(
                            id=fid,
                            label=fn_name,
                            type=NodeType.FUNCTION,
                            language=self._target_language,
                            file_path=rel_posix,
                            loc=0,
                            cyclomatic_complexity=1.0,
                            max_complexity=1,
                            mean_complexity=1.0,
                        )
                    )

            # Syntactic import edges
            for imp in imports:
                # Resolve relative or module targets where possible
                for other_file, other_mod_id in file_to_mod_id.items():
                    if other_mod_id != mod_id and (other_file.stem in imp or other_mod_id in imp):
                        if (mod_id, other_mod_id) not in seen_edges:
                            seen_edges.add((mod_id, other_mod_id))
                            edges.append(
                                GraphEdge(
                                    source=mod_id,
                                    target=other_mod_id,
                                    edge_type="import",
                                    confidence="parsed",
                                    weight=1.0,
                                )
                            )

        nodes.sort(key=lambda n: n.id)
        edges.sort(key=lambda e: (e.source, e.target))

        graph = DependencyGraph(nodes=nodes, edges=edges)
        result = AnalysisResult(
            repo_id=repo_id,
            path=root.name or "repository",
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
        for node in result.graph.nodes:
            if node.type == NodeType.MODULE and node.loc > 500:
                smells.append(
                    Smell(
                        type=SmellType.GOD_MODULE,
                        file=node.file_path or node.id,
                        severity=SmellSeverity.HIGH,
                        description=f"Module '{node.label}' has {node.loc} lines (threshold: 500).",
                        suggestion="Extract functions or classes into separate cohesive files.",
                    )
                )
        smells.sort(key=lambda s: (s.severity.value, s.type.value, s.file, s.description))
        return smells
