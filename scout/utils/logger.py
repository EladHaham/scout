"""
scout/utils/logger.py

Structured logging for Scout.

Two channels:
- Progress output (human-readable) → stderr
- Structured events (machine-readable) → .scout/scout.log as NDJSON

Log events are designed for the observability dashboard:
- context_query: fired on every scout_context call
- notes_run: fired on every scout_notes call
- retrieval_fallback: fired when retrieval drops below level 1
"""
from __future__ import annotations

import contextlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Progress output (stderr)
# ---------------------------------------------------------------------------

def progress(msg: str) -> None:
    """Write a human-readable progress line to stderr."""
    print(msg, file=sys.stderr, flush=True)


@contextlib.contextmanager
def stdout_to_stderr():
    """
    Redirect stdout to stderr for the duration of the block.

    MCP uses stdio for JSON-RPC — any stray print() to stdout corrupts
    the stream. Progress output from generate_notes / build_retrieval_index
    is useful for humans but must go to stderr when running under MCP.

    This is NOT for errors — just for progress chatter that belongs on
    the diagnostic channel, not the data channel.
    """
    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        yield
    finally:
        sys.stdout = old_stdout


# ---------------------------------------------------------------------------
# Structured log (NDJSON → .scout/scout.log)
# ---------------------------------------------------------------------------

def _log_path(repo_root: Path) -> Path:
    return repo_root / ".scout" / "scout.log"


def _write_event(repo_root: Path, event: dict[str, Any]) -> None:
    """Append one NDJSON line to the log file. Silent on failure."""
    try:
        path = _log_path(repo_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False, default=str) + "\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # never let logging break the main flow


def log_context_query(
    repo_root: Path,
    *,
    query: str,
    top_score: float,
    fallback_level: int,
    direct_count: int,
    neighbor_count: int,
    token_count: int,
    symbols: list[dict],   # [{symbol, file, score, relevance}]
    duration_ms: float,
) -> None:
    """Log a scout_context retrieval event."""
    _write_event(repo_root, {
        "event": "context_query",
        "ts": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "top_score": round(top_score, 4),
        "fallback_level": fallback_level,
        "direct_count": direct_count,
        "neighbor_count": neighbor_count,
        "token_count": token_count,
        "duration_ms": round(duration_ms, 1),
        "symbols": symbols,
    })


def log_notes_run(
    repo_root: Path,
    *,
    generated: int,
    skipped: int,
    total: int,
    indexed: int,
    duration_ms: float,
) -> None:
    """Log a scout_notes indexing event."""
    _write_event(repo_root, {
        "event": "notes_run",
        "ts": datetime.now(timezone.utc).isoformat(),
        "generated": generated,
        "skipped": skipped,
        "total": total,
        "indexed": indexed,
        "duration_ms": round(duration_ms, 1),
    })