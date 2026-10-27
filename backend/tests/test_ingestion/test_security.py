"""Security unit and integration tests for ArchLens ingestion layer."""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from ingestion.config import IngestionLimits
from ingestion.exceptions import (
    LimitExceeded,
    SecurityError,
    ZipBombError,
)
from ingestion.security import (
    detect_archive_type,
    safe_extract_archive,
    validate_safe_url,
)

# ── SSRF Tests ───────────────────────────────────────────────────────────────


class TestSSRFProtection:
    def test_reject_http_scheme(self) -> None:
        with pytest.raises(SecurityError, match="Only HTTPS URLs are allowed"):
            validate_safe_url("http://github.com/octocat/Hello-World")

    def test_reject_ftp_and_file_schemes(self) -> None:
        with pytest.raises(SecurityError, match="Only HTTPS URLs are allowed"):
            validate_safe_url("file:///etc/passwd")

        with pytest.raises(SecurityError, match="Only HTTPS URLs are allowed"):
            validate_safe_url("ftp://example.com/repo.git")

    def test_reject_loopback_raw_ip(self) -> None:
        with pytest.raises(SecurityError, match="blocked"):
            validate_safe_url("https://127.0.0.1/malicious.zip")

    def test_reject_private_rfc1918_ips(self) -> None:
        with pytest.raises(SecurityError, match="blocked"):
            validate_safe_url("https://10.0.0.1/repo.git")
        with pytest.raises(SecurityError, match="blocked"):
            validate_safe_url("https://172.16.5.20/repo.git")
        with pytest.raises(SecurityError, match="blocked"):
            validate_safe_url("https://192.168.1.100/repo.git")

    def test_reject_ipv6_loopback(self) -> None:
        with pytest.raises(SecurityError, match="blocked"):
            validate_safe_url("https://[::1]/repo.git")

    def test_reject_hostname_resolving_to_loopback(self) -> None:
        # localhost resolves to 127.0.0.1 or ::1
        with pytest.raises(SecurityError, match="blocked"):
            validate_safe_url("https://localhost/repo.git")

    def test_reject_mocked_dns_rebinding_to_private_ip(self) -> None:
        fake_addr_info = [(2, 1, 6, "", ("10.200.1.5", 443))]
        with patch("socket.getaddrinfo", return_value=fake_addr_info):
            with pytest.raises(SecurityError, match="resolves to private/internal IP"):
                validate_safe_url("https://attacker-internal.com/archive.zip")

    def test_allow_legitimate_public_url(self) -> None:
        fake_public_addr = [(2, 1, 6, "", ("140.82.121.4", 443))]
        with patch("socket.getaddrinfo", return_value=fake_public_addr):
            # Should not raise
            validate_safe_url("https://github.com/pallets/flask.git")


# ── Zip Slip Tests ───────────────────────────────────────────────────────────


class TestZipSlipProtection:
    def test_reject_zip_slip_relative_traversal(self, tmp_path: Path) -> None:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            # Entry attempting to write outside workspace
            zf.writestr("../../evil.txt", "MALICIOUS PAYLOAD")

        archive_file = tmp_path / "slip.zip"
        archive_file.write_bytes(zip_buf.getvalue())

        dest_dir = tmp_path / "workspace"
        limits = IngestionLimits()

        with pytest.raises(SecurityError, match="Zip Slip"):
            safe_extract_archive(archive_file, dest_dir, limits)

        # Non-negotiable acceptance: NOTHING is written outside dest_dir
        evil_file = tmp_path / "evil.txt"
        assert not evil_file.exists(), "Malicious file was written outside workspace!"

    def test_reject_zip_slip_absolute_unix_path(self, tmp_path: Path) -> None:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("/tmp/evil.txt", "MALICIOUS")

        archive_file = tmp_path / "abs_slip.zip"
        archive_file.write_bytes(zip_buf.getvalue())
        dest_dir = tmp_path / "workspace"

        with pytest.raises(SecurityError, match="Zip Slip"):
            safe_extract_archive(archive_file, dest_dir, IngestionLimits())

    def test_reject_tar_slip_relative_traversal(self, tmp_path: Path) -> None:
        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w") as tf:
            ti = tarfile.TarInfo(name="../../tar_evil.txt")
            ti.size = 12
            tf.addfile(ti, io.BytesIO(b"evil content"))

        archive_file = tmp_path / "slip.tar"
        archive_file.write_bytes(tar_buf.getvalue())
        dest_dir = tmp_path / "workspace"

        with pytest.raises(SecurityError, match="Zip Slip"):
            safe_extract_archive(archive_file, dest_dir, IngestionLimits())

        assert not (tmp_path / "tar_evil.txt").exists()


# ── Symlink Escape Tests ─────────────────────────────────────────────────────


class TestSymlinkEscapeProtection:
    def test_reject_tar_symlink_pointing_outside_workspace(self, tmp_path: Path) -> None:
        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w") as tf:
            ti = tarfile.TarInfo(name="escape_symlink")
            ti.type = tarfile.SYMTYPE
            ti.linkname = "../../outside_file.txt"
            tf.addfile(ti)

        archive_file = tmp_path / "symlink_escape.tar"
        archive_file.write_bytes(tar_buf.getvalue())
        dest_dir = tmp_path / "workspace"

        with pytest.raises(SecurityError, match="Symlink escape"):
            safe_extract_archive(archive_file, dest_dir, IngestionLimits())

    def test_reject_zip_symlink_pointing_to_root(self, tmp_path: Path) -> None:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zi = zipfile.ZipInfo("symlink_entry")
            zi.create_system = 3  # Unix
            zi.external_attr = 0o120777 << 16  # Symlink mode
            zf.writestr(zi, "/etc/passwd")

        archive_file = tmp_path / "symlink_abs.zip"
        archive_file.write_bytes(zip_buf.getvalue())
        dest_dir = tmp_path / "workspace"

        with pytest.raises(SecurityError, match="Symlink escape"):
            safe_extract_archive(archive_file, dest_dir, IngestionLimits())


# ── Zip Bomb Tests ───────────────────────────────────────────────────────────


class TestZipBombProtection:
    def test_reject_exceeding_max_uncompressed_bytes(self, tmp_path: Path) -> None:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("big.txt", b"A" * 50_000)

        archive_file = tmp_path / "bomb_size.zip"
        archive_file.write_bytes(zip_buf.getvalue())

        dest_dir = tmp_path / "workspace"
        limits = IngestionLimits(max_uncompressed_bytes=10_000)  # low cap for test

        with pytest.raises(ZipBombError, match="uncompressed size exceeds limit"):
            safe_extract_archive(archive_file, dest_dir, limits)

    def test_reject_exceeding_max_files(self, tmp_path: Path) -> None:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for i in range(15):
                zf.writestr(f"file_{i}.txt", f"data {i}")

        archive_file = tmp_path / "bomb_count.zip"
        archive_file.write_bytes(zip_buf.getvalue())

        dest_dir = tmp_path / "workspace"
        limits = IngestionLimits(max_files=10)  # low cap for test

        with pytest.raises(LimitExceeded, match="Archive contains more than 10 files"):
            safe_extract_archive(archive_file, dest_dir, limits)

    def test_reject_exceeding_nesting_depth(self, tmp_path: Path) -> None:
        # Create inner zip
        inner_buf = io.BytesIO()
        with zipfile.ZipFile(inner_buf, "w") as zf_inner:
            zf_inner.writestr("leaf.txt", "hello")

        # Create middle zip containing inner zip
        mid_buf = io.BytesIO()
        with zipfile.ZipFile(mid_buf, "w") as zf_mid:
            zf_mid.writestr("inner.zip", inner_buf.getvalue())

        # Create outer zip containing middle zip
        outer_buf = io.BytesIO()
        with zipfile.ZipFile(outer_buf, "w") as zf_outer:
            zf_outer.writestr("mid.zip", mid_buf.getvalue())

        archive_file = tmp_path / "nested.zip"
        archive_file.write_bytes(outer_buf.getvalue())

        dest_dir = tmp_path / "workspace"
        # Cap nesting at 1
        limits = IngestionLimits(max_archive_nesting=1)

        with pytest.raises(ZipBombError, match="nesting depth"):
            safe_extract_archive(archive_file, dest_dir, limits)


# ── Magic Bytes Detection Tests ──────────────────────────────────────────────


class TestMagicBytesDetection:
    def test_detect_zip(self, tmp_path: Path) -> None:
        f = tmp_path / "test.zip"
        f.write_bytes(b"PK\x03\x04restofzip")
        assert detect_archive_type(f) == "zip"

    def test_detect_gzip(self, tmp_path: Path) -> None:
        f = tmp_path / "test.tar.gz"
        f.write_bytes(b"\x1f\x8brestofgzip")
        assert detect_archive_type(f) == "tar.gz"

    def test_detect_bzip2(self, tmp_path: Path) -> None:
        f = tmp_path / "test.tar.bz2"
        f.write_bytes(b"BZhrestofbzip")
        assert detect_archive_type(f) == "tar.bz2"

    def test_detect_by_bytes_content_not_extension(self, tmp_path: Path) -> None:
        # File named .txt but with ZIP magic bytes
        f = tmp_path / "misleading.txt"
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("code.py", "print('hello')")
        f.write_bytes(zip_buf.getvalue())

        assert detect_archive_type(f) == "zip"
