import type { IndexStatus } from "../lib/types"

interface Props {
  status: IndexStatus
  repoName: string
}

export function IndexStatusBanner({ status, repoName }: Props) {
  if (!status.exists) {
    return (
      <div className="flex items-center gap-3 px-6 py-2.5 bg-cyan-950/20 border-b border-cyan-900/30">
        <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0" />
        <p className="text-cyan-300/80 text-xs flex-1">
          No index found for <span className="font-medium">{repoName}</span>. Ask Claude to run{" "}
          <code className="text-cyan-300">scout_notes</code> to build it.
        </p>
      </div>
    )
  }

  if (!status.fresh) {
    return (
      <div className="flex items-center gap-3 px-6 py-2.5 bg-cyan-950/20 border-b border-cyan-900/30">
        <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse shrink-0" />
        <p className="text-cyan-300/80 text-xs flex-1">
          Index may be stale — commits have been made since last index run.
          {status.head && <span className="text-cyan-400/50 ml-1">HEAD: {status.head}</span>}
        </p>
      </div>
    )
  }

  return null
}
