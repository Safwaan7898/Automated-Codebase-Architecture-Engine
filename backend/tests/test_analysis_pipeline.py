"""Integration test for the unified analysis pipeline.

Verifies that:
- Ingestion, /analyze, /graph/{id}, and /reports/{id} produce and read from
  the same persisted AnalysisRecord in SQLite.
- Node count, edge count, cycle count, and health score are identical across all endpoints.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from ingestion.orchestrator import default_orchestrator
from ingestion.sources import FolderUploadSource


@pytest.mark.asyncio
async def test_unified_pipeline_identical_metrics(client: AsyncClient) -> None:
    """Assert ingest -> /graph/{id} -> /reports/{id} return identical node, edge, and cycle counts."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "mini_repo"
    assert fixtures_dir.exists(), f"Fixture directory not found: {fixtures_dir}"

    # 1. Trigger analysis via POST /analyze
    analyze_resp = await client.post(
        "/analyze",
        json={"path": str(fixtures_dir), "language": "python"},
    )
    assert analyze_resp.status_code == 200, analyze_resp.text
    analyze_data = analyze_resp.json()

    repo_id = analyze_data["repo_id"]
    analyze_nodes = analyze_data["node_count"]
    analyze_edges = analyze_data["edge_count"]
    analyze_cycle_smells = sum(1 for s in analyze_data.get("smells", []) if s.get("type") == "circular_import")
    analyze_cycle_edges = sum(1 for e in analyze_data["graph"]["edges"] if e.get("is_cycle"))

    assert analyze_nodes == 4, f"Expected 4 nodes for mini_repo, got {analyze_nodes}"
    assert analyze_edges == 4, f"Expected 4 internal edges for mini_repo, got {analyze_edges}"
    assert analyze_cycle_smells == 1, f"Expected 1 cycle smell for mini_repo, got {analyze_cycle_smells}"
    assert analyze_cycle_edges == 2, f"Expected 2 cycle edges for 2-module cycle, got {analyze_cycle_edges}"

    # 2. Retrieve graph from GET /graph/{repo_id}
    graph_resp = await client.get(f"/graph/{repo_id}")
    assert graph_resp.status_code == 200, graph_resp.text
    graph_data = graph_resp.json()

    graph_nodes = graph_data["node_count"]
    graph_edges = graph_data["edge_count"]
    graph_cycle_edges = sum(1 for e in graph_data["graph"]["edges"] if e.get("is_cycle"))
    graph_score = graph_data["health"]["score"]

    assert graph_nodes == analyze_nodes
    assert graph_edges == analyze_edges
    assert graph_cycle_edges == analyze_cycle_edges

    # 3. Retrieve report from GET /api/reports/{repo_id}
    report_resp = await client.get(f"/api/reports/{repo_id}")
    assert report_resp.status_code == 200, report_resp.text
    report_data = report_resp.json()

    report_nodes = report_data["executive_summary"]["total_components"]
    report_edges = report_data["executive_summary"]["total_dependencies"]
    report_cycles = report_data["executive_summary"]["total_circular_cycles"]
    report_score = report_data["executive_summary"]["health_score"]

    assert report_nodes == analyze_nodes, f"Report nodes {report_nodes} != analyze {analyze_nodes}"
    assert report_edges == analyze_edges, f"Report edges {report_edges} != analyze {analyze_edges}"
    assert report_cycles == analyze_cycle_smells, f"Report cycles {report_cycles} != analyze {analyze_cycle_smells}"
    assert report_score == graph_score, f"Report score {report_score} != graph score {graph_score}"

    # 4. Generate report with analysis_id via POST /api/reports/generate
    gen_resp = await client.post(
        "/api/reports/generate",
        json={"analysis_id": repo_id, "format": "json"},
    )
    assert gen_resp.status_code == 200, gen_resp.text
    gen_data = gen_resp.json()

    assert gen_data["executive_summary"]["total_components"] == analyze_nodes
    assert gen_data["executive_summary"]["total_dependencies"] == analyze_edges
    assert gen_data["executive_summary"]["total_circular_cycles"] == analyze_cycle_smells
    assert gen_data["executive_summary"]["health_score"] == graph_score

    # 5. Retrieve refactor suggestions by analysis ID via GET /api/refactor/{repo_id}
    refactor_resp = await client.get(f"/api/refactor/{repo_id}")
    assert refactor_resp.status_code == 200, refactor_resp.text
    refactor_data = refactor_resp.json()
    assert "suggestions" in refactor_data


@pytest.mark.asyncio
async def test_orchestrator_ingestion_persists_to_analysis_store(client: AsyncClient) -> None:
    """Ingestion orchestrator executes analyzer_service and persists record in SQLite store."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "mini_repo"

    # Read files for folder upload source
    files = []
    for f in fixtures_dir.glob("*.py"):
        files.append((f.name, f.read_bytes()))

    src = FolderUploadSource(files=files, folder_name="mini_repo")
    metadata, result = await default_orchestrator.run_sync(src)

    assert metadata is not None
    job_id = metadata.job_id

    # Retrieve from /graph/{job_id}
    graph_resp = await client.get(f"/graph/{job_id}")
    assert graph_resp.status_code == 200, graph_resp.text
    graph_data = graph_resp.json()

    assert graph_data["node_count"] == 4
    assert graph_data["edge_count"] == 4
    cycle_edges = sum(1 for e in graph_data["graph"]["edges"] if e.get("is_cycle"))
    assert cycle_edges == 2

    # Retrieve from /api/reports/{job_id}
    report_resp = await client.get(f"/api/reports/{job_id}")
    assert report_resp.status_code == 200, report_resp.text
    report_data = report_resp.json()

    assert report_data["executive_summary"]["total_components"] == 4
    assert report_data["executive_summary"]["total_dependencies"] == 4
    assert report_data["executive_summary"]["total_circular_cycles"] == 1
