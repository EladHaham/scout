from __future__ import annotations

from pathlib import Path

from scout.notes.parsers.base import ParsedSymbol  # re-export for callers
from scout.notes.parsers import python, typescript
from scout.notes.parsers import json as json_parser
from scout.notes.parsers import toml as toml_parser

__all__ = ["ParsedSymbol", "parse_file"]


def parse_file(path: Path, repo_root: Path) -> list[ParsedSymbol]:
    """
    Dispatch to the appropriate language parser based on file extension.
    Returns a list of ParsedSymbol instances ready for note generation.
    """
    suffix = path.suffix.lower()

    if suffix == ".py":
        return python.parse(path, repo_root)

    if suffix in typescript.EXTENSIONS:
        return typescript.parse(path, repo_root)

    if suffix == ".json":
        return json_parser.parse(path, repo_root)

    if suffix == ".toml":
        return toml_parser.parse(path, repo_root)

    return []


# Re-export for call_graph.py compatibility
from scout.notes.parsers.python import _is_test_file  # noqa: F401