import { useState } from "react";

interface Props {
  onAdd: (path: string) => Promise<void>;
}

export function OnboardingPage({ onAdd }: Props) {
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAdd = async () => {
    setAdding(true);
    setError(null);
    try {
      const path = await window.scout.pickFolder();
      if (!path) return;
      const { valid } = await window.scout.validateRepo(path);
      if (!valid) {
        setError("Selected folder is not a git repository.");
        return;
      }
      await onAdd(path);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="flex items-center justify-center h-full">
      <div className="max-w-sm w-full px-8">
        {/* Mark */}
        <div className="mb-10">
          <div className="w-8 h-8 border border-cyan-400/40 flex items-center justify-center mb-6">
            <div className="w-2 h-2 bg-cyan-400" />
          </div>
          <h1 className="text-xl font-bold text-[#f0ede8] mb-2 tracking-tight">
            Welcome to Scout
          </h1>
          <p className="text-[#555] text-sm leading-relaxed">
            Scout gives Claude precise, symbol-level context from your codebase
            — no more full file dumps.
          </p>
        </div>

        {/* Steps */}
        <div className="space-y-4 mb-10">
          {[
            {
              n: "01",
              label: "Add a repository",
              sub: "Pick any git repo from your machine",
            },
            {
              n: "02",
              label: "Build the index",
              sub: "Scout parses symbols and generates notes",
            },
            {
              n: "03",
              label: "Ask Claude",
              sub: "Scout retrieves relevant context automatically",
            },
          ].map(({ n, label, sub }) => (
            <div key={n} className="flex gap-4">
              <span className="text-[#2a2a2a] text-[10px] tabular-nums pt-0.5 shrink-0">
                {n}
              </span>
              <div>
                <p className="text-[#ccc] text-xs font-medium">{label}</p>
                <p className="text-[#444] text-[11px] mt-0.5">{sub}</p>
              </div>
            </div>
          ))}
        </div>

        {/* CTA */}
        <button
          onClick={handleAdd}
          disabled={adding}
          className="w-full py-3 bg-cyan-400 hover:bg-cyan-300 disabled:opacity-50 text-black text-sm font-bold tracking-wide transition-colors"
        >
          {adding ? "Selecting..." : "Add Repository"}
        </button>

        {error && (
          <p className="text-red-400 text-xs mt-3 text-center">{error}</p>
        )}

        <p className="text-[#2a2a2a] text-[10px] text-center mt-4 leading-relaxed">
          Requires Claude Desktop + a Python repo with Scout installed
        </p>
      </div>
    </div>
  );
}
