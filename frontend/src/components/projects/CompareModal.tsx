import { useState } from 'react'
import {
  X,
  GitCompare,
  PlusCircle,
  MinusCircle,
  AlertCircle,
  Sparkles,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  RefreshCw,
} from 'lucide-react'
import type { WorkspaceProject, AnalysisComparison } from '../../types'
import { projectApi } from '../../api/client'
import { AIBadge, AIFallback } from '../ui/AILabel'

interface CompareModalProps {
  project: WorkspaceProject
  onClose: () => void
}

export function CompareModal({ project, onClose }: CompareModalProps) {
  const history = project.history || []
  const [baseId, setBaseId] = useState<string>(history[1]?.analysis_id || history[0]?.analysis_id || '')
  const [targetId, setTargetId] = useState<string>(history[0]?.analysis_id || '')
  const [enableAi, setEnableAi] = useState<boolean>(true)
  const [comparison, setComparison] = useState<AnalysisComparison | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleCompare = async () => {
    if (!baseId || !targetId) {
      setError('Please select both base and target analysis runs to compare')
      return
    }
    if (baseId === targetId) {
      setError('Base and target runs must be different')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const res = await projectApi.compareAnalyses(baseId, targetId, enableAi)
      setComparison(res)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to compare analyses')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className="glass-card w-full max-w-3xl max-h-[90vh] rounded-2xl flex flex-col overflow-hidden shadow-2xl border border-[var(--border)] dark:border-white/10">
        {/* Header */}
        <div className="p-4 border-b border-[var(--border)] dark:border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitCompare size={18} className="text-accent" />
            <h2 className="text-sm font-bold tracking-wide text-[var(--text-primary)]">
              Compare Analysis Runs: {project.name}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-muted hover:text-[var(--text-primary)] hover:bg-surface-2 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Run Selectors Bar */}
        <div className="p-4 bg-surface-2 dark:bg-white/[0.02] border-b border-[var(--border)] dark:border-white/5 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 text-xs">
          <div className="flex flex-1 items-center gap-2">
            <div className="flex-1">
              <label className="text-[10px] text-muted uppercase font-bold block mb-1">Base Run (Older)</label>
              <select
                value={baseId}
                onChange={(e) => setBaseId(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg border border-[var(--border)] dark:border-white/10 bg-surface text-[var(--text-primary)] font-mono text-xs focus:ring-1 focus:ring-accent"
              >
                {history.map((h) => (
                  <option key={h.analysis_id} value={h.analysis_id}>
                    {new Date(h.created_at).toLocaleDateString()} ({h.commit_sha}) - Score {h.score}
                  </option>
                ))}
              </select>
            </div>

            <ArrowRight size={14} className="text-muted mt-4 shrink-0" />

            <div className="flex-1">
              <label className="text-[10px] text-muted uppercase font-bold block mb-1">Target Run (Newer)</label>
              <select
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg border border-[var(--border)] dark:border-white/10 bg-surface text-[var(--text-primary)] font-mono text-xs focus:ring-1 focus:ring-accent"
              >
                {history.map((h) => (
                  <option key={h.analysis_id} value={h.analysis_id}>
                    {new Date(h.created_at).toLocaleDateString()} ({h.commit_sha}) - Score {h.score}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3 self-end sm:self-auto mt-2 sm:mt-0">
            <label className="flex items-center gap-1.5 text-[11px] text-muted cursor-pointer">
              <input
                type="checkbox"
                checked={enableAi}
                onChange={(e) => setEnableAi(e.target.checked)}
                className="rounded accent-accent"
              />
              <span>AI Summary</span>
            </label>

            <button
              onClick={handleCompare}
              disabled={loading}
              className="px-4 py-2 rounded-xl text-xs font-bold bg-accent text-slate-950 hover:opacity-90 flex items-center gap-1.5 shadow-md transition-all"
            >
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
              <span>{loading ? 'Computing...' : 'Run Comparison'}</span>
            </button>
          </div>
        </div>

        {/* Body content */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {error && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
              <AlertCircle size={15} />
              <span>{error}</span>
            </div>
          )}

          {!comparison && !loading && (
            <div className="flex flex-col items-center justify-center py-12 text-center text-muted">
              <GitCompare size={36} className="opacity-40 mb-2" />
              <p className="text-xs">Select two analysis runs above and click <strong>Run Comparison</strong> to view structural diffs.</p>
            </div>
          )}

          {comparison && (
            <div className="space-y-4">
              {/* Summary KPIs */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-surface-2 dark:bg-white/[0.03] border border-[var(--border)] dark:border-white/5">
                  <div className="text-[10px] text-muted uppercase font-bold">Health Score Delta</div>
                  <div
                    className={`text-xl font-bold font-mono mt-0.5 flex items-center gap-1 ${
                      comparison.score_delta >= 0 ? 'text-emerald-400' : 'text-red-400'
                    }`}
                  >
                    {comparison.score_delta >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                    <span>{comparison.score_delta > 0 ? `+${comparison.score_delta}` : comparison.score_delta}</span>
                  </div>
                  <div className="text-[10px] text-muted">
                    {comparison.base_score} ({comparison.base_grade}) → {comparison.target_score} ({comparison.target_grade})
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-surface-2 dark:bg-white/[0.03] border border-[var(--border)] dark:border-white/5">
                  <div className="text-[10px] text-muted uppercase font-bold">Modules Added / Removed</div>
                  <div className="text-xl font-bold font-mono text-[var(--text-primary)] mt-0.5">
                    <span className="text-emerald-400">+{comparison.added_modules.length}</span> /{' '}
                    <span className="text-red-400">-{comparison.removed_modules.length}</span>
                  </div>
                  <div className="text-[10px] text-muted">{comparison.modified_modules.length} modified</div>
                </div>

                <div className="p-3 rounded-xl bg-surface-2 dark:bg-white/[0.03] border border-[var(--border)] dark:border-white/5">
                  <div className="text-[10px] text-muted uppercase font-bold">Cycles Delta</div>
                  <div
                    className={`text-xl font-bold font-mono mt-0.5 ${
                      comparison.cycles_delta <= 0 ? 'text-emerald-400' : 'text-red-400'
                    }`}
                  >
                    {comparison.cycles_delta > 0 ? `+${comparison.cycles_delta}` : comparison.cycles_delta}
                  </div>
                  <div className="text-[10px] text-muted">
                    {comparison.base_cycles} → {comparison.target_cycles} circular loops
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-surface-2 dark:bg-white/[0.03] border border-[var(--border)] dark:border-white/5">
                  <div className="text-[10px] text-muted uppercase font-bold">Smells Delta</div>
                  <div
                    className={`text-xl font-bold font-mono mt-0.5 ${
                      comparison.smells_delta <= 0 ? 'text-emerald-400' : 'text-amber-400'
                    }`}
                  >
                    {comparison.smells_delta > 0 ? `+${comparison.smells_delta}` : comparison.smells_delta}
                  </div>
                  <div className="text-[10px] text-muted">
                    {comparison.base_smells} → {comparison.target_smells} findings
                  </div>
                </div>
              </div>

              {/* AI / Deterministic Change Summary */}
              {comparison.summary && (
                <div className="p-3.5 rounded-xl bg-surface-2 dark:bg-white/[0.04] border border-[var(--border)] dark:border-white/10 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold flex items-center gap-1.5 text-accent">
                      <Sparkles size={13} /> Architectural Delta Summary
                    </span>
                    {comparison.is_ai_generated ? (
                      <AIBadge label="AI-generated" size="xs" />
                    ) : (
                      <AIFallback message="Deterministic comparison" />
                    )}
                  </div>
                  <p className="text-muted leading-relaxed font-sans">{comparison.summary}</p>
                </div>
              )}

              {/* Added Modules */}
              {comparison.added_modules.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-xs font-bold text-emerald-400 flex items-center gap-1">
                    <PlusCircle size={13} /> Added Modules ({comparison.added_modules.length})
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {comparison.added_modules.map((m) => (
                      <span
                        key={m}
                        className="px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                      >
                        +{m}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Removed Modules */}
              {comparison.removed_modules.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-xs font-bold text-red-400 flex items-center gap-1">
                    <MinusCircle size={13} /> Removed Modules ({comparison.removed_modules.length})
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {comparison.removed_modules.map((m) => (
                      <span
                        key={m}
                        className="px-2 py-0.5 rounded text-[11px] font-mono bg-red-500/10 text-red-300 border border-red-500/20 line-through opacity-75"
                      >
                        -{m}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Modified Modules */}
              {comparison.modified_modules.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1">
                    <span>Modified Modules ({comparison.modified_modules.length})</span>
                  </div>
                  <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
                    {comparison.modified_modules.slice(0, 20).map((m) => (
                      <div
                        key={m.id}
                        className="p-2 rounded-lg bg-surface-2 dark:bg-white/[0.02] border border-[var(--border)] dark:border-white/5 flex items-center justify-between text-xs font-mono"
                      >
                        <span className="font-bold text-[var(--text-primary)]">{m.id}</span>
                        <div className="flex items-center gap-3 text-muted text-[11px]">
                          <span>
                            LOC: {m.loc_before} → {m.loc_after} ({m.loc_delta >= 0 ? `+${m.loc_delta}` : m.loc_delta})
                          </span>
                          <span>
                            CC: {m.complexity_before} → {m.complexity_after} ({m.complexity_delta >= 0 ? `+${m.complexity_delta}` : m.complexity_delta})
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
