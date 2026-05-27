from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedSymbol:
    file: str             # relative path from repo root
    symbol: str           # e.g. "get_repo_map" or "AiderMapper.get_map"
    symbol_type: str      # "function" | "class" | "method" | "interface" | "type" | "json"
    line_start: int
    line_end: int
    signature: str        # human-readable signature
    body: str             # full source of just this symbol
    structural_hash: str  # hash of name + signature only
    needs_note: bool      # whether this symbol should be sent to the note generator


def structural_hash(name: str, signature: str) -> str:
    payload = f"{name}\n{signature}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def extract_lines(source_lines: list[str], start: int, end: int) -> str:
    """Extract lines start..end (1-indexed, inclusive)."""
    return "".join(source_lines[start - 1:end])


def is_test_file(rel_path: str) -> bool:
    """
    Cross-language test file detection.

    Covers:
    - Python: test_*.py, *_test.py, anything under tests/
    - JS/TS:  *.test.*, *.spec.*, anything under __tests__/
    - Generic: anything under tests/ or test/
    """
    parts = Path(rel_path).parts
    name = Path(rel_path).name
    stem = Path(rel_path).stem  # filename without final suffix

    # Directory-based: tests/, test/, __tests__/ anywhere in the path
    if any(p in {"tests", "test", "__tests__"} for p in parts):
        return True

    # Python conventions
    if name.startswith("test_") or name.endswith("_test.py"):
        return True

    # JS/TS conventions: foo.test.ts, foo.spec.tsx, etc.
    if ".test." in name or ".spec." in name:
        return True
    if stem.endswith(".test") or stem.endswith(".spec"):
        return True

    return False