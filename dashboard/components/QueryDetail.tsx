"use client"

import type { ContextQueryEvent } from "@/lib/types"
import { FALLBACK_COLORS, FALLBACK_LABELS } from "@/lib/types"

interface Props {
  event: ContextQueryEvent
  onClose: () => void
}

function Tag({ children, color }: { children: React.ReactNode; color?: string }) {
  return (
    <span
      className="text-[10px] px-1.5 py-0.5 rounded-sm"
      style={{
        color: color ?? "#666",
        background: (color ?? "#666") + "18",
      }}
    >
      {children}
    </span>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-[#1a1a1a] pt-4 mt-4">
      <div className="text-[#444] text-[10px] tracking-[0.15em] uppercase mb-3">{title}</div>
      {children}
    </div>
  )
}

export function QueryDetail({ event, onClose }: Props) {
  const direct = event.symbols.filter((s) => s.relevance === "direct")
  const neighbors = event.symbols.filter((s) => s.relevance === "neighbor")
  const ts = new Date(event.ts).toLocaleString()

  return (
    <div className="p-5 h-full overflow-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex-1">
          <p className="text-[#e2e2e2] text-sm leading-relaxed">{event.query}</p>
          <p className="text-[#333] text-[10px] mt-1">{ts}</p>
        </div>
        <button onClick={onClose} className="text-[#333] hover:text-[#666] text-lg leading-none mt-0.5">×</button>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-2">
        {[
          { label: "Fallback level", value: `L${event.fallback_level} — ${FALLBACK_LABELS[event.fallback_level]}`, color: FALLBACK_COLORS[event.fallback_level] },
          { label: "Top score", value: event.top_score.toFixed(4), color: event.top_score >= 0.45 ? "#4ade80" : event.top_score >= 0.25 ? "#facc15" : "#fb923c" },
          { label: "Token count", value: event.token_count.toLocaleString() },
          { label: "Latency", value: `${Math.round(event.duration_ms)}ms` },
          { label: "Direct hits", value: event.direct_count },
          { label: "Neighbors", value: event.neighbor_count },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-[#0d0d0d] border border-[#1a1a1a] px-3 py-2">
            <div className="text-[#444] text-[10px] mb-1">{label}</div>
            <div className="text-sm tabular-nums" style={{ color: color ?? "#888" }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Direct hits */}
      {direct.length > 0 && (
        <Section title={`Direct hits (${direct.length})`}>
          <div className="space-y-2">
            {direct.map((s, i) => (
              <div key={i} className="bg-[#0d0d0d] border border-[#1a1a1a] px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[#4ade80] text-xs font-medium truncate">{s.symbol}</span>
                  {s.score != null && (
                    <span className="text-[#555] text-[10px] tabular-nums shrink-0">{s.score.toFixed(3)}</span>
                  )}
                </div>
                <div className="text-[#444] text-[10px] mt-0.5 truncate">{s.file}</div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Neighbors */}
      {neighbors.length > 0 && (
        <Section title={`Neighbors (${neighbors.length})`}>
          <div className="space-y-1.5">
            {neighbors.map((s, i) => (
              <div key={i} className="flex items-center justify-between px-3 py-1.5 border border-[#161616] bg-[#0a0a0a]">
                <span className="text-[#555] text-xs truncate">{s.symbol}</span>
                <span className="text-[#2a2a2a] text-[10px] shrink-0 ml-2">{s.file.split("/").pop()}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}
