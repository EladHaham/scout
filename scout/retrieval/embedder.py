from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from scout.utils.errors import ScoutError


def _embedding_cache_path(repo_root: Path, model: str) -> Path:
    # Sanitize the model name for safe use as a filename component.
    safe_model = re.sub(r"[^\w\-.]", "_", model)
    return repo_root / ".scout" / f"embeddings.{safe_model}.json"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_cache(cache_path: Path) -> dict[str, list[float]]:
    if not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache_path: Path, cache: dict[str, list[float]]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def _get_client():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ScoutError("openai package is not installed. Run: pip install openai") from exc

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ScoutError("OPENAI_API_KEY is not set. Add it to your .env file.")

    return OpenAI(api_key=api_key)


def embed_texts(
    texts: list[str],
    repo_root: Path,
    force: bool = False,
    model: str | None = None,
) -> list[list[float]]:
    """
    Embed a list of texts using OpenAI's embedding API.

    Results are cached by content hash in .scout/embeddings.<model>.json.
    The cache is namespaced per model so switching embedding models never
    silently returns vectors from the wrong model.

    Only texts whose hash is missing from the cache for this model are
    sent to the API. Model defaults to .scout/config.json.
    """
    from scout.config import load_config
    _model = model or load_config(repo_root).embedding_model

    cache_path = _embedding_cache_path(repo_root, _model)
    cache = {} if force else _load_cache(cache_path)

    hashes = [_hash_text(t) for t in texts]
    missing_indices = [i for i, h in enumerate(hashes) if h not in cache]

    if missing_indices:
        client = _get_client()
        missing_texts = [texts[i] for i in missing_indices]

        # Batch in groups of 100
        batch_size = 100
        new_vectors: list[list[float]] = []
        for start in range(0, len(missing_texts), batch_size):
            batch = missing_texts[start : start + batch_size]
            response = client.embeddings.create(model=_model, input=batch)
            new_vectors.extend(item.embedding for item in response.data)

        for i, vec in zip(missing_indices, new_vectors):
            cache[hashes[i]] = vec

        _save_cache(cache_path, cache)

    return [cache[h] for h in hashes]


def embed_query(query: str, repo_root: Path | None = None) -> list[float]:
    """
    Embed a single query string. No caching — queries are ephemeral.
    Model defaults to the value in .scout/config.json if repo_root is provided.
    """
    from scout.config import load_config, ScoutConfig
    _model = (
        load_config(repo_root).embedding_model
        if repo_root is not None
        else ScoutConfig().embedding_model
    )
    client = _get_client()
    response = client.embeddings.create(model=_model, input=[query])
    return response.data[0].embedding