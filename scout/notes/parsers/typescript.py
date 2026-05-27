from __future__ import annotations

import sys
from pathlib import Path

from scout.notes.parsers.base import (
    ParsedSymbol,
    extract_lines,
    is_test_file,
    structural_hash,
)

# JS/TS boilerplate to skip.
# Note: `render` is intentionally NOT here — React class components have
# meaningful render methods that should be indexed.
_SKIP_METHODS = {
    "constructor", "toString", "toJSON", "valueOf",
}

_PRIVATE_MIN_LINES = 8

# Extensions handled by this parser
EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".mjs"}


def _should_note(name: str, line_start: int, line_end: int, is_test: bool) -> bool:
    if is_test:
        return False
    bare = name.split(".")[-1]
    if bare in _SKIP_METHODS:
        return False
    if bare.startswith(("_", "#")) and (line_end - line_start + 1) < _PRIVATE_MIN_LINES:
        return False
    return True


def _get_language(suffix: str):
    """Return the appropriate Tree-sitter Language for a given file extension."""
    import tree_sitter_typescript as ts_ts
    import tree_sitter_javascript as ts_js
    from tree_sitter import Language

    if suffix == ".tsx":
        return Language(ts_ts.language_tsx())
    if suffix in (".ts",):
        return Language(ts_ts.language_typescript())
    return Language(ts_js.language())  # .js, .jsx, .mjs


def _param_name(param_node, source_bytes: bytes) -> str:
    """
    Extract just the parameter name (or destructuring pattern) from a
    parameter AST node, dropping type annotations and default values.

    Tree-sitter exposes parameters as nodes with a `pattern` field (the
    identifier or destructuring pattern) and an optional `type` field
    (the annotation). We want the pattern only.
    """
    pattern = param_node.child_by_field_name("pattern")
    if pattern is not None:
        return source_bytes[pattern.start_byte:pattern.end_byte].decode("utf-8", errors="replace").strip()

    # Fallback: some grammar variants put the name directly on the param node
    # under different field names. Try `name` first, then take the first
    # identifier-shaped child.
    name = param_node.child_by_field_name("name")
    if name is not None:
        return source_bytes[name.start_byte:name.end_byte].decode("utf-8", errors="replace").strip()

    for child in param_node.children:
        if child.type in ("identifier", "shorthand_property_identifier"):
            return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()

    return ""


def _build_signature(name: str, sym_type: str, node, source_bytes: bytes) -> str:
    if sym_type == "interface":
        return f"interface {name}"
    if sym_type == "type":
        return f"type {name}"
    if sym_type == "class":
        return f"class {name}"
    if sym_type == "namespace":
        return f"namespace {name}"

    params_node = node.child_by_field_name("parameters")
    if params_node is None:
        return f"{name}()"

    # Walk the AST instead of regex-stripping the source text.
    # Each named child of the parameters node is one parameter; we extract
    # just its identifier (or destructuring pattern), discarding type
    # annotations and default values. This is robust to commas inside
    # generics, function-typed parameters, and default value expressions
    # that would all break a regex approach.
    names = [_param_name(p, source_bytes) for p in params_node.named_children]
    names = [n for n in names if n]
    return f"{name}({', '.join(names)})"


def _extract_symbols(source: str, rel_path: str, language, is_test: bool) -> list[ParsedSymbol]:
    from tree_sitter import Parser as TSParser

    parser = TSParser(language)
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)
    source_lines = source.splitlines(keepends=True)
    symbols: list[ParsedSymbol] = []

    def node_lines(node) -> tuple[int, int]:
        return node.start_point[0] + 1, node.end_point[0] + 1

    def node_body(node) -> str:
        start, end = node_lines(node)
        return extract_lines(source_lines, start, end)

    def get_name(node) -> str | None:
        n = node.child_by_field_name("name")
        return n.text.decode("utf-8") if n else None

    def add(name: str, sym_type: str, node, class_name: str | None = None) -> None:
        qualified = f"{class_name}.{name}" if class_name else name
        line_start, line_end = node_lines(node)
        sig = _build_signature(name, sym_type, node, source_bytes)
        symbols.append(ParsedSymbol(
            file=rel_path, symbol=qualified, symbol_type=sym_type,
            line_start=line_start, line_end=line_end,
            signature=sig, body=node_body(node),
            structural_hash=structural_hash(qualified, sig),
            needs_note=_should_note(qualified, line_start, line_end, is_test),
        ))

    def walk(node, class_name: str | None = None) -> None:
        t = node.type

        if t == "export_statement":
            for child in node.children:
                if child.type not in ("export", "default", "declare", ";"):
                    walk(child, class_name)
            return

        if t in ("function_declaration", "function_expression"):
            name = get_name(node)
            if name:
                add(name, "method" if class_name else "function", node, class_name)
            return

        if t == "class_declaration":
            name = get_name(node)
            if name:
                add(name, "class", node)
                body = node.child_by_field_name("body")
                if body:
                    for child in body.children:
                        walk(child, class_name=name)
            return

        if t == "method_definition":
            name = get_name(node)
            if name:
                add(name, "method", node, class_name)
            return

        if t == "interface_declaration":
            name = get_name(node)
            if name:
                add(name, "interface", node)
            return

        if t == "type_alias_declaration":
            name = get_name(node)
            if name:
                add(name, "type", node)
            return

        # Namespace and module declarations — TypeScript-only.
        # Index the namespace itself, then walk into its body to surface
        # the functions, classes, interfaces and types declared inside.
        # Symbols inside a namespace are NOT qualified with the namespace
        # name to keep behavior consistent with how class methods are the
        # only qualified symbols in this parser.
        if t in ("internal_module", "module", "namespace_declaration"):
            name = get_name(node)
            if name:
                add(name, "namespace", node)
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    walk(child, class_name=None)
            return

        if t == "lexical_declaration" and class_name is None:
            # const foo = () => ... or const foo = function() ...
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    value_node = child.child_by_field_name("value")
                    if name_node and value_node and value_node.type in (
                        "arrow_function", "function_expression"
                    ):
                        name = name_node.text.decode("utf-8")
                        line_start, line_end = node_lines(child)
                        # For arrow/function-expression bindings we build the
                        # signature from the value node's parameters so the
                        # hash tracks the actual parameter list.
                        sig = _build_signature(name, "function", value_node, source_bytes)
                        symbols.append(ParsedSymbol(
                            file=rel_path, symbol=name, symbol_type="function",
                            line_start=line_start, line_end=line_end,
                            signature=sig, body=node_body(child),
                            structural_hash=structural_hash(name, sig),
                            needs_note=_should_note(name, line_start, line_end, is_test),
                        ))
            return

        if class_name is None:
            for child in node.children:
                walk(child)

    walk(tree.root_node)
    return symbols


def parse(path: Path, repo_root: Path) -> list[ParsedSymbol]:
    try:
        import tree_sitter_typescript  # noqa: F401
        import tree_sitter_javascript  # noqa: F401
    except ImportError:
        return []  # silently skip if not installed

    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    rel_path = str(path.relative_to(repo_root))
    is_test = is_test_file(rel_path)
    language = _get_language(path.suffix.lower())

    # Defensive: tree-sitter can throw on certain malformed inputs.
    # One bad file shouldn't kill an indexing run — but the failure
    # should be visible, not silent, so indexing-pipeline bugs don't
    # masquerade as "no symbols in this file."
    try:
        return _extract_symbols(source, rel_path, language, is_test)
    except Exception as exc:
        print(
            f"[scout] typescript parser failed on {rel_path}: {exc}",
            file=sys.stderr,
        )
        return []