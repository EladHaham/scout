from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


RepoMapSource = Literal["aider", "cache"]
SymbolType = Literal["function", "class", "method"]


@dataclass(slots=True)
class RepoMapResult:
    repo_path: Path
    map_text: str
    source: RepoMapSource
    generated_at: datetime

    def to_dict(self) -> dict[str, str]:
        return {
            "repo_path": str(self.repo_path),
            "source": self.source,
            "generated_at": self.generated_at.isoformat(),
            "map_text": self.map_text,
        }

@dataclass(slots=True)
class SymbolNote:
    file: str                          # relative path from repo root
    symbol: str                        # function or class name
    symbol_type: SymbolType            # "function" | "class" | "method"
    line_start: int
    line_end: int
    purpose: str                       # one sentence — this is what gets embedded
    tags: list[str]
    related_symbols: list[str]
    structural_hash: str               # hash of name+signature, used for staleness
    generated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "symbol": self.symbol,
            "symbol_type": self.symbol_type,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "purpose": self.purpose,
            "tags": self.tags,
            "related_symbols": self.related_symbols,
            "structural_hash": self.structural_hash,
            "generated_at": self.generated_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SymbolNote":
        return SymbolNote(
            file=data["file"],
            symbol=data["symbol"],
            symbol_type=data["symbol_type"],
            line_start=data["line_start"],
            line_end=data["line_end"],
            purpose=data["purpose"],
            tags=data.get("tags", []),
            related_symbols=data.get("related_symbols", []),
            structural_hash=data["structural_hash"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
        )