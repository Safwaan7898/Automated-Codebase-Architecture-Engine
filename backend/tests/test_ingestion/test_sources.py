"""Unit and integration tests for all 6 IngestionSource implementations."""

from __future__ import annotations

import io
import re
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from ingestion.config import IngestionLimits
from ingestion.exceptions import (
    LocalPathDisabledError,
    SecurityError,
    SourceError,
)
from ingestion.sources import (
    ArchiveUploadSource,
    ArchiveUrlSource,
    FolderUploadSource,
    GitSource,
    LocalPathSource,
    SnippetSource,
)


@pytest.fixture
def mock_progress():
    return AsyncMock()


# ── 1. Archive Upload Source Tests ────────────────────────────────────────────


class TestArchiveUploadSource:
    @pytest.mark.asyncio
    async def test_zip_archive_upload_sample(self, tmp_path: Path, mock_progress) -> None:
        # Create a real ZIP archive containing a Python file and a Java file
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("app/main.py", "def run():\n    print('Flask running')\n")
            zf.writestr("app/Pet.java", "public class Pet { private String name; }\n")

        src = ArchiveUploadSource(archive_data=zip_buf.getvalue(), filename="project.zip")
        assert src.source_type == "archive"
        assert src.repo_name == "project"
        assert len(src.fingerprint) == 64
        assert re.fullmatch(r"[0-9a-f]{64}", src.fingerprint) is not None
        assert re.match(r"^[0-9a-f]{64}:[^:]+:[0-9a-f]+:(python|java|auto)$", src.cache_key) is not None

        src_dir = tmp_path / "src"
        meta = await src.fetch(src_dir, IngestionLimits(), mock_progress)

        assert meta["archive_type"] == "zip"
        assert (src_dir / "app" / "main.py").exists()
        assert (src_dir / "app" / "Pet.java").exists()
        assert "Flask running" in (src_dir / "app" / "main.py").read_text()

    @pytest.mark.asyncio
    async def test_tar_gz_upload_sample(self, tmp_path: Path, mock_progress) -> None:
        # Create a .tar.gz archive
        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w:gz") as tf:
            code = b"import os\nprint('hello')\n"
            ti = tarfile.TarInfo(name="pkg/script.py")
            ti.size = len(code)
            tf.addfile(ti, io.BytesIO(code))

        src = ArchiveUploadSource(archive_data=tar_buf.getvalue(), filename="bundle.tar.gz")
        assert src.repo_name == "bundle"

        src_dir = tmp_path / "src"
        meta = await src.fetch(src_dir, IngestionLimits(), mock_progress)

        assert meta["archive_type"] == "tar.gz"
        assert (src_dir / "pkg" / "script.py").exists()

    @pytest.mark.asyncio
    async def test_reject_corrupt_or_non_archive(self, tmp_path: Path, mock_progress) -> None:
        src = ArchiveUploadSource(archive_data=b"NOT AN ARCHIVE", filename="corrupt.zip")
        src_dir = tmp_path / "src"
        with pytest.raises(SourceError, match="not a recognized archive format"):
            await src.fetch(src_dir, IngestionLimits(), mock_progress)


# ── 2. Folder Upload Source Tests ────────────────────────────────────────────


class TestFolderUploadSource:
    @pytest.mark.asyncio
    async def test_folder_upload_preserves_hierarchy(self, tmp_path: Path, mock_progress) -> None:
        files = [
            ("src/core/app.py", b"def main(): pass\n"),
            ("src/core/utils.py", b"def helper(): pass\n"),
            ("tests/test_app.py", b"def test(): assert True\n"),
        ]
        src = FolderUploadSource(files=files, folder_name="my_project")
        assert src.source_type == "folder"
        assert src.display_name == "my_project"

        src_dir = tmp_path / "src"
        meta = await src.fetch(src_dir, IngestionLimits(), mock_progress)

        assert meta["files_written"] == 3
        assert (src_dir / "src" / "core" / "app.py").exists()
        assert (src_dir / "tests" / "test_app.py").exists()

    @pytest.mark.asyncio
    async def test_folder_upload_rejects_path_traversal(self, tmp_path: Path, mock_progress) -> None:
        files = [
            ("src/safe.py", b"safe"),
            ("../../escape.py", b"malicious"),
        ]
        src = FolderUploadSource(files=files, folder_name="evil_folder")
        src_dir = tmp_path / "src"

        with pytest.raises(SecurityError, match="Path traversal '..' detected"):
            await src.fetch(src_dir, IngestionLimits(), mock_progress)

        assert not (tmp_path.parent / "escape.py").exists()


# ── 3. Snippet Source Tests ──────────────────────────────────────────────────


