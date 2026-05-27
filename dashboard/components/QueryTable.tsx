"use client"

import type { ContextQueryEvent } from "@/lib/types"
import { FALLBACK_COLORS, FALLBACK_LABELS } from "@/lib/types"

interface Props {
  queries: ContextQueryEvent[]
  selected: ContextQueryEvent | null
  onSelect: (q: ContextQueryEvent) => void
}

export function QueryTable({ queries, selected, onSelect }: Props) {
  return (
    <div>
      {queries.map((q, i) => {
        const isSelected = selected === q
        const time = new Date(q.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
        return (
          <div
            key={i}
            onClick={() => onSelect(q)}
            className={`px-6 py-3 cursor-pointer border-b border-[#111] hover:bg-[#0f0f0f] transition-colors ${
              isSelected ? "bg-[#111] border-l-2 border-l-[#4ade80]" : "border-l-2 border-l-transparent"
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <p className="text-[#ccc] text-xs leading-relaxed flex-1 line-clamp-2">{q.query}</p>
              <div className="flex flex-col items-end gap-1 shrink-0">
                <div
                  className="text-[10px] px-1.5 py-0.5 rounded-sm font-medium"
                  style={{
                    color: FALLBACK_COLORS[q.fallback_level],
                    background: FALLBACK_COLORS[q.fallback_level] + "18",
                  }}
                >
                  L{q.fallback_level}
                </div>
                <span className="text-[#333] text-[10px] tabular-nums">{time}</span>
              </div>
            </div>
            <div className="flex gap-4 mt-1.5">
              <span className="text-[#333] text-[10px] tabular-nums">
                score <span className="text-[#555]">{q.top_score.toFixed(3)}</span>
              </span>
              <span className="text-[#333] text-[10px] tabular-nums">
                <span className="text-[#555]">{q.direct_count}d</span>
                {q.neighbor_count > 0 && <span className="text-[#444]"> +{q.neighbor_count}n</span>}
              </span>
              <span className="text-[#333] text-[10px] tabular-nums">
                <span className="text-[#555]">{q.token_count.toLocaleString()}</span> tok
              </span>
              <span className="text-[#333] text-[10px] tabular-nums">
                <span className="text-[#555]">{Math.round(q.duration_ms)}</span>ms
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
