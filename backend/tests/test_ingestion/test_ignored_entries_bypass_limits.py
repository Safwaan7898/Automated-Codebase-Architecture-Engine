"""Test proving that entries in ignored directories do NOT count toward max_files / max_uncompressed."""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest
from ingestion.config import IngestionLimits
from ingestion.security import safe_extract_archive


def test_ignored_entries_do_not_count_toward_zip_limits(tmp_path: Path) -> None:
    """Ignored directories (node_modules, .git, venv) must not consume max_files or max_uncompressed quota."""
    zip_path = tmp_path / "huge_ignored.zip"
    dest_dir = tmp_path / "extracted_zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Add valid code files (2 files, 80 bytes total)
        zf.writestr("app/main.py", "def run():\n    return 'ok'\n")
        zf.writestr("app/service.py", "from app.main import run\n")

        # 2. Add 20 ignored files each containing 2000 bytes (40,000 bytes total)
        for i in range(10):
            zf.writestr(f"node_modules/pkg{i}/index.js", "x" * 2000)
            zf.writestr(f".git/objects/{i:02d}/pack", "g" * 2000)

    # Configure tight limits: max_files = 5, max_uncompressed_bytes = 1000 bytes
    # If the 20 ignored files were counted, total files (22) > 5 and uncompressed (40,080 bytes) > 1000 bytes!
    limits = IngestionLimits(
        max_files=5,
        max_uncompressed_bytes=1000,
    )

    result = safe_extract_archive(zip_path, dest_dir, limits)

    # Proves only the 2 valid files were counted and extracted
    assert int(result) == 2
    assert result.skipped_files == 20
    assert result.skipped_by_dir.get("node_modules") == 10
    assert result.skipped_by_dir.get(".git") == 10

    assert (dest_dir / "app" / "main.py").exists()
    assert (dest_dir / "app" / "service.py").exists()
    assert not (dest_dir / "node_modules").exists()
    assert not (dest_dir / ".git").exists()


def test_ignored_entries_do_not_count_toward_tar_limits(tmp_path: Path) -> None:
    """Ignored directories in tar.gz must also bypass max_files and max_uncompressed quota."""
    tar_path = tmp_path / "huge_ignored.tar.gz"
    dest_dir = tmp_path / "extracted_tar"

    with tarfile.open(tar_path, mode="w:gz") as tf:
        # Valid code file
        code = b"print('hello')\n"
        ti = tarfile.TarInfo("src/app.py")
        ti.size = len(code)
        tf.addfile(ti, io.BytesIO(code))

        # 15 Ignored node_modules files (each 3000 bytes)
        for i in range(15):
            body = b"y" * 3000
            ti_node = tarfile.TarInfo(f"node_modules/lib_{i}.js")
            ti_node.size = len(body)
            tf.addfile(ti_node, io.BytesIO(body))

    limits = IngestionLimits(
        max_files=5,
        max_uncompressed_bytes=500,
    )

    result = safe_extract_archive(tar_path, dest_dir, limits)
    assert int(result) == 1
    assert (dest_dir / "src" / "app.py").exists()
    assert not (dest_dir / "node_modules").exists()
