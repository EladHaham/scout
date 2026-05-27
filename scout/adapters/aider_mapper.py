from __future__ import annotations

from pathlib import Path, PurePosixPath

from scout.domain.ports import RepoMapper
from scout.utils.errors import ScoutError

_IGNORED_DIR_NAMES = {
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".aider.tags.cache.v4",
    ".git",
}

_IGNORED_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
}

_IGNORED_FILE_NAMES = {
    ".DS_Store",
    ".coverage",
    ".aider.chat.history.md",
}


_KNOWN_EXTENSIONLESS_FILES = {
    "Makefile",
    "Dockerfile",
    "LICENSE",
    "README",
    "CHANGELOG",
    "AUTHORS",
    "CONTRIBUTORS",
}


def _candidate_repo_map_path(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None
    if stripped.startswith(("│", "⋮", "╭", "╰", "─")):
        return None
    candidate = stripped[:-1] if stripped.endswith(":") else stripped
    name = PurePosixPath(candidate.replace("\\", "/")).name
    if "/" in candidate or candidate.startswith(".") or "." in name:
        return candidate
    if name in _KNOWN_EXTENSIONLESS_FILES:
        return candidate
    return None


def _looks_like_junk_path(path: str) -> bool:
    pure = PurePosixPath(path.replace("\\", "/"))
    parts = pure.parts
    name = pure.name
    if any(part in _IGNORED_DIR_NAMES for part in parts):
        return True
    if any(part.endswith(".egg-info") for part in parts):
        return True
    if name in _IGNORED_FILE_NAMES:
        return True
    if pure.suffix in _IGNORED_FILE_SUFFIXES:
        return True
    return False


def _filter_repo_map(text: str) -> str:
    """Remove generated/cache artifacts from repo map text."""
    output: list[str] = []
    skip_current_block = False

    for line in text.splitlines():
        candidate_path = _candidate_repo_map_path(line)
        if candidate_path is not None:
            skip_current_block = _looks_like_junk_path(candidate_path)
            if skip_current_block:
                continue
            output.append(line)
            continue
        if skip_current_block:
            continue
        output.append(line)

    compact: list[str] = []
    previous_blank = False
    for line in output:
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue
        compact.append(line)
        previous_blank = is_blank

    return "\n".join(compact).strip()


def _collect_repo_files(repo_path: Path) -> list[str]:
    """Return all non-junk file paths under repo_path as absolute strings."""
    files = []
    for f in repo_path.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(repo_path)
        if _looks_like_junk_path(str(rel)):
            continue
        files.append(str(f))
    return files


def _build_repo_map(repo_path: Path, map_tokens: int = 1024) -> str:
    try:
        from aider.io import InputOutput
        from aider.models import Model
        from aider.repomap import RepoMap
    except ImportError as exc:
        raise ScoutError(
            "aider-chat is not installed. Run: pip install aider-chat"
        ) from exc

    io = InputOutput(pretty=False, fancy_input=False)
    model = Model("gpt-4o-mini")  # used only for token counting

    rm = RepoMap(
        map_tokens=map_tokens,
        root=str(repo_path),
        main_model=model,
        io=io,
    )

    files = _collect_repo_files(repo_path)
    result = rm.get_repo_map(chat_files=[], other_files=files)

    if not result:
        raise ScoutError("Aider RepoMap returned empty output.")

    return _filter_repo_map(result)


class AiderMapper(RepoMapper):
    """RepoMapper implementation backed by Aider's Python API."""

    def __init__(self, map_tokens: int = 1024) -> None:
        self.map_tokens = map_tokens

    def get_map(self, repo_path: Path) -> str:
        return _build_repo_map(repo_path, map_tokens=self.map_tokens)