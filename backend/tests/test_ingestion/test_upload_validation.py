"""Tests for upload validation, security, streaming, and error status codes.

Covers:
- valid zip
- valid tar.gz
- Windows-style zip
- zip-slip attempt (rejected)
- oversize (clear 413)
- empty archive (clear 422)
"""

from __future__ import annotations

import asyncio
import io
import tarfile
import zipfile
from unittest.mock import patch

import httpx
import pytest
from app.main import app


@pytest.mark.asyncio
class TestUploadValidationSuite:
    async def test_valid_zip_upload(self) -> None:
        """Valid zip with Python files processes successfully and returns analysis result."""
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("app/main.py", "def run():\n    return 'ok'\n")
            zf.writestr("app/service.py", "from app.main import run\n")

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            files = {"archive": ("project.zip", zip_buf.getvalue(), "application/zip")}
            res = await ac.post("/ingest/archive", files=files)
            assert res.status_code == 202
            job_id = res.json()["job_id"]

            job_data = {}
            for _ in range(50):
                jres = await ac.get(f"/jobs/{job_id}")
                assert jres.status_code == 200
                job_data = jres.json()
                if job_data.get("status") in ("complete", "failed"):
                    break
                await asyncio.sleep(0.05)

            assert job_data.get("status") == "complete"
            assert "analysis_id" in job_data
            assert job_data["metadata"]["file_count"] == 2

    async def test_valid_tar_gz_upload(self) -> None:
        """Valid tar.gz archive uploads, extracts, and produces an analysis id."""
        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w:gz") as tf:
            code = b"class Calculator:\n    def add(self, a, b):\n        return a + b\n"
            ti = tarfile.TarInfo("calc/calc.py")
            ti.size = len(code)
            tf.addfile(ti, io.BytesIO(code))

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            files = {"archive": ("calc.tar.gz", tar_buf.getvalue(), "application/gzip")}
            res = await ac.post("/ingest/archive", files=files)
            assert res.status_code == 202
            job_id = res.json()["job_id"]

            job_data = {}
            for _ in range(50):
                jres = await ac.get(f"/jobs/{job_id}")
                job_data = jres.json()
                if job_data.get("status") in ("complete", "failed"):
                    break
                await asyncio.sleep(0.05)

            assert job_data.get("status") == "complete"
            assert "analysis_id" in job_data
            assert job_data["metadata"]["primary_language"] == "Python"

    async def test_windows_style_zip_upload(self) -> None:
        """Zip archive created on Windows with backslashes normalizes paths safely."""
        win_buf = io.BytesIO()
        with zipfile.ZipFile(win_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(r"pkg\subpkg\win_module.py", "def win_func():\n    return 'windows'\n")
            zf.writestr(r"pkg\main.py", "from pkg.subpkg.win_module import win_func\n")

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            files = {"archive": ("win_project.zip", win_buf.getvalue(), "application/zip")}
            res = await ac.post("/ingest/archive", files=files)
            assert res.status_code == 202
            job_id = res.json()["job_id"]

            job_data = {}
            for _ in range(50):
                jres = await ac.get(f"/jobs/{job_id}")
                job_data = jres.json()
                if job_data.get("status") in ("complete", "failed"):
                    break
                await asyncio.sleep(0.05)

            assert job_data.get("status") == "complete"
            assert "analysis_id" in job_data
            assert job_data["metadata"]["file_count"] == 2

    async def test_zip_slip_attempt_rejected(self) -> None:
        """Archive with directory traversal (Zip Slip) is rejected with clear security error."""
        slip_buf = io.BytesIO()
        with zipfile.ZipFile(slip_buf, "w") as zf:
            zf.writestr("../../etc/passwd", "evil:x:0:0::/root:/bin/bash\n")
            zf.writestr("app/valid.py", "print('hello')\n")

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            files = {"archive": ("evil.zip", slip_buf.getvalue(), "application/zip")}
            res = await ac.post("/ingest/archive", files=files)
            assert res.status_code == 202
            job_id = res.json()["job_id"]

            job_data = {}
            for _ in range(50):
                jres = await ac.get(f"/jobs/{job_id}")
                job_data = jres.json()
                if job_data.get("status") in ("complete", "failed"):
                    break
                await asyncio.sleep(0.05)

            assert job_data.get("status") == "failed"
            assert "Unsafe path rejected" in job_data.get("error", "")

    async def test_oversize_archive_rejected_with_clear_413(self) -> None:
        """Archive exceeding max_compressed_bytes returns clear HTTP 413 Payload Too Large."""
        # Create a small archive, but lower limit to 1 KB to test 413 deterministically
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("test.py", "a = 1\n" * 500)

        raw_bytes = zip_buf.getvalue()

        from ingestion.orchestrator import default_orchestrator

        original_limit = default_orchestrator.limits.max_compressed_bytes
        try:
            # Set limit to 200 bytes
            default_orchestrator.limits.max_compressed_bytes = 200

            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
                files = {"archive": ("oversize.zip", raw_bytes, "application/zip")}
                res = await ac.post("/ingest/archive", files=files)
                assert res.status_code == 413
                detail = res.json().get("detail", "")
                assert "the limit is" in detail
        finally:
            default_orchestrator.limits.max_compressed_bytes = original_limit

    async def test_empty_archive_rejected_with_clear_422(self) -> None:
        """Empty archive (0 bytes or 0 files) returns clear HTTP 422 Unprocessable Entity."""
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            # 0 bytes upload
            files = {"archive": ("empty.zip", b"", "application/zip")}
            res = await ac.post("/ingest/archive", files=files)
            assert res.status_code == 422
            detail = res.json().get("detail", "")
            assert "empty" in detail.lower()

    async def test_no_python_or_java_files_fails_with_clear_message(self) -> None:
        """Archive containing only unsupported files fails with clear user-facing message."""
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("notes.txt", "some notes\n")
            zf.writestr("README.md", "# Project\n")

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            files = {"archive": ("docs.zip", zip_buf.getvalue(), "application/zip")}
            res = await ac.post("/ingest/archive", files=files)
            assert res.status_code == 202
            job_id = res.json()["job_id"]

            job_data = {}
            for _ in range(50):
                jres = await ac.get(f"/jobs/{job_id}")
                job_data = jres.json()
                if job_data.get("status") in ("complete", "failed"):
                    break
                await asyncio.sleep(0.05)

            assert job_data.get("status") == "failed"
            assert "No Python or Java files found" in job_data.get("error", "")

    async def test_invalid_extension_rejected_with_422(self) -> None:
        """Uploading a file with unsupported extension (e.g. .png) returns 422 Unprocessable Entity."""
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            files = {"archive": ("image.png", b"\x89PNG\r\n\x1a\n", "image/png")}
            res = await ac.post("/ingest/archive", files=files)
            assert res.status_code == 422
            detail = res.json().get("detail", "")
            assert "unsupported archive format" in detail.lower()

    async def test_non_existent_job_returns_404(self) -> None:
        """Querying a non-existent job ID returns 404 Not Found."""
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/jobs/00000000-0000-0000-0000-000000000000")
            assert res.status_code == 404
            assert "not found" in res.json().get("detail", "").lower()

    async def test_non_existent_graph_returns_404(self) -> None:
        """Querying a non-existent repo/graph returns 404 Not Found."""
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/graph/00000000-0000-0000-0000-000000000000")
            assert res.status_code == 404
            assert "no analysis found" in res.json().get("detail", "").lower()

    async def test_local_path_disabled_by_default_returns_403(self) -> None:
        """Ingesting local path when ARCHLENS_ALLOW_LOCAL_PATHS is false returns 403 Forbidden."""
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/ingest", json={"source_type": "local", "path": "some/path"})
            assert res.status_code == 403
            assert "local path ingestion is disabled" in res.json().get("detail", "").lower()
