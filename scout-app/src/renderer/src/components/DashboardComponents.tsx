// ── StatsBar ──────────────────────────────────────────────────────────────────

import { useState } from "react"
import type { ContextQueryEvent, NotesRunEvent } from "../lib/types"
import { FALLBACK_COLORS, FALLBACK_LABELS } from "../lib/types"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts"

export function StatsBar({ queries, notes }: { queries: ContextQueryEvent[]; notes: NotesRunEvent[] }) {
  if (queries.length === 0) return null
  const avgScore = queries.reduce((s, q) => s + q.top_score, 0) / queries.length
  const avgTokens = Math.round(queries.reduce((s, q) => s + q.token_count, 0) / queries.length)
  const highConfidencePct = Math.round(((queries.filter(q => q.fallback_level === 1).length) / queries.length) * 100)

  return (
    <div className="grid grid-cols-4 border-b border-[#1e1e1e]">
      {[
        { label: "Queries", value: queries.length, sub: notes.length > 0 ? `${notes.length} index runs` : undefined },
        { label: "High confidence", value: `${highConfidencePct}%`, color: highConfidencePct >= 70 ? "#4ade80" : highConfidencePct >= 40 ? "#facc15" : "#f87171" },
        { label: "Avg score", value: avgScore.toFixed(3), color: avgScore >= 0.45 ? "#4ade80" : avgScore >= 0.25 ? "#facc15" : "#fb923c" },
        { label: "Avg tokens", value: avgTokens.toLocaleString() },
      ].map(({ label, value, sub, color }: any) => (
        <div key={label} className="px-6 py-4 border-r border-[#1e1e1e] last:border-r-0">
          <div className="text-[#666] text-[10px] tracking-[0.15em] uppercase mb-1.5">{label}</div>
          <div className="text-2xl font-bold tabular-nums" style={{ color: color ?? "#e8e4de" }}>{value}</div>
          {sub && <div className="text-[#555] text-[10px] mt-0.5">{sub}</div>}
        </div>
      ))}
    </div>
  )
}

// ── FallbackChart ─────────────────────────────────────────────────────────────

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null
  const { query, top_score, fallback_level, token_count, duration_ms } = payload[0].payload
  return (
    <div className="bg-[#161616] border border-[#333] p-3 text-xs max-w-[260px] shadow-xl">
      <p className="text-[#ddd] mb-2 leading-relaxed line-clamp-2">{query}</p>
      <div className="space-y-1 text-[#777]">
        <div className="flex justify-between gap-4">
          <span>Level</span>
          <span style={{ color: FALLBACK_COLORS[fallback_level] }}>{FALLBACK_LABELS[fallback_level]}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Score</span><span className="text-[#aaa]">{top_score.toFixed(3)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Tokens</span><span className="text-[#aaa]">{token_count.toLocaleString()}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Latency</span><span className="text-[#aaa]">{Math.round(duration_ms)}ms</span>
        </div>
      </div>
    </div>
  )
}

