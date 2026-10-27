"""AST-based rule detecting SQL built by string concatenation."""

from __future__ import annotations

import ast
import re
import warnings
from pathlib import Path

from diagnostics.models import Finding, Severity
from diagnostics.rules.base import SecurityRule

SQL_KEYWORD_PATTERN = re.compile(
    r"\b(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|DROP\s+TABLE|CREATE\s+TABLE|ALTER\s+TABLE)\b",
    re.IGNORECASE,
)

SQL_EXEC_METHODS = frozenset(
    {
        "execute",
        "executemany",
        "raw",
        "cursor.execute",
        "executeQuery",
        "executeUpdate",
        "createNativeQuery",
    }
)


def _is_sql_string(s: str) -> bool:
    return bool(SQL_KEYWORD_PATTERN.search(s))


def _contains_sql_concat_binop(node: ast.AST) -> bool:
    """Check if node is an addition involving an SQL string literal."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        # Left or right is string literal with SQL keyword
        left_str = (
            isinstance(node.left, ast.Constant) and isinstance(node.left.value, str) and _is_sql_string(node.left.value)
        )
        right_str = (
            isinstance(node.right, ast.Constant)
            and isinstance(node.right.value, str)
            and _is_sql_string(node.right.value)
        )
        if left_str or right_str:
            return True
        return _contains_sql_concat_binop(node.left) or _contains_sql_concat_binop(node.right)
    return False


def _contains_sql_fstring(node: ast.AST) -> bool:
    """Check if node is an f-string containing SQL keyword and formatted values."""
    if isinstance(node, ast.JoinedStr):
        has_sql = False
        has_expr = False
        for val in node.values:
            if isinstance(val, ast.Constant) and isinstance(val.value, str) and _is_sql_string(val.value):
                has_sql = True
            elif isinstance(val, ast.FormattedValue):
                has_expr = True
        return has_sql and has_expr
    return False


def _contains_sql_format(node: ast.AST) -> bool:
    """Check if node is a % formatting or .format() call with SQL keyword."""
    # Modulo: "SELECT ... %s" % var
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str) and _is_sql_string(node.left.value):
            return True
    # .format() call: "SELECT ... {}".format(var)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        if (
            isinstance(node.func.value, ast.Constant)
            and isinstance(node.func.value.value, str)
            and _is_sql_string(node.func.value.value)
        ):
            return True
    return False


class SqlConcatenationRule(SecurityRule):
    """Detects SQL queries built via string concatenation or interpolation."""

    id = "SEC-SQL-CONCAT"
    name = "SQL Built by String Concatenation"
    severity = Severity.CRITICAL
    cwe = "CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')"
    owasp = "A03:2021-Injection"
    remediation = (
        "Use parameterized queries (e.g. cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,)) "
        "or PreparedStatement) instead of constructing SQL strings via concatenation or interpolation."
    )

    def check_file(self, file_path: Path, content: str, language: str) -> list[Finding]:
        findings: list[Finding] = []
        lang = language.lower()
        if lang in ("python", "py"):
            findings.extend(self._check_python(file_path, content))
        elif lang in ("java",):
            findings.extend(self._check_java(file_path, content))
        elif lang in ("javascript", "js", "typescript", "ts", "jsx", "tsx"):
            findings.extend(self._check_javascript(file_path, content))
        return findings

    def _check_python(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError:
                return findings

        lines = content.splitlines()

        for node in ast.walk(tree):
            line_no = getattr(node, "lineno", None)
            snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None

            # Case 1: Direct SQL concatenation in BinOp or JoinedStr
            if _contains_sql_concat_binop(node) or _contains_sql_fstring(node) or _contains_sql_format(node):
                # Check if this node is inside an assignment or call
                findings.append(
                    self.create_finding(
                        message="SQL query built using string concatenation or interpolation, risking SQL injection.",
                        file_path=str(file_path),
                        line_number=line_no,
                        column_number=getattr(node, "col_offset", None),
                        snippet=snippet,
                    )
                )

            # Case 2: Execution calls where argument 0 is a concatenation or f-string
            elif isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in ("execute", "executemany", "raw") and node.args:
                    arg0 = node.args[0]
                    # If arg0 is BinOp(+) or JoinedStr or % or format
                    if isinstance(arg0, ast.BinOp) and isinstance(arg0.op, ast.Add):
                        findings.append(
                            self.create_finding(
                                message=(
                                    "Dynamic string concatenation passed directly to SQL execution "
                                    f"method '{func_name}'."
                                ),
                                file_path=str(file_path),
                                line_number=line_no,
                                column_number=getattr(node, "col_offset", None),
                                snippet=snippet,
                            )
                        )
                    elif isinstance(arg0, ast.JoinedStr):
                        findings.append(
                            self.create_finding(
                                message=f"Formatted f-string passed directly to SQL execution method '{func_name}'.",
                                file_path=str(file_path),
                                line_number=line_no,
                                column_number=getattr(node, "col_offset", None),
                                snippet=snippet,
                            )
                        )

        # Deduplicate findings by line_number to avoid redundant hits on nested AST nodes
        unique_findings: list[Finding] = []
        seen_lines: set[int] = set()
        for f in findings:
            if f.line_number not in seen_lines:
                if f.line_number is not None:
                    seen_lines.add(f.line_number)
                unique_findings.append(f)

        return unique_findings

    def _check_java(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        try:
            import javalang

            tree = javalang.parse.parse(content)
        except Exception:
            # Fallback to AST-inspired token/line analysis if javalang fails on newer syntax
            return self._check_java_fallback(file_path, content)

        lines = content.splitlines()

        for _, bin_op in tree.filter(javalang.tree.BinaryOperation):
            if bin_op.operator == "+":
                # Check if left or right is string literal with SQL keyword
                left_is_sql = (
                    isinstance(bin_op.operandl, javalang.tree.Literal)
                    and isinstance(bin_op.operandl.value, str)
                    and _is_sql_string(bin_op.operandl.value)
                )
                right_is_sql = (
                    isinstance(bin_op.operandr, javalang.tree.Literal)
                    and isinstance(bin_op.operandr.value, str)
                    and _is_sql_string(bin_op.operandr.value)
                )

                if (left_is_sql and not isinstance(bin_op.operandr, javalang.tree.Literal)) or (
                    right_is_sql and not isinstance(bin_op.operandl, javalang.tree.Literal)
                ):
                    pos = getattr(bin_op, "position", None)
                    line_no = pos.line if pos else None
                    snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None
                    findings.append(
                        self.create_finding(
                            message="SQL query constructed via string concatenation with '+' operator in Java.",
                            file_path=str(file_path),
                            line_number=line_no,
                            column_number=pos.column if pos else None,
                            snippet=snippet,
                        )
                    )

        # Method calls like executeQuery with '+'
        for _, call in tree.filter(javalang.tree.MethodInvocation):
            if call.member in ("executeQuery", "executeUpdate", "createNativeQuery"):
                if call.arguments and any(
                    isinstance(a, javalang.tree.BinaryOperation) and a.operator == "+" for a in call.arguments
                ):
                    pos = getattr(call, "position", None)
                    line_no = pos.line if pos else None
                    if not any(f.line_number == line_no for f in findings):
                        snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None
                        findings.append(
                            self.create_finding(
                                message=f"Dynamic string concatenation passed directly to '{call.member}'.",
                                file_path=str(file_path),
                                line_number=line_no,
                                snippet=snippet,
                            )
                        )

        return findings

    def _check_java_fallback(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()
        for idx, line in enumerate(lines, 1):
            if _is_sql_string(line) and "+" in line and not line.strip().startswith("//"):
                findings.append(
                    self.create_finding(
                        message="SQL query built using string concatenation in Java.",
                        file_path=str(file_path),
                        line_number=idx,
                        snippet=line.strip(),
                    )
                )
        return findings

    def _check_javascript(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()
        sql_concat_pat = re.compile(
            r"""(?:\b(?:query|execute)\s*\(\s*["'].*?(?:SELECT|INSERT|UPDATE|DELETE|WHERE|FROM).*?["']\s*\+)|"""
            r"""(?:["'].*?(?:SELECT|INSERT|UPDATE|DELETE|WHERE|FROM).*?["']\s*\+\s*[a-zA-Z0-9_]+)|"""
            r"""(?:\b(?:query|execute)\s*\(\s*`.*?(?:SELECT|INSERT|UPDATE|DELETE|WHERE|FROM).*?\$\{.*?`)|"""
            r"""(?:`.*?(?:SELECT|INSERT|UPDATE|DELETE|WHERE|FROM).*?\$\{.*?`\s*\))""",
            re.IGNORECASE,
        )
        for idx, line in enumerate(lines, 1):
            sline = line.strip()
            if sline.startswith("//") or sline.startswith("/*"):
                continue
            if sql_concat_pat.search(line):
                findings.append(
                    self.create_finding(
                        message="SQL query constructed via string concatenation or template literal interpolation.",
                        file_path=str(file_path),
                        line_number=idx,
                        snippet=sline,
                        metadata={"type": "sql_concatenation"},
                    )
                )
        return findings
