from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path

from scout.notes.parser import ParsedSymbol, _is_test_file

# Python builtins we don't want to track as external deps
_BUILTINS = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))
_BUILTIN_MODULES = {
    "os", "sys", "re", "json", "hashlib", "pathlib", "subprocess",
    "datetime", "dataclasses", "typing", "abc", "collections", "itertools",
    "functools", "contextlib", "io", "math", "random", "time", "copy",
    "inspect", "importlib", "warnings", "logging", "traceback", "threading",
    "ast",  # ast is stdlib — don't show ast.walk as external
}


@dataclass
class SymbolEdges:
    symbol: str
    file: str
    line_start: int = 0
    line_end: int = 0
    calls_internal: list[str] = field(default_factory=list)
    calls_external: list[str] = field(default_factory=list)
    called_by_internal: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "file": self.file,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "calls_internal": self.calls_internal,
            "calls_external": self.calls_external,
            "called_by_internal": self.called_by_internal,
        }

    @staticmethod
    def from_dict(data: dict) -> "SymbolEdges":
        return SymbolEdges(
            symbol=data["symbol"],
            file=data["file"],
            line_start=data.get("line_start", 0),
            line_end=data.get("line_end", 0),
            calls_internal=data.get("calls_internal", []),
            calls_external=data.get("calls_external", []),
            called_by_internal=data.get("called_by_internal", []),
        )


@dataclass
class CallGraph:
    edges: dict[str, SymbolEdges] = field(default_factory=dict)

    def get(self, symbol: str) -> SymbolEdges | None:
        return self.edges.get(symbol)

    def neighbors(self, symbol: str, depth: int = 1) -> list[str]:
        visited: set[str] = set()
        frontier = {symbol}

        for _ in range(depth):
            next_frontier: set[str] = set()
            for sym in frontier:
                edges = self.edges.get(sym)
                if edges is None:
                    continue
                for neighbor in edges.calls_internal + edges.called_by_internal:
                    if neighbor not in visited and neighbor != symbol:
                        next_frontier.add(neighbor)
            visited.update(frontier)
            frontier = next_frontier - visited

        visited.update(frontier)
        visited.discard(symbol)
        return list(visited)
    
    def to_dict(self) -> dict:
        return {sym: e.to_dict() for sym, e in self.edges.items()}

    @staticmethod
    def from_dict(data: dict) -> "CallGraph":
        return CallGraph(
            edges={sym: SymbolEdges.from_dict(e) for sym, e in data.items()}
        )


def _extract_imports(tree: ast.Module) -> dict[str, str]:
    """
    Build a map of imported name -> module.
    e.g. {"RepoMap": "aider.repomap", "ScoutError": "scout.utils.errors"}
    """
    imports: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                name = alias.asname or alias.name
                imports[name] = node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                imports[name] = alias.name
    return imports


def _extract_calls(
    func_node: ast.AST,
    imports: dict[str, str],
    class_name: str | None = None,   # set when processing a method, for self.x() resolution
    symbol_names: set[str] = frozenset(),
) -> tuple[list[str], list[str]]:
    """
    Walk a function/method AST node and return:
    - raw_calls: names to resolve against the symbol index
    - external_calls: resolved third-party calls e.g. "aider.repomap.RepoMap"
    """
    raw_calls: list[str] = []
    external_calls: list[str] = []

    for node in ast.walk(func_node):
        if not isinstance(node, ast.Call):
            continue

        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name in imports:
                module = imports[name]
                if module.startswith("scout."):
                    raw_calls.append(name)
                else:
                    root = module.split(".")[0]
                    if root not in _BUILTIN_MODULES and name not in _BUILTINS:
                        # Fix: use just "module.Name" not "module.module.Name"
                        external_calls.append(f"{module}.{name}")
            else:
                raw_calls.append(name)

        elif isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if isinstance(node.func.value, ast.Name):
                obj = node.func.value.id

                if obj == "self" and class_name:
                    # self.method() — resolve to ClassName.method
                    qualified = f"{class_name}.{attr}"
                    if qualified in symbol_names:
                        raw_calls.append(qualified)
                    # also try bare method name
                    elif attr in symbol_names:
                        raw_calls.append(attr)

                elif obj in imports:
                    module = imports[obj]
                    if module.startswith("scout."):
                        # Internal scout class method call e.g. SymbolNote.from_dict()
                        # Resolve as "ClassName.method" against the symbol index
                        raw_calls.append(f"{obj}.{attr}")
                    else:
                        root = module.split(".")[0]
                        if root not in _BUILTIN_MODULES:
                            external_calls.append(f"{module}.{attr}")
                else:
                    # Could be ClassName.method() or local_var.method()
                    # Keep as qualified name — symbol index lookup will resolve it
                    raw_calls.append(f"{obj}.{attr}")

    return raw_calls, list(set(external_calls))


