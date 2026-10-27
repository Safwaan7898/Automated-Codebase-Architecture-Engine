"""End-to-end integration tests for the IngestionOrchestrator pipeline."""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest
from ingestion.config import IngestionLimits
from ingestion.job_store import JobStore
from ingestion.models import JobStatus
from ingestion.orchestrator import IngestionOrchestrator
from ingestion.sources import (
    ArchiveUploadSource,
    FolderUploadSource,
    SnippetSource,
)
from ingestion.workspace import WorkspaceManager


@pytest.fixture
def clean_orchestrator(tmp_path: Path):
    store = JobStore()
    ws_mgr = WorkspaceManager(base_dir=tmp_path / "workspaces")
    limits = IngestionLimits(workspace_ttl_s=3600)
    return IngestionOrchestrator(job_store=store, workspace_manager=ws_mgr, limits=limits)


class TestOrchestratorPipeline:
    @pytest.mark.asyncio
    async def test_pasted_python_snippet_pipeline(self, clean_orchestrator: IngestionOrchestrator) -> None:
        code = (
            "import os\n\n"
            "class Greeter:\n"
            "    def greet(self, name: str) -> str:\n"
            "        return f'Hello, {name}!'\n\n"
            "def main():\n"
            "    g = Greeter()\n"
            "    return g.greet('World')\n"
        )
        src = SnippetSource(code=code, language="python", filename="greeter.py")
        metadata, result = await clean_orchestrator.run_sync(src)

        assert metadata.primary_language == "Python"
        assert metadata.file_count == 1
        assert metadata.supported is True
        assert result is not None
        assert result.node_count > 0
        assert any(n.name == "Greeter" for n in result.nodes)
        assert any(n.name == "greet" for n in result.nodes)

    @pytest.mark.asyncio
    async def test_zip_java_pipeline(self, clean_orchestrator: IngestionOrchestrator) -> None:
        java_code = (
            "package com.example.demo;\n\n"
            "import java.util.List;\n\n"
            "public class Calculator {\n"
            "    public int add(int a, int b) {\n"
            "        return a + b;\n"
            "    }\n"
            "}\n"
        )
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("com/example/demo/Calculator.java", java_code)

        src = ArchiveUploadSource(archive_data=zip_buf.getvalue(), filename="calc_java.zip")
        metadata, result = await clean_orchestrator.run_sync(src)

        assert metadata.primary_language == "Java"
        assert metadata.supported is True
        assert result is not None
        assert result.node_count > 0
        assert any(n.name == "Calculator" for n in result.nodes)

    @pytest.mark.asyncio
    async def test_tar_gz_python_pipeline(self, clean_orchestrator: IngestionOrchestrator) -> None:
        py_code = b"class Service:\n    def execute(self):\n        pass\n"
        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w:gz") as tf:
            ti = tarfile.TarInfo(name="service.py")
            ti.size = len(py_code)
            tf.addfile(ti, io.BytesIO(py_code))

        src = ArchiveUploadSource(archive_data=tar_buf.getvalue(), filename="service.tar.gz")
        metadata, result = await clean_orchestrator.run_sync(src)

        assert metadata.primary_language == "Python"
        assert result is not None
        assert any(n.name == "Service" for n in result.nodes)

    @pytest.mark.asyncio
    async def test_folder_upload_pipeline(self, clean_orchestrator: IngestionOrchestrator) -> None:
        files = [
            ("core/engine.py", b"class Engine:\n    def start(self): pass\n"),
            ("core/config.py", b"DEBUG = True\n"),
        ]
        src = FolderUploadSource(files=files, folder_name="my_app")
        metadata, result = await clean_orchestrator.run_sync(src)

        assert metadata.primary_language == "Python"
        assert result is not None
        assert any(n.name == "Engine" for n in result.nodes)

    @pytest.mark.asyncio
    async def test_deduplication_reuses_cached_result(self, clean_orchestrator: IngestionOrchestrator) -> None:
        code = "def dedupe_test(): return 123\n"
        src1 = SnippetSource(code=code, language="python", filename="dedupe.py")
        src2 = SnippetSource(code=code, language="python", filename="dedupe.py")

        assert src1.source_hash == src2.source_hash

        job_id_1 = await clean_orchestrator.start_ingestion(src1)
        # Give pipeline a moment to complete in background
        import asyncio

        for _ in range(50):
            job1 = clean_orchestrator.job_store.get_job(job_id_1)
            if job1 and job1.status == JobStatus.COMPLETE:
                break
            await asyncio.sleep(0.05)

        assert job1.status == JobStatus.COMPLETE

        # Second submission with same source hash
        job_id_2 = await clean_orchestrator.start_ingestion(src2)
        job2 = clean_orchestrator.job_store.get_job(job_id_2)

        # Should be immediately COMPLETE with cached result
        assert job2.status == JobStatus.COMPLETE
        assert job2.result is not None
        assert job2.events[-1].stage == "cached"
