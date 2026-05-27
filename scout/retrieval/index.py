from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from scout.utils.errors import ScoutError

_INDEX_FILE = "embedding_index.json"


@dataclass(frozen=True)
class IndexEntry:
    symbol: str       # e.g. "load_cached_map"
    file: str         # relative path
    purpose: str      # the text that was embedded
    vector: list[float]


@dataclass(frozen=True)
class SearchResult:
    symbol: str
    file: str
    purpose: str
    score: float      # cosine similarity, 0.0–1.0


def _index_path(repo_root: Path) -> Path:
    return repo_root / ".scout" / _INDEX_FILE


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    try:
        import numpy as np
    except ImportError as exc:
        raise ScoutError("numpy is required for retrieval. Run: pip install numpy") from exc

    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def build_index(entries: list[IndexEntry], repo_root: Path) -> None:
    """Persist an index of symbol vectors to .scout/embedding_index.json."""
    index_path = _index_path(repo_root)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    data = [
        {
            "symbol": e.symbol,
            "file": e.file,
            "purpose": e.purpose,
            "vector": e.vector,
        }
        for e in entries
    ]
    index_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def load_index(repo_root: Path) -> list[IndexEntry]:
    """Load the persisted index. Returns empty list if not built yet."""
    index_path = _index_path(repo_root)
    if not index_path.exists():
        return []
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return [
        IndexEntry(
            symbol=item["symbol"],
            file=item["file"],
            purpose=item["purpose"],
            vector=item["vector"],
        )
        for item in data
    ]


def search(
    query_vector: list[float],
    index: list[IndexEntry],
    top_k: int = 5,
) -> list[SearchResult]:
    """
    Return the top_k most similar entries to query_vector by cosine similarity.
    Results are sorted descending by score.
    """
    if not index:
        return []

    scored = [
        SearchResult(
            symbol=entry.symbol,
            file=entry.file,
            purpose=entry.purpose,
            score=_cosine_similarity(query_vector, entry.vector),
        )
        for entry in index
    ]
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]