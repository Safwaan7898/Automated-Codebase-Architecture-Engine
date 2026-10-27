"""Unit tests for language detection and workspace scanning."""

from __future__ import annotations

from pathlib import Path

from ingestion.config import IngestionLimits
from ingestion.language_detector import is_binary_file, scan_workspace


class TestLanguageDetector:
    def test_detect_breakdown_and_primary(self, tmp_path: Path) -> None:
        src = tmp_path / "repo"
        src.mkdir()

        # Write 3 Python files, 1 Java file, 1 Markdown file
        (src / "a.py").write_text("print('a')")
        (src / "b.py").write_text("print('b')")
        (src / "c.py").write_text("print('c')")
        (src / "Main.java").write_text("public class Main {}")
        (src / "README.md").write_text("# Readme")

        res = scan_workspace(src, IngestionLimits())

        assert res.file_count == 5
        assert res.primary_language == "Python"
        assert res.supported is True
        assert res.language_breakdown["Python"] == 3
        assert res.language_breakdown["Java"] == 1
        assert res.language_breakdown["Markdown"] == 1

    def test_warn_on_unsupported_language(self, tmp_path: Path) -> None:
        src = tmp_path / "go_repo"
        src.mkdir()

        # Write 4 Go files
        for i in range(4):
            (src / f"worker_{i}.go").write_text("package main")

        res = scan_workspace(src, IngestionLimits())

        assert res.primary_language == "Go"
        assert res.supported is False
        assert any("not yet supported" in w for w in res.warnings)

    def test_skip_vendored_and_build_dirs(self, tmp_path: Path) -> None:
        src = tmp_path / "full_repo"
        src.mkdir()

        (src / "src").mkdir()
        (src / "src" / "App.java").write_text("public class App {}")

        # Directories that should be skipped by default
        (src / "node_modules").mkdir()
        (src / "node_modules" / "ignored.js").write_text("console.log()")

        (src / ".git").mkdir()
        (src / ".git" / "HEAD").write_text("ref: refs/heads/main")

        (src / "build").mkdir()
        (src / "build" / "Compiled.class").write_bytes(b"\xca\xfe\xba\xbe")

        res = scan_workspace(src, IngestionLimits())

        assert res.file_count == 1
        assert res.primary_language == "Java"
        assert "JavaScript" not in res.language_breakdown

    def test_skip_binary_files(self, tmp_path: Path) -> None:
        src = tmp_path / "bin_repo"
        src.mkdir()

        (src / "app.py").write_text("print('code')")
        (src / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
        (src / "binary.dat").write_bytes(b"\x00\x01\x02\x03\x00\xff")

        assert is_binary_file(src / "image.png")
        assert is_binary_file(src / "binary.dat")
        assert not is_binary_file(src / "app.py")

        res = scan_workspace(src, IngestionLimits())
        assert res.file_count == 1
        assert "Python" in res.language_breakdown
