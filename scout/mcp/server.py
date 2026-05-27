"""
Scout MCP server.

Usage:
    scout-mcp /path/to/repo
"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

from scout.utils.logger import stdout_to_stderr
from scout.utils.errors import ScoutError
from mcp.server.fastmcp import FastMCP

_INDEX_FINGERPRINT_FILE = ".scout/index_fingerprint.json"
_MAX_FILE_SIZE = 100_000  # ~100KB — skip very large files


# ---------------------------------------------------------------------------
# Fingerprint-based staleness
# ---------------------------------------------------------------------------

def _current_fingerprint(repo_path: Path) -> str:
    from scout.adapters.filesystem import repo_state_fingerprint
    return repo_state_fingerprint(repo_path)


def _load_index_fingerprint(repo_path: Path) -> str | None:
    fp_path = repo_path / _INDEX_FINGERPRINT_FILE
    if not fp_path.exists():
        return None
    try:
        return json.loads(fp_path.read_text())["fingerprint"]
    except Exception:
        return None


def _save_index_fingerprint(repo_path: Path, fingerprint: str) -> None:
    fp_path = repo_path / _INDEX_FINGERPRINT_FILE
    fp_path.parent.mkdir(parents=True, exist_ok=True)
    fp_path.write_text(json.dumps({"fingerprint": fingerprint}))


def _index_is_stale(repo_path: Path) -> bool:
    saved = _load_index_fingerprint(repo_path)
    if saved is None:
        return True
    return saved != _current_fingerprint(repo_path)


# ---------------------------------------------------------------------------
# Instructions — always includes a fresh repo map
# ---------------------------------------------------------------------------

def _build_instructions(repo_path: Path) -> str:
    try:
        from scout.service import get_repo_map
        result = get_repo_map(repo=str(repo_path), use_cache=True, refresh=False)
        repo_map_text = result.map_text
    except Exception as exc:
        print(f"[scout] warning: could not load repo map: {exc}", file=sys.stderr)
        repo_map_text = None

    base = (
        f"You are connected to Scout, a code context engine for the repository at {repo_path}.\n\n"
        "## When to call scout_context\n\n"
        "MUST call scout_context if:\n"
        "- The question mentions a specific symbol, function, class, or file from this repo\n"
        "- You are about to write or modify code that touches existing logic\n"
        "- You are unsure how something is implemented in this codebase\n\n"
        "SKIP scout_context if:\n"
        "- You already retrieved this symbol/file earlier in this conversation\n"
        "- The question is a follow-up on code already shown in this chat\n"
        "- The question is about general programming concepts unrelated to this codebase\n"
        "- The answer is fully visible in the repo map below\n\n"
        "NEVER answer 'how does X work in this codebase' from memory or training data — "
        "if X is in this repo, retrieve it first.\n\n"
        "## When to call scout_read_file\n\n"
        "- Use scout_read_file when you need to edit an existing file\n"
        "- Read the file first, make your changes, then return the complete modified file\n"
        "- File paths are relative to the repo root (e.g. 'front/components/ui/ProductManager.tsx')\n\n"
        "## When to call scout_notes\n\n"
        "- ONLY if the user explicitly asks to reindex or refresh the index\n"
        "- Reindexing happens automatically in the background — do NOT call it proactively\n"
        "- Use refresh=True only if the user says notes are wrong or outdated\n\n"
        "## Query writing rules\n\n"
        "- One symbol or concept per query — never combine multiple unrelated symbols in one call\n"
        "- Be specific: use symbol names, file names, and domain terms from the repo map\n"
        "- If you need multiple symbols, make sequential calls\n"
        "- After receiving context, if you see unfamiliar symbols or hooks being called, "
        "retrieve those too before answering\n\n"
    )

    if repo_map_text:
        base += "## Repo map\n\n" + repo_map_text
    else:
        base += "## Repo map\n\n(Not available — call `scout_notes` to build the index.)"

    return base


# ---------------------------------------------------------------------------
# Background indexing
# ---------------------------------------------------------------------------

class _IndexState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.running: bool = False
        self.last_result: str | None = None
        self.last_error: str | None = None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self.running

    def start(self, repo_path: Path, refresh: bool = False) -> bool:
        with self._lock:
            if self.running:
                return False
            self.running = True
            self.last_result = None
            self.last_error = None
        threading.Thread(target=self._run, args=(repo_path, refresh), daemon=True).start()
        return True

    def _run(self, repo_path: Path, refresh: bool) -> None:
        from scout.notes.service import generate_notes
        from scout.retrieval.service import build_retrieval_index
        from scout.utils.logger import log_notes_run

        try:
            fingerprint = _current_fingerprint(repo_path)
            t_start = time.monotonic()

            with stdout_to_stderr():
                result = generate_notes(repo_root=repo_path, refresh=refresh)
                indexed = build_retrieval_index(repo_root=repo_path)

            duration_ms = (time.monotonic() - t_start) * 1000

            if not result.below_threshold:
                _save_index_fingerprint(repo_path, fingerprint)

            log_notes_run(
                repo_path,
                generated=result.generated,
                skipped=result.skipped,
                total=result.total,
                indexed=indexed,
                duration_ms=duration_ms,
            )

            if result.below_threshold:
                msg = (
                    f"Only {result.total - result.skipped} symbol(s) changed — "
                    "below threshold for API call. Line numbers refreshed, "
                    "call graph rebuilt. Use scout_notes with refresh=True to force regeneration."
                )
            else:
                msg = (
                    f"Done. {result.generated} notes generated, "
                    f"{result.skipped} skipped, "
                    f"{indexed} symbols indexed. "
                    f"({duration_ms / 1000:.1f}s)"
                )

            with self._lock:
                self.last_result = msg

        except Exception as exc:
            with self._lock:
                self.last_error = str(exc)
        finally:
            with self._lock:
                self.running = False

    def status(self) -> str:
        with self._lock:
            if self.running:
                return "running"
            if self.last_error:
                return f"error: {self.last_error}"
            if self.last_result:
                return f"done: {self.last_result}"
            return "idle"


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------

def create_server(repo_path: Path) -> FastMCP:
    with stdout_to_stderr():
        instructions = _build_instructions(repo_path)

    mcp = FastMCP(name="scout", instructions=instructions)
    index_state = _IndexState()

    if _index_is_stale(repo_path):
        print(f"[scout] index stale — starting background reindex of {repo_path.name}", file=sys.stderr)
        index_state.start(repo_path)

    @mcp.tool()
    def scout_notes(refresh: bool = False) -> str:
        """
        Build or refresh Scout's index for the repository.
        Runs in the background — returns immediately.
        Use scout_index_status to check progress.

        Args:
            refresh: If True, regenerate all notes even if signatures are unchanged.
                     Also bypasses the minimum-dirty threshold.
        """
        if index_state.is_running:
            return "Index is already running. Use scout_index_status to check progress."
        index_state.start(repo_path, refresh=refresh)
        return (
            f"Indexing {repo_path.name} in the background. "
            "This usually takes 1–5 minutes. "
            "Call scout_index_status to check progress."
        )

    @mcp.tool()
    def scout_index_status() -> str:
        """
        Check the status of a background indexing job started by scout_notes.
        Returns: 'idle', 'running', 'done: <summary>', or 'error: <message>'.
        """
        return index_state.status()

    @mcp.tool()
    def scout_context(query: str, top_k: int = 5, depth: int = 1) -> str:
        """
        Retrieve relevant code context for a task query.
        Returns matching symbols, their purposes, and source code spans.
        Call this BEFORE writing any code that touches existing logic.

        If the retrieved code imports or uses a hook, utility, or type you don't
        recognize — especially hooks, API clients, or shared types — make
        additional calls for those before answering. Import paths in results are
        authoritative; never assume or invent paths not seen in the codebase.

        Args:
            query: The exact symbol name you are looking for, optionally followed
                by 1-4 context words. Start with the symbol name.
                Good: 'ProductManager', 'handlePutFarmerProduct', 'useApi put'
                Bad: 'ProductManager component product list edit price'
                If a task spans multiple concerns, make separate calls for each.
            top_k: Number of direct symbol matches to retrieve (default 5).
            depth: Call graph expansion depth (default 1).
        """
        from scout.retrieval.service import get_context

        stale = _index_is_stale(repo_path)
        if stale and not index_state.is_running:
            index_state.start(repo_path)

        packet = get_context(
            repo_root=repo_path,
            query=query,
            top_k=top_k,
            depth=depth,
        )

        text = packet.to_text()

        if stale:
            text = (
                "> ⚠️ Index is stale (repo changed since last index). "
                "Results may be incomplete. Reindexing in background — "
                "call scout_index_status to check progress.\n\n"
            ) + text

        return text

    @mcp.tool()
    def scout_read_file(path: str) -> str:
        """
        Read the full contents of a file in the repository.
        Use this when you need to edit an existing file — read it first,
        make your changes, then return the complete modified file to the user.

        Args:
            path: Relative path from repo root (e.g. 'front/components/ui/ProductManager.tsx').
                  Use paths exactly as they appear in scout_context results.
        """
        file_path = repo_path / path

        if not file_path.exists():
            return f"Error: file not found: {path}"

        if not file_path.is_file():
            return f"Error: not a file: {path}"

        # Safety check — don't serve files outside the repo
        try:
            file_path.resolve().relative_to(repo_path.resolve())
        except ValueError:
            return f"Error: path outside repository: {path}"

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return f"Error reading file: {e}"

        if len(content) > _MAX_FILE_SIZE:
            return (
                f"File too large to read in full ({len(content):,} chars). "
                f"Use scout_context to retrieve specific symbols instead."
            )

        line_count = content.count("\n") + 1
        return f"// {path} ({line_count} lines)\n\n{content}"

    return mcp


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: scout-mcp <repo-path>", file=sys.stderr)
        sys.exit(1)

    raw = sys.argv[1]
    try:
        from scout.adapters.filesystem import normalize_repo_path
        repo_path = normalize_repo_path(raw)
    except ScoutError as exc:
        print(f"scout-mcp error: {exc}", file=sys.stderr)
        sys.exit(1)

    server = create_server(repo_path)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()