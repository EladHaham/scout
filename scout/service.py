from __future__ import annotations

from datetime import datetime, timezone

from scout.adapters.aider_mapper import AiderMapper
from scout.adapters.filesystem import normalize_repo_path, repo_state_fingerprint
from scout.domain.models import RepoMapResult
from scout.domain.ports import RepoMapper
from scout.storage.cache import load_cached_map, save_cached_map

_default_mapper = AiderMapper()


def get_repo_map(
    repo: str,
    use_cache: bool = True,
    refresh: bool = False,
    mapper: RepoMapper | None = None,
) -> RepoMapResult:
    mapper = mapper or _default_mapper
    repo_path = normalize_repo_path(repo)
    fingerprint = repo_state_fingerprint(repo_path)

    if use_cache and not refresh:
        cached = load_cached_map(repo_path=repo_path, fingerprint=fingerprint)
        if cached is not None:
            return cached

    map_text = mapper.get_map(repo_path)

    result = RepoMapResult(
        repo_path=repo_path,
        map_text=map_text,
        source="aider",
        generated_at=datetime.now(timezone.utc),
    )

    if use_cache:
        save_cached_map(result=result, fingerprint=fingerprint)

    return result