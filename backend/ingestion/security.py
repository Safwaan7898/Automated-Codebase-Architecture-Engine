"""Security controls for the ingestion layer.

Protections implemented:
1. SSRF prevention: HTTPS only, resolution to private/loopback/link-local/multicast IP blocked.
   Redirects validated step-by-step.
2. Zip Slip / Path traversal prevention: entry paths cannot escape workspace.
3. Symlink escape prevention: symlinks cannot point outside workspace.
4. Zip bomb prevention: uncompressed size limit, file count limit, compression ratio limit, nesting limit.
5. Magic bytes auto-detection for archives.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import shutil
import socket
import tarfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import httpx

from ingestion.config import IngestionLimits
from ingestion.exceptions import EmptyArchiveError, LimitExceeded, SecurityError, SourceError, ZipBombError

logger = logging.getLogger(__name__)

# Disallowed IPv4 / IPv6 subnets
_DISALLOWED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),  # Current network (only valid as source)
    ipaddress.ip_network("10.0.0.0/8"),  # RFC 1918 private
    ipaddress.ip_network("100.64.0.0/10"),  # Shared Address Space / CGNAT
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("172.16.0.0/12"),  # RFC 1918 private
    ipaddress.ip_network("192.0.0.0/24"),  # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),  # RFC 1918 private
    ipaddress.ip_network("198.18.0.0/15"),  # Network benchmark tests
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast
    # IPv6
    ipaddress.ip_network("::/128"),  # Unspecified
    ipaddress.ip_network("::1/128"),  # Loopback
    ipaddress.ip_network("fc00::/7"),  # Unique Local Address (private)
    ipaddress.ip_network("fe80::/10"),  # Link-local
    ipaddress.ip_network("ff00::/8"),  # Multicast
]


def is_ip_disallowed(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address belongs to any private/internal/disallowed range."""
    # NAT64 well-known prefix 64:ff9b::/96 maps public IPv4 addresses
    if isinstance(ip, ipaddress.IPv6Address) and ip in ipaddress.ip_network("64:ff9b::/96"):
        embedded_ipv4 = ipaddress.IPv4Address(ip.packed[-4:])
        return is_ip_disallowed(embedded_ipv4)
    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
        return True
    return any(ip in net for net in _DISALLOWED_NETWORKS)


