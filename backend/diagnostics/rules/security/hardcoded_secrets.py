"""AST-based rule detecting hardcoded secrets, API keys, and passwords."""

from __future__ import annotations

import ast
import math
import re
import warnings
from pathlib import Path

from diagnostics.models import Finding, Severity
from diagnostics.rules.base import SecurityRule

SECRET_NAME_PATTERN = re.compile(
    r"(?i)(api[_-]?key|secret[_-]?key|auth[_-]?token|access[_-]?token|private[_-]?key|client[_-]?secret|password|passwd|aws[_-]?secret)",
)

KNOWN_SECRET_PATTERNS = [
    re.compile(r"sk_live_[0-9a-zA-Z]{20,}"),
    re.compile(r"sk_test_[0-9a-zA-Z]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[0-9a-zA-Z]{36}"),
    re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"),
    re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"),  # JWT
]

BENIGN_VALUES = frozenset(
    {
        "",
        "changeme",
        "todo",
        "your_key",
        "your_api_key",
        "your_secret_here",
        "placeholder",
        "dummy",
        "admin",
        "password",
        "test",
        "root",
        "123456",
        "default",
        "env",
        "production",
        "development",
        "localhost",
    }
)


def _shannon_entropy(s: str) -> float:
    """Calculate the Shannon entropy of a string."""
    if not s:
        return 0.0
    entropy = 0.0
    length = len(s)
    counts: dict[str, int] = {}
    for c in s:
        counts[c] = counts.get(c, 0) + 1
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def _is_suspicious_secret(val: str) -> bool:
    """Determine whether a string value is likely an actual secret."""
    cleaned = val.strip().strip("'\"")
    if len(cleaned) < 10:
        return False
    if cleaned.lower() in BENIGN_VALUES:
        return False
    # Check known patterns
    for pat in KNOWN_SECRET_PATTERNS:
        if pat.search(cleaned):
            return True
    # Entropy check for longer strings
    if len(cleaned) >= 16:
        has_alpha = any(c.isalpha() for c in cleaned)
        has_digit = any(c.isdigit() for c in cleaned)
        if has_alpha and has_digit and _shannon_entropy(cleaned) >= 3.0:
            return True
    return False


class HardcodedSecretsRule(SecurityRule):
    """Detects hardcoded API keys, secrets, passwords, and tokens."""

    id = "SEC-HARDCODED-SECRET"
    name = "Hardcoded Secret Detected"
    severity = Severity.HIGH
    cwe = "CWE-798: Use of Hard-coded Credentials"
    owasp = "A07:2021-Identification and Authentication Failures"
    remediation = (
        "Store sensitive keys, tokens, and passwords in environment variables or a secure secret manager "
        "(e.g. AWS Secrets Manager, HashiCorp Vault) rather than hardcoding them in source code."
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
            # Target assignments: variable = "secret"
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    var_name = ""
                    if isinstance(target, ast.Name):
                        var_name = target.id
                    elif isinstance(target, ast.Attribute):
                        var_name = target.attr

                    if var_name and SECRET_NAME_PATTERN.search(var_name):
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            val = node.value.value
                            if _is_suspicious_secret(val):
                                line_no = getattr(node, "lineno", None)
                                snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None
                                findings.append(
                                    self.create_finding(
                                        message=f"Hardcoded secret detected in variable '{var_name}'.",
                                        file_path=str(file_path),
                                        line_number=line_no,
                                        column_number=getattr(node, "col_offset", None),
                                        snippet=snippet,
                                        metadata={"variable": var_name},
                                    )
                                )

            # Also check direct literals matching known high-confidence token prefixes
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                for pat in KNOWN_SECRET_PATTERNS:
                    if pat.search(node.value):
                        line_no = getattr(node, "lineno", None)
                        if not any(f.line_number == line_no for f in findings):
                            snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None
                            findings.append(
                                self.create_finding(
                                    message="Hardcoded secret token pattern detected in source code.",
                                    file_path=str(file_path),
                                    line_number=line_no,
                                    column_number=getattr(node, "col_offset", None),
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

            # Check variable declarations
            for _, decl in tree.filter(javalang.tree.VariableDeclarator):
                var_name = decl.name
                if SECRET_NAME_PATTERN.search(var_name):
                    init = decl.initializer
                    if isinstance(init, javalang.tree.Literal) and isinstance(init.value, str):
                        if _is_suspicious_secret(init.value):
                            pos = getattr(decl, "position", None)
                            line_no = pos.line if pos else None
                            snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None
                            findings.append(
                                self.create_finding(
                                    message=f"Hardcoded secret detected in Java variable '{var_name}'.",
                                    file_path=str(file_path),
                                    line_number=line_no,
                                    snippet=snippet,
                                    metadata={"variable": var_name},
                                )
                            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("javalang parsing failed: %s", exc)

        # Also fallback regex for known token patterns
        for idx, line in enumerate(lines, 1):
            if any(f.line_number == idx for f in findings):
                continue
            for pat in KNOWN_SECRET_PATTERNS:
                if pat.search(line):
                    findings.append(
                        self.create_finding(
                            message="Hardcoded secret token pattern detected in Java source.",
                            file_path=str(file_path),
                            line_number=idx,
                            snippet=line.strip(),
                        )
                    )
                    break

        return findings

    def _check_javascript(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()
        js_secret_var = re.compile(
            r"""(?:const|let|var)\s+([a-zA-Z0-9_]*(?:api_?key|secret|password|passwd|token|auth_?token|jwt|private_?key)[a-zA-Z0-9_]*)\s*[:=]\s*["']([^"']{8,})["']""",
            re.IGNORECASE,
        )
        js_secret_prop = re.compile(
            r"""["']?([a-zA-Z0-9_]*(?:api_?key|secret|password|passwd|token|auth_?token|jwt|private_?key)[a-zA-Z0-9_]*)["']?\s*:\s*["']([^"']{8,})["']""",
            re.IGNORECASE,
        )
        for idx, line in enumerate(lines, 1):
            sline = line.strip()
            if sline.startswith("//") or sline.startswith("/*"):
                continue
            m = js_secret_var.search(line) or js_secret_prop.search(line)
            if m:
                var_name, val = m.group(1), m.group(2)
                if _is_suspicious_secret(val):
                    findings.append(
                        self.create_finding(
                            message=f"Hardcoded secret detected in JavaScript variable '{var_name}'.",
                            file_path=str(file_path),
                            line_number=idx,
                            snippet=sline,
                            metadata={"variable": var_name},
                        )
                    )
                    continue
            for pat in KNOWN_SECRET_PATTERNS:
                if pat.search(line):
                    findings.append(
                        self.create_finding(
                            message="Hardcoded secret token pattern detected in JavaScript source.",
                            file_path=str(file_path),
                            line_number=idx,
                            snippet=sline,
                        )
                    )
                    break
        return findings
