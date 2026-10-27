"""FastAPI endpoints for ArchLens rule-based diagnostics and risk scoring."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from analysis.facade import build_graph_from_dict
from diagnostics.engine import default_diagnostics_engine
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import require_permission
from app.auth.models import Permission

router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])


class AnalyzeFileRequest(BaseModel):
    content: str = Field(..., description="Source code text to analyze")
    language: str = Field(..., description="'python' or 'java'")
    file_path: str = Field("sample_file", description="Path or label for the file")


class AnalyzeDependenciesRequest(BaseModel):
    content: str = Field(..., description="Manifest file content")
    manifest_type: str = Field(
        ...,
        description="'requirements.txt', 'pom.xml', or 'build.gradle'",
    )
    manifest_path: str = Field("manifest", description="Path to manifest file")


class AnalyzeRepoRequest(BaseModel):
    repo_path: str = Field(..., description="Absolute or relative path to repo on disk")
    query_osv: bool = Field(True, description="Query OSV.dev for dependency CVEs")


@router.get(
    "/rules",
    dependencies=[Depends(require_permission(Permission.VIEW_SMELLS))],
)
def get_rules() -> dict[str, Any]:
    """Return all active diagnostic rules with metadata."""
    rules = default_diagnostics_engine.registry.list_rules()
    return {"total_rules": len(rules), "rules": rules}


@router.post(
    "/analyze-file",
    dependencies=[Depends(require_permission(Permission.VIEW_SMELLS))],
)
def analyze_file(req: AnalyzeFileRequest) -> dict[str, Any]:
    """Run AST security rules on source code content."""
    findings = default_diagnostics_engine.analyze_source_code(
        content=req.content,
        language=req.language.lower(),
        file_path=req.file_path,
    )
    return {
        "file_path": req.file_path,
        "language": req.language,
        "total_findings": len(findings),
        "findings": [f.to_dict() for f in findings],
    }


@router.post(
    "/analyze-dependencies",
    dependencies=[Depends(require_permission(Permission.VIEW_SMELLS))],
)
def analyze_dependencies(req: AnalyzeDependenciesRequest) -> dict[str, Any]:
    """Parse manifest and query OSV.dev for known CVEs."""
    findings = default_diagnostics_engine.analyze_dependencies_content(
        content=req.content,
        manifest_type=req.manifest_type,
        manifest_path=req.manifest_path,
        query_osv=True,
    )
    return {
        "manifest_path": req.manifest_path,
        "manifest_type": req.manifest_type,
        "total_vulnerabilities": len(findings),
        "findings": [f.to_dict() for f in findings],
    }


@router.post(
    "/analyze-graph",
    dependencies=[Depends(require_permission(Permission.VIEW_SMELLS))],
)
def analyze_graph(graph_data: dict[str, Any]) -> dict[str, Any]:
    """Run architectural smell rules and compute risk scores on a graph."""
    graph = build_graph_from_dict(graph_data)
    smell_findings = default_diagnostics_engine.analyze_graph(graph)

    findings_by_node: dict[str, list[Any]] = {}
    for f in smell_findings:
        if f.node_id:
            findings_by_node.setdefault(f.node_id, []).append(f)

    from analysis.centrality import compute_betweenness_centrality, compute_pagerank

    bw = compute_betweenness_centrality(graph)
    pr = compute_pagerank(graph)
    risk_scores = default_diagnostics_engine.scorer.score_all_nodes(graph, findings_by_node, bw, pr)

    return {
        "node_count": graph.node_count,
        "smell_findings_count": len(smell_findings),
        "findings": [f.to_dict() for f in smell_findings],
        "risk_scores": {nid: s.to_dict() for nid, s in risk_scores.items()},
    }


@router.get(
    "/cve",
    summary="Access complete CVE vulnerability intelligence and dependency advisories",
    dependencies=[Depends(require_permission(Permission.VIEW_SECURITY_FINDINGS))],
)
def get_cve_details() -> dict[str, Any]:
    """Access detailed CVE feeds and OSV database mappings. Restricted to Security Analysts and Admins."""
    return {
        "cve_database": "OSV.dev + NVD",
        "advisory_feeds": [
            "GitHub Advisory Database (GHSA)",
            "PyPI Advisory Database",
            "Maven Central Security Feed",
        ],
        "monitored_ecosystems": ["PyPI", "Maven"],
        "severity_thresholds": {
            "CRITICAL": "CVSS >= 9.0",
            "HIGH": "CVSS 7.0 - 8.9",
            "MEDIUM": "CVSS 4.0 - 6.9",
            "LOW": "CVSS 0.1 - 3.9",
        },
    }


@router.post(
    "/analyze-repo",
    dependencies=[Depends(require_permission(Permission.VIEW_SMELLS))],
)
def analyze_repo(req: AnalyzeRepoRequest) -> dict[str, Any]:
    """Run full diagnostic analysis over a repository directory."""
    path = Path(req.repo_path)
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=404, detail=f"Directory '{req.repo_path}' not found")

    report = default_diagnostics_engine.analyze_directory(
        root_dir=path,
        query_osv=req.query_osv,
    )
    return report.to_dict()


class ExplainSmellRequest(BaseModel):
    smell: dict[str, Any]
    repo_context: dict[str, Any] = Field(default_factory=dict)


class EnrichSecurityRequest(BaseModel):
    finding: dict[str, Any]
    code_snippet: str | None = None


@router.post(
    "/explain-smell",
    dependencies=[Depends(require_permission(Permission.VIEW_SMELLS))],
)
async def api_explain_smell(req: ExplainSmellRequest) -> dict[str, Any]:
    """Contextual explanation and fix outline for an architectural smell."""
    from ai.features import explain_smell

    res = await explain_smell(req.smell, req.repo_context)
    return res.model_dump()


@router.post(
    "/enrich-security",
    dependencies=[Depends(require_permission(Permission.VIEW_SMELLS))],
)
async def api_enrich_security(req: EnrichSecurityRequest) -> dict[str, Any]:
    """Enrich security finding with explanation, false-positive likelihood, and fix outline."""
    from ai.features import enrich_security_finding

    res = await enrich_security_finding(req.finding, req.code_snippet)
    return res.model_dump()
