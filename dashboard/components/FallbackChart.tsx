"use client"

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts"
import type { ContextQueryEvent } from "@/lib/types"
import { FALLBACK_LABELS, FALLBACK_COLORS } from "@/lib/types"

interface Props {
  queries: ContextQueryEvent[]
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null
  const { query, top_score, fallback_level, token_count, duration_ms } = payload[0].payload
  return (
    <div className="bg-[#111] border border-[#2a2a2a] p-3 text-xs max-w-[280px]">
      <p className="text-[#e2e2e2] mb-2 leading-relaxed line-clamp-2">{query}</p>
      <div className="space-y-1 text-[#666]">
        <div className="flex justify-between gap-4">
          <span>Level</span>
          <span style={{ color: FALLBACK_COLORS[fallback_level] }}>
            {FALLBACK_LABELS[fallback_level]}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Score</span>
          <span className="text-[#888]">{top_score.toFixed(3)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Tokens</span>
          <span className="text-[#888]">{token_count.toLocaleString()}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Latency</span>
          <span className="text-[#888]">{Math.round(duration_ms)}ms</span>
        </div>
      </div>
    </div>
  )
}

export function FallbackChart({ queries }: Props) {
  if (queries.length === 0) return null

  const data = queries.map((q, i) => ({
    ...q,
    index: i,
    score_pct: Math.round(q.top_score * 100),
  }))

  // Level distribution summary
  const dist = [1, 2, 3, 4].map((level) => ({
    level,
    label: FALLBACK_LABELS[level],
    count: queries.filter((q) => q.fallback_level === level).length,
    color: FALLBACK_COLORS[level],
  })).filter((d) => d.count > 0)

  return (
    <div className="pt-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[#555] text-[10px] tracking-[0.15em] uppercase">Score per query</span>
        <div className="flex gap-3">
          {dist.map((d) => (
            <div key={d.level} className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full" style={{ background: d.color }} />
              <span className="text-[#444] text-[10px]">{d.label} ({d.count})</span>
            </div>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={80}>
        <BarChart data={data} margin={{ top: 0, right: 0, bottom: 0, left: 0 }} barSize={12}>
          <XAxis dataKey="index" hide />
          <YAxis domain={[0, 100]} hide />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "#1a1a1a" }} />
          <Bar dataKey="score_pct" radius={[2, 2, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={FALLBACK_COLORS[entry.fallback_level]} fillOpacity={0.8} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
