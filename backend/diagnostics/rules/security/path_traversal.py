"""AST-based rule detecting path traversal vulnerabilities."""

from __future__ import annotations

import ast
import re
import warnings
from pathlib import Path

from diagnostics.models import Finding, Severity
from diagnostics.rules.base import SecurityRule

FILE_OPEN_FUNCS = frozenset({"open", "read_text", "read_bytes", "write_text", "write_bytes"})


def _is_path_concat(node: ast.AST) -> bool:
    """Check if AST node represents an unvalidated path concatenation."""
    # Addition with path separator like "/" or "\\"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        # Look for literal string with "/" or concatenation with variable
        if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
            if "/" in node.left.value or "\\" in node.left.value:
                # If right is a variable (Name or Attribute), it's string concat path
                if not isinstance(node.right, ast.Constant):
                    return True
        if isinstance(node.right, ast.Constant) and isinstance(node.right.value, str):
            if "/" in node.right.value or "\\" in node.right.value:
                if not isinstance(node.left, ast.Constant):
                    return True
        # Recurse
        return _is_path_concat(node.left) or _is_path_concat(node.right)

    # f-string containing "/" with dynamic formatted value
    if isinstance(node, ast.JoinedStr):
        has_slash = False
        has_expr = False
        for val in node.values:
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                if "/" in val.value or "\\" in val.value:
                    has_slash = True
            elif isinstance(val, ast.FormattedValue):
                has_expr = True
        return has_slash and has_expr

    return False


class PathTraversalRule(SecurityRule):
    """Detects path traversal vulnerabilities where file paths are constructed without sanitation."""

    id = "SEC-PATH-TRAVERSAL"
    name = "Path Traversal Vulnerability"
    severity = Severity.HIGH
    cwe = "CWE-22: Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')"
    owasp = "A01:2021-Broken Access Control"
    remediation = (
        "Sanitize untrusted file names with os.path.basename(), and verify resolved paths "
        "using Path.resolve() / os.path.commonpath() stay within the intended base directory."
    )

    def check_file(self, file_path: Path, content: str, language: str) -> list[Finding]:
        findings: list[Finding] = []
        if language == "python":
            findings.extend(self._check_python(file_path, content))
        elif language == "java":
            findings.extend(self._check_java(file_path, content))
        elif language in ("javascript", "typescript", "js", "ts"):
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

        # First pass: find variables assigned via path concatenation without sanitization
        concat_vars: dict[str, tuple[int, int | None]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and _is_path_concat(node.value):
                line_no = getattr(node, "lineno", None)
                snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None
                if snippet and "basename" not in snippet and "resolve" not in snippet and "commonpath" not in snippet:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            concat_vars[target.id] = (line_no or 1, getattr(node, "col_offset", None))

        # Second pass: check open() calls or unvalidated path concat assignments
        opened_concat_vars = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                line_no = getattr(node, "lineno", None)
                snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None

                # Check calls to open(...) with direct path concatenation or concatenated variable
                if func_name in ("open", "read_text", "write_text") and node.args:
                    arg0 = node.args[0]
                    is_direct_concat = _is_path_concat(arg0)
                    var_name = arg0.id if isinstance(arg0, ast.Name) else None
                    is_var_concat = var_name in concat_vars

                    if is_direct_concat or is_var_concat:
                        if snippet and "basename" not in snippet and "resolve" not in snippet:
                            findings.append(
                                self.create_finding(
                                    message=(
                                        "File opened with unvalidated path concatenation risking directory traversal."
                                    ),
                                    file_path=str(file_path),
                                    line_number=line_no,
                                    snippet=snippet,
                                )
                            )
                            if var_name:
                                opened_concat_vars.add(var_name)

        # Also flag any assigned path concat that wasn't directly in an open call
        for var_name, (line_no, col) in concat_vars.items():
            if var_name not in opened_concat_vars:
                snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None
                findings.append(
                    self.create_finding(
                        message=f"Path constructed via unvalidated concatenation in variable '{var_name}'.",
                        file_path=str(file_path),
                        line_number=line_no,
                        column_number=col,
                        snippet=snippet,
                    )
                )

        return findings

    def _check_java(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()

        try:
            import javalang

            tree = javalang.parse.parse(content)

            # Check new File(baseDir + "/" + userInput) or new FileInputStream(...)
            for _, creator in tree.filter(javalang.tree.ClassCreator):
                type_name = getattr(creator.type, "name", "")
                if type_name in ("File", "FileInputStream", "FileOutputStream", "FileReader", "FileWriter"):
                    if creator.arguments and any(
                        isinstance(a, javalang.tree.BinaryOperation) and a.operator == "+" for a in creator.arguments
                    ):
                        pos = getattr(creator, "position", None)
                        line_no = pos.line if pos else None
                        snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None
                        if snippet and "getCanonicalPath" not in snippet:
                            findings.append(
                                self.create_finding(
                                    message=(
                                        f"Path constructed via concatenation inside '{type_name}' "
                                        "without path traversal validation."
                                    ),
                                    file_path=str(file_path),
                                    line_number=line_no,
                                    snippet=snippet,
                                )
                            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("javalang parsing failed: %s", exc)

        # Fallback check
        pattern = re.compile(r"new\s+(?:File|FileInputStream)\s*\([^)]*\+[^)]*\)")
        for idx, line in enumerate(lines, 1):
            if any(f.line_number == idx for f in findings):
                continue
            if pattern.search(line) and "getCanonicalPath" not in line and not line.strip().startswith("//"):
                findings.append(
                    self.create_finding(
                        message="Potential path traversal via string concatenation in file instantiation.",
                        file_path=str(file_path),
                        line_number=idx,
                        snippet=line.strip(),
                    )
                )

        return findings

    def _check_javascript(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()

        # Match fs operations with dynamic concatenations or template literals:
        # e.g. fs.readFile(dir + '/' + file), fs.readFileSync(`...${input}...`)
        fs_patterns = [
            (
                re.compile(r"fs\.(?:readFile|readFileSync|createReadStream|createWriteStream|writeFile|writeFileSync)\s*\([^)]*(?:\+|`[^`]*\$\{)[^)]*\)"),
                "File operation with unvalidated dynamic path concatenation risking path traversal."
            ),
            (
                re.compile(r"(?:res\.sendFile|res\.download)\s*\([^)]*(?:\+|`[^`]*\$\{)[^)]*\)"),
                "Express res.sendFile / res.download with dynamic unvalidated path."
            ),
        ]

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            for pat, msg in fs_patterns:
                if pat.search(line):
                    findings.append(
                        self.create_finding(
                            message=msg,
                            file_path=str(file_path),
                            line_number=idx,
                            snippet=stripped,
                        )
                    )
                    break

        return findings
