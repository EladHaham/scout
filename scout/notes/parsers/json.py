from __future__ import annotations

import json
from pathlib import Path

from scout.notes.parsers.base import ParsedSymbol, structural_hash

# Large or generated files to always skip
_SKIP_FILES = {"package-lock.json", "yarn.lock"}

# Don't index files longer than this — likely generated
_MAX_LINES = 300

# Short-circuit huge files before we even read them.
# 200KB is enough headroom for a generously-sized config file.
_MAX_BYTES = 200_000


def parse(path: Path, repo_root: Path) -> list[ParsedSymbol]:
    """Index a JSON config file as a single whole-file symbol."""
    if path.name in _SKIP_FILES:
        return []

    try:
        if path.stat().st_size > _MAX_BYTES:
            return []
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    lines = source.splitlines()
    if len(lines) > _MAX_LINES:
        return []

    try:
        json.loads(source)
    except json.JSONDecodeError:
        return []

    rel_path = str(path.relative_to(repo_root))
    sig = f"json:{path.name}"

    return [ParsedSymbol(
        file=rel_path,
        symbol=rel_path,        # whole-file symbol: symbol == file path
        symbol_type="json",
        line_start=1,
        line_end=len(lines),
        signature=sig,
        # Hash includes the actual content, not just the length —
        # otherwise a value change that preserves file length silently
        # leaves a stale description.
        body=source,
        structural_hash=structural_hash(rel_path, f"{sig}\n{source}"),
        needs_note=True,
    )]