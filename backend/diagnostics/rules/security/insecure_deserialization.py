"""AST-based rule detecting insecure deserialization (Python pickle/yaml.load, Java ObjectInputStream)."""

from __future__ import annotations

import ast
import re
import warnings
from pathlib import Path

from diagnostics.models import Finding, Severity
from diagnostics.rules.base import SecurityRule


class InsecureDeserializationRule(SecurityRule):
    """Detects insecure deserialization of untrusted payloads."""

    id = "SEC-INSECURE-DESERIALIZATION"
    name = "Insecure Deserialization"
    severity = Severity.CRITICAL
    cwe = "CWE-502: Deserialization of Untrusted Data"
    owasp = "A08:2021-Software and Data Integrity Failures"
    remediation = (
        "Avoid using pickle, shelve, or Java ObjectInputStream for untrusted data. "
        "Use safe serialization formats like JSON with schema validation, or yaml.safe_load()."
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

                # 1. pickle.loads / pickle.load / _pickle.loads
                if isinstance(node.func, ast.Attribute):
                    mod_name = ""
                    if isinstance(node.func.value, ast.Name):
                        mod_name = node.func.value.id

                    if mod_name in ("pickle", "_pickle") and node.func.attr in ("load", "loads"):
                        findings.append(
                            self.create_finding(
                                message=(
                                    f"Insecure deserialization using '{mod_name}.{node.func.attr}' "
                                    "allows arbitrary code execution."
                                ),
                                file_path=str(file_path),
                                line_number=line_no,
                                snippet=snippet,
                                metadata={"module": mod_name, "function": node.func.attr},
                            )
                        )

                    # 2. shelve.open(...)
                    elif mod_name == "shelve" and node.func.attr == "open":
                        findings.append(
                            self.create_finding(
                                message=(
                                    "Insecure deserialization using 'shelve.open' which uses pickle under the hood."
                                ),
                                file_path=str(file_path),
                                line_number=line_no,
                                snippet=snippet,
                                metadata={"module": "shelve"},
                            )
                        )

                    # 3. yaml.load(...) without SafeLoader
                    elif mod_name == "yaml" and node.func.attr == "load":
                        # Check keyword args for Loader=SafeLoader
                        has_safe_loader = False
                        for kw in node.keywords:
                            if kw.arg == "Loader":
                                # e.g. yaml.SafeLoader or SafeLoader
                                if isinstance(kw.value, ast.Attribute) and kw.value.attr == "SafeLoader":
                                    has_safe_loader = True
                                elif isinstance(kw.value, ast.Name) and kw.value.id == "SafeLoader":
                                    has_safe_loader = True

                        if not has_safe_loader:
                            findings.append(
                                self.create_finding(
                                    message=(
                                        "Insecure 'yaml.load()' without SafeLoader allows arbitrary "
                                        "Python object execution. Use yaml.safe_load()."
                                    ),
                                    file_path=str(file_path),
                                    line_number=line_no,
                                    snippet=snippet,
                                    metadata={"module": "yaml", "function": "load"},
                                )
                            )

        return findings

    def _check_java(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()

        try:
            import javalang

            tree = javalang.parse.parse(content)

            # Check new ObjectInputStream(...)
            for _, creator in tree.filter(javalang.tree.ClassCreator):
                type_name = getattr(creator.type, "name", "")
                if type_name in ("ObjectInputStream", "XMLDecoder"):
                    pos = getattr(creator, "position", None)
                    line_no = pos.line if pos else None
                    snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None
                    findings.append(
                        self.create_finding(
                            message=f"Insecure Java deserialization using '{type_name}' enables remote code execution.",
                            file_path=str(file_path),
                            line_number=line_no,
                            snippet=snippet,
                            metadata={"class": type_name},
                        )
                    )

            # Check .readObject() calls
            for _, call in tree.filter(javalang.tree.MethodInvocation):
                if call.member == "readObject":
                    pos = getattr(call, "position", None)
                    line_no = pos.line if pos else None
                    if not any(f.line_number == line_no for f in findings):
                        snippet = lines[line_no - 1].strip() if line_no and line_no <= len(lines) else None
                        findings.append(
                            self.create_finding(
                                message="Insecure Java deserialization via '.readObject()'.",
                                file_path=str(file_path),
                                line_number=line_no,
                                snippet=snippet,
                                metadata={"method": "readObject"},
                            )
                        )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("javalang parsing failed: %s", exc)

        # Regex fallback
        ois_pattern = re.compile(r"\b(ObjectInputStream|XMLDecoder|\.readObject\s*\(\s*\))\b")
        for idx, line in enumerate(lines, 1):
            if any(f.line_number == idx for f in findings):
                continue
            if ois_pattern.search(line) and not line.strip().startswith("//"):
                findings.append(
                    self.create_finding(
                        message="Insecure Java deserialization mechanism detected in source.",
                        file_path=str(file_path),
                        line_number=idx,
                        snippet=line.strip(),
                    )
                )

        return findings

    def _check_javascript(self, file_path: Path, content: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()
        patterns = [
            (
                re.compile(r"\b(?:node-serialize|serialize)\.unserialize\s*\("),
                "Insecure deserialization via node-serialize unserialize() allows remote code execution.",
            ),
            (
                re.compile(r"\bunserialize\s*\("),
                "Potentially insecure deserialization via unserialize().",
            ),
            (
                re.compile(r"\bserialize-javascript\b"),
                "Deserialization library serialize-javascript detected.",
            ),
        ]
        for idx, line in enumerate(lines, 1):
            sline = line.strip()
            if sline.startswith("//") or sline.startswith("/*"):
                continue
            for pat, msg in patterns:
                if pat.search(line):
                    findings.append(
                        self.create_finding(
                            message=msg,
                            file_path=str(file_path),
                            line_number=idx,
                            snippet=sline,
                            metadata={"module": "javascript_deserialization"},
                        )
                    )
                    break
        return findings
