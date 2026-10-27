"""Tree-sitter common utilities, language mappings, shebang detection, and complexity scoring."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tree_sitter import Language, Parser

# ── Extension to Language Mapping ─────────────────────────────────────────────

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    # Tier 1
    ".py": "python",
    ".pyw": "python",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".go": "go",
    # Tier 2
    ".cs": "csharp",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hh": "cpp",
    ".hxx": "cpp",
    ".rs": "rust",
    ".php": "php",
    ".phtml": "php",
    ".rb": "ruby",
    ".kt": "kotlin",
    ".kts": "kotlin",
}

# ── Shebang Matchers ──────────────────────────────────────────────────────────

SHEBANG_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^#!\s*(?:/usr/bin/env\s+)?python[0-9.]*"), "python"),
    (re.compile(r"^#!\s*(?:/usr/bin/env\s+)?node"), "javascript"),
    (re.compile(r"^#!\s*(?:/usr/bin/env\s+)?ruby"), "ruby"),
    (re.compile(r"^#!\s*(?:/usr/bin/env\s+)?php"), "php"),
]


def detect_language(path: Path, first_line: str = "") -> str:
    """Detect language from file extension or shebang line."""
    ext = path.suffix.lower()
    if ext in EXTENSION_TO_LANGUAGE:
        return EXTENSION_TO_LANGUAGE[ext]

    if first_line.startswith("#!"):
        for pattern, lang in SHEBANG_PATTERNS:
            if pattern.match(first_line.strip()):
                return lang

    return "unknown"


# ── Lazy-Loaded Tree-Sitter Parsers ───────────────────────────────────────────

_PARSER_CACHE: dict[str, Parser] = {}


def get_tree_sitter_parser(language: str) -> Parser | None:
    """Return a configured tree-sitter Parser for the given language."""
    lang_key = language.lower()
    if lang_key in _PARSER_CACHE:
        return _PARSER_CACHE[lang_key]

    try:
        lang_obj = None
        if lang_key == "go":
            import tree_sitter_go as ts_mod

            lang_obj = Language(ts_mod.language())
        elif lang_key in ("javascript", "js"):
            import tree_sitter_javascript as ts_mod

            lang_obj = Language(ts_mod.language())
        elif lang_key in ("typescript", "ts"):
            import tree_sitter_typescript as ts_mod

            lang_obj = Language(ts_mod.language_typescript())
        elif lang_key in ("csharp", "cs"):
            import tree_sitter_c_sharp as ts_mod

            lang_obj = Language(ts_mod.language())
        elif lang_key == "rust":
            import tree_sitter_rust as ts_mod

            lang_obj = Language(ts_mod.language())
        elif lang_key in ("cpp", "c++"):
            import tree_sitter_cpp as ts_mod

            lang_obj = Language(ts_mod.language())
        elif lang_key == "c":
            import tree_sitter_c as ts_mod

            lang_obj = Language(ts_mod.language())
        elif lang_key == "php":
            import tree_sitter_php as ts_mod

            lang_obj = Language(ts_mod.language_php())
        elif lang_key == "ruby":
            import tree_sitter_ruby as ts_mod

            lang_obj = Language(ts_mod.language())
        elif lang_key == "kotlin":
            import tree_sitter_kotlin as ts_mod

            lang_obj = Language(ts_mod.language())
        elif lang_key == "python":
            import tree_sitter_python as ts_mod

            lang_obj = Language(ts_mod.language())
        elif lang_key == "java":
            import tree_sitter_java as ts_mod

            lang_obj = Language(ts_mod.language())

        if lang_obj is not None:
            parser = Parser(lang_obj)
            _PARSER_CACHE[lang_key] = parser
            return parser
    except Exception:
        return None

    return None


# ── McCabe Cyclomatic Complexity by Language ──────────────────────────────────

BRANCH_NODE_TYPES: dict[str, set[str]] = {
    "go": {
        "if_statement",
        "for_statement",
        "expression_switch_statement",
        "type_switch_statement",
        "select_statement",
        "communication_case",
        "expression_case",
        "default_case",
    },
    "rust": {
        "if_expression",
        "for_expression",
        "while_expression",
        "loop_expression",
        "match_arm",
    },
    "csharp": {
        "if_statement",
        "for_statement",
        "for_each_statement",
        "while_statement",
        "do_statement",
        "switch_section",
        "catch_clause",
    },
    "c": {
        "if_statement",
        "for_statement",
        "while_statement",
        "do_statement",
        "case_statement",
    },
    "cpp": {
        "if_statement",
        "for_statement",
        "for_range_loop",
        "while_statement",
        "do_statement",
        "case_statement",
        "catch_clause",
    },
    "php": {
        "if_statement",
        "for_statement",
        "foreach_statement",
        "while_statement",
        "do_statement",
        "case_statement",
        "catch_clause",
    },
    "ruby": {
        "if",
        "unless",
        "while",
        "until",
        "for",
        "when",
        "rescue",
    },
    "kotlin": {
        "if_expression",
        "when_entry",
        "for_statement",
        "while_statement",
        "do_while_statement",
        "catch_block",
    },
    "javascript": {
        "if_statement",
        "for_statement",
        "for_in_statement",
        "for_of_statement",
        "while_statement",
        "do_statement",
        "switch_case",
        "catch_clause",
    },
    "typescript": {
        "if_statement",
        "for_statement",
        "for_in_statement",
        "for_of_statement",
        "while_statement",
        "do_statement",
        "switch_case",
        "catch_clause",
    },
}


def compute_ast_complexity(root_node: Any, language: str) -> int:
    """Calculate McCabe cyclomatic complexity: 1 + branch nodes."""
    lang_key = language.lower()
    branch_types = BRANCH_NODE_TYPES.get(lang_key, set())
    if not branch_types:
        return 1

    branches = 0
    stack = [root_node]
    while stack:
        curr = stack.pop()
        if curr.type in branch_types:
            branches += 1
        elif curr.type == "binary_expression":
            # Check for logical AND / OR operators
            for child in curr.children:
                if child.type in ("&&", "||", "and", "or"):
                    branches += 1
        stack.extend(curr.children)

    return max(1, 1 + branches)
