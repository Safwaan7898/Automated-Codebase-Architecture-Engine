"""Tests for strict deterministic repository analysis.

Requirements verified:
1. In-process repeatability: 5 repeated runs produce byte-identical canonical JSON.
2. Separate processes with PYTHONHASHSEED=0, 1, and random produce byte-identical canonical JSON.
3. Node IDs, paths, and graph outputs never contain absolute or machine-specific paths (e.g. archlens_clone_).
4. A cache hit and a fresh run produce byte-identical outputs.
5. All graph algorithms (SCC, PageRank, Betweenness, Louvain, dead code) break ties deterministically.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from app.models.graph import AnalysisResult
from app.services import analyzer_service

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_repo"


def _canonical_json(data: dict[str, Any] | AnalysisResult) -> str:
    if isinstance(data, AnalysisResult):
        raw = data.model_dump(mode="json")
    else:
        raw = data
    return json.dumps(raw, sort_keys=True, separators=(",", ":"))


def test_in_process_5_runs_byte_identical() -> None:
    """Analyze the same fixture repository 5 times in one process; outputs must be byte-identical."""
    assert FIXTURE_DIR.exists()

    canonical_runs: list[str] = []
    for _ in range(5):
        # Clear in-memory caches to test pure calculation repeatability
        analyzer_service._cache.clear()
        analyzer_service._cache_by_key.clear()

        result = analyzer_service.run_analysis(str(FIXTURE_DIR), language="python")
        canonical_runs.append(_canonical_json(result))

    first = canonical_runs[0]
    for idx, cjson in enumerate(canonical_runs[1:], start=2):
        assert cjson == first, f"Run {idx} diverged from Run 1:\nRun 1: {first[:200]}\nRun {idx}: {cjson[:200]}"


def test_separate_processes_hash_seed_variance() -> None:
    """Run in separate processes with PYTHONHASHSEED=0, 1, and random. Outputs must be byte-identical."""
    backend_path = str(Path(__file__).resolve().parent.parent)
    fixture_path = str(FIXTURE_DIR)

    worker_code = f"""
import sys, json
sys.path.insert(0, {json.dumps(backend_path)})
from app.services import analyzer_service

res = analyzer_service.run_analysis({json.dumps(fixture_path)}, language="python")
d = res.model_dump(mode="json")
print(json.dumps(d, sort_keys=True, separators=(",", ":")))
"""

    seeds = ["0", "1", "random", "42", "9999"]
    outputs: list[str] = []

    for seed in seeds:
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        env["PYTHONPATH"] = backend_path

        proc = subprocess.run(
            [sys.executable, "-c", worker_code],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        assert proc.returncode == 0, f"Process with PYTHONHASHSEED={seed} failed: {proc.stderr}"
        outputs.append(proc.stdout.strip())

    base = outputs[0]
    for idx, (seed, out) in enumerate(zip(seeds[1:], outputs[1:], strict=False), start=2):
        assert out == base, (
            f"Process with PYTHONHASHSEED={seed} (run {idx}) differed from run 1 (PYTHONHASHSEED={seeds[0]})"
        )


def test_no_machine_specific_or_absolute_paths_in_output() -> None:
    """Verify node IDs, edge endpoints, file_paths, and result.path never contain absolute paths or clone markers."""
    analyzer_service._cache.clear()
    analyzer_service._cache_by_key.clear()

    result = analyzer_service.run_analysis(str(FIXTURE_DIR), language="python")
    data = result.model_dump(mode="json")

    # Absolute path regex for Windows drive letters (e.g. C:\ or C:/) and POSIX root (/...)
    win_abs_re = re.compile(r"^[A-Za-z]:[\\/]")
    posix_abs_re = re.compile(r"^/[a-zA-Z0-9_]")
    clone_re = re.compile(r"archlens_clone_[a-zA-Z0-9_]+")

    # 1. Result path
    assert not win_abs_re.match(result.path), f"result.path is an absolute Windows path: {result.path}"
    assert not posix_abs_re.match(result.path), f"result.path is an absolute POSIX path: {result.path}"
    assert not clone_re.search(result.path), f"result.path leaks clone directory: {result.path}"

    # 2. Nodes
    for node in result.graph.nodes:
        assert not win_abs_re.match(node.id), f"Node ID is absolute: {node.id}"
        assert not posix_abs_re.match(node.id), f"Node ID is absolute: {node.id}"
        assert not clone_re.search(node.id), f"Node ID leaks clone folder: {node.id}"

        if node.file_path:
            assert "\\" not in node.file_path, f"Node file_path uses Windows backslashes: {node.file_path}"
            assert not win_abs_re.match(node.file_path), f"Node file_path is absolute: {node.file_path}"
            assert not posix_abs_re.match(node.file_path), f"Node file_path is absolute: {node.file_path}"
            assert not clone_re.search(node.file_path), f"Node file_path leaks clone folder: {node.file_path}"

    # 3. Edges
    for edge in result.graph.edges:
        assert not clone_re.search(edge.source), f"Edge source leaks clone folder: {edge.source}"
        assert not clone_re.search(edge.target), f"Edge target leaks clone folder: {edge.target}"

    # 4. Canonical JSON global scan
    serialized = json.dumps(data)
    assert "archlens_clone_" not in serialized, "Serialized output contains 'archlens_clone_'"


def test_cache_hit_and_fresh_run_produce_identical_output() -> None:
    """Verify that a cache hit and a fresh run produce byte-identical canonical JSON."""
    analyzer_service._cache.clear()
    analyzer_service._cache_by_key.clear()

    # Fresh run
    fresh_res = analyzer_service.run_analysis(str(FIXTURE_DIR), language="python")
    fresh_json = _canonical_json(fresh_res)

    # Cache hit (served from in-memory / SQLite store)
    cached_res = analyzer_service.run_analysis(str(FIXTURE_DIR), language="python")
    cached_json = _canonical_json(cached_res)

    assert fresh_json == cached_json
    assert fresh_res.source_fingerprint == cached_res.source_fingerprint
    assert fresh_res.repo_id == cached_res.repo_id
