// ── Repo state ────────────────────────────────────────────────────────────────

export interface Repo {
  id: string
  name: string
  path: string
  mcpBin: string
}

export interface ScoutState {
  repos: Repo[]
  activeId: string | null
}

export interface IndexStatus {
  exists: boolean
  fresh: boolean
  head?: string
}

// ── Log events ────────────────────────────────────────────────────────────────

export interface SymbolHit {
  symbol: string
  file: string
  score: number | null
  relevance: "direct" | "neighbor"
}

export interface ContextQueryEvent {
  event: "context_query"
  ts: string
  query: string
  top_score: number
  fallback_level: 1 | 2 | 3 | 4
  direct_count: number
  neighbor_count: number
  token_count: number
  duration_ms: number
  symbols: SymbolHit[]
}

export interface NotesRunEvent {
  event: "notes_run"
  ts: string
  generated: number
  skipped: number
  total: number
  indexed: number
  duration_ms: number
}

export type ScoutEvent = ContextQueryEvent | NotesRunEvent

export function parseLog(raw: string): ScoutEvent[] {
  return raw.split("\n").filter(Boolean).flatMap((line) => {
    try { return [JSON.parse(line) as ScoutEvent] } catch { return [] }
  })
}

export function isContextQuery(e: ScoutEvent): e is ContextQueryEvent {
  return e.event === "context_query"
}

export function isNotesRun(e: ScoutEvent): e is NotesRunEvent {
  return e.event === "notes_run"
}

export const FALLBACK_LABELS: Record<number, string> = {
  1: "High confidence",
  2: "Moderate",
  3: "Whole file",
  4: "Repo map only",
}

export const FALLBACK_COLORS: Record<number, string> = {
  1: "#4ade80",
  2: "#facc15",
  3: "#fb923c",
  4: "#f87171",
}

// ── Window API ────────────────────────────────────────────────────────────────

declare global {
  interface Window {
    scout: {
      pickFolder: () => Promise<string | null>
      validateRepo: (path: string) => Promise<{ valid: boolean; name: string | null }>
      getRepos: () => Promise<ScoutState>
      addRepo: (path: string) => Promise<ScoutState>
      removeRepo: (id: string) => Promise<ScoutState>
      setActiveRepo: (id: string) => Promise<ScoutState>
      readLog: (path: string) => Promise<string | null>
      indexStatus: (path: string) => Promise<IndexStatus>
      restartClaude: () => Promise<boolean>
      revealInFinder: (path: string) => Promise<void>
    }
  }
}
