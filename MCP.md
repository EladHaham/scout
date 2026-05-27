# Scout MCP Server

Scout will expose its retrieval engine as an MCP server so LLM clients (Claude, Cursor, etc.) can call it directly during coding sessions.

## Why MCP

The LLM has full conversation context and can rewrite vague user queries ("fix it", "what should I do now?") into precise retrieval queries before calling Scout. This solves the referential query problem that a standalone CLI can't handle.

## Tools

### `scout_context`

The primary tool. Called by the LLM whenever it needs codebase context for a task.

```
scout_context(repo: str, query: str, top_k?: int, depth?: int) → ContextPacket
```

Returns the full context packet (direct symbol matches + call graph neighbors + code spans), formatted as text or JSON.

### `scout_notes`

Builds or refreshes the index. Called once on setup, or when the user says "re-index the repo".

```
scout_notes(repo: str, refresh?: bool) → summary string
```

Runs note generation + call graph build + embedding index. Safe to re-run — only re-processes changed symbols.

## Implementation plan

- `scout/mcp/server.py` — MCP server entry point using the `mcp` Python SDK
- Wraps `get_context()` and `generate_notes()` from existing services
- No new business logic — pure transport layer
- Add `scout-mcp` entry point to `pyproject.toml`

## Usage (once built)

```bash
pip install mcp
scout-mcp  # starts the MCP server on stdio
```

Configure in Claude Desktop / Cursor:

```json
{
  "mcpServers": {
    "scout": {
      "command": "scout-mcp",
      "args": []
    }
  }
}
```
