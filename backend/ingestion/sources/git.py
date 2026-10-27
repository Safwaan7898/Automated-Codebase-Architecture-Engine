"""Git URL ingestion source.

Supports:
- GitHub, GitLab, Bitbucket, and arbitrary HTTPS git repositories.
- Shallow clone (--depth 1) for speed and resource protection.
- Branch, tag, or specific commit hash checkout.
- Subpath selection for monorepos (extracting only the relevant subpath).
- Access tokens for private repositories passed strictly in-memory (via http.extraHeader).
  Never written to disk, database, or logged.
- Security:
  - SSRF URL validation (HTTPS only, no private/loopback IPs).
  - Code execution disabled (core.hooksPath="", init.templateDir="").
  - Submodule recursion disabled by default.
"""

from __future__ import annotations

import base64
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ingestion.config import IngestionLimits
from ingestion.exceptions import AuthError, IngestionError, SourceError
from ingestion.hash_utils import hash_git_source
from ingestion.models import IngestionSource, JobStatus, ProgressReporter
from ingestion.security import validate_safe_url

logger = logging.getLogger(__name__)


class GitSource(IngestionSource):
    """Clones a remote Git repository into the workspace."""

    def __init__(
        self,
        url: str,
        *,
        branch: str | None = None,
        commit: str | None = None,
        subpath: str | None = None,
        access_token: str | None = None,
    ) -> None:
        self.url = url.strip()
        self.branch = branch.strip() if branch else None
        self.commit = commit.strip() if commit else None
        self.subpath = subpath.strip().strip("/\\") if subpath else None
        # Access token is stored only in-memory on the instance, never serialized or logged
        self._token = access_token.strip() if access_token else None

    @property
    def source_type(self) -> str:
        return "git"

    @property
    def display_name(self) -> str:
        # Never include token in display name
        parsed = urlparse(self.url)
        return f"{parsed.netloc}{parsed.path}"

    @property
    def repo_name(self) -> str:
        parsed = urlparse(self.url)
        name = Path(parsed.path).stem
        return name or "repository"

    @property
    def source_hash(self) -> str:
        return hash_git_source(self.url, self.branch, self.commit, self.subpath)

    async def fetch(
        self,
        src_dir: Path,
        limits: IngestionLimits,
        progress: ProgressReporter,
    ) -> dict[str, Any]:
        await progress(JobStatus.FETCHING, "validating_url", 5.0, f"Validating Git URL: {self.display_name}")

        # 1. Security: SSRF validation
        validate_safe_url(self.url)

        await progress(JobStatus.FETCHING, "cloning", 20.0, f"Cloning shallow repository from {self.display_name}")

        # Build git command with secure config (no hooks, no templates, no terminal prompt)
        git_config_args = [
            "-c",
            "core.hooksPath=",
            "-c",
            "init.templateDir=",
        ]

        # Handle authentication if token is provided
        if self._token:
            auth_header = f"Authorization: Basic {base64.b64encode(f'token:{self._token}'.encode()).decode()}"
            git_config_args.extend(["-c", f"http.extraHeader={auth_header}"])

        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"

        # Clone into a temporary directory first so we can cleanly isolate and handle subpaths
        temp_clone_dir = Path(tempfile.mkdtemp(prefix="archlens_git_"))
        try:
            clone_cmd = [
                "git",
                *git_config_args,
                "clone",
                "--depth",
                str(limits.git_clone_depth),
                "--no-recurse-submodules",
                "--quiet",
            ]

            if self.branch and not self.commit:
                clone_cmd.extend(["--branch", self.branch])

            clone_cmd.extend([self.url, str(temp_clone_dir)])

            try:
                proc = subprocess.run(
                    clone_cmd,
                    capture_output=True,
                    text=True,
                    timeout=limits.fetch_timeout_s,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                raise IngestionError(f"Git clone timed out after {limits.fetch_timeout_s} seconds.") from None

            if proc.returncode != 0:
                stderr = proc.stderr or ""
                # Scrub any possible token reflection in error output
                if self._token:
                    stderr = stderr.replace(self._token, "[REDACTED]")

                err_lower = stderr.lower()
                is_auth_err = (
                    "authentication failed" in err_lower
                    or "could not read username" in err_lower
                    or "access denied" in err_lower
                )
                if is_auth_err:
                    raise AuthError(
                        "Git authentication failed. A personal access token may be required for this repository."
                    )
                if "Remote branch" in stderr and "not found" in stderr:
                    raise SourceError(f"Branch '{self.branch}' was not found in remote repository.")
                raise SourceError(f"Git clone failed: {stderr.strip()}")

            # If specific commit requested, fetch and checkout
            if self.commit:
                checkout_proc = subprocess.run(
                    ["git", *git_config_args, "checkout", self.commit],
                    cwd=str(temp_clone_dir),
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env,
                )
                if checkout_proc.returncode != 0:
                    err_msg = f"Failed to checkout requested commit '{self.commit}': {checkout_proc.stderr.strip()}"
                    raise SourceError(err_msg)

            # Extract commit hash and actual branch
            head_commit = (
                subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(temp_clone_dir),
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.strip()
                or self.commit
            )

            active_branch = self.branch
            if not active_branch:
                branch_out = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=str(temp_clone_dir),
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.strip()
                if branch_out and branch_out != "HEAD":
                    active_branch = branch_out

            # Remove .git metadata directory from the clone before copying to workspace
            git_meta_dir = temp_clone_dir / ".git"
            if git_meta_dir.exists():
                shutil.rmtree(git_meta_dir, ignore_errors=True)

            # Move files to src_dir (respecting subpath if set)
            copy_source = temp_clone_dir
            if self.subpath:
                sub_path_dir = temp_clone_dir / self.subpath
                if not sub_path_dir.exists() or not sub_path_dir.is_dir():
                    raise SourceError(f"Subpath '{self.subpath}' does not exist in repository.")
                copy_source = sub_path_dir

            await progress(JobStatus.EXTRACTING, "copying_files", 70.0, "Preparing workspace source files")

            # Copy files from copy_source into src_dir
            for item in copy_source.iterdir():
                dest_item = src_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest_item)
                else:
                    shutil.copy2(item, dest_item)

            await progress(JobStatus.EXTRACTING, "complete", 100.0, "Git ingestion complete")

            return {
                "commit_hash": head_commit,
                "branch": active_branch,
                "subpath": self.subpath,
            }

        finally:
            shutil.rmtree(temp_clone_dir, ignore_errors=True)
