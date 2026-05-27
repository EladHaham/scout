import { useState, useEffect, useCallback } from "react"
import type { Repo, IndexStatus, ScoutEvent, ContextQueryEvent, NotesRunEvent } from "../lib/types"
import { parseLog, isContextQuery, isNotesRun } from "../lib/types"
import { StatsBar } from "../components/StatsBar"
import { FallbackChart } from "../components/FallbackChart"
import { QueryTable } from "../components/QueryTable"
import { QueryDetail } from "../components/QueryDetail"
import { NotesHistory } from "../components/NotesHistory"
import { IndexStatusBanner } from "../components/IndexStatusBanner"

interface Props {
  repo: Repo
}

export function DashboardPage({ repo }: Props) {
  const [events, setEvents] = useState<ScoutEvent[]>([])
  const [indexStatus, setIndexStatus] = useState<IndexStatus | null>(null)
  const [selected, setSelected] = useState<ContextQueryEvent | null>(null)
  const [activeTab, setActiveTab] = useState<"queries" | "index">("queries")

  const reload = useCallback(async () => {
    const [raw, status] = await Promise.all([
      window.scout.readLog(repo.path),
      window.scout.indexStatus(repo.path),
    ])
    setEvents(raw ? parseLog(raw) : [])
    setIndexStatus(status)
    setSelected(null)
  }, [repo.path])

  useEffect(() => {
    reload()
  }, [reload])

  const queries = events.filter(isContextQuery)
  const notes = events.filter(isNotesRun)

  return (
    <div className="flex flex-col h-full">
      {/* Repo header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-[#1a1a1b]">
        <div className="flex items-center gap-3">
          <span className="text-[#f0ede8] text-sm font-medium">{repo.name}</span>
          <span className="text-[#2a2a2a] text-xs truncate max-w-[300px]">{repo.path}</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => window.scout.revealInFinder(repo.path)}
            className="text-[#333] hover:text-[#666] text-[10px] tracking-wide transition-colors"
          >
            Show in Finder
          </button>
          <button
            onClick={reload}
            className="text-[#333] hover:text-[#666] text-[10px] tracking-wide transition-colors"
          >
            Refresh ↺
          </button>
        </div>
      </div>

      {/* Index status banner */}
      {indexStatus && <IndexStatusBanner status={indexStatus} repoName={repo.name} />}

      {/* Tabs */}
      <div className="flex border-b border-[#1a1a1b] px-6">
        {[
          { id: "queries", label: `Queries${queries.length > 0 ? ` (${queries.length})` : ""}` },
          { id: "index", label: `Index runs${notes.length > 0 ? ` (${notes.length})` : ""}` },
        ].map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id as any)}
            className={`text-xs py-2.5 mr-6 border-b-2 transition-colors ${
              activeTab === id
                ? "border-cyan-400 text-[#f0ede8]"
                : "border-transparent text-[#444] hover:text-[#666]"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 overflow-auto">
          {activeTab === "queries" ? (
            queries.length === 0 ? (
              <EmptyState
                title="No queries yet"
                sub="Ask Claude something about this repo and Scout will log the retrieval here."
              />
            ) : (
              <>
                <StatsBar queries={queries} notes={notes} />
                <div className="px-6 py-4 border-b border-[#111]">
                  <FallbackChart queries={queries} />
                </div>
                <QueryTable queries={queries} selected={selected} onSelect={setSelected} />
              </>
            )
          ) : (
            notes.length === 0 ? (
              <EmptyState
                title="No index runs yet"
                sub={`Ask Claude to run scout_notes on ${repo.name} to build the index.`}
              />
            ) : (
              <NotesHistory notes={notes} />
            )
          )}
        </div>

        {/* Detail panel */}
        {activeTab === "queries" && (
          <div className="w-[400px] border-l border-[#1a1a1b] overflow-auto shrink-0">
            {selected ? (
              <QueryDetail event={selected} onClose={() => setSelected(null)} />
            ) : (
              <div className="flex items-center justify-center h-full text-[#222] text-xs">
                Select a query to inspect
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function EmptyState({ title, sub }: { title: string; sub: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center px-8">
      <div className="w-6 h-6 border border-[#2a2a2a] mb-4 flex items-center justify-center">
        <div className="w-1.5 h-1.5 bg-[#2a2a2a]" />
      </div>
      <p className="text-[#555] text-sm mb-1">{title}</p>
      <p className="text-[#333] text-xs leading-relaxed max-w-xs">{sub}</p>
    </div>
  )
}
