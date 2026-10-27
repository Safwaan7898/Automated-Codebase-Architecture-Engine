"""Tests for incremental parsing by file hash, timeouts, and huge repo size limits."""

from pathlib import Path

import pytest
from parsers.cache import FileParseCache, hash_file_content
from parsers.config import IngestionConfig
from parsers.models import Edge, EdgeType, Node, NodeType, ParseResult
from parsers.parallel_runner import parse_repository


def test_file_parse_cache_set_get_and_stats(tmp_path: Path) -> None:
    cache = FileParseCache(max_entries=3)

    file_a = tmp_path / "a.py"
    file_a.write_text("x = 1\n", encoding="utf-8")
    hash_a = hash_file_content(file_a)

    node = Node(id="test.a", type=NodeType.MODULE, name="a", path="a.py", language="python")
    edge = Edge(source="test.a", target="test.b", type=EdgeType.IMPORTS)
    pr = ParseResult(file_path="a.py", language="python", nodes=[node], edges=[edge])

    # Cache miss
    assert cache.get(hash_a, "a.py") is None

    # Set and cache hit
    cache.set(hash_a, pr)
    cached = cache.get(hash_a, "workspace/sub/a.py")
    assert cached is not None
    assert cached.file_path == "workspace/sub/a.py"
    assert cached.nodes[0].path == "workspace/sub/a.py"

    stats = cache.stats
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["size"] == 1
    assert stats["hit_ratio"] == 0.5

    # Eviction test (max 3 entries)
    cache.set("hash_2", pr)
    cache.set("hash_3", pr)
    cache.set("hash_4", pr)  # Should evict hash_a
    assert cache.get(hash_a, "a.py") is None
    assert cache.stats["size"] == 3

    # Clear
    cache.clear()
    assert cache.stats["size"] == 0
    assert cache.stats["hits"] == 0


@pytest.mark.asyncio
async def test_incremental_parsing_skips_unchanged_files(tmp_path: Path) -> None:
    cache = FileParseCache()
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()

    f1 = repo_dir / "mod1.py"
    f1.write_text("def foo():\n    return 42\n", encoding="utf-8")

    f2 = repo_dir / "mod2.py"
    f2.write_text("import mod1\n\ndef bar():\n    return mod1.foo()\n", encoding="utf-8")

    cfg = IngestionConfig(supported_languages=["python"])

    # First run: cold cache
    res1 = await parse_repository(str(repo_dir), config=cfg, cache=cache)
    assert res1.files_parsed == 2
    assert cache.stats["hits"] == 0
    assert cache.stats["misses"] == 2

    # Second run: warm cache - both files hit cache
    res2 = await parse_repository(str(repo_dir), config=cfg, cache=cache)
    assert res2.files_parsed == 2
    assert cache.stats["hits"] == 2

    # Modify mod2.py: mod1 should hit cache, mod2 should miss and update cache
    f2.write_text("import mod1\n\ndef bar():\n    return mod1.foo() + 10\n", encoding="utf-8")
    res3 = await parse_repository(str(repo_dir), config=cfg, cache=cache)
    assert res3.files_parsed == 2
    assert cache.stats["hits"] == 3  # mod1 hit
    assert cache.stats["misses"] == 3  # mod2 missed (changed hash)


@pytest.mark.asyncio
async def test_huge_repo_file_limits(tmp_path: Path) -> None:
    repo_dir = tmp_path / "huge_repo"
    repo_dir.mkdir()

    for i in range(10):
        (repo_dir / f"file_{i}.py").write_text(f"x_{i} = {i}\n", encoding="utf-8")

    # Limit max files to 3
    cfg = IngestionConfig(supported_languages=["python"], max_files=3)
    res = await parse_repository(str(repo_dir), config=cfg)

    assert res.files_parsed <= 3
    assert any("exceeds limit" in err for err in res.errors)
