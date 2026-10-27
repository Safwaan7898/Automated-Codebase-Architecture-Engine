import React, { useState } from 'react'
import {
  Wrench,
  GitPullRequest,
  ArrowRight,
  Check,
  Code2,
  Copy,
} from 'lucide-react'
import type { RefactorSuggestion } from '../types'

interface RefactorPlanSectionProps {
  suggestions: RefactorSuggestion[]
  onSelectNode: (nodeId: string) => void
  onDraftDiff: (suggestion: RefactorSuggestion) => void
  loadingDiffId: string | null
}

export const RefactorPlanSection: React.FC<RefactorPlanSectionProps> = ({
  suggestions,
  onSelectNode,
  onDraftDiff,
  loadingDiffId,
}) => {
  const [selectedSuggestion, setSelectedSuggestion] = useState<RefactorSuggestion | null>(null)
  const [copiedDiff, setCopiedDiff] = useState(false)

  const handleCopyDiff = (diffText: string) => {
    navigator.clipboard.writeText(diffText)
    setCopiedDiff(true)
    setTimeout(() => setCopiedDiff(false), 2000)
  }

  return (
    <section id="refactor-section" className="py-20 px-6 md:px-12 max-w-7xl mx-auto w-full border-t border-white/5">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-4">
        <div>
          <span className="text-xs font-mono uppercase tracking-widest text-amber-400 block mb-2">
            03 // AUTOMATED REFACTORING ENGINE
          </span>
          <h2 className="agencia-display text-4xl md:text-6xl text-white tracking-wider">
            RANKED REFACTORING PROPOSALS
          </h2>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-white/50">
            {suggestions.length} Concrete Actions Generated
          </span>
        </div>
      </div>

      {/* Grid of suggestions */}
      {suggestions.length === 0 ? (
        <div className="p-12 text-center bg-[#0a0a0a] rounded-2xl border border-white/5">
          <Wrench className="w-12 h-12 text-white/20 mx-auto mb-3" />
          <h3 className="font-mono text-sm text-white font-bold">Codebase In Cohesive State</h3>
          <p className="text-xs font-mono text-white/50 mt-1">
            No cyclic dependencies or god classes identified requiring structural partitioning.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {suggestions.map((s, idx) => (
            <div
              key={s.id || idx}
              className="p-6 bg-[#0f0f0f] border border-white/10 hover:border-white/25 rounded-2xl flex flex-col justify-between space-y-4 transition-colors duration-150 shadow-glass-luxury"
            >
              <div>
                {/* Header Tag */}
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30 text-[10px] font-mono uppercase font-bold">
                    {s.type.replace(/_/g, ' ')}
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-white/10 text-white/80 text-[10px] font-mono">
                    Effort: {s.effort}
                  </span>
                </div>

                <h3 className="font-mono text-sm font-bold text-white mb-2 leading-snug">
                  {s.title}
                </h3>

                <p className="text-xs font-mono text-white/60 leading-relaxed line-clamp-3">
                  {s.rationale}
                </p>
              </div>

              {/* Simulated Metrics Diff Before / After */}
              {s.impact_before && s.impact_after && (
                <div className="p-3 bg-black/50 rounded-xl border border-white/5 space-y-1.5 text-xs font-mono">
                  <div className="flex justify-between items-center text-white/40 text-[10px] uppercase">
                    <span>Metric</span>
                    <span>Before → Simulated After</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-white/70">Coupling:</span>
                    <span className="flex items-center gap-1.5">
                      <span className="text-red-400">{s.impact_before.coupling}</span>
                      <ArrowRight className="w-3 h-3 text-white/30" />
                      <span className="text-emerald-400 font-bold">{s.impact_after.coupling}</span>
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-white/70">Cyclic Edges:</span>
                    <span className="flex items-center gap-1.5">
                      <span className="text-red-400">{s.impact_before.cycles}</span>
                      <ArrowRight className="w-3 h-3 text-white/30" />
                      <span className="text-emerald-400 font-bold">{s.impact_after.cycles}</span>
                    </span>
                  </div>
                </div>
              )}

              {/* Affected Nodes Pills */}
              <div>
                <span className="text-[10px] font-mono text-white/40 uppercase block mb-1.5">
                  Affected Nodes:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {s.affected_nodes.slice(0, 3).map((nodeId, nIdx) => (
                    <button
                      key={nIdx}
                      onClick={() => onSelectNode(nodeId)}
                      className="px-2 py-0.5 rounded bg-white/5 hover:bg-white/15 text-[10px] font-mono text-white/80 truncate max-w-[140px] transition-colors"
                      title={nodeId}
                    >
                      {nodeId.split('.').pop() || nodeId}
                    </button>
                  ))}
                  {s.affected_nodes.length > 3 && (
                    <span className="text-[10px] font-mono text-white/40 self-center">
                      +{s.affected_nodes.length - 3} more
                    </span>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 border-t border-white/10 flex items-center gap-2">
                <button
                  onClick={() => onDraftDiff(s)}
                  disabled={loadingDiffId === s.id}
                  className="agencia-glass-btn flex-1 py-2.5 px-4 text-xs font-mono uppercase tracking-wider text-white font-medium flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Code2 className="w-3.5 h-3.5 text-blue-400" />
                  <span>{loadingDiffId === s.id ? 'Drafting…' : 'Draft Diff'}</span>
                </button>

                {s.diff_preview && (
                  <button
                    onClick={() => setSelectedSuggestion(s)}
                    className="p-2.5 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
                    title="View Refactoring Diff"
                  >
                    <GitPullRequest className="w-4 h-4 text-emerald-400" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Diff Preview Modal */}
      {selectedSuggestion && selectedSuggestion.diff_preview && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-[#0e0e0e] border border-white/20 rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-glass-luxury overflow-hidden animate-slide-up">
            <div className="p-5 border-b border-white/10 flex items-center justify-between">
              <div>
                <h3 className="font-mono text-sm font-bold text-white">
                  Refactoring Diff Preview
                </h3>
                <p className="text-xs font-mono text-white/50">{selectedSuggestion.title}</p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleCopyDiff(selectedSuggestion.diff_preview || '')}
                  className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-mono text-white flex items-center gap-1.5 transition-colors"
                >
                  {copiedDiff ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedDiff ? 'Copied' : 'Copy'}</span>
                </button>
                <button
                  onClick={() => setSelectedSuggestion(null)}
                  className="p-1.5 rounded-lg text-white/50 hover:text-white"
                >
                  ✕
                </button>
              </div>
            </div>

            <div className="p-5 overflow-y-auto flex-1 font-mono text-xs text-white/80 bg-black/50">
              <pre className="whitespace-pre-wrap">{selectedSuggestion.diff_preview}</pre>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
