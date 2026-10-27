"""AST-based rule detecting disabled TLS / SSL certificate verification."""

from __future__ import annotations

import ast
import re
import warnings
from pathlib import Path

from diagnostics.models import Finding, Severity
from diagnostics.rules.base import SecurityRule

HTTP_LIBS = frozenset({"requests", "httpx"})
HTTP_METHODS = frozenset(
    {"get", "post", "put", "delete", "patch", "head", "options", "request", "Client", "AsyncClient", "Session"}
)


class DisabledTlsVerificationRule(SecurityRule):
    """Detects code explicitly disabling TLS/SSL certificate validation."""

    id = "SEC-DISABLED-TLS"
    name = "Disabled TLS / SSL Verification"
    severity = Severity.HIGH
    cwe = "CWE-295: Improper Certificate Validation"
    owasp = "A07:2021-Identification and Authentication Failures"
    remediation = (
        "Never disable TLS verification in production. Retain verify=True (the default), "
        "and specify custom CA certificate paths if communicating with private/internal authorities."
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

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                line_no = getattr(node, "lineno", None)
                snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None

                # 1. verify=False in requests / httpx calls
                for kw in node.keywords:
                    if kw.arg == "verify" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                        findings.append(
                            self.create_finding(
                                message="TLS certificate verification disabled via 'verify=False'.",
                                file_path=str(file_path),
                                line_number=line_no,
                                snippet=snippet,
                                metadata={"param": "verify", "value": False},
                            )
                        )
                        break

                # 2. ssl._create_unverified_context()
                if isinstance(node.func, ast.Attribute) and node.func.attr == "_create_unverified_context":
                    findings.append(
                        self.create_finding(
                            message="Creation of unverified SSL context via 'ssl._create_unverified_context()'.",
                            file_path=str(file_path),
                            line_number=line_no,
                            snippet=snippet,
                        )
                    )

                # 3. urllib3 cert_reqs='CERT_NONE'
                for kw in node.keywords:
                    if kw.arg == "cert_reqs" and isinstance(kw.value, ast.Constant) and kw.value.value == "CERT_NONE":
                        findings.append(
                            self.create_finding(
                                message="TLS certificate validation disabled via 'cert_reqs=CERT_NONE'.",
                                file_path=str(file_path),
                                line_number=line_no,
                                snippet=snippet,
                            )
                        )

        return findings

    def _check_java(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()

        # Check for trust-all trust managers or hostname verifiers
        patterns = [
            (
                re.compile(r"setDefaultHostnameVerifier\s*\(\s*\([^)]*\)\s*->\s*true\s*\)"),
                "Hostname verification globally bypassed with '(hostname, session) -> true'.",
            ),
            (
                re.compile(r"\bALLOW_ALL_HOSTNAME_VERIFIER\b"),
                "Insecure ALLOW_ALL_HOSTNAME_VERIFIER used.",
            ),
            (
                re.compile(r"checkServerTrusted\s*\([^)]*\)\s*\{\s*\}"),
                "Empty checkServerTrusted method creates a trust-all X509TrustManager.",
            ),
            (
                re.compile(r"checkClientTrusted\s*\([^)]*\)\s*\{\s*\}"),
                "Empty checkClientTrusted method disables client certificate verification.",
            ),
        ]

        for idx, line in enumerate(lines, 1):
            for pat, msg in patterns:
                if pat.search(line):
                    findings.append(
                        self.create_finding(
                            message=msg,
                            file_path=str(file_path),
                            line_number=idx,
                            snippet=line.strip(),
                        )
                    )

        # In case checkServerTrusted method body spans multiple lines, check full content
        multi_pat = re.compile(r"void\s+checkServerTrusted\s*\([^)]*\)\s*(?:throws[^{]+)?\{\s*\}", re.DOTALL)
        for m in multi_pat.finditer(content):
            line_no = content[: m.start()].count("\n") + 1
            if not any(f.line_number == line_no for f in findings):
                findings.append(
                    self.create_finding(
                        message="Empty checkServerTrusted method creates a trust-all X509TrustManager.",
                        file_path=str(file_path),
                        line_number=line_no,
                        snippet="void checkServerTrusted(...) { }",
                    )
                )

        return findings

    def _check_javascript(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()

        patterns = [
            (
                re.compile(r"rejectUnauthorized\s*:\s*false"),
                "TLS certificate verification disabled via 'rejectUnauthorized: false'.",
            ),
            (
                re.compile(r"NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]0['\"]"),
                "Node.js TLS certificate rejection globally disabled via NODE_TLS_REJECT_UNAUTHORIZED = '0'.",
            ),
        ]

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            for pat, msg in patterns:
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
