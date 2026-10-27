"""Regression test ensuring PARSER_VERSION is bumped whenever analyzer logic changes."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from parsers.fingerprint import PARSER_VERSION

# Map of PARSER_VERSION -> expected analyzer source SHA-256 hash
# If analyzer files are modified, a new version must be declared and the expected hash updated.
KNOWN_ANALYZER_HASHES = {
    "1.1.0": "12931a1cb40c32d5479fa6a49f2d387d97e7f7616163fdb601e327231369ffa5",
    "1.2.0": "1c37252f8dbc99e6051620b39d184c7d259b265b6c32a0c29e1e4440dafc8361",
    "1.3.0": "49c77c5f316fa6623d132f3b5f650df62167651fcba4fcee7a1d6542e4f46837",
    "1.4.0": "342d3dd11eaf87fa094c7dd6c986b0420e7904960a76dfc87058a9f4bbd39c15",
    "1.5.0": "d6fe7f74e5f55c3532b5a782ad9c58c5886b52d39ce3d983043d88f6dd1afb65",
    "2.0.0": "23361cc6b631488897176f532c396047fe11f4ef1af6683362f1992913e70483",
}

ANALYZER_FILES = [
    Path("app/analyzers/base.py"),
    Path("app/analyzers/python_analyzer.py"),
    Path("app/analyzers/java_analyzer.py"),
    Path("app/analyzers/javascript_analyzer.py"),
    Path("app/analyzers/go_analyzer.py"),
    Path("app/analyzers/treesitter_analyzer.py"),
    Path("app/analyzers/treesitter_common.py"),
    Path("app/analyzers/multilang_analyzer.py"),
    Path("parsers/base.py"),
    Path("parsers/fingerprint.py"),
    Path("parsers/import_resolver.py"),
    Path("parsers/java_parser.py"),
    Path("parsers/python_parser.py"),
    Path("diagnostics/engine.py"),
    Path("diagnostics/rules/base.py"),
    Path("diagnostics/rules/security/command_injection.py"),
    Path("diagnostics/rules/security/disabled_tls.py"),
    Path("diagnostics/rules/security/hardcoded_secrets.py"),
    Path("diagnostics/rules/security/insecure_deserialization.py"),
    Path("diagnostics/rules/security/path_traversal.py"),
    Path("diagnostics/rules/security/sql_injection.py"),
    Path("diagnostics/rules/security/weak_crypto.py"),
    Path("diagnostics/rules/smells/cyclic_dependency.py"),
    Path("diagnostics/rules/smells/dead_code.py"),
    Path("diagnostics/rules/smells/deep_inheritance.py"),
    Path("diagnostics/rules/smells/feature_envy.py"),
    Path("diagnostics/rules/smells/god_class.py"),
    Path("diagnostics/rules/smells/high_coupling.py"),
    Path("diagnostics/rules/smells/long_method.py"),
]


def _compute_current_analyzer_hash(root: Path) -> str:
    hasher = hashlib.sha256()
    for rel_path in sorted(ANALYZER_FILES, key=lambda p: p.as_posix()):
        full_path = root / rel_path
        if not full_path.exists():
            full_path = root / "backend" / rel_path
        assert full_path.exists(), f"Expected analyzer file missing: {full_path}"
        content = full_path.read_bytes().replace(b"\r\n", b"\n")
        fhash = hashlib.sha256(content).hexdigest()
        hasher.update(f"{rel_path.as_posix()}:{fhash}\n".encode("utf-8"))
    return hasher.hexdigest()


def test_analyzer_source_changes_require_version_bump() -> None:
    """Fails if analyzer source files are modified without updating PARSER_VERSION and the version registry."""
    backend_root = Path(__file__).resolve().parent.parent.parent
    current_hash = _compute_current_analyzer_hash(backend_root)

    expected_hash = KNOWN_ANALYZER_HASHES.get(PARSER_VERSION)
    assert expected_hash is not None, (
        f"PARSER_VERSION '{PARSER_VERSION}' is not registered in KNOWN_ANALYZER_HASHES. "
        "Did you change PARSER_VERSION without adding the expected hash?"
    )

    assert current_hash == expected_hash, (
        f"Analyzer source files have been modified but PARSER_VERSION '{PARSER_VERSION}' was not bumped!\n"
        f"Current hash:  {current_hash}\n"
        f"Expected hash: {expected_hash}\n"
        "Please bump PARSER_VERSION in backend/parsers/fingerprint.py, backend/app/models/graph.py, "
        "and register the new version and hash in KNOWN_ANALYZER_HASHES."
    )
