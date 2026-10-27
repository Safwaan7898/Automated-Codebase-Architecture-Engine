"""Integration tests: run the full parser pipeline on both sample repos.

These tests are marked ``@pytest.mark.integration`` and are automatically
skipped if the sample repos don't exist (fresh checkout without samples).

Run them explicitly:
    pytest tests/test_parsers/test_sample_repos.py -v -s
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from parsers.config import IngestionConfig
from parsers.parallel_runner import parse_repository

REPO_ROOT = Path(__file__).parent.parent.parent.parent  # monorepo root
SAMPLES_ROOT = REPO_ROOT / "samples"
JAVA_SAMPLE = SAMPLES_ROOT / "java-spring"
PYTHON_SAMPLE = SAMPLES_ROOT / "python-flask"


def _skip_if_missing(path: Path):
    if not path.exists():
        pytest.skip(f"Sample repo not found: {path}. Run 'git clone ...' first.")


# ── Python Flask sample ───────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_python_flask_sample():
    _skip_if_missing(PYTHON_SAMPLE)

    progress_events = []

    async def track(update):
        progress_events.append(update)

    cfg = IngestionConfig(include_test_files=False, max_workers=8)
    t0 = time.monotonic()
    result = await parse_repository(str(PYTHON_SAMPLE), cfg, progress_callback=track)
    elapsed = time.monotonic() - t0

    print("\n" + "=" * 60)
    print("Flask sample analysis:")
    print(result.summary())
    print(f"  Progress events: {len(progress_events)}")
    print("=" * 60)

    assert result.node_count > 0, "Expected nodes from Flask source"
    assert result.edge_count > 0, "Expected edges from Flask source"
    assert result.language == "python"
    assert result.files_parsed > 0
    assert elapsed < 120, f"Took too long: {elapsed:.1f}s"

    # Check we got class and function nodes
    from parsers.models import NodeType

    node_types = {n.type for n in result.nodes}
    assert NodeType.MODULE in node_types or NodeType.CLASS in node_types


# ── Java Spring sample ────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_java_spring_sample():
    _skip_if_missing(JAVA_SAMPLE)

    try:
        from parsers.java_parser import JavaParser  # noqa: F401
    except RuntimeError as exc:
        pytest.skip(f"Java parser unavailable: {exc}")

    progress_events = []

    async def track(update):
        progress_events.append(update)

    cfg = IngestionConfig(include_test_files=False, max_workers=8)
    t0 = time.monotonic()
    result = await parse_repository(str(JAVA_SAMPLE), cfg, progress_callback=track)
    elapsed = time.monotonic() - t0

    print("\n" + "=" * 60)
    print("Spring PetClinic analysis:")
    print(result.summary())
    print(f"  Progress events: {len(progress_events)}")
    print("=" * 60)

    assert result.node_count > 0, "Expected nodes from Spring source"
    assert result.language == "java"
    assert result.files_parsed > 0
    assert elapsed < 120, f"Java analysis took too long: {elapsed:.1f}s"

    # Should have class nodes
    from parsers.models import NodeType

    node_types = {n.type for n in result.nodes}
    assert NodeType.CLASS in node_types or NodeType.INTERFACE in node_types


# ── Parallel runner unit tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_parse_empty_directory(tmp_path):
    result = await parse_repository(str(tmp_path))
    assert result.node_count == 0
    assert result.edge_count == 0
    assert result.language == "unknown"


@pytest.mark.asyncio
async def test_parse_single_python_file(tmp_path):
    (tmp_path / "hello.py").write_text(
        "import os\n\nclass Greeter:\n    def greet(self, name: str) -> str:\n        return f'Hello {name}'\n"
    )
    result = await parse_repository(str(tmp_path))
    assert result.node_count >= 1
    assert result.language == "python"


@pytest.mark.asyncio
async def test_progress_callback_called(tmp_path):
    for i in range(5):
        (tmp_path / f"mod_{i}.py").write_text(f"x_{i} = {i}")

    events = []

    async def capture(update):
        events.append(update.type)

    await parse_repository(str(tmp_path), progress_callback=capture)
    assert "progress" in events or "log" in events


@pytest.mark.asyncio
async def test_nonexistent_path_raises():
    with pytest.raises((ValueError, RuntimeError)):
        await parse_repository("/totally/nonexistent/path_archlens_test")


@pytest.mark.asyncio
async def test_broken_files_do_not_crash_pipeline(tmp_path):
    (tmp_path / "good.py").write_text("x = 1\n")
    (tmp_path / "broken.py").write_text("def foo(\n  # unclosed")
    result = await parse_repository(str(tmp_path))
    # Pipeline must complete; broken.py may produce errors but not crash
    assert result is not None
    # good.py node should still be there
    assert result.node_count >= 1