def build_call_graph(symbols: list[ParsedSymbol], repo_root: Path) -> CallGraph:
    """
    Build a full call graph from a list of parsed symbols.
    Excludes test file symbols — they pollute called_by with test callers.
    """
    # Filter out test symbols entirely from the graph
    non_test_symbols = [s for s in symbols if not _is_test_file(s.file)]

    symbol_names: set[str] = {s.symbol for s in non_test_symbols}
    # Index bare names for resolution (e.g. "get_map" -> "AiderMapper.get_map")
    bare_names: dict[str, str] = {}
    for s in non_test_symbols:
        bare = s.symbol.split(".")[-1]
        # Don't overwrite — first wins (avoids ambiguity)
        bare_names.setdefault(bare, s.symbol)

    # Cache parsed trees per file
    trees: dict[str, tuple[ast.Module, dict[str, str]]] = {}
    for sym in non_test_symbols:
        if sym.file not in trees:
            try:
                source = (repo_root / sym.file).read_text(encoding="utf-8")
                tree = ast.parse(source)
                imports = _extract_imports(tree)
                trees[sym.file] = (tree, imports)
            except (OSError, SyntaxError):
                trees[sym.file] = (ast.Module(body=[], type_ignores=[]), {})

    # Initialize graph nodes
    graph = CallGraph()
    for sym in non_test_symbols:
        graph.edges[sym.symbol] = SymbolEdges(
            symbol=sym.symbol,
            file=sym.file,
            line_start=sym.line_start,
            line_end=sym.line_end,
        )

    for sym in non_test_symbols:
        # Classes don't execute calls themselves — only their methods do.
        # Extracting calls from a class node walks all method bodies, causing false edges.
        if sym.symbol_type == "class":
            continue

        tree, imports = trees[sym.file]

        func_node = _find_node(tree, sym.symbol)
        if func_node is None:
            continue

        # Determine class context for self.x() resolution
        class_name = sym.symbol.split(".")[0] if "." in sym.symbol else None

        raw_calls, external_calls = _extract_calls(
            func_node, imports, class_name=class_name, symbol_names=symbol_names
        )

        internal_calls: list[str] = []
        for name in raw_calls:
            if name in symbol_names:
                internal_calls.append(name)
            elif name in bare_names:
                internal_calls.append(bare_names[name])

        # Deduplicate, preserve order
        internal_calls = list(dict.fromkeys(internal_calls))
        # Don't include self-references
        internal_calls = [c for c in internal_calls if c != sym.symbol]

        graph.edges[sym.symbol].calls_internal = internal_calls
        graph.edges[sym.symbol].calls_external = external_calls

        # Backfill called_by
        for callee in internal_calls:
            if callee in graph.edges:
                if sym.symbol not in graph.edges[callee].called_by_internal:
                    graph.edges[callee].called_by_internal.append(sym.symbol)

    return graph


def _find_node(
    tree: ast.Module, qualified_name: str
) -> ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | None:
    """Find the AST node for a possibly qualified name like 'AiderMapper.get_map'."""
    parts = qualified_name.split(".")

    if len(parts) == 1:
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == parts[0]:
                    return node

    elif len(parts) == 2:
        class_name, method_name = parts
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if child.name == method_name:
                            return child

    return None


# ── Persistence ───────────────────────────────────────────────────────────────

def _graph_path(repo_root: Path) -> Path:
    return repo_root / ".scout" / "call_graph.json"


def save_call_graph(repo_root: Path, graph: CallGraph) -> None:
    path = _graph_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(graph.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_call_graph(repo_root: Path) -> CallGraph | None:
    path = _graph_path(repo_root)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return CallGraph.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return None