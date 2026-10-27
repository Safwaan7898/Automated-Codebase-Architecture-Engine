"""AST-based rule detecting command injection (os.system, subprocess shell=True, Runtime.exec)."""

from __future__ import annotations

import ast
import re
import warnings
from pathlib import Path

from diagnostics.models import Finding, Severity
from diagnostics.rules.base import SecurityRule

SUBPROCESS_FUNCS = frozenset(
    {
        "run",
        "Popen",
        "call",
        "check_call",
        "check_output",
    }
)


class CommandInjectionRule(SecurityRule):
    """Detects command injection vulnerabilities in system execution calls."""

    id = "SEC-COMMAND-INJECTION"
    name = "Command Injection Risk"
    severity = Severity.CRITICAL
    cwe = "CWE-78: Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')"
    owasp = "A03:2021-Injection"
    remediation = (
        "Pass arguments as a list with shell=False when invoking subprocess commands. "
        "Avoid os.system() and Runtime.getRuntime().exec() with concatenated command strings."
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
                tree = None

        lines = content.splitlines()

        if tree:
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    line_no = getattr(node, "lineno", None)
                    snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None

                    # 1. Direct built-in calls: eval(...) and exec(...)
                    if isinstance(node.func, ast.Name):
                        if node.func.id == "eval":
                            findings.append(
                                self.create_finding(
                                    message="Dynamic code execution via 'eval()' allows arbitrary execution of untrusted input.",
                                    file_path=str(file_path),
                                    line_number=line_no,
                                    snippet=snippet,
                                    metadata={"function": "eval"},
                                    cwe="CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code ('Eval Injection')",
                                )
                            )
                        elif node.func.id == "exec":
                            findings.append(
                                self.create_finding(
                                    message="Dynamic code execution via 'exec()' allows arbitrary execution of untrusted input.",
                                    file_path=str(file_path),
                                    line_number=line_no,
                                    snippet=snippet,
                                    metadata={"function": "exec"},
                                    cwe="CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code ('Eval Injection')",
                                )
                            )

                    # 2. os.system(...) or os.popen(...)
                    elif isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                            if node.func.attr in ("system", "popen"):
                                findings.append(
                                    self.create_finding(
                                        message=f"Insecure system command execution via 'os.{node.func.attr}()'.",
                                        file_path=str(file_path),
                                        line_number=line_no,
                                        snippet=snippet,
                                        metadata={"module": "os", "function": node.func.attr},
                                    )
                                )

                        # 3. subprocess.*(..., shell=True) or subprocess calls
                        elif isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                            if node.func.attr in SUBPROCESS_FUNCS:
                                has_shell_true = any(
                                    kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True
                                    for kw in node.keywords
                                )
                                arg0 = node.args[0] if node.args else None
                                is_literal_list = isinstance(arg0, (ast.List, ast.Tuple))
                                is_dynamic_or_concat = isinstance(arg0, (ast.JoinedStr, ast.BinOp, ast.Name))

                                should_flag = False
                                if has_shell_true:
                                    should_flag = True
                                elif is_dynamic_or_concat and not is_literal_list:
                                    should_flag = True
                                elif is_literal_list and arg0.elts and isinstance(arg0.elts[0], (ast.Name, ast.BinOp, ast.JoinedStr)):
                                    should_flag = True

                                if should_flag:
                                    findings.append(
                                        self.create_finding(
                                            message=(
                                                f"Subprocess call 'subprocess.{node.func.attr}()' "
                                                f"{'with shell=True ' if has_shell_true else ''}invites command injection."
                                            ),
                                            file_path=str(file_path),
                                            line_number=line_no,
                                            snippet=snippet,
                                            metadata={
                                                "module": "subprocess",
                                                "function": node.func.attr,
                                                "shell": has_shell_true,
                                            },
                                        )
                                    )

        # Regex fallback for scripts
        py_patterns = [
            (re.compile(r"\b(?:os\.system|os\.popen)\s*\("), "Insecure system command execution via os.system/popen.", None),
            (re.compile(r"\bsubprocess\.(?:run|Popen|call|check_call|check_output)\s*\([^)]*shell\s*=\s*True", re.IGNORECASE), "Subprocess call with shell=True invites command injection.", None),
            (re.compile(r"\b(?:eval|exec)\s*\("), "Dynamic execution via eval/exec allows arbitrary code execution.", "CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code ('Eval Injection')"),
        ]
        for idx, line in enumerate(lines, 1):
            if any(f.line_number == idx for f in findings):
                continue
            if line.strip().startswith("#"):
                continue
            for pat, msg, cwe_override in py_patterns:
                if pat.search(line):
                    findings.append(
                        self.create_finding(
                            message=msg,
                            file_path=str(file_path),
                            line_number=idx,
                            snippet=line.strip(),
                            cwe=cwe_override,
                        )
                    )
                    break

        return findings

    def _check_javascript(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()

        patterns = [
            (
                re.compile(r"\b(?:child_process\.)?(?:exec|execSync)\s*\("),
                "Command execution via exec/execSync invites command injection.",
                "exec",
                None,
            ),
            (
                re.compile(r"\bchild_process\.spawn(?:Sync)?\s*\([^)]*shell:\s*true", re.IGNORECASE),
                "Child process spawn with shell: true invites command injection.",
                "spawn",
                None,
            ),
            (
                re.compile(r"\beval\s*\("),
                "Dynamic execution via eval() allows arbitrary code execution.",
                "eval",
                "CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code ('Eval Injection')",
            ),
            (
                re.compile(r"\b(?:new\s+)?Function\s*\("),
                "Dynamic code evaluation via Function constructor invites code injection.",
                "Function",
                "CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code ('Eval Injection')",
            ),
        ]

        for idx, line in enumerate(lines, 1):
            sline = line.strip()
            if sline.startswith("//") or sline.startswith("/*"):
                continue
            for pat, msg, target, cwe_override in patterns:
                if pat.search(line):
                    findings.append(
                        self.create_finding(
                            message=msg,
                            file_path=str(file_path),
                            line_number=idx,
                            snippet=sline,
                            metadata={"function": target},
                            cwe=cwe_override,
                        )
                    )
                    break
        return findings

    def _check_java(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()

        try:
            import javalang

            tree = javalang.parse.parse(content)

            # Check Runtime.getRuntime().exec(...) or runtime.exec(...)
            for _, call in tree.filter(javalang.tree.MethodInvocation):
                if call.member == "exec":
                    pos = getattr(call, "position", None)
                    line_no = pos.line if pos else None
                    snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None
                    findings.append(
                        self.create_finding(
                            message="Command execution via Runtime.exec() can lead to command injection.",
                            file_path=str(file_path),
                            line_number=line_no,
                            snippet=snippet,
                            metadata={"method": "Runtime.exec"},
                        )
                    )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("javalang parsing failed: %s", exc)

        # Regex fallback for unparsed Java files
        runtime_pat = re.compile(r"\b(?:Runtime\.getRuntime\(\)\.exec|runtime\.exec)\b")
        pb_concat_pat = re.compile(r"new\s+ProcessBuilder\s*\([^)]*\+[^)]*\)")
        pb_shell_pat = re.compile(r'new\s+ProcessBuilder\s*\(\s*["\'](?:sh|cmd|bash)["\']\s*,\s*["\']-[cC]["\']')

        for idx, line in enumerate(lines, 1):
            if any(f.line_number == idx for f in findings):
                continue
            if line.strip().startswith("//"):
                continue

            if runtime_pat.search(line):
                findings.append(
                    self.create_finding(
                        message="Potential command injection via Runtime.getRuntime().exec().",
                        file_path=str(file_path),
                        line_number=idx,
                        snippet=line.strip(),
                    )
                )
            elif pb_concat_pat.search(line) or pb_shell_pat.search(line):
                findings.append(
                    self.create_finding(
                        message=(
                            "Potential command injection in ProcessBuilder with "
                            "concatenated arguments or shell wrapper."
                        ),
                        file_path=str(file_path),
                        line_number=idx,
                        snippet=line.strip(),
                    )
                )

        return findings