export function FallbackChart({ queries }: { queries: ContextQueryEvent[] }) {
  if (queries.length === 0) return null
  const data = queries.map((q, i) => ({ ...q, index: i, score_pct: Math.round(q.top_score * 100) }))
  const dist = [1, 2, 3, 4].map((level) => ({
    level, label: FALLBACK_LABELS[level], color: FALLBACK_COLORS[level],
    count: queries.filter((q) => q.fallback_level === level).length,
  })).filter((d) => d.count > 0)

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-[#666] text-[10px] tracking-[0.15em] uppercase">Score per query</span>
        <div className="flex gap-4">
          {dist.map((d) => (
            <div key={d.level} className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full" style={{ background: d.color }} />
              <span className="text-[#666] text-[10px]">{d.label} ({d.count})</span>
            </div>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={72}>
        <BarChart data={data} margin={{ top: 0, right: 0, bottom: 0, left: 0 }} barSize={10}>
          <XAxis dataKey="index" hide />
          <YAxis domain={[0, 100]} hide />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "#1a1a1a" }} />
          <Bar dataKey="score_pct" radius={[2, 2, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={FALLBACK_COLORS[entry.fallback_level]} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── QueryTable ────────────────────────────────────────────────────────────────

export function QueryTable({ queries, selected, onSelect }: {
  queries: ContextQueryEvent[]
  selected: ContextQueryEvent | null
  onSelect: (q: ContextQueryEvent) => void
}) {
  return (
    <div>
      {queries.map((q, i) => {
        const isSelected = selected === q
        const time = new Date(q.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
        return (
          <div
            key={i}
            onClick={() => onSelect(q)}
            className={`px-6 py-3 cursor-pointer border-b border-[#161616] hover:bg-[#111] transition-colors ${
              isSelected ? "bg-[#141414] border-l-2 border-l-cyan-400" : "border-l-2 border-l-transparent"
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <p className="text-[#ddd] text-xs leading-relaxed flex-1 line-clamp-2">{q.query}</p>
              <div className="flex flex-col items-end gap-1 shrink-0">
                <div className="text-[10px] px-1.5 py-0.5 font-bold"
                  style={{ color: FALLBACK_COLORS[q.fallback_level], background: FALLBACK_COLORS[q.fallback_level] + "22" }}>
                  L{q.fallback_level}
                </div>
                <span className="text-[#555] text-[10px] tabular-nums">{time}</span>
              </div>
            </div>
            <div className="flex gap-4 mt-1.5">
              <span className="text-[#666] text-[10px]">score <span className="text-[#999]">{q.top_score.toFixed(3)}</span></span>
              <span className="text-[#666] text-[10px]"><span className="text-[#999]">{q.direct_count}d</span>{q.neighbor_count > 0 && <span className="text-[#777]"> +{q.neighbor_count}n</span>}</span>
              <span className="text-[#666] text-[10px]"><span className="text-[#999]">{q.token_count.toLocaleString()}</span> tok</span>
              <span className="text-[#666] text-[10px]"><span className="text-[#999]">{Math.round(q.duration_ms)}</span>ms</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── QueryDetail ───────────────────────────────────────────────────────────────

function buildExportText(event: ContextQueryEvent): string {
  const direct = event.symbols.filter((s) => s.relevance === "direct")
  const neighbors = event.symbols.filter((s) => s.relevance === "neighbor")
  const lines: string[] = []
  lines.push(`# Scout Query Export`)
  lines.push(``)
  lines.push(`**Query:** ${event.query}`)
  lines.push(`**Time:** ${new Date(event.ts).toLocaleString()}`)
  lines.push(`**Fallback level:** L${event.fallback_level} — ${FALLBACK_LABELS[event.fallback_level]}`)
  lines.push(`**Top score:** ${event.top_score.toFixed(4)}`)
  lines.push(`**Tokens:** ${event.token_count.toLocaleString()}`)
  lines.push(`**Latency:** ${Math.round(event.duration_ms)}ms`)
  lines.push(``)
  if (direct.length > 0) {
    lines.push(`## Direct hits (${direct.length})`)
    direct.forEach((s) => {
      lines.push(`- **${s.symbol}** (${s.file})${s.score != null ? ` — score: ${s.score.toFixed(3)}` : ""}`)
    })
    lines.push(``)
  }
  if (neighbors.length > 0) {
    lines.push(`## Neighbors (${neighbors.length})`)
    neighbors.forEach((s) => {
      lines.push(`- ${s.symbol} (${s.file})`)
    })
  }
  return lines.join("\n")
}

export function QueryDetail({ event, onClose }: { event: ContextQueryEvent; onClose: () => void }) {
  const [copied, setCopied] = useState(false)
  const direct = event.symbols.filter((s) => s.relevance === "direct")
  const neighbors = event.symbols.filter((s) => s.relevance === "neighbor")

  const handleCopy = () => {
    navigator.clipboard.writeText(buildExportText(event))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="p-5">
      <div className="flex items-start justify-between gap-3 mb-5">
        <div className="flex-1">
          <p className="text-[#e8e4de] text-sm leading-relaxed">{event.query}</p>
          <p className="text-[#555] text-[10px] mt-1.5">{new Date(event.ts).toLocaleString()}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="text-[10px] px-2 py-1 border border-[#222] hover:border-cyan-400/40 text-[#555] hover:text-cyan-400 transition-colors"
          >
            {copied ? "Copied ✓" : "Copy"}
          </button>
          <button onClick={onClose} className="text-[#444] hover:text-[#888] text-xl leading-none mt-0.5">×</button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-5">
        {[
          { label: "Level", value: `L${event.fallback_level} — ${FALLBACK_LABELS[event.fallback_level]}`, color: FALLBACK_COLORS[event.fallback_level] },
          { label: "Top score", value: event.top_score.toFixed(4), color: event.top_score >= 0.45 ? "#4ade80" : event.top_score >= 0.25 ? "#facc15" : "#fb923c" },
          { label: "Tokens", value: event.token_count.toLocaleString() },
          { label: "Latency", value: `${Math.round(event.duration_ms)}ms` },
        ].map(({ label, value, color }: any) => (
          <div key={label} className="bg-[#111] border border-[#222] px-3 py-2.5">
            <div className="text-[#555] text-[10px] mb-1">{label}</div>
            <div className="text-sm tabular-nums font-medium" style={{ color: color ?? "#aaa" }}>{value}</div>
          </div>
        ))}
      </div>

      {direct.length > 0 && (
        <div className="mb-4">
          <div className="text-[#666] text-[10px] tracking-[0.15em] uppercase mb-2">Direct hits ({direct.length})</div>
          <div className="space-y-1.5">
            {direct.map((s, i) => (
              <div key={i} className="bg-[#111] border border-[#222] px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-cyan-300 text-xs font-medium truncate">{s.symbol}</span>
                  {s.score != null && <span className="text-[#666] text-[10px] tabular-nums shrink-0">{s.score.toFixed(3)}</span>}
                </div>
                <div className="text-[#555] text-[10px] mt-0.5 truncate">{s.file}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {neighbors.length > 0 && (
        <div>
          <div className="text-[#666] text-[10px] tracking-[0.15em] uppercase mb-2">Neighbors ({neighbors.length})</div>
          <div className="space-y-1">
            {neighbors.map((s, i) => (
              <div key={i} className="flex items-center justify-between px-3 py-1.5 border border-[#1e1e1e] bg-[#0e0e0e]">
                <span className="text-[#777] text-xs truncate">{s.symbol}</span>
                <span className="text-[#444] text-[10px] shrink-0 ml-2">{s.file.split("/").pop()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── NotesHistory ──────────────────────────────────────────────────────────────

export function NotesHistory({ notes }: { notes: NotesRunEvent[] }) {
  return (
    <div className="px-6 py-4 space-y-2">
      {notes.map((n, i) => (
        <div key={i} className="flex items-center gap-4 border border-[#222] px-4 py-3 bg-[#0e0e0e]">
          <div className="w-1.5 h-1.5 rounded-full bg-[#4ade80] shrink-0" />
          <div className="flex-1">
            <div className="flex gap-5 text-[11px]">
              <span className="text-[#666]"><span className="text-[#aaa]">{n.generated}</span> generated</span>
              <span className="text-[#666]"><span className="text-[#aaa]">{n.skipped}</span> skipped</span>
              <span className="text-[#666]"><span className="text-[#aaa]">{n.indexed}</span> indexed</span>
              <span className="text-[#666]"><span className="text-[#aaa]">{Math.round(n.duration_ms / 1000)}s</span></span>
            </div>
            <div className="text-[#444] text-[10px] mt-0.5">{new Date(n.ts).toLocaleString()}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
