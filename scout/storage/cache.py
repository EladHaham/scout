from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

from scout.domain.models import RepoMapResult


def _cache_root() -> Path:
    override = os.environ.get("SCOUT_CACHE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".scout" / "cache"


def _repo_key(repo_path: Path) -> str:
    return hashlib.sha256(str(repo_path).encode("utf-8")).hexdigest()[:16]


def _repo_cache_dir(repo_path: Path) -> Path:
    return _cache_root() / _repo_key(repo_path)


def load_cached_map(repo_path: Path, fingerprint: str) -> RepoMapResult | None:
    folder = _repo_cache_dir(repo_path)
    text_file = folder / "repo_map.txt"
    meta_file = folder / "meta.json"

    if not text_file.exists() or not meta_file.exists():
        return None

    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    if meta.get("fingerprint") != fingerprint:
        return None

    try:
        generated_at = datetime.fromisoformat(meta["generated_at"])
    except (KeyError, ValueError):
        return None

    return RepoMapResult(
        repo_path=repo_path,
        map_text=text_file.read_text(encoding="utf-8"),
        source="cache",
        generated_at=generated_at,
    )


def save_cached_map(result: RepoMapResult, fingerprint: str) -> None:
    folder = _repo_cache_dir(result.repo_path)
    folder.mkdir(parents=True, exist_ok=True)

    text_file = folder / "repo_map.txt"
    meta_file = folder / "meta.json"

    text_file.write_text(result.map_text, encoding="utf-8")
    meta_file.write_text(
        json.dumps(
            {
                "repo_path": str(result.repo_path),
                "fingerprint": fingerprint,
                "generated_at": result.generated_at.isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )