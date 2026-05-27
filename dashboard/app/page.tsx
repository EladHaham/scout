"use client"

import { useState, useCallback } from "react"
import { parseLog, isContextQuery, isNotesRun, type ScoutEvent } from "@/lib/types"
import { StatsBar } from "@/components/StatsBar"
import { FallbackChart } from "@/components/FallbackChart"
import { QueryTable } from "@/components/QueryTable"
import { QueryDetail } from "@/components/QueryDetail"
import { NotesHistory } from "@/components/NotesHistory"
import type { ContextQueryEvent } from "@/lib/types"

export default function Home() {
  const [events, setEvents] = useState<ScoutEvent[]>([])
  const [selected, setSelected] = useState<ContextQueryEvent | null>(null)
  const [dragging, setDragging] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)

  const loadFile = useCallback((file: File) => {
    setFileName(file.name)
    const reader = new FileReader()
    reader.onload = (e) => {
      const text = e.target?.result as string
      setEvents(parseLog(text))
      setSelected(null)
    }
    reader.readAsText(file)
  }, [])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) loadFile(file)
  }, [loadFile])

  const onFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) loadFile(file)
  }, [loadFile])

  const queries = events.filter(isContextQuery)
  const notes = events.filter(isNotesRun)

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e2e2e2] font-mono">
      {/* Header */}
      <header className="border-b border-[#1e1e1e] px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-[#4ade80] animate-pulse" />
          <span className="text-[#4ade80] text-sm font-bold tracking-[0.2em] uppercase">Scout</span>
          <span className="text-[#3a3a3a]">/</span>
          <span className="text-[#666] text-sm tracking-wide">Observability</span>
        </div>
        <div className="flex items-center gap-4">
          {fileName && (
            <span className="text-[#444] text-xs">{fileName}</span>
          )}
          <label className="cursor-pointer border border-[#2a2a2a] hover:border-[#3a3a3a] px-3 py-1.5 text-xs text-[#888] hover:text-[#bbb] transition-colors">
            Load log
            <input type="file" accept=".log,.txt,.ndjson" className="hidden" onChange={onFileInput} />
          </label>
        </div>
      </header>

      {events.length === 0 ? (
        // Drop zone
        <div
          className={`flex flex-col items-center justify-center h-[calc(100vh-57px)] transition-colors ${
            dragging ? "bg-[#0f1a0f]" : ""
          }`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <div className={`border border-dashed p-16 text-center transition-colors ${
            dragging ? "border-[#4ade80] bg-[#0f1a0f]" : "border-[#2a2a2a]"
          }`}>
            <div className="text-4xl mb-4 opacity-30">⌘</div>
            <p className="text-[#555] text-sm mb-2">Drop <code className="text-[#888]">.scout/scout.log</code> here</p>
            <p className="text-[#333] text-xs">or use the Load log button above</p>
          </div>
        </div>
      ) : (
        <div className="flex h-[calc(100vh-57px)]">
          {/* Left panel */}
          <div className="flex-1 overflow-auto border-r border-[#1a1a1a]">
            <StatsBar queries={queries} notes={notes} />
            <div className="px-6 pb-4">
              <FallbackChart queries={queries} />
            </div>
            <div className="border-t border-[#1a1a1a]">
              <div className="px-6 pt-4 pb-2 flex items-center justify-between">
                <span className="text-[#555] text-xs tracking-[0.15em] uppercase">Queries</span>
                <span className="text-[#333] text-xs">{queries.length} total</span>
              </div>
              <QueryTable
                queries={queries}
                selected={selected}
                onSelect={setSelected}
              />
            </div>
            {notes.length > 0 && (
              <div className="border-t border-[#1a1a1a] mt-4">
                <div className="px-6 pt-4 pb-2">
                  <span className="text-[#555] text-xs tracking-[0.15em] uppercase">Index runs</span>
                </div>
                <NotesHistory notes={notes} />
              </div>
            )}
          </div>

          {/* Right panel - detail */}
          <div className="w-[420px] overflow-auto">
            {selected ? (
              <QueryDetail event={selected} onClose={() => setSelected(null)} />
            ) : (
              <div className="flex items-center justify-center h-full text-[#2a2a2a] text-sm">
                Select a query to inspect
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
