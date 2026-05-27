from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from scout.domain.models import SymbolNote
from scout.domain.ports import NoteGenerator
from scout.notes.generator import OpenAINoteGenerator
from scout.notes.parser import ParsedSymbol, parse_file
from scout.notes.call_graph import build_call_graph, save_call_graph
from scout.notes.store import is_stale, load_note, save_note

_default_generator = OpenAINoteGenerator()

# Only call the LLM if at least this many symbols need new notes.
# Below this threshold, line numbers and call graph are still refreshed (free).
# refresh=True bypasses this check entirely.
MIN_DIRTY_FOR_API = 5

# File extensions to index
_SOURCE_GLOBS = ["*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.mjs", "*.json", "*.toml"]

# Directories to always skip
_SKIP_DIRS = {"__pycache__", "venv", ".venv", "node_modules", "dist", "dist-electron", ".next", "build", ".git", "site-packages"}
@dataclass
class NotesResult:
    generated: int
    skipped: int
    total: int
    below_threshold: bool = False


def _should_skip(path: Path, repo_root: Path) -> bool:
    parts = path.relative_to(repo_root).parts
    # Skip if any part of the path matches a skip dir (catches nested .venv/lib/site-packages etc.)
    return any(p.startswith(".") or p in _SKIP_DIRS for p in parts)


def generate_notes(
    repo_root: Path,
    generator: NoteGenerator | None = None,
    refresh: bool = False,
    min_dirty: int = MIN_DIRTY_FOR_API,
) -> NotesResult:
    generator = generator or _default_generator

    # 1. Parse all supported files
    print("→ Parsing files...", flush=True)
    all_symbols: list[ParsedSymbol] = []

    for glob in _SOURCE_GLOBS:
        for src_file in sorted(repo_root.rglob(glob)):
            if _should_skip(src_file, repo_root):
                continue
            found = parse_file(src_file, repo_root)
            if found:
                print(f"  {src_file.relative_to(repo_root)} — {len(found)} symbols", flush=True)
            all_symbols.extend(found)

    if not all_symbols:
        print("  No symbols found.", flush=True)
        return NotesResult(generated=0, skipped=0, total=0)

    print(f"  Total: {len(all_symbols)} symbols\n", flush=True)

    # 2. Diff: find symbols that need a new note
    print("→ Checking staleness...", flush=True)
    dirty: list[ParsedSymbol] = []
    skipped: list[ParsedSymbol] = []

    for sym in all_symbols:
        if not sym.needs_note:
            skipped.append(sym)
            continue
        existing = load_note(repo_root, sym.file, sym.symbol)
        if refresh or existing is None or is_stale(existing, sym.structural_hash):
            dirty.append(sym)
        else:
            skipped.append(sym)

    print(f"  {len(dirty)} to generate, {len(skipped)} up to date\n", flush=True)

    # 3. Refresh line numbers on skipped notes (free — no API)
    lines_refreshed = 0
    for sym in skipped:
        if not sym.needs_note:
            continue
        existing = load_note(repo_root, sym.file, sym.symbol)
        if existing is None:
            continue
        if existing.line_start != sym.line_start or existing.line_end != sym.line_end:
            updated = SymbolNote(
                file=existing.file, symbol=existing.symbol,
                symbol_type=existing.symbol_type,
                line_start=sym.line_start, line_end=sym.line_end,
                purpose=existing.purpose, tags=existing.tags,
                related_symbols=existing.related_symbols,
                structural_hash=existing.structural_hash,
                generated_at=existing.generated_at,
            )
            save_note(repo_root, updated)
            lines_refreshed += 1

    if lines_refreshed:
        print(f"→ Refreshed line numbers for {lines_refreshed} symbols.\n", flush=True)

    # 4. Call the LLM only if enough symbols are dirty
    if dirty and (refresh or len(dirty) >= min_dirty):
        print(f"→ Calling OpenAI API ({len(dirty)} symbols)...", flush=True)
        symbol_dicts = [
            {
                "file": s.file,
                "symbol": s.symbol,
                "symbol_type": s.symbol_type,
                "signature": s.signature,
                "body": s.body,
            }
            for s in dirty
        ]

        raw_notes = generator.generate(symbol_dicts)
        print(f"  API returned {len(raw_notes)} notes\n", flush=True)

        # Build lookup keyed by "file:symbol" (primary) and "symbol" (fallback).
        # The model is instructed to return both fields, so file:symbol is preferred
        # to correctly handle duplicate symbol names (Props, parse, main, etc.)
        notes_by_symbol: dict[str, dict] = {}
        for n in raw_notes:
            if "file" in n:
                notes_by_symbol[f"{n['file']}:{n['symbol']}"] = n
            notes_by_symbol.setdefault(n["symbol"], n)
            # Also index by basename for whole-file JSON/TOML symbols
            basename = Path(n["symbol"]).name
            if basename != n["symbol"]:
                notes_by_symbol.setdefault(basename, n)

        print("→ Saving notes...", flush=True)
        now = datetime.now(timezone.utc)
        saved = 0
        for sym in dirty:
            # Try compound key first (handles duplicate symbol names across files)
            raw = notes_by_symbol.get(f"{sym.file}:{sym.symbol}") or notes_by_symbol.get(sym.symbol)
            if raw is None:
                print(f"  ⚠ No note returned for {sym.symbol}", flush=True)
                continue
            note = SymbolNote(
                file=sym.file, symbol=sym.symbol,
                symbol_type=sym.symbol_type,
                line_start=sym.line_start, line_end=sym.line_end,
                purpose=raw.get("purpose", ""),
                tags=raw.get("tags", []),
                related_symbols=raw.get("related_symbols", []),
                structural_hash=sym.structural_hash,
                generated_at=now,
            )
            save_note(repo_root, note)
            print(f"  ✓ {sym.symbol}", flush=True)
            saved += 1

        print(f"\n  Saved {saved} notes.", flush=True)
        generated_count = len(dirty)
        below_threshold = False

    elif dirty:
        print(
            f"→ {len(dirty)} symbol(s) changed but below threshold ({min_dirty}). "
            "Skipping API call. Use refresh=True to force.",
            flush=True,
        )
        generated_count = 0
        below_threshold = True

    else:
        generated_count = 0
        below_threshold = False

    # 5. Prune orphaned notes (symbols that no longer exist in the codebase)
    current_keys = {(s.file, s.symbol) for s in all_symbols if s.needs_note}
    from scout.notes.store import _notes_root
    notes_root = _notes_root(repo_root)
    pruned = 0
    if notes_root.exists():
        for note_file in notes_root.glob("*.json"):
            try:
                import json as _json
                d = _json.loads(note_file.read_text())
                if (d["file"], d["symbol"]) not in current_keys:
                    note_file.unlink()
                    pruned += 1
            except Exception:
                continue
    if pruned:
        print(f"→ Pruned {pruned} orphaned notes.", flush=True)

    # 6. Rebuild call graph (Python only for now — JS/TS call graph is a future task)
    print("\n→ Building call graph...", flush=True)
    python_symbols = [s for s in all_symbols if s.file.endswith(".py")]
    graph = build_call_graph(python_symbols, repo_root)
    save_call_graph(repo_root, graph)
    print(f"  {len(graph.edges)} nodes, saved to .scout/call_graph.json", flush=True)

    return NotesResult(
        generated=generated_count,
        skipped=len(skipped),
        total=len(all_symbols),
        below_threshold=below_threshold,
    )