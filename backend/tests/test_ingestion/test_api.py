"""API route integration tests for ArchLens ingestion endpoints."""

from __future__ import annotations

import asyncio
import io
import zipfile

import httpx
import pytest
from app.main import app
from starlette.testclient import TestClient

client = TestClient(app)


class TestIngestionAPI:
    @pytest.mark.asyncio
    async def test_post_ingest_snippet(self) -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "source_type": "snippet",
                "code": "def hello(): return 'world'\n",
                "language": "python",
                "filename": "hello.py",
            }
            response = await ac.post("/ingest", json=payload)
            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "pending"

            job_id = data["job_id"]
            # Poll for completion with asyncio.sleep so background task runs
            jdata = {}
            for _ in range(50):
                res = await ac.get(f"/jobs/{job_id}")
                assert res.status_code == 200
                jdata = res.json()
                if jdata["status"] == "complete":
                    break
                await asyncio.sleep(0.05)

            assert jdata["status"] == "complete"
            assert jdata["metadata"]["primary_language"] == "Python"

    @pytest.mark.asyncio
    async def test_post_ingest_local_disabled_returns_403(self) -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "source_type": "local",
                "path": "/some/local/path",
            }
            response = await ac.post("/ingest", json=payload)
            assert response.status_code == 403
            assert "disabled" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_post_ingest_archive_upload(self) -> None:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("app.py", "def api(): return True\n")

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            files = {"archive": ("test_repo.zip", zip_buf.getvalue(), "application/zip")}
            response = await ac.post("/ingest/archive", files=files)
            assert response.status_code == 202
            job_id = response.json()["job_id"]

            jdata = {}
            for _ in range(50):
                res = await ac.get(f"/jobs/{job_id}")
                jdata = res.json()
                if jdata["status"] == "complete":
                    break
                await asyncio.sleep(0.05)

            assert jdata["status"] == "complete"
            assert jdata["metadata"]["file_count"] == 1

    @pytest.mark.asyncio
    async def test_post_ingest_folder_upload(self) -> None:
        files = [
            ("files", ("main.py", b"print(1)", "text/plain")),
            ("files", ("util.py", b"print(2)", "text/plain")),
        ]
        data = {
            "paths": ["src/main.py", "src/util.py"],
            "folder_name": "client_folder",
        }
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/ingest/folder", files=files, data=data)
            assert response.status_code == 202
            job_id = response.json()["job_id"]

            jdata = {}
            for _ in range(50):
                res = await ac.get(f"/jobs/{job_id}")
                jdata = res.json()
                if jdata["status"] == "complete":
                    break
                await asyncio.sleep(0.05)

            assert jdata["status"] == "complete"
            assert jdata["metadata"]["repo_name"] == "client_folder"

    @pytest.mark.asyncio
    async def test_get_nonexistent_job_returns_404(self) -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/jobs/nonexistent-id-0000")
            assert res.status_code == 404

    def test_websocket_streaming(self) -> None:
        # Create a job first
        payload = {
            "source_type": "snippet",
            "code": "print('stream test')\n",
            "language": "python",
        }
        response = client.post("/ingest", json=payload)
        job_id = response.json()["job_id"]

        # Connect via WebSocket
        with client.websocket_connect(f"/ws/jobs/{job_id}") as ws:
            # Read first event
            data = ws.receive_json()
            assert data["type"] == "job_event"
            assert data["job_id"] == job_id
            assert "stage" in data
