"use client"

import type { ContextQueryEvent, NotesRunEvent } from "@/lib/types"
import { FALLBACK_LABELS, FALLBACK_COLORS } from "@/lib/types"

interface Props {
  queries: ContextQueryEvent[]
  notes: NotesRunEvent[]
}

function Stat({ label, value, sub, color }: {
  label: string
  value: string | number
  sub?: string
  color?: string
}) {
  return (
    <div className="border-r border-[#1a1a1a] px-6 py-5 last:border-r-0">
      <div className="text-[#444] text-[10px] tracking-[0.15em] uppercase mb-1">{label}</div>
      <div className="text-2xl font-bold tabular-nums" style={{ color: color ?? "#e2e2e2" }}>
        {value}
      </div>
      {sub && <div className="text-[#444] text-xs mt-0.5">{sub}</div>}
    </div>
  )
}

export function StatsBar({ queries, notes }: Props) {
  if (queries.length === 0) return null

  const avgScore = queries.reduce((s, q) => s + q.top_score, 0) / queries.length
  const avgTokens = Math.round(queries.reduce((s, q) => s + q.token_count, 0) / queries.length)
  const avgDuration = Math.round(queries.reduce((s, q) => s + q.duration_ms, 0) / queries.length)

  const levelCounts = queries.reduce((acc, q) => {
    acc[q.fallback_level] = (acc[q.fallback_level] ?? 0) + 1
    return acc
  }, {} as Record<number, number>)

  const dominantLevel = Object.entries(levelCounts).sort((a, b) => b[1] - a[1])[0]
  const highConfidencePct = Math.round(((levelCounts[1] ?? 0) / queries.length) * 100)

  return (
    <div className="grid grid-cols-5 border-b border-[#1a1a1a]">
      <Stat label="Queries" value={queries.length} sub={notes.length > 0 ? `${notes.length} index runs` : undefined} />
      <Stat
        label="High confidence"
        value={`${highConfidencePct}%`}
        sub="level 1"
        color={highConfidencePct >= 70 ? "#4ade80" : highConfidencePct >= 40 ? "#facc15" : "#f87171"}
      />
      <Stat
        label="Avg score"
        value={avgScore.toFixed(3)}
        color={avgScore >= 0.45 ? "#4ade80" : avgScore >= 0.25 ? "#facc15" : "#fb923c"}
      />
      <Stat label="Avg tokens" value={avgTokens.toLocaleString()} sub="per query" />
      <Stat label="Avg latency" value={`${avgDuration}ms`} sub="retrieval" />
    </div>
  )
}
