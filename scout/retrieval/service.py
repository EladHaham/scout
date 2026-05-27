from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from scout.retrieval.embedder import embed_texts, embed_query
from scout.retrieval.index import IndexEntry, SearchResult, build_index, load_index, search
from scout.utils.errors import ScoutError


def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken (cl100k_base — compatible with GPT-4 and Claude)."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        return len(text) // 4


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------

@dataclass
class SymbolContext:
    symbol: str
    file: str
    line_start: int
    line_end: int
    purpose: str | None
    tags: list[str]
    code_span: str
    relevance: str            # "direct" | "neighbor"
    score: float | None       # cosine score for direct hits, None for neighbors


@dataclass
class ContextPacket:
    query: str
    repo_path: Path
    symbols: list[SymbolContext] = field(default_factory=list)
    repo_map: str | None = None
    truncated: bool = False   # True if token cap was applied

    def to_text(self) -> str:
        lines: list[str] = []

        if self.repo_map:
            lines.append("## Repo map\n")
            lines.append(self.repo_map)
            lines.append("")

        direct = [s for s in self.symbols if s.relevance == "direct"]
        neighbors = [s for s in self.symbols if s.relevance == "neighbor"]

        whole_file_mode = direct and all(s.symbol == s.file for s in direct)

        if direct:
            lines.append("## Whole files (low confidence)\n" if whole_file_mode else "## Direct matches\n")
            for sym in direct:
                lines.append(_format_symbol(sym))

        if neighbors:
            lines.append("## Neighbors (call graph expansion)\n")
            for sym in neighbors:
                lines.append(_format_symbol(sym))

        if self.truncated:
            lines.append(
                "\n> ⚠️ Context truncated to fit token budget. "
                "Some symbols were dropped. Consider a more specific query."
            )

        body = "\n".join(lines)
        token_count = _count_tokens(body)
        header = f"# Context for: {self.query} (~{token_count:,} tokens)\n"
        return header + "\n" + body

    def to_dict(self) -> dict:
        body = self.to_text()
        token_count = _count_tokens(body)
        return {
            "query": self.query,
            "repo_path": str(self.repo_path),
            "token_count": token_count,
            "truncated": self.truncated,
            "symbols": [
                {
                    "symbol": s.symbol,
                    "file": s.file,
                    "line_start": s.line_start,
                    "line_end": s.line_end,
                    "purpose": s.purpose,
                    "tags": s.tags,
                    "relevance": s.relevance,
                    "score": s.score,
                    "code_span": s.code_span,
                }
                for s in self.symbols
            ],
        }


def _format_symbol(sym: SymbolContext) -> str:
    lines = []
    if sym.line_start:
        header = f"### `{sym.symbol}` — {sym.file}:{sym.line_start}-{sym.line_end}"
    else:
        header = f"### `{sym.symbol}` — {sym.file}"
    if sym.score is not None:
        header += f"  (score: {sym.score:.3f})"
    lines.append(header)
    if sym.purpose:
        lines.append(f"_{sym.purpose}_")
    if sym.tags:
        lines.append(f"tags: {', '.join(sym.tags)}")
    if sym.code_span:
        lines.append("")
        lines.append("```python")
        lines.append(sym.code_span)
        lines.append("```")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Token budget enforcement
# ---------------------------------------------------------------------------

def _apply_token_budget(packet: ContextPacket, max_tokens: int) -> None:
    """
    Trim symbols from the packet until to_text() fits within max_tokens.
    Drop order: neighbors first (lowest score first), then direct hits (lowest score first).
    Mutates packet in place and sets packet.truncated if anything was dropped.
    """
    if max_tokens <= 0:
        return

    if _count_tokens(packet.to_text()) <= max_tokens:
        return

    # Sort symbols so we drop cheapest first:
    # neighbors before direct, then by score ascending (lowest = least useful)
    def _drop_priority(sym: SymbolContext) -> tuple:
        order = 0 if sym.relevance == "neighbor" else 1
        score = sym.score if sym.score is not None else 0.0
        return (order, score)

    packet.truncated = True

    while packet.symbols and _count_tokens(packet.to_text()) > max_tokens:
        # Find the symbol with lowest drop priority
        worst = min(packet.symbols, key=_drop_priority)
        packet.symbols.remove(worst)


# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------

def build_retrieval_index(repo_root: Path, force: bool = False) -> int:
    """
    Embed all symbol notes and persist the vector index.
    Returns the number of symbols indexed.
    """
    from scout.notes.store import load_all_notes

    notes = load_all_notes(repo_root)
    if not notes:
        return 0

    texts = [note.purpose for note in notes]
    vectors = embed_texts(texts, repo_root=repo_root, force=force)

    entries = [
        IndexEntry(
            symbol=note.symbol,
            file=note.file,
            purpose=note.purpose,
            vector=vec,
        )
        for note, vec in zip(notes, vectors)
    ]
    build_index(entries, repo_root)
    return len(entries)


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------

def _read_code_span(repo_root: Path, file: str, line_start: int, line_end: int) -> str:
    try:
        source = (repo_root / file).read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines()
        span = lines[line_start - 1 : line_end]
        return "\n".join(span)
    except OSError:
        return ""


def _load_notes_by_symbol(repo_root: Path) -> dict[str, object]:
    from scout.notes.store import load_all_notes
    return {note.symbol: note for note in load_all_notes(repo_root)}


def _load_call_graph(repo_root: Path):
    try:
        from scout.notes.call_graph import load_call_graph
        return load_call_graph(repo_root)
    except Exception as e:
        import sys
        print(f"[scout] warning: could not load call graph: {e}", file=sys.stderr)
        return None


