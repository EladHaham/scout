from __future__ import annotations

import json
import os
import re
from pathlib import Path

from scout.domain.models import SymbolNote


def _notes_root(repo_root: Path) -> Path:
    override = os.environ.get("SCOUT_NOTES_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return repo_root / ".scout" / "notes"


def _key(file: str, symbol: str) -> str:
    """Turn 'scout/service.py' + 'get_repo_map' into a safe filename."""
    raw = f"{file}__{symbol}"
    return re.sub(r"[^\w\-.]", "_", raw) + ".json"


def load_note(repo_root: Path, file: str, symbol: str) -> SymbolNote | None:
    note_path = _notes_root(repo_root) / _key(file, symbol)
    if not note_path.exists():
        return None
    try:
        data = json.loads(note_path.read_text(encoding="utf-8"))
        return SymbolNote.from_dict(data)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def save_note(repo_root: Path, note: SymbolNote) -> None:
    folder = _notes_root(repo_root)
    folder.mkdir(parents=True, exist_ok=True)
    note_path = folder / _key(note.file, note.symbol)
    note_path.write_text(
        json.dumps(note.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_all_notes(repo_root: Path) -> list[SymbolNote]:
    folder = _notes_root(repo_root)
    if not folder.exists():
        return []
    notes = []
    for p in folder.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            notes.append(SymbolNote.from_dict(data))
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return notes


def is_stale(note: SymbolNote, current_hash: str) -> bool:
    """A note is stale if the symbol's structural hash has changed."""
    return note.structural_hash != current_hash