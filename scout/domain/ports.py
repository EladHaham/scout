from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class RepoMapper(ABC):
    """Port: anything that can produce a repo map from a local path."""

    @abstractmethod
    def get_map(self, repo_path: Path) -> str: ...


class NoteGenerator(ABC):
    """Port: anything that can generate symbol notes from source code."""

    @abstractmethod
    def generate(self, symbols: list[dict]) -> list[dict]:
        """
        Given a list of symbol dicts (name, type, signature, body, file),
        return a list of note dicts (purpose, tags, related_symbols).
        Input and output are plain dicts to stay serialization-friendly.
        """
        ...