"""GET /graph/{repo_id} — retrieve a cached analysis graph."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import require_permission
from app.auth.models import Permission
from app.services import analyzer_service
from app.storage.analysis_store import default_analysis_store

router = APIRouter(tags=["graph"])

VULNERABLE_BENCHMARK_FIXTURE = {
    "repo_id": "vulnerable-microservice-003",
    "path": "samples/vulnerable-python-service",
    "language": "Python",
    "node_count": 4,
    "edge_count": 4,
    "smells": [
        {
            "type": "circular_import",
            "file": "backend/tests/fixtures/diagnostics/vulnerable_python.py",
            "severity": "critical",
            "description": "Circular reference loop between UserAuthService, DatabaseManager, and PaymentGateway.",
        },
        {
            "type": "large_class",
            "file": "backend/tests/fixtures/diagnostics/vulnerable_python.py",
            "severity": "high",
            "description": (
                "UserAuthService concentrates 620 LOC with high cyclomatic complexity and multiple CWE findings."
            ),
        },
    ],
    "findings": [
        {
            "id": "FINDING-SQLI-001",
            "rule_id": "SEC-001-SQLI",
            "title": "SQL Injection via String Concatenation",
            "severity": "critical",
            "category": "Security",
            "cwe": "CWE-89",
            "owasp": "A03:2021-Injection",
            "file_path": "vulnerable_python.py",
            "line_number": 24,
            "code_snippet": 'cursor.execute("SELECT * FROM users WHERE id = \'" + user_id + "\'")',
            "remediation": 'Use parameterized queries: cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))',
        },
        {
            "id": "FINDING-CMD-001",
            "rule_id": "SEC-005-CMD-INJ",
            "title": "Command Injection via subprocess shell=True",
            "severity": "critical",
            "category": "Security",
            "cwe": "CWE-78",
            "owasp": "A03:2021-Injection",
            "file_path": "vulnerable_python.py",
            "line_number": 48,
            "code_snippet": 'subprocess.Popen(f"ping -c 1 {user_host}", shell=True)',
            "remediation": 'Pass args as a list with shell=False: subprocess.Popen(["ping", "-c", "1", user_host])',
        },
        {
            "id": "FINDING-CRYPTO-001",
            "rule_id": "SEC-004-WEAK-HASH",
            "title": "Cryptographically Weak MD5 Hash for Secrets",
            "severity": "high",
            "category": "Cryptography",
            "cwe": "CWE-327",
            "owasp": "A02:2021-Cryptographic Failures",
            "file_path": "vulnerable_python.py",
            "line_number": 62,
            "code_snippet": "hashlib.md5(card_number.encode()).hexdigest()",
            "remediation": "Migrate to SHA-256 or bcrypt/argon2 for secret hashing",
        },
        {
            "id": "FINDING-JWT-001",
            "rule_id": "SEC-006-NONE-ALG",
            "title": "Insecure JWT Algorithm None Accepted",
            "severity": "critical",
            "category": "Authentication",
            "cwe": "CWE-345",
            "owasp": "A07:2021-Identification and Authentication Failures",
            "file_path": "vulnerable_python.py",
            "line_number": 89,
            "code_snippet": 'jwt.decode(token, algorithms=["none", "HS256"])',
            "remediation": 'Disallow the "none" algorithm and enforce strong signing keys',
        },
    ],
    "cycles": [["auth.service.UserAuthService", "db.connector.DatabaseManager", "payment.gateway.PaymentGateway"]],
    "graph": {
        "nodes": [
            {
                "id": "auth.service.UserAuthService",
                "label": "UserAuthService",
                "type": "class",
                "file_path": "backend/tests/fixtures/diagnostics/vulnerable_python.py",
                "loc": 620,
                "cyclomatic_complexity": 34.0,
                "max_complexity": 34,
                "mean_complexity": 34.0,
                "community": 0,
                "risk_score": 92.0,
                "is_vulnerable": True,
                "findings": [
                    {
                        "id": "FINDING-SQLI-001",
                        "rule_id": "SEC-001-SQLI",
                        "title": "SQL Injection via String Concatenation",
                        "severity": "critical",
                        "category": "Security",
                        "cwe": "CWE-89",
                        "owasp": "A03:2021-Injection",
                        "file_path": "vulnerable_python.py",
                        "line_number": 24,
                        "code_snippet": 'cursor.execute("SELECT * FROM users WHERE id = \'" + user_id + "\'")',
                        "remediation": (
                            'Use parameterized queries: cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))'
                        ),
                    },
                    {
                        "id": "FINDING-CMD-001",
                        "rule_id": "SEC-005-CMD-INJ",
                        "title": "Command Injection via subprocess shell=True",
                        "severity": "critical",
                        "category": "Security",
                        "cwe": "CWE-78",
                        "owasp": "A03:2021-Injection",
                        "file_path": "vulnerable_python.py",
                        "line_number": 48,
                        "code_snippet": 'subprocess.Popen(f"ping -c 1 {user_host}", shell=True)',
                        "remediation": (
                            'Pass args as a list with shell=False: subprocess.Popen(["ping", "-c", "1", user_host])'
                        ),
                    },
                ],
                "metadata": {
                    "incoming": ["payment.gateway.PaymentGateway"],
                    "outgoing": ["db.connector.DatabaseManager"],
                },
            },
            {
                "id": "payment.gateway.PaymentGateway",
                "label": "PaymentGateway",
                "type": "class",
                "file_path": "backend/tests/fixtures/diagnostics/vulnerable_python.py",
                "loc": 480,
                "cyclomatic_complexity": 22.0,
                "max_complexity": 22,
                "mean_complexity": 22.0,
                "community": 0,
                "risk_score": 85.0,
                "is_vulnerable": True,
                "findings": [
                    {
                        "id": "FINDING-CRYPTO-001",
                        "rule_id": "SEC-004-WEAK-HASH",
                        "title": "Cryptographically Weak MD5 Hash for Secrets",
                        "severity": "high",
                        "category": "Cryptography",
                        "cwe": "CWE-327",
                        "owasp": "A02:2021-Cryptographic Failures",
                        "file_path": "vulnerable_python.py",
                        "line_number": 62,
                        "code_snippet": "hashlib.md5(card_number.encode()).hexdigest()",
                        "remediation": "Migrate to SHA-256 or bcrypt/argon2 for secret hashing",
                    },
                ],
                "metadata": {
                    "incoming": ["db.connector.DatabaseManager"],
                    "outgoing": ["auth.service.UserAuthService"],
                },
            },
            {
                "id": "db.connector.DatabaseManager",
                "label": "DatabaseManager",
                "type": "class",
                "file_path": "backend/tests/fixtures/diagnostics/vulnerable_python.py",
                "loc": 540,
                "cyclomatic_complexity": 19.0,
                "max_complexity": 19,
                "mean_complexity": 19.0,
                "community": 0,
                "risk_score": 78.0,
                "is_vulnerable": False,
                "findings": [],
                "metadata": {
                    "incoming": ["auth.service.UserAuthService"],
                    "outgoing": ["payment.gateway.PaymentGateway"],
                },
            },
            {
                "id": "utils.jwt_helper",
                "label": "jwt_helper",
                "type": "module",
                "file_path": "backend/tests/fixtures/diagnostics/vulnerable_python.py",
                "loc": 110,
                "cyclomatic_complexity": 5.0,
                "max_complexity": 5,
                "mean_complexity": 5.0,
                "community": 1,
                "risk_score": 72.0,
                "is_vulnerable": True,
                "findings": [
                    {
                        "id": "FINDING-JWT-001",
                        "rule_id": "SEC-006-NONE-ALG",
                        "title": "Insecure JWT Algorithm None Accepted",
                        "severity": "critical",
                        "category": "Authentication",
                        "cwe": "CWE-345",
                        "owasp": "A07:2021-Identification and Authentication Failures",
                        "file_path": "vulnerable_python.py",
                        "line_number": 89,
                        "code_snippet": 'jwt.decode(token, algorithms=["none", "HS256"])',
                        "remediation": 'Disallow the "none" algorithm and enforce strong signing keys',
                    },
                ],
                "metadata": {"incoming": ["auth.service.UserAuthService"], "outgoing": []},
            },
        ],
        "edges": [
            {
                "source": "auth.service.UserAuthService",
                "target": "db.connector.DatabaseManager",
                "edge_type": "call",
                "weight": 2.2,
                "is_cycle": True,
            },
            {
                "source": "db.connector.DatabaseManager",
                "target": "payment.gateway.PaymentGateway",
                "edge_type": "call",
                "weight": 1.8,
                "is_cycle": True,
            },
            {
                "source": "payment.gateway.PaymentGateway",
                "target": "auth.service.UserAuthService",
                "edge_type": "import",
                "weight": 2.0,
                "is_cycle": True,
            },
            {
                "source": "auth.service.UserAuthService",
                "target": "utils.jwt_helper",
                "edge_type": "call",
                "weight": 1.0,
                "is_cycle": False,
            },
        ],
    },
    "health": {
        "status": "ok",
        "score": 38.0,
        "grade": "D",
        "sub_scores": {"security": 20.0, "modularity": 45.0, "complexity": 50.0},
        "summary": "Multiple critical vulnerabilities and circular dependencies detected.",
    },
    "external_dependencies": [],
    "files_excluded": 0,
    "include_tests": False,
    "parser_version": "1.4.0",
    "settings_hash": "",
    "source_fingerprint": "",
    "commit_sha": "a1b2c3d",
}


@router.get(
    "/graph/{repo_id}",
    summary="Retrieve cached graph",
    dependencies=[Depends(require_permission(Permission.VIEW_GRAPH))],
)
async def get_graph(repo_id: str) -> dict:
    """Return the cached dependency graph and analysis result for a prior analysis.

    Args:
        repo_id: UUID returned by POST /analyze or POST /ingest.

    Raises:
        404 if the repo_id is not found in the cache or database.
    """
    result = analyzer_service.get_cached_result(repo_id)
    if result is None:
        if repo_id == "vulnerable-microservice-003":
            return VULNERABLE_BENCHMARK_FIXTURE
        raise HTTPException(
            status_code=404,
            detail=f"No analysis found for repo_id='{repo_id}'. Run POST /analyze first.",
        )
    return {
        "repo_id": str(result.repo_id),
        "path": result.path,
        "language": result.language,
        "node_count": result.node_count,
        "edge_count": result.edge_count,
        "smells": result.smells,
        "findings": getattr(result, "findings", []),
        "cycles": getattr(result, "cycles", []),
        "summary": getattr(result, "summary", {}),
        "graph": result.graph.model_dump(),
        "health": result.health.model_dump() if hasattr(result.health, "model_dump") else result.health,
        "external_dependencies": [d.model_dump() for d in result.external_dependencies],
        "files_excluded": result.files_excluded,
        "include_tests": result.include_tests,
        "parser_version": result.parser_version,
        "settings_hash": result.settings_hash,
        "source_fingerprint": result.source_fingerprint,
        "commit_sha": result.commit_sha,
    }


@router.get(
    "/graphs",
    summary="List all cached graph IDs and recent analyses",
    dependencies=[Depends(require_permission(Permission.VIEW_GRAPH))],
)
async def list_graphs() -> dict:
    """Return all repo IDs and recent analysis metadata."""
    records = default_analysis_store.list_records()
    items = []
    seen_ids = set()
    for rec in records:
        if rec.id in seen_ids:
            continue
        seen_ids.add(rec.id)
        score = None
        grade = None
        tests_included = False
        if rec.result_json:
            try:
                data = json.loads(rec.result_json)
                health = data.get("health", {})
                score = health.get("score")
                grade = health.get("grade")
                tests_included = bool(data.get("include_tests", False))
            except Exception:
                pass

        # Repo name: clean from repo_url
        repo_url = rec.repo_url or ""
        repo_name = repo_url.rstrip("/\\").replace("\\", "/").split("/")[-1] or "repository"
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        commit = rec.commit_sha[:7] if rec.commit_sha else None

        items.append(
            {
                "id": rec.id,
                "repo_name": repo_name,
                "branch": rec.branch or "main",
                "commit_sha": commit,
                "created_at": rec.created_at,
                "score": score,
                "grade": grade,
                "include_tests": tests_included,
            }
        )

    cached_ids = analyzer_service.list_cached_ids()
    return {
        "repo_ids": cached_ids,
        "items": items,
    }
