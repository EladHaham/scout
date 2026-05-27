"use client"

import type { NotesRunEvent } from "@/lib/types"

interface Props {
  notes: NotesRunEvent[]
}

export function NotesHistory({ notes }: Props) {
  return (
    <div className="px-6 pb-4 space-y-2">
      {notes.map((n, i) => {
        const ts = new Date(n.ts).toLocaleString()
        return (
          <div key={i} className="flex items-center gap-4 border border-[#1a1a1a] px-4 py-2.5 bg-[#0a0a0a]">
            <div className="w-1.5 h-1.5 rounded-full bg-[#4ade80] shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex gap-4 text-[10px]">
                <span className="text-[#555]">
                  <span className="text-[#888]">{n.generated}</span> generated
                </span>
                <span className="text-[#555]">
                  <span className="text-[#888]">{n.skipped}</span> skipped
                </span>
                <span className="text-[#555]">
                  <span className="text-[#888]">{n.indexed}</span> indexed
                </span>
                <span className="text-[#555]">
                  <span className="text-[#888]">{Math.round(n.duration_ms / 1000)}s</span>
                </span>
              </div>
              <div className="text-[#2a2a2a] text-[10px] mt-0.5">{ts}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
