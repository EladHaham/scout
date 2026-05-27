import { useState, useEffect } from "react"
import type { Repo, ScoutState } from "./lib/types"
import { Sidebar } from "./components/Sidebar"
import { OnboardingPage } from "./pages/OnboardingPage"
import { DashboardPage } from "./pages/DashboardPage"

export default function App() {
  const [state, setState] = useState<ScoutState>({ repos: [], activeId: null })
  const [loading, setLoading] = useState(true)
  const [showRestart, setShowRestart] = useState(false)

  useEffect(() => {
    window.scout.getRepos().then((s) => {
      setState(s)
      setLoading(false)
    })
  }, [])

  const applyState = (s: ScoutState, needsRestart = false) => {
    setState(s)
    if (needsRestart) setShowRestart(true)
  }

  const addRepo = async (path: string) => {
    const s = await window.scout.addRepo(path)
    applyState(s, true)
  }

  const removeRepo = async (id: string) => {
    const s = await window.scout.removeRepo(id)
    applyState(s, true)
  }

  const setActive = async (id: string) => {
    const s = await window.scout.setActiveRepo(id)
    applyState(s, true)
  }

  const handleRestart = async () => {
    setShowRestart(false)
    await window.scout.restartClaude()
  }

  if (loading) {
    return (
      <div className="flex h-screen bg-[#0c0c0d] items-center justify-center">
        <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
      </div>
    )
  }

  const activeRepo = state.repos.find((r) => r.id === state.activeId) ?? null

  return (
    <div className="flex h-screen bg-[#0c0c0d] text-[#e8e4de] overflow-hidden" style={{ fontFamily: "'Geist Mono', 'JetBrains Mono', monospace" }}>
      <div className="fixed top-0 left-0 right-0 h-8 app-drag z-50" />

      <Sidebar
        repos={state.repos}
        activeId={state.activeId}
        onSetActive={setActive}
        onAdd={addRepo}
        onRemove={removeRepo}
        showRestart={showRestart}
        onRestart={handleRestart}
        onDismissRestart={() => setShowRestart(false)}
      />

      <main className="flex-1 overflow-hidden pt-8">
        {state.repos.length === 0 || !activeRepo ? (
          <OnboardingPage onAdd={addRepo} />
        ) : (
          <DashboardPage repo={activeRepo} />
        )}
      </main>
    </div>
  )
}
