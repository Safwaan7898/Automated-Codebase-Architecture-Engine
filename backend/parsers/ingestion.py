"""Repository ingestion — accept a GitHub URL or a local path.

Provides:
    - :func:`ingest_source` — resolves a source string to a local directory
    - :func:`collect_files` — recursively collects files obeying ``IngestionConfig``
    - :class:`FileInfo` — metadata about a collected file
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from parsers.config import IngestionConfig
from parsers.registry import detect_language_by_extension

logger = logging.getLogger(__name__)

# ── GitHub URL patterns ───────────────────────────────────────────────────────

_GITHUB_RE = re.compile(
    r"^(https?://github\.com/[\w.\-]+/[\w.\-]+(?:\.git)?|"
    r"git@github\.com:[\w.\-]+/[\w.\-]+(?:\.git)?)$",
    re.IGNORECASE,
)

_GITLIKE_RE = re.compile(r"^(https?://|git@|git://|ssh://)", re.IGNORECASE)


@dataclass
class FileInfo:
    """Metadata for a single collected source file."""

    abs_path: Path
    rel_path: str
    """Path relative to the repository root, using forward slashes."""

    language: str
    size_bytes: int


@dataclass
class IngestedRepo:
    """Result of ingesting a source (URL or local path)."""

    root: Path
    """Absolute path to the repository root (may be a temp directory for clones)."""

    is_temp: bool
    """True if *root* is a temporary directory that should be cleaned up."""

    source: str
    """Original source string (URL or path)."""

    commit_sha: str | None = None
    """Git commit SHA if available."""


# ── Public API ────────────────────────────────────────────────────────────────


def ingest_source(source: str, config: IngestionConfig) -> IngestedRepo:
    """Resolve *source* to a local directory.

    Args:
        source: A local path or a GitHub/git URL.
        config: Ingestion configuration (clone depth, timeout, etc.).

    Returns:
        :class:`IngestedRepo` — caller is responsible for calling
        :func:`cleanup_ingested` when done if ``is_temp`` is ``True``.

    Raises:
        ValueError: If the source is invalid or unreachable.
        RuntimeError: If git clone fails.
    """
    source = source.strip()

    if _GITLIKE_RE.match(source):
        return _clone_repo(source, config)

    path = Path(source).resolve()
    if not path.exists():
        raise ValueError(f"Path does not exist: {source}")
    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {source}")

    logger.info("Using local path: %s", path)
    from parsers.fingerprint import get_git_commit_sha

    commit_sha = get_git_commit_sha(path)
    return IngestedRepo(root=path, is_temp=False, source=source, commit_sha=commit_sha)


def cleanup_ingested(repo: IngestedRepo) -> None:
    """Remove the temporary clone directory if applicable."""
    if repo.is_temp and repo.root.exists():
        try:
            shutil.rmtree(repo.root, ignore_errors=True)
            logger.debug("Cleaned up temp clone: %s", repo.root)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to clean up temp dir %s: %s", repo.root, exc)


def collect_files(root: Path, config: IngestionConfig) -> list[FileInfo]:
    """Walk *root* and return all parseable source files.

    Applies ignore-dir and ignore-file rules from *config*.
    Files are returned in sorted order (deterministic across platforms).
    """
    files: list[FileInfo] = []
    _walk_dir(root, root, config, files)
    files.sort(key=lambda f: f.rel_path)
    logger.info(
        "Collected %d files from %s (supported languages: %s)",
        len(files),
        root,
        config.supported_languages,
    )
    return files


def detect_primary_language(files: list[FileInfo]) -> str:
    """Return the most common language in *files*, or ``'unknown'``."""
    counts: dict[str, int] = {}
    for f in files:
        if f.language != "unknown":
            counts[f.language] = counts.get(f.language, 0) + 1
    if not counts:
        return "unknown"
    return max(counts, key=lambda k: counts[k])


# ── Private helpers ───────────────────────────────────────────────────────────


def _clone_repo(url: str, config: IngestionConfig) -> IngestedRepo:
    """Shallow-clone *url* into a temporary directory."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="archlens_clone_"))
    logger.info("Cloning %s → %s (depth=%d)", url, tmp_dir, config.clone_depth)
    t0 = time.monotonic()
    try:
        env = dict(subprocess.os.environ)
        env["GIT_TERMINAL_PROMPT"] = "0"
        cmd = [
            "git",
            "-c",
            "core.hooksPath=",
            "-c",
            "init.templateDir=",
            "clone",
            "--depth",
            str(config.clone_depth),
            "--single-branch",
            "--no-recurse-submodules",
            "--no-tags",
            "--quiet",
            url,
            str(tmp_dir),
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.clone_timeout_s,
            env=env,
        )
        if result.returncode != 0:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise RuntimeError(f"git clone failed (code {result.returncode}): {result.stderr.strip()}")
        # Extract commit SHA before sanitization
        commit_sha: str | None = None
        git_dir = tmp_dir / ".git"
        if git_dir.exists():
            try:
                sha_res = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(tmp_dir),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if sha_res.returncode == 0 and sha_res.stdout.strip():
                    commit_sha = sha_res.stdout.strip()
            except Exception:
                pass
            shutil.rmtree(git_dir, ignore_errors=True)
        elapsed = time.monotonic() - t0
        logger.info("Clone finished in %.1f s (commit_sha=%s)", elapsed, commit_sha)
        return IngestedRepo(root=tmp_dir, is_temp=True, source=url, commit_sha=commit_sha)
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"git clone timed out after {config.clone_timeout_s} s") from None
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


def _walk_dir(
    current: Path,
    root: Path,
    config: IngestionConfig,
    out: list[FileInfo],
) -> None:
    """Recursive directory walker respecting ignore rules."""
    try:
        entries = sorted(current.iterdir(), key=lambda p: p.name)
    except PermissionError:
        return

    for entry in entries:
        if entry.is_symlink():
            continue  # skip symlinks to avoid cycles

        if entry.is_dir():
            if config.should_ignore_dir(entry.name):
                continue
            _walk_dir(entry, root, config, out)

        elif entry.is_file():
            lang = detect_language_by_extension(entry)
            if lang not in config.supported_languages:
                continue
            try:
                size = entry.stat().st_size
            except OSError:
                continue
            if size > config.max_file_size_bytes:
                logger.debug("Skipping oversized file: %s (%d bytes)", entry, size)
                continue
            if config.should_ignore_file(entry):
                continue
            rel = entry.relative_to(root).as_posix()
            out.append(FileInfo(abs_path=entry, rel_path=rel, language=lang, size_bytes=size))
