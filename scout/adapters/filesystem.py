from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from scout.utils.errors import ScoutError


def normalize_repo_path(repo: str | Path) -> Path:
    """
    Resolve the input path and normalize it to the git repo root.
    """
    raw_path = Path(repo).expanduser().resolve()

    if not raw_path.exists():
        raise ScoutError(f"Path does not exist: {raw_path}")

    if not raw_path.is_dir():
        raise ScoutError(f"Path is not a directory: {raw_path}")

    return detect_git_root(raw_path)


def detect_git_root(path: Path) -> Path:
    """
    Return the git repository root for the given path.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except FileNotFoundError as exc:
        raise ScoutError(
            "Git is not installed or not available on PATH."
        ) from exc

    if proc.returncode != 0:
        raise ScoutError(
            f"Path is not inside a git repository: {path}"
        )

    root = proc.stdout.strip()
    if not root:
        raise ScoutError(f"Could not determine git root for: {path}")

    return Path(root).resolve()


def _git_output(repo_root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def repo_state_fingerprint(repo_root: Path) -> str:
    """
    Build a cache fingerprint from:
    - normalized repo root
    - current HEAD commit (if available)
    - working tree status (including untracked files)

    This keeps the cache simple while invalidating when the repo changes.
    """
    head = _git_output(repo_root, "rev-parse", "HEAD") or "NO_HEAD"
    status = _git_output(repo_root, "status", "--porcelain", "--untracked-files=all")

    payload = f"{repo_root}\n{head}\n{status}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()