def _read_whole_file(repo_root: Path, file: str) -> str | None:
    try:
        return (repo_root / file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _load_repo_map(repo_root: Path) -> str | None:
    try:
        from scout.service import get_repo_map
        return get_repo_map(repo=str(repo_root)).map_text
    except Exception:
        return None


def get_context(
    repo_root: Path,
    query: str,
    top_k: int | None = None,
    depth: int | None = None,
    include_repo_map: bool = False,
) -> ContextPacket:
    """
    Main entry point. Given a task query, return a ContextPacket with:
    - top_k direct matches (by embedding similarity)
    - their call graph neighbors up to `depth` hops
    - code spans for all symbols
    - enforced token budget (symbols dropped lowest-score-first if over limit)
    """
    import time
    from scout.config import load_config
    from scout.utils.logger import log_context_query

    t_start = time.monotonic()
    config = load_config(repo_root)
    top_k = top_k if top_k is not None else config.default_top_k
    depth = depth if depth is not None else config.default_depth

    index = load_index(repo_root)
    if not index:
        raise ScoutError(
            "No embedding index found. Run `scout notes <repo>` first to build it."
        )

    # 1. Embed query and search
    query_vec = embed_query(query, repo_root=repo_root)
    candidates: list[SearchResult] = search(query_vec, index, top_k=top_k + 1)

    # 2. Detect confidence level and apply retrieval strategy
    top_score = candidates[0].score if candidates else 0.0
    packet = ContextPacket(query=query, repo_path=repo_root)

    # Level 4 — no signal: return repo map only
    if top_score < config.repo_map_only_threshold:
        packet.repo_map = _load_repo_map(repo_root)
        _log_retrieval(repo_root, query=query, top_score=top_score, fallback_level=4,
                       packet=packet, t_start=t_start)
        return packet

    # Level 3 — very low confidence: whole files
    if top_score < config.whole_file_score_threshold:
        broad_results = search(query_vec, index, top_k=config.default_top_k)
        files_seen: set[str] = set()
        for r in broad_results:
            if r.file in files_seen:
                continue
            files_seen.add(r.file)
            content = _read_whole_file(repo_root, r.file)
            if content is None:
                continue
            packet.symbols.append(SymbolContext(
                symbol=r.file,
                file=r.file,
                line_start=1,
                line_end=content.count("\n") + 1,
                purpose=None,
                tags=[],
                code_span=content,
                relevance="direct",
                score=r.score,
            ))
        _apply_token_budget(packet, config.max_context_tokens)
        _log_retrieval(repo_root, query=query, top_score=top_score, fallback_level=3,
                       packet=packet, t_start=t_start)
        return packet

    # Level 1/2 — normal or moderate confidence: symbol-level retrieval
    fallback_level = 2 if top_score < config.min_top_score else 1
    results = candidates[:top_k]
    if fallback_level == 1 and len(candidates) > top_k:
        boundary_gap = candidates[top_k - 1].score - candidates[top_k].score
        if boundary_gap < config.min_score_gap:
            results = candidates[:top_k + 1]

    # 3. Load notes and call graph
    notes_by_symbol = _load_notes_by_symbol(repo_root)
    call_graph = _load_call_graph(repo_root)

    # 4. Direct hits
    direct_symbols: set[str] = {r.symbol for r in results}

    # 5. Expand neighbors
    neighbor_symbols: set[str] = set()
    if call_graph is not None:
        low_confidence = top_score < config.min_top_score
        top_symbols = {r.symbol for r in results[:2]} if low_confidence else set()
        for result in results:
            effective_depth = 2 if result.symbol in top_symbols else depth
            neighbors = call_graph.neighbors(result.symbol, depth=effective_depth)
            neighbor_symbols.update(set(neighbors) - direct_symbols)

    # 6. Assemble SymbolContext
    score_map = {r.symbol: r.score for r in results}

    def _make_symbol_context(symbol: str, relevance: str) -> SymbolContext | None:
        note = notes_by_symbol.get(symbol)
        score = score_map.get(symbol)

        if note is not None:
            code_span = _read_code_span(repo_root, note.file, note.line_start, note.line_end)
            return SymbolContext(
                symbol=symbol,
                file=note.file,
                line_start=note.line_start,
                line_end=note.line_end,
                purpose=note.purpose,
                tags=note.tags,
                code_span=code_span,
                relevance=relevance,
                score=score,
            )

        if call_graph is not None:
            edges = call_graph.get(symbol)
            if edges is not None and edges.line_start:
                code_span = _read_code_span(repo_root, edges.file, edges.line_start, edges.line_end)
                return SymbolContext(
                    symbol=symbol,
                    file=edges.file,
                    line_start=edges.line_start,
                    line_end=edges.line_end,
                    purpose="",
                    tags=[],
                    code_span=code_span,
                    relevance=relevance,
                    score=score,
                )

        return None

    for result in results:
        ctx = _make_symbol_context(result.symbol, "direct")
        if ctx:
            packet.symbols.append(ctx)

    for symbol in sorted(neighbor_symbols):
        ctx = _make_symbol_context(symbol, "neighbor")
        if ctx:
            packet.symbols.append(ctx)

    if include_repo_map:
        packet.repo_map = _load_repo_map(repo_root)

    # 7. Enforce token budget
    _apply_token_budget(packet, config.max_context_tokens)

    _log_retrieval(repo_root, query=query, top_score=top_score,
                   fallback_level=fallback_level, packet=packet, t_start=t_start)
    return packet


def _log_retrieval(
    repo_root: Path,
    *,
    query: str,
    top_score: float,
    fallback_level: int,
    packet: ContextPacket,
    t_start: float,
) -> None:
    import time
    from scout.utils.logger import log_context_query

    direct = [s for s in packet.symbols if s.relevance == "direct"]
    neighbors = [s for s in packet.symbols if s.relevance == "neighbor"]
    packet_text = packet.to_text()
    token_count = _count_tokens(packet_text)

    log_context_query(
        repo_root,
        query=query,
        top_score=top_score,
        fallback_level=fallback_level,
        direct_count=len(direct),
        neighbor_count=len(neighbors),
        token_count=token_count,
        symbols=[
            {
                "symbol": s.symbol,
                "file": s.file,
                "score": round(s.score, 4) if s.score is not None else None,
                "relevance": s.relevance,
            }
            for s in packet.symbols
        ],
        duration_ms=(time.monotonic() - t_start) * 1000,
    )