def validate_safe_url(url: str) -> None:
    """Validate that a URL is safe to fetch (SSRF prevention).

    Requires HTTPS.
    Resolves hostname to IP and verifies that none of the resolved IPs are private or loopback.

    Raises:
        SecurityError: If URL is non-HTTPS or resolves to a disallowed IP.
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise SecurityError(f"Only HTTPS URLs are allowed for security. Received scheme: '{parsed.scheme or 'none'}'")

    hostname = parsed.hostname
    if not hostname:
        raise SecurityError("Invalid URL: missing hostname.")

    # Check for raw IP in URL hostname
    try:
        raw_ip = ipaddress.ip_address(hostname)
        if is_ip_disallowed(raw_ip):
            raise SecurityError(f"Access to private/internal IP address '{hostname}' is blocked.")
        return
    except ValueError:
        pass

    # Resolve hostname to all associated IPs
    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SourceError(f"Could not resolve hostname '{hostname}': {exc}") from exc

    for item in addr_info:
        sockaddr = item[4]
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            if is_ip_disallowed(ip_obj):
                raise SecurityError(
                    f"Access to URL '{url}' is blocked: domain '{hostname}' resolves to private/internal IP '{ip_str}'."
                )
        except ValueError:
            continue


async def safe_download_url(
    url: str,
    dest_path: Path,
    limits: IngestionLimits,
) -> int:
    """Download a file via HTTPS with SSRF checks, redirect validation, timeout and size caps.

    Returns the total bytes downloaded.
    """
    current_url = url
    redirects = 0
    client_timeout = httpx.Timeout(limits.fetch_timeout_s, connect=10.0)

    async with httpx.AsyncClient(timeout=client_timeout, follow_redirects=False) as client:
        while True:
            validate_safe_url(current_url)

            try:
                response = await client.get(current_url)
            except httpx.RequestError as exc:
                raise SourceError(f"Failed to connect to '{current_url}': {exc}") from exc

            # Handle redirects
            if response.status_code in (301, 302, 303, 307, 308):
                redirects += 1
                if redirects > limits.max_redirects:
                    raise LimitExceeded(f"Too many redirects (exceeded limit of {limits.max_redirects}).")
                location = response.headers.get("Location")
                if not location:
                    raise SourceError(f"Redirect response {response.status_code} missing Location header.")
                # Resolve relative redirect URLs
                current_url = str(response.url.join(location))
                continue

            if response.status_code != 200:
                raise SourceError(f"HTTP request to '{current_url}' failed with status {response.status_code}.")

            # Check Content-Length header if present
            cl_header = response.headers.get("Content-Length")
            if cl_header:
                try:
                    expected_len = int(cl_header)
                    if expected_len > limits.max_compressed_bytes:
                        msg = (
                            f"Remote file size ({expected_len} bytes) exceeds "
                            f"limit ({limits.max_compressed_bytes} bytes)."
                        )
                        raise LimitExceeded(msg)
                except ValueError:
                    pass

            # Stream download to disk
            total_bytes = 0
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with dest_path.open("wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                    total_bytes += len(chunk)
                    if total_bytes > limits.max_compressed_bytes:
                        dest_path.unlink(missing_ok=True)
                        raise LimitExceeded(
                            f"Downloaded file exceeded maximum size ({limits.max_compressed_bytes} bytes)."
                        )
                    f.write(chunk)

            return total_bytes


def is_safe_path(target_path: Path, base_dir: Path) -> bool:
    """Ensure target_path resolves strictly within base_dir."""
    try:
        base = base_dir.resolve()
        target = target_path.resolve()
        target.relative_to(base)
        return True
    except (ValueError, RuntimeError):
        return False


def detect_archive_type(data_or_path: bytes | Path) -> str | None:
    """Detect archive format by inspecting magic bytes, not file extension.

    Supported formats: 'zip', 'tar', 'tar.gz', 'tar.bz2'.
    """
    if isinstance(data_or_path, Path):
        with data_or_path.open("rb") as f:
            header = f.read(512)
    else:
        header = data_or_path[:512]

    if len(header) < 4:
        return None

    # Zip magic bytes: PK\x03\x04, PK\x05\x06 (empty zip), PK\x07\x08 (spanned)
    if header.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "zip"

    # Gzip: \x1f\x8b
    if header.startswith(b"\x1f\x8b"):
        return "tar.gz"

    # Bzip2: BZh
    if header.startswith(b"BZh"):
        return "tar.bz2"

    # Tar: POSIX ustar at offset 257
    if len(header) >= 262 and header[257:262] == b"ustar":
        return "tar"

    # Check if tarfile can parse it (some legacy tar formats lack standard ustar magic)
    if isinstance(data_or_path, Path):
        try:
            with tarfile.open(data_or_path, "r:*") as tf:
                if tf.getmembers():
                    return "tar"
        except Exception as exc:
            logger.debug("Failed to detect tar format: %s", exc)

    return None


def safe_extract_archive(
    archive_path: Path,
    dest_dir: Path,
    limits: IngestionLimits,
    depth: int = 0,
) -> int:
    """Extract an archive securely into dest_dir.

    Enforces:
    - Zip Slip check (no .. or path traversal outside dest_dir)
    - Symlink escape check (no symlinks pointing outside dest_dir)
    - Zip Bomb check (uncompressed size, file count, compression ratio)
    - Nested archive check (maximum archive nesting depth)

    Returns:
        Number of files extracted.
    """
    if depth > limits.max_archive_nesting:
        raise ZipBombError(f"Archive nesting depth {depth} exceeds limit of {limits.max_archive_nesting}.")

    archive_type = detect_archive_type(archive_path)
    if not archive_type:
        raise SourceError(f"Unsupported or corrupted archive format in '{archive_path.name}'.")

    dest_dir.mkdir(parents=True, exist_ok=True)
    resolved_dest = dest_dir.resolve()

    if archive_type == "zip":
        return _extract_zip(archive_path, resolved_dest, limits, depth)
    elif archive_type in ("tar", "tar.gz", "tar.bz2"):
        return _extract_tar(archive_path, resolved_dest, limits, depth, archive_type)
    else:
        raise SourceError(f"Unsupported archive format: {archive_type}")


class ExtractionResult(int):
    """Integer subclass containing extraction metrics (extracted_files, skipped_files, skipped_by_dir)."""

    extracted_files: int
    skipped_files: int
    skipped_by_dir: dict[str, int]

    def __new__(cls, extracted: int, skipped: int = 0, skipped_by_dir: dict[str, int] | None = None):
        obj = super().__new__(cls, extracted)
        obj.extracted_files = extracted
        obj.skipped_files = skipped
        obj.skipped_by_dir = skipped_by_dir or {}
        return obj


def _extract_zip(
    archive_path: Path,
    resolved_dest: Path,
    limits: IngestionLimits,
    depth: int,
) -> ExtractionResult:
    try:
        zf = zipfile.ZipFile(archive_path)
    except zipfile.BadZipFile as exc:
        raise SourceError(f"Corrupt zip archive: {exc}") from exc

    total_uncompressed = 0
    file_count = 0
    skipped_count = 0
    skipped_by_dir: dict[str, int] = {}
    nested_archives: list[Path] = []

    with zf:
        for member in zf.infolist():
            raw_name = member.filename
            norm_name = raw_name.replace("\\", "/")
            name = norm_name.lstrip("/")

            # Check for directory traversal in member name
            if raw_name.startswith("/") or raw_name.startswith("\\") or (len(raw_name) > 1 and raw_name[1] == ":") or norm_name.startswith("/"):
                raise SecurityError(f"Unsafe path rejected (Zip Slip): absolute path detected in archive entry '{raw_name}'.")

            parts = Path(name).parts
            if ".." in parts:
                raise SecurityError(f"Unsafe path rejected: Zip Slip path traversal '..' detected in archive entry '{raw_name}'.")

            target_path = (resolved_dest / name).resolve()
            try:
                target_path.relative_to(resolved_dest)
            except ValueError:
                raise SecurityError(f"Unsafe path rejected: entry '{raw_name}' extracts outside target directory.") from None

            # Skip ignored directories (node_modules, .git, __pycache__, .venv, dist, build, etc.)
            skip_set = {d.lower() for d in limits.skip_dirs} | {
                "node_modules",
                ".git",
                ".svn",
                ".hg",
                "__pycache__",
                ".venv",
                "venv",
                "env",
                ".env",
                "dist",
                "build",
                ".next",
                ".nuxt",
                ".cache",
                ".turbo",
                ".idea",
                ".vscode",
                "target",
                ".reports_storage",
            }
            matching_skip = [part for part in parts if part.lower() in skip_set]
            if matching_skip:
                skipped_count += 1
                dir_key = matching_skip[0]
                skipped_by_dir[dir_key] = skipped_by_dir.get(dir_key, 0) + 1
                continue

            # Skip directory entries
            if member.is_dir():
                continue

            # Zip bomb checks: size, count, ratio
            file_count += 1
            if file_count > limits.max_files:
                raise LimitExceeded(f"Archive contains more than {limits.max_files} files.")

            total_uncompressed += member.file_size
            if total_uncompressed > limits.max_uncompressed_bytes:
                raise ZipBombError(f"Archive uncompressed size exceeds limit of {limits.max_uncompressed_bytes} bytes.")

            if member.compress_size > 0:
                ratio = member.file_size / member.compress_size
                if ratio > limits.max_compression_ratio and member.file_size > 1024 * 1024:
                    raise ZipBombError(
                        f"Zip bomb detected: entry '{name}' has suspicious compression ratio {ratio:.1f}."
                    )

            # Check if this is a symlink (Unix attribute 0o120000)
            is_symlink = (member.external_attr >> 16) & 0o170000 == 0o120000
            if is_symlink:
                # Read symlink target
                link_content = zf.read(member).decode("utf-8", errors="replace").strip()
                # Symlinks must not escape
                if os.path.isabs(link_content) or (len(link_content) > 1 and link_content[1] == ":"):
                    raise SecurityError(f"Symlink escape: absolute symlink target '{link_content}'.")
                resolved_link = (target_path.parent / link_content).resolve()
                try:
                    resolved_link.relative_to(resolved_dest)
                except ValueError:
                    raise SecurityError(
                        f"Symlink escape: symlink '{name}' points to '{link_content}' outside workspace."
                    ) from None

            # Extract the file safely
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src_f, target_path.open("wb") as dst_f:
                    shutil.copyfileobj(src_f, dst_f)
            except Exception as write_err:
                logger.warning("Failed to extract %s: %s (skipping)", name, write_err)
                continue

            # Check if extracted file is a nested archive
            if detect_archive_type(target_path):
                nested_archives.append(target_path)

    # Process nested archives
    for nested_arch in nested_archives:
        nested_out = nested_arch.with_suffix(".extracted")
        try:
            extracted = safe_extract_archive(nested_arch, nested_out, limits, depth=depth + 1)
            file_count += extracted
            nested_arch.unlink(missing_ok=True)
        except (EmptyArchiveError, SourceError) as exc:
            logger.debug("Nested archive %s could not be extracted (%s); keeping as raw file", nested_arch, exc)

    if file_count == 0:
        raise EmptyArchiveError("Uploaded archive is empty or contains no files.")

    return ExtractionResult(file_count, skipped_count, skipped_by_dir)


def _extract_tar(
    archive_path: Path,
    resolved_dest: Path,
    limits: IngestionLimits,
    depth: int,
    archive_type: str,
) -> int:
    mode = "r:*"
    if archive_type == "tar.gz":
        mode = "r:gz"
    elif archive_type == "tar.bz2":
        mode = "r:bz2"

    try:
        tf = tarfile.open(archive_path, mode)
    except (tarfile.TarError, OSError) as exc:
        raise SourceError(f"Corrupt tar archive: {exc}") from exc

    total_uncompressed = 0
    file_count = 0
    nested_archives: list[Path] = []

    with tf:
        for member in tf.getmembers():
            raw_name = member.name
            norm_name = raw_name.replace("\\", "/")
            name = norm_name.lstrip("/")

            if raw_name.startswith("/") or raw_name.startswith("\\") or (len(raw_name) > 1 and raw_name[1] == ":") or norm_name.startswith("/"):
                raise SecurityError(f"Unsafe path rejected: absolute path detected in tar entry '{raw_name}'.")

            parts = Path(name).parts
            if ".." in parts:
                raise SecurityError(f"Unsafe path rejected: Zip Slip path traversal '..' detected in tar entry '{raw_name}'.")

            target_path = (resolved_dest / name).resolve()
            try:
                target_path.relative_to(resolved_dest)
            except ValueError:
                raise SecurityError(f"Unsafe path rejected: entry '{raw_name}' extracts outside target directory.") from None

            # Symlink or hardlink check
            if member.issym() or member.islnk():
                linkname = member.linkname
                if os.path.isabs(linkname) or (len(linkname) > 1 and linkname[1] == ":"):
                    raise SecurityError(f"Symlink escape: absolute symlink target '{linkname}' in tar.")
                resolved_link = (target_path.parent / linkname).resolve()
                try:
                    resolved_link.relative_to(resolved_dest)
                except ValueError:
                    raise SecurityError(
                        f"Symlink escape: entry '{name}' points to '{linkname}' outside workspace."
                    ) from None
                continue

            # Skip ignored directories (node_modules, .git, __pycache__, .venv, dist, build, etc.)
            skip_set = {d.lower() for d in limits.skip_dirs} | {
                "node_modules",
                ".git",
                ".svn",
                ".hg",
                "__pycache__",
                ".venv",
                "venv",
                "env",
                ".env",
                "dist",
                "build",
                ".next",
                ".nuxt",
                ".cache",
                ".turbo",
                ".idea",
                ".vscode",
                "target",
                ".reports_storage",
            }
            if any(part.lower() in skip_set for part in parts):
                continue

            if member.isdir():
                continue

            if not member.isreg():
                # Skip device files, fifos, etc.
                continue

            file_count += 1
            if file_count > limits.max_files:
                raise LimitExceeded(f"Archive contains more than {limits.max_files} files.")

            total_uncompressed += member.size
            if total_uncompressed > limits.max_uncompressed_bytes:
                raise ZipBombError(f"Archive uncompressed size exceeds limit of {limits.max_uncompressed_bytes} bytes.")

            # Extract regular file safely
            target_path.parent.mkdir(parents=True, exist_ok=True)
            f_src = tf.extractfile(member)
            if f_src is not None:
                with f_src, target_path.open("wb") as dst_f:
                    shutil.copyfileobj(f_src, dst_f)

            if detect_archive_type(target_path):
                nested_archives.append(target_path)

    for nested_arch in nested_archives:
        nested_out = nested_arch.with_suffix(".extracted")
        try:
            extracted = safe_extract_archive(nested_arch, nested_out, limits, depth=depth + 1)
            file_count += extracted
            nested_arch.unlink(missing_ok=True)
        except (EmptyArchiveError, SourceError) as exc:
            logger.debug("Nested archive %s could not be extracted (%s); keeping as raw file", nested_arch, exc)

    if file_count == 0:
        raise EmptyArchiveError("Uploaded archive is empty or contains no files.")

    return file_count
