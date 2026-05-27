from __future__ import annotations

from pathlib import Path

from scout.notes.parsers.base import ParsedSymbol, structural_hash

_MAX_LINES = 300
_MAX_BYTES = 200_000


def parse(path: Path, repo_root: Path) -> list[ParsedSymbol]:
    """Index a TOML config file as a single whole-file symbol."""
    try:
        if path.stat().st_size > _MAX_BYTES:
            return []
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    lines = source.splitlines()
    if len(lines) > _MAX_LINES:
        return []

    # Validate it's real TOML
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # backport for 3.10
        except ImportError:
            tomllib = None  # type: ignore

    if tomllib is not None:
        try:
            tomllib.loads(source)
        except Exception:
            return []

    rel_path = str(path.relative_to(repo_root))
    sig = f"toml:{path.name}"

    return [ParsedSymbol(
        file=rel_path,
        symbol=rel_path,
        symbol_type="toml",
        line_start=1,
        line_end=len(lines),
        signature=sig,
        body=source,
        # Hash includes the actual content, not just the length —
        # otherwise a value change that preserves file length silently
        # leaves a stale description.
        structural_hash=structural_hash(rel_path, f"{sig}\n{source}"),
        needs_note=True,
    )]