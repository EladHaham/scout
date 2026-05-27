from __future__ import annotations

import ast
from pathlib import Path

from scout.notes.parsers.base import ParsedSymbol, structural_hash, extract_lines

_SKIP_METHODS = {
    "to_dict", "from_dict", "to_json", "from_json",
    "__init__", "__repr__", "__str__", "__eq__", "__hash__",
    "__len__", "__iter__", "__next__", "__enter__", "__exit__",
    "__getitem__", "__setitem__", "__delitem__", "__contains__",
}

_PRIVATE_MIN_LINES = 10


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = [arg.arg for arg in node.args.args]
    return f"def {node.name}({', '.join(args)})"


def _is_test_file(rel_path: str) -> bool:
    parts = Path(rel_path).parts
    name = Path(rel_path).name
    return name.startswith("test_") or name.endswith("_test.py") or "tests" in parts


def _should_note(name: str, line_start: int, line_end: int, is_test: bool) -> bool:
    if is_test:
        return False
    bare = name.split(".")[-1]
    if bare in _SKIP_METHODS:
        return False
    if bare.startswith("_") and (line_end - line_start + 1) < _PRIVATE_MIN_LINES:
        return False
    return True


def parse(path: Path, repo_root: Path) -> list[ParsedSymbol]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    source_lines = source.splitlines(keepends=True)
    rel_path = str(path.relative_to(repo_root))
    is_test = _is_test_file(rel_path)
    symbols: list[ParsedSymbol] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sig = _signature(node)
            symbols.append(ParsedSymbol(
                file=rel_path, symbol=node.name, symbol_type="function",
                line_start=node.lineno, line_end=node.end_lineno,
                signature=sig,
                body=extract_lines(source_lines, node.lineno, node.end_lineno),
                structural_hash=structural_hash(node.name, sig),
                needs_note=_should_note(node.name, node.lineno, node.end_lineno, is_test),
            ))
        elif isinstance(node, ast.ClassDef):
            symbols.append(ParsedSymbol(
                file=rel_path, symbol=node.name, symbol_type="class",
                line_start=node.lineno, line_end=node.end_lineno,
                signature=f"class {node.name}",
                body=extract_lines(source_lines, node.lineno, node.end_lineno),
                structural_hash=structural_hash(node.name, f"class {node.name}"),
                needs_note=_should_note(node.name, node.lineno, node.end_lineno, is_test),
            ))
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    sig = _signature(child)
                    qualified = f"{node.name}.{child.name}"
                    symbols.append(ParsedSymbol(
                        file=rel_path, symbol=qualified, symbol_type="method",
                        line_start=child.lineno, line_end=child.end_lineno,
                        signature=sig,
                        body=extract_lines(source_lines, child.lineno, child.end_lineno),
                        structural_hash=structural_hash(qualified, sig),
                        needs_note=_should_note(qualified, child.lineno, child.end_lineno, is_test),
                    ))

    return symbols