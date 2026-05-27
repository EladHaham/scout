# Scout App

macOS desktop app for Scout — adds repositories, writes the Claude Desktop config, and shows the observability dashboard.

## Dev setup

```bash
npm install
npm run electron:dev
```

## Build

```bash
npm run electron:build
```

Outputs a `.dmg` in `dist/`.

## Structure

```
src/
  main/
    main.ts        # Electron main process — file system, config writing, Claude restart
    preload.ts     # Secure IPC bridge to renderer
  renderer/
    index.html
    src/
      App.tsx                        # Root — sidebar + page routing
      lib/types.ts                   # Shared types + log parsing
      pages/
        OnboardingPage.tsx           # First-run experience
        DashboardPage.tsx            # Per-repo observability
      components/
        Sidebar.tsx                  # Repo list + add/remove
        IndexStatusBanner.tsx        # Stale index warning
        StatsBar.tsx                 # Summary metrics
        FallbackChart.tsx            # Score-per-query bar chart
        DashboardComponents.tsx      # QueryTable, QueryDetail, NotesHistory
```

## What it does

1. **Add repository** — opens native Finder dialog, validates git repo, writes `scout-mcp` entry to `~/Library/Application Support/Claude/claude_desktop_config.json`
2. **Auto-detects scout-mcp** — looks in `.venv/bin/`, `venv/bin/`, then PATH
3. **Reads API keys** — picks up `DEEPSEEK_API_KEY` and `OPENAI_API_KEY` from `.env` in the repo root and injects them into the MCP server config
4. **Restart Claude Desktop** — confirmation prompt → `osascript quit` → `open -a Claude`
5. **Observability dashboard** — reads `.scout/scout.log` directly (no drag-and-drop needed), shows queries, scores, fallback levels, symbols retrieved
6. **Index status** — warns when index is behind git HEAD
