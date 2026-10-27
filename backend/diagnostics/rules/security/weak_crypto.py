"""AST-based rule detecting weak cryptographic algorithms (MD5, SHA-1, DES)."""

from __future__ import annotations

import ast
import re
import warnings
from pathlib import Path

from diagnostics.models import Finding, Severity
from diagnostics.rules.base import SecurityRule

WEAK_ALGORITHMS = frozenset({"md5", "sha1", "sha-1", "des", "rc4", "3des", "desede"})


def _extract_string_value(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


class WeakCryptoRule(SecurityRule):
    """Detects usage of broken or weak cryptographic algorithms (MD5, SHA1, DES)."""

    id = "SEC-WEAK-CRYPTO"
    name = "Weak Cryptographic Algorithm"
    severity = Severity.HIGH
    cwe = "CWE-327: Use of a Broken or Risky Cryptographic Algorithm"
    owasp = "A02:2021-Cryptographic Failures"
    remediation = (
        "Upgrade to collision-resistant algorithms such as SHA-256, SHA-512, or SHA-3 for hashing, "
        "and AES-256-GCM for encryption. Avoid MD5, SHA-1, and DES."
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
            if isinstance(node, ast.Call):
                line_no = getattr(node, "lineno", None)
                snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None

                # Case 1: hashlib.md5(), hashlib.sha1()
                if isinstance(node.func, ast.Attribute):
                    attr_name = node.func.attr.lower()
                    # Check module/class name: e.g. DES.new or hashlib.md5
                    mod_id = ""
                    if isinstance(node.func.value, ast.Name):
                        mod_id = node.func.value.id
                    elif isinstance(node.func.value, ast.Attribute):
                        mod_id = node.func.value.attr

                    # Case 1: DES.new(...) or Cipher.DES.new(...)
                    if attr_name == "new" and mod_id == "DES":
                        findings.append(
                            self.create_finding(
                                message="Insecure DES cipher instantiated (DES.new).",
                                file_path=str(file_path),
                                line_number=line_no,
                                snippet=snippet,
                                metadata={"algorithm": "DES"},
                            )
                        )
                    # Case 2: hashlib.md5(), hashlib.sha1()
                    elif attr_name in ("md5", "sha1") and mod_id == "hashlib":
                        findings.append(
                            self.create_finding(
                                message=f"Weak hash algorithm 'hashlib.{attr_name}' used.",
                                file_path=str(file_path),
                                line_number=line_no,
                                snippet=snippet,
                                metadata={"algorithm": attr_name.upper()},
                            )
                        )
                    # Case 3: hashlib.new("md5"), hashlib.new("sha1")
                    elif attr_name == "new" and mod_id == "hashlib" and node.args:
                        arg0 = _extract_string_value(node.args[0])
                        if arg0 and arg0.lower() in WEAK_ALGORITHMS:
                            findings.append(
                                self.create_finding(
                                    message=f"Weak cryptographic algorithm '{arg0}' instantiated via hashlib.new().",
                                    file_path=str(file_path),
                                    line_number=line_no,
                                    snippet=snippet,
                                    metadata={"algorithm": arg0.upper()},
                                )
                            )

        return findings

    def _check_java(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()

        try:
            import javalang

            tree = javalang.parse.parse(content)

            for _, call in tree.filter(javalang.tree.MethodInvocation):
                if call.member == "getInstance" and call.arguments:
                    arg0 = call.arguments[0]
                    if isinstance(arg0, javalang.tree.Literal) and isinstance(arg0.value, str):
                        clean_algo = arg0.value.strip("'\"").lower()
                        for weak in WEAK_ALGORITHMS:
                            if weak in clean_algo:
                                pos = getattr(call, "position", None)
                                line_no = pos.line if pos else None
                                snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None
                                findings.append(
                                    self.create_finding(
                                        message=(
                                            f"Weak cryptographic algorithm '{arg0.value.strip('\"')}' "
                                            "used in Java getInstance."
                                        ),
                                        file_path=str(file_path),
                                        line_number=line_no,
                                        snippet=snippet,
                                        metadata={"algorithm": arg0.value.strip('"')},
                                    )
                                )
                                break
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("javalang parsing failed: %s", exc)

        # Regex fallback for MessageDigest or Cipher
        pattern = re.compile(r'getInstance\s*\(\s*["\'](MD5|SHA-?1|DES(?:ede)?)[^"\']*["\']', re.IGNORECASE)
        for idx, line in enumerate(lines, 1):
            if any(f.line_number == idx for f in findings):
                continue
            m = pattern.search(line)
            if m:
                findings.append(
                    self.create_finding(
                        message=f"Weak cryptographic algorithm '{m.group(1)}' detected in getInstance().",
                        file_path=str(file_path),
                        line_number=idx,
                        snippet=line.strip(),
                        metadata={"algorithm": m.group(1)},
                    )
                )

        return findings

    def _check_javascript(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()
        weak_hash_pat = re.compile(
            r"""crypto\.createHash\s*\(\s*["'](md5|sha1|sha-1|des|rc4)["']""",
            re.IGNORECASE,
        )
        weak_cipher_pat = re.compile(
            r"""crypto\.createCipher(?:iv)?\s*\(\s*["'](des|rc4|3des|des-ede)["']""",
            re.IGNORECASE,
        )
        for idx, line in enumerate(lines, 1):
            sline = line.strip()
            if sline.startswith("//") or sline.startswith("/*"):
                continue
            m = weak_hash_pat.search(line) or weak_cipher_pat.search(line)
            if m:
                algo = m.group(1).upper()
                findings.append(
                    self.create_finding(
                        message=f"Weak cryptographic algorithm '{algo}' used in Node.js crypto.",
                        file_path=str(file_path),
                        line_number=idx,
                        snippet=sline,
                        metadata={"algorithm": algo},
                    )
                )
        return findings