class TestSnippetSource:
    @pytest.mark.asyncio
    async def test_pasted_python_snippet(self, tmp_path: Path, mock_progress) -> None:
        code = "class Calculator:\n    def add(self, a, b):\n        return a + b\n"
        src = SnippetSource(code=code, language="python", filename="calc.py")

        assert src.source_type == "snippet"
        assert src.display_name == "calc.py (Python)"
        assert src.repo_name == "calc"

        src_dir = tmp_path / "src"
        await src.fetch(src_dir, IngestionLimits(), mock_progress)

        target = src_dir / "calc.py"
        assert target.exists()
        assert target.read_text(encoding="utf-8") == code

    @pytest.mark.asyncio
    async def test_pasted_java_snippet_auto_extension(self, tmp_path: Path, mock_progress) -> None:
        code = "public class OrderService { public void process() {} }"
        # No filename provided -> defaults to snippet.java
        src = SnippetSource(code=code, language="java")

        src_dir = tmp_path / "src"
        await src.fetch(src_dir, IngestionLimits(), mock_progress)

        target = src_dir / "snippet.java"
        assert target.exists()
        assert "OrderService" in target.read_text(encoding="utf-8")


# ── 4. Local Path Source Tests ───────────────────────────────────────────────


class TestLocalPathSource:
    @pytest.mark.asyncio
    async def test_local_path_disabled_by_default(self, tmp_path: Path, mock_progress) -> None:
        src = LocalPathSource(path=str(tmp_path))
        limits = IngestionLimits(allow_local_paths=False)

        with pytest.raises(LocalPathDisabledError, match="Local path ingestion is disabled"):
            await src.fetch(tmp_path / "dest", limits, mock_progress)

    @pytest.mark.asyncio
    async def test_local_path_enabled_copies_files(self, tmp_path: Path, mock_progress) -> None:
        local_repo = tmp_path / "local_repo"
        local_repo.mkdir()
        (local_repo / "main.py").write_text("print(1)")
        (local_repo / "sub").mkdir()
        (local_repo / "sub" / "lib.py").write_text("print(2)")

        src = LocalPathSource(path=str(local_repo))
        limits = IngestionLimits(allow_local_paths=True)
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        meta = await src.fetch(dest_dir, limits, mock_progress)
        assert meta["files_copied"] == 2
        assert (dest_dir / "main.py").exists()
        assert (dest_dir / "sub" / "lib.py").exists()


# ── 5. Git Source Tests ──────────────────────────────────────────────────────


class TestGitSource:
    def test_git_source_properties(self) -> None:
        src = GitSource("https://github.com/pallets/flask.git", branch="main", access_token="secret-pat-123")
        assert src.source_type == "git"
        assert src.display_name == "github.com/pallets/flask.git"
        assert src.repo_name == "flask"
        # Token is NOT in display name or hash
        assert "secret-pat" not in src.display_name

    def test_git_source_ssrf_rejects_http(self) -> None:
        src = GitSource("http://insecure-repo.com/repo.git")
        # SSRF validation will trigger in fetch or validate_safe_url
        with pytest.raises(SecurityError):
            src_limits = IngestionLimits()
            # Fetch checks URL safety first
            import asyncio

            asyncio.run(src.fetch(Path("/tmp"), src_limits, AsyncMock()))

    @pytest.mark.asyncio
    async def test_git_token_not_leaked_on_error(self, tmp_path: Path, mock_progress) -> None:
        secret = "super_secret_github_token_xyz987"
        src = GitSource(
            url="https://github.com/nonexistent-org-12345/nonexistent-repo-9999.git",
            access_token=secret,
        )

        with patch("ingestion.sources.git.validate_safe_url"), patch("subprocess.run") as mock_run:
            from subprocess import CompletedProcess

            # Simulate failure containing the secret
            mock_run.return_value = CompletedProcess(
                args=["git", "clone"],
                returncode=128,
                stdout="",
                stderr=f"fatal: Authentication failed for token {secret}",
            )
            with pytest.raises(Exception) as exc_info:
                await src.fetch(tmp_path / "src", IngestionLimits(), mock_progress)

            error_str = str(exc_info.value)
            assert secret not in error_str
            assert "[REDACTED]" in error_str or "authentication failed" in error_str.lower()


# ── 6. Archive URL Source Tests ──────────────────────────────────────────────


class TestArchiveUrlSource:
    def test_archive_url_properties(self) -> None:
        src = ArchiveUrlSource("https://example.com/downloads/v1.0.0.tar.gz")
        assert src.source_type == "archive_url"
        assert src.repo_name == "v1.0.0"
        assert src.display_name == "example.com/downloads/v1.0.0.tar.gz"

    @pytest.mark.asyncio
    async def test_archive_url_fetch_and_extract(self, tmp_path: Path, mock_progress) -> None:
        # Mock safe_download_url and verify extraction
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("module.py", "x = 42\n")

        src = ArchiveUrlSource("https://example.com/project.zip")
        dest_dir = tmp_path / "src"

        async def fake_download(url, dest_path, limits):
            dest_path.write_bytes(zip_buf.getvalue())
            return len(zip_buf.getvalue())

        with patch("ingestion.sources.archive_url.safe_download_url", side_effect=fake_download):
            meta = await src.fetch(dest_dir, IngestionLimits(), mock_progress)
            assert meta["extracted_files"] == 1
            assert (dest_dir / "module.py").exists()
