// ── StatsBar ──────────────────────────────────────────────────────────────────

import type { ContextQueryEvent, NotesRunEvent } from "../lib/types"
import { FALLBACK_COLORS } from "../lib/types"

export function StatsBar({ queries, notes }: { queries: ContextQueryEvent[]; notes: NotesRunEvent[] }) {
  if (queries.length === 0) return null
  const avgScore = queries.reduce((s, q) => s + q.top_score, 0) / queries.length
  const avgTokens = Math.round(queries.reduce((s, q) => s + q.token_count, 0) / queries.length)
  const avgDuration = Math.round(queries.reduce((s, q) => s + q.duration_ms, 0) / queries.length)
  const highConfidencePct = Math.round(((queries.filter(q => q.fallback_level === 1).length) / queries.length) * 100)

  return (
    <div className="grid grid-cols-4 border-b border-[#111]">
      {[
        { label: "Queries", value: queries.length, sub: notes.length > 0 ? `${notes.length} runs` : undefined },
        { label: "High confidence", value: `${highConfidencePct}%`, color: highConfidencePct >= 70 ? "#4ade80" : highConfidencePct >= 40 ? "#facc15" : "#f87171" },
        { label: "Avg score", value: avgScore.toFixed(3), color: avgScore >= 0.45 ? "#4ade80" : avgScore >= 0.25 ? "#facc15" : "#fb923c" },
        { label: "Avg tokens", value: avgTokens.toLocaleString() },
      ].map(({ label, value, sub, color }: any) => (
        <div key={label} className="px-6 py-4 border-r border-[#111] last:border-r-0">
          <div className="text-[#3a3a3a] text-[10px] tracking-[0.15em] uppercase mb-1">{label}</div>
          <div className="text-xl font-bold tabular-nums" style={{ color: color ?? "#f0ede8" }}>{value}</div>
          {sub && <div className="text-[#333] text-[10px] mt-0.5">{sub}</div>}
        </div>
      ))}
    </div>
  )
}
