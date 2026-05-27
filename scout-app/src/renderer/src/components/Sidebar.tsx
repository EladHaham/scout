import { useState } from "react"
import type { Repo } from "../lib/types"

interface Props {
  repos: Repo[]
  activeId: string | null
  onSetActive: (id: string) => void
  onAdd: (path: string) => Promise<void>
  onRemove: (id: string) => void
  showRestart: boolean
  onRestart: () => void
  onDismissRestart: () => void
}

export function Sidebar({ repos, activeId, onSetActive, onAdd, onRemove, showRestart, onRestart, onDismissRestart }: Props) {
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleAdd = async () => {
    setAdding(true)
    setError(null)
    try {
      const path = await window.scout.pickFolder()
      if (!path) return
      const { valid } = await window.scout.validateRepo(path)
      if (!valid) { setError("Not a git repository"); return }
      await onAdd(path)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setAdding(false)
    }
  }

  return (
    <aside className="w-56 flex flex-col border-r border-[#222] pt-10 pb-4 shrink-0">
      {/* Logo */}
      <div className="px-5 mb-7">
        <div className="flex items-center gap-2.5">
          <div className="w-2 h-2 rounded-full bg-cyan-400 shrink-0" />
          <span className="text-cyan-300 text-xs font-bold tracking-[0.2em] uppercase">Scout</span>
        </div>
      </div>

      {/* Repo list */}
      <div className="flex-1 overflow-auto px-3">
        {repos.length > 0 && (
          <div className="px-2 mb-2">
            <span className="text-[#555] text-[10px] tracking-[0.15em] uppercase">Repositories</span>
          </div>
        )}
        {repos.map((repo) => (
          <RepoItem
            key={repo.id}
            repo={repo}
            active={repo.id === activeId}
            onSelect={() => onSetActive(repo.id)}
            onRemove={() => onRemove(repo.id)}
          />
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="mx-3 mb-2 px-3 py-2 bg-red-950/40 border border-red-800/40 text-red-300 text-[11px] leading-relaxed">
          {error}
        </div>
      )}

      {/* Restart banner */}
      {showRestart && (
        <div className="mx-3 mb-2 px-3 py-3 bg-cyan-950/40 border border-cyan-700/40">
          <p className="text-cyan-200 text-[11px] mb-2.5 leading-relaxed">
            Restart Claude Desktop to apply changes.
          </p>
          <button
            onClick={onRestart}
            className="w-full text-[11px] bg-cyan-400 hover:bg-cyan-300 text-black font-bold py-1.5 transition-colors mb-1"
          >
            Restart Claude
          </button>
          <button
            onClick={onDismissRestart}
            className="w-full text-[11px] text-[#555] hover:text-[#888] py-1 transition-colors"
          >
            Later
          </button>
        </div>
      )}

      {/* Add repo */}
      <div className="px-3 pt-2 border-t border-[#1e1e1e]">
        <button
          onClick={handleAdd}
          disabled={adding}
          className="w-full flex items-center gap-2 px-3 py-2 text-[#666] hover:text-[#aaa] hover:bg-[#141414] transition-colors text-xs rounded-sm"
        >
          <span className="text-base leading-none">+</span>
          <span>{adding ? "Selecting..." : "Add repository"}</span>
        </button>
      </div>
    </aside>
  )
}

function RepoItem({ repo, active, onSelect, onRemove }: {
  repo: Repo
  active: boolean
  onSelect: () => void
  onRemove: () => void
}) {
  const [hovering, setHovering] = useState(false)

  return (
    <div
      onClick={onSelect}
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      className={`flex items-center justify-between px-2 py-2 cursor-pointer rounded-sm transition-all mb-0.5 ${
        active
          ? "bg-[#1a1a1a] text-[#f0ede8] border-l-2 border-cyan-400 pl-1.5"
          : "text-[#888] hover:text-[#ccc] hover:bg-[#141414] border-l-2 border-transparent"
      }`}
    >
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-xs truncate font-medium">{repo.name}</span>
      </div>
      {hovering && !active && (
        <button
          onClick={(e) => { e.stopPropagation(); onRemove() }}
          className="text-[#444] hover:text-red-400 transition-colors text-sm ml-1 shrink-0"
        >
          ×
        </button>
      )}
      {active && (
        <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0 ml-1" />
      )}
    </div>
  )
}
