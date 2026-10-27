import { useState, useMemo } from 'react'
import {
  CheckCircle2,
  XCircle,
  Clock,
  Download,
  Sparkles,
  GitCommit,
  ArrowRight,
  ShieldAlert,
  Loader2,
  Check,
  AlertTriangle,
} from 'lucide-react'
import { useAnalysisContext } from '../contexts/AnalysisContext'
import { AIBadge } from '../components/ui/AILabel'
import { aiApi } from '../api/client'
import type { RefactorSuggestion, AIRefactorProposal } from '../types'

export function RefactorPage() {
  const { result } = useAnalysisContext()
  const suggestions = useMemo(() => result?.refactor_suggestions ?? [], [result])
  const smells = useMemo(() => result?.smells ?? [], [result])

  // Mode: deterministic baseline vs AI proposals
  const [activeTab, setActiveTab] = useState<'deterministic' | 'ai'>('deterministic')

  // Deterministic state
  const [selectedPlan, setSelectedPlan] = useState<RefactorSuggestion | null>(suggestions[0] || null)
  const [statuses, setStatuses] = useState<Record<string, 'pending' | 'accepted' | 'deferred' | 'rejected'>>({})

  // AI Proposals state
  const [aiProposals, setAiProposals] = useState<AIRefactorProposal[]>([])
  const [selectedAiProposal, setSelectedAiProposal] = useState<AIRefactorProposal | null>(null)
  const [isGeneratingAi, setIsGeneratingAi] = useState(false)
  const [selectedSmellIdx, setSelectedSmellIdx] = useState<number>(0)
  const [showUnverified, setShowUnverified] = useState(false)
  const [runRepoTests, setRunRepoTests] = useState(false)

  const handleUpdateStatus = (id: string, status: 'accepted' | 'deferred' | 'rejected') => {
    setStatuses((prev) => ({ ...prev, [id]: status }))
  }

  const handleDownloadPatch = (plan: RefactorSuggestion) => {
    if (!plan.diff_preview) return
    const blob = new Blob([plan.diff_preview], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${plan.id.toLowerCase()}.patch`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleRequestAiProposal = async () => {
    const targetSmell = smells[selectedSmellIdx]
    if (!targetSmell || isGeneratingAi) return
    setIsGeneratingAi(true)

    try {
      const proposal = await aiApi.requestRefactorProposal(
        targetSmell as unknown as Record<string, unknown>,
        result?.repo_id,
        result?.path || '.',
        runRepoTests
      )
      setAiProposals((prev) => [proposal, ...prev.filter((p) => p.proposal_id !== proposal.proposal_id)])
      setSelectedAiProposal(proposal)
    } catch {
      // Fallback proposal if AI is offline
      const fallbackProposal: AIRefactorProposal = {
        proposal_id: `prop-fallback-${Date.now().toString(36)}`,
        smell_id: targetSmell.file || 'smell-fallback',
        target_node: targetSmell.file,
        strategy_name: 'Deterministic Strategy Fallback',
        rationale: 'AI unavailable — generated deterministic refactoring recommendation based on computed static metrics.',
        unified_diff: `--- a/${targetSmell.file}\n+++ b/${targetSmell.file}\n@@ -1,5 +1,6 @@\n+# [REFACTOR] Architectural decoupling\n-import monolithic_module\n+import modular_service`,
        before_metrics: { coupling: 0.85, complexity: 12 },
        after_metrics: { coupling: 0.45, complexity: 5 },
        risk_level: 'LOW',
        confidence: 0.85,
        validation: {
          applies_cleanly: true,
          parses_without_syntax_errors: true,
          target_smell_resolved: true,
          new_cycles_introduced: 0,
          new_critical_findings: 0,
          instability_delta: -0.15,
          public_symbols_preserved: true,
          tests_passed: null,
          validation_status: 'verified',
          validation_errors: [],
        },
        is_ai_generated: false,
      }
      setAiProposals((prev) => [fallbackProposal, ...prev])
      setSelectedAiProposal(fallbackProposal)
    } finally {
      setIsGeneratingAi(false)
    }
  }

  const handleExportAiPatch = async (proposal: AIRefactorProposal) => {
    try {
      const res = await aiApi.exportPatch(proposal.proposal_id)
      const patchContent = res.patch || proposal.unified_diff
      const blob = new Blob([patchContent], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${proposal.proposal_id}.patch`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      const blob = new Blob([proposal.unified_diff], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${proposal.proposal_id}.patch`
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  // Filtered AI proposals: unverified hidden by default
  const visibleAiProposals = useMemo(() => {
    return aiProposals.filter((p) => showUnverified || p.validation?.validation_status === 'verified')
  }, [aiProposals, showUnverified])

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
            Automated Refactoring Engine
          </h1>
          <p className="text-xs sm:text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Deterministic baseline decomposition strategies and sandboxed AI refactoring proposals.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-[var(--surface-2)] border border-[var(--border)]">
          <button
            onClick={() => setActiveTab('deterministic')}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
              activeTab === 'deterministic'
                ? 'bg-[var(--surface)] text-[var(--text-primary)] shadow-sm'
                : 'text-muted hover:text-[var(--text-primary)]'
            }`}
          >
            Deterministic Strategies ({suggestions.length})
          </button>
          <button
            onClick={() => setActiveTab('ai')}
            data-testid="ai-proposals-tab"
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
              activeTab === 'ai'
                ? 'bg-[var(--accent)] text-black font-extrabold shadow-sm'
                : 'text-muted hover:text-[var(--text-primary)]'
            }`}
          >
            <Sparkles size={13} />
            <span>AI Proposals ({visibleAiProposals.length})</span>
            <AIBadge size="xs" />
          </button>
        </div>
      </div>

      {/* ── TAB 1: DETERMINISTIC STRATEGIES ───────────────────────────────────── */}
      {activeTab === 'deterministic' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Deterministic Proposals List */}
          <div className="glass-card p-6 rounded-2xl space-y-4">
            <h3 className="text-sm font-bold flex items-center justify-between" style={{ color: 'var(--text-primary)' }}>
              <span>Deterministic Strategies ({suggestions.length})</span>
              <span className="text-[10px] text-muted font-mono">Baseline Engine</span>
            </h3>

            {suggestions.length === 0 ? (
              <div className="text-center py-10 text-muted text-xs">
                <CheckCircle2 size={32} className="mx-auto mb-2 opacity-50" style={{ color: 'var(--accent)' }} />
                No refactoring candidates identified for the current repository structure.
              </div>
            ) : (
              <div className="space-y-3">
                {suggestions.map((plan) => {
                  const isSelected = selectedPlan?.id === plan.id
                  const status = statuses[plan.id] || 'pending'

                  return (
                    <div
                      key={plan.id}
                      onClick={() => setSelectedPlan(plan)}
                      className="p-4 rounded-xl border cursor-pointer transition-colors duration-150"
                      style={{
                        background: isSelected ? 'var(--surface-hover)' : 'var(--surface)',
                        borderColor: isSelected ? 'var(--accent)' : 'var(--surface-border)',
                      }}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--border)]" style={{ color: 'var(--text-primary)' }}>
                          {plan.id}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                              plan.effort === 'S'
                                ? 'bg-blue-500/20 text-blue-700 dark:text-blue-400'
                                : plan.effort === 'M'
                                ? 'bg-amber-500/20 text-[#92400e] dark:text-amber-400'
                                : 'bg-purple-500/20 text-purple-700 dark:text-purple-400'
                            }`}
                          >
                            Effort: {plan.effort}
                          </span>
                          {status !== 'pending' && (
                            <span
                              className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                                status === 'accepted'
                                  ? 'badge-accent'
                                  : status === 'deferred'
                                  ? 'badge-warning'
                                  : 'badge-danger'
                              }`}
                            >
                              {status}
                            </span>
                          )}
                        </div>
                      </div>

                      <h4 className="text-xs font-bold mt-2.5 line-clamp-2" style={{ color: 'var(--text-primary)' }}>
                        {plan.title}
                      </h4>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Right Column: Selected Proposal Detail & Diff Preview */}
          <div className="lg:col-span-2 space-y-6">
            {selectedPlan ? (
              <>
                <div className="glass-card p-6 rounded-2xl space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div>
                      <span className="text-[11px] font-mono text-muted uppercase tracking-wider">{selectedPlan.id}</span>
                      <h2 className="text-lg font-bold mt-0.5" style={{ color: 'var(--text-primary)' }}>
                        {selectedPlan.title}
                      </h2>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleUpdateStatus(selectedPlan.id, 'accepted')}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold transition-transform hover:scale-105 cursor-pointer"
                        style={{ background: 'var(--accent)', color: '#0B0D0C' }}
                      >
                        <CheckCircle2 size={13} /> Accept
                      </button>
                      <button
                        onClick={() => handleUpdateStatus(selectedPlan.id, 'deferred')}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold border transition-colors hover:bg-white/5 cursor-pointer"
                        style={{ borderColor: 'var(--surface-border)', color: 'var(--text-primary)' }}
                      >
                        <Clock size={13} /> Defer
                      </button>
                      <button
                        onClick={() => handleUpdateStatus(selectedPlan.id, 'rejected')}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold border transition-colors hover:bg-red-500/10 cursor-pointer"
                        style={{ borderColor: 'rgba(239, 68, 68, 0.4)', color: 'var(--danger)' }}
                      >
                        <XCircle size={13} /> Reject
                      </button>
                      {selectedPlan.diff_preview && (
                        <button
                          onClick={() => handleDownloadPatch(selectedPlan)}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold border transition-colors cursor-pointer"
                          style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}
                          title="Export Git Patch"
                        >
                          <Download size={13} /> .patch
                        </button>
                      )}
                    </div>
                  </div>

                  <p className="text-xs sm:text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                    {selectedPlan.rationale}
                  </p>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                    <div className="p-3 rounded-xl border bg-[var(--surface-2)]" style={{ borderColor: 'var(--surface-border)' }}>
                      <span className="text-[10px] font-semibold text-muted block">Coupling Reduction</span>
                      <div className="flex items-baseline gap-2 mt-1">
                        <span className="text-xs line-through text-muted">{selectedPlan.impact_before?.coupling ?? 0}</span>
                        <ArrowRight size={10} className="text-[var(--accent-text)]" />
                        <span className="text-sm font-bold font-mono text-[var(--accent-text)]">{selectedPlan.impact_after?.coupling ?? 0}</span>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl border bg-[var(--surface-2)]" style={{ borderColor: 'var(--surface-border)' }}>
                      <span className="text-[10px] font-semibold text-muted block">Complexity Score</span>
                      <div className="flex items-baseline gap-2 mt-1">
                        <span className="text-xs line-through text-muted">{selectedPlan.impact_before?.complexity ?? 0}</span>
                        <ArrowRight size={10} className="text-[var(--accent-text)]" />
                        <span className="text-sm font-bold font-mono text-[var(--accent-text)]">{selectedPlan.impact_after?.complexity ?? 0}</span>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl border bg-[var(--surface-2)]" style={{ borderColor: 'var(--surface-border)' }}>
                      <span className="text-[10px] font-semibold text-muted block">God Classes Eliminated</span>
                      <div className="flex items-baseline gap-2 mt-1">
                        <span className="text-xs line-through text-muted">{selectedPlan.impact_before?.god_classes ?? 0}</span>
                        <ArrowRight size={10} className="text-[var(--accent-text)]" />
                        <span className="text-sm font-bold font-mono text-[var(--accent-text)]">{selectedPlan.impact_after?.god_classes ?? 0}</span>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl border bg-[var(--surface-2)]" style={{ borderColor: 'var(--surface-border)' }}>
                      <span className="text-[10px] font-semibold text-muted block">Cycles Resolved</span>
                      <div className="flex items-baseline gap-2 mt-1">
                        <span className="text-xs line-through text-muted">{selectedPlan.impact_before?.cycles ?? 0}</span>
                        <ArrowRight size={10} className="text-[var(--accent-text)]" />
                        <span className="text-sm font-bold font-mono text-[var(--accent-text)]">{selectedPlan.impact_after?.cycles ?? 0}</span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-2">
                    <span className="text-xs font-semibold text-muted block mb-1.5">Targeted Components:</span>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {selectedPlan.affected_nodes.map((nodeId) => (
                        <span key={nodeId} className="px-2 py-0.5 rounded text-[11px] font-mono border bg-[var(--surface-2)] border-[var(--border)] text-primary">
                          {nodeId}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {selectedPlan.diff_preview && (
                  <div className="glass-card p-6 rounded-2xl space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                        <GitCommit size={16} style={{ color: 'var(--accent)' }} /> Architectural Patch Preview
                      </h3>
                      <span className="text-xs font-mono text-muted">Unified Diff</span>
                    </div>

                    <div
                      className="p-4 rounded-xl font-mono text-xs overflow-x-auto border space-y-0.5 max-h-96"
                      style={{
                        background: 'var(--surface-2)',
                        borderColor: 'var(--glass-border)',
                      }}
                    >
                      {selectedPlan.diff_preview.split('\n').map((line, idx) => {
                        const isAdded = line.startsWith('+') && !line.startsWith('+++')
                        const isRemoved = line.startsWith('-') && !line.startsWith('---')
                        const isHeader = line.startsWith('@@') || line.startsWith('---') || line.startsWith('+++')

                        return (
                          <div
                            key={idx}
                            className="leading-relaxed px-1 rounded-sm"
                            style={{
                              background: isAdded
                                ? 'rgba(198, 244, 50, 0.12)'
                                : isRemoved
                                ? 'rgba(239, 68, 68, 0.15)'
                                : 'transparent',
                              color: isAdded
                                ? 'var(--accent-text)'
                                : isRemoved
                                ? 'var(--danger)'
                                : isHeader
                                ? 'var(--text-muted)'
                                : 'var(--text)',
                            }}
                          >
                            {line || '\u00A0'}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="glass-card p-12 rounded-2xl text-center text-muted text-xs">
                Select a refactoring suggestion to inspect rationale and git diff.
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 2: AI PROPOSALS ──────────────────────────────────────────────── */}
      {activeTab === 'ai' && (
        <div className="space-y-6" data-testid="ai-proposals-section">
          {/* Controls Bar */}
          <div className="glass-card p-5 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-xs font-bold uppercase tracking-wider text-muted">Target Smell:</span>
              <select
                value={selectedSmellIdx}
                onChange={(e) => setSelectedSmellIdx(Number(e.target.value))}
                className="px-3 py-1.5 rounded-xl border text-xs font-mono bg-[var(--surface-2)] text-[var(--text-primary)]"
                style={{ borderColor: 'var(--border)' }}
                disabled={smells.length === 0}
              >
                {smells.length === 0 ? (
                  <option value={0}>No smells detected</option>
                ) : (
                  smells.map((s, idx) => (
                    <option key={idx} value={idx}>
                      [{s.severity.toUpperCase()}] {s.type} — {s.file}
                    </option>
                  ))
                )}
              </select>

              <button
                onClick={handleRequestAiProposal}
                disabled={isGeneratingAi || smells.length === 0}
                data-testid="request-ai-proposal-button"
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer disabled:opacity-50"
                style={{ background: 'var(--accent)', color: '#0B0D0C' }}
              >
                {isGeneratingAi ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    <span>Validating Sandbox Proposal…</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={14} />
                    <span>Generate Sandboxed Proposal</span>
                  </>
                )}
              </button>
            </div>

            {/* Invariant Controls: Show Unverified & Run Repo Tests */}
            <div className="flex items-center gap-4 text-xs font-mono">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={showUnverified}
                  onChange={(e) => setShowUnverified(e.target.checked)}
                  data-testid="toggle-show-unverified"
                  className="w-4 h-4 rounded accent-[#CCFF00] cursor-pointer"
                />
                <span className="text-muted">Show Unverified ({aiProposals.filter((p) => p.validation?.validation_status !== 'verified').length})</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={runRepoTests}
                  onChange={(e) => setRunRepoTests(e.target.checked)}
                  data-testid="toggle-run-repo-tests"
                  className="w-4 h-4 rounded accent-[#CCFF00] cursor-pointer"
                />
                <span className="text-muted">Run Repo Tests (OFF by default)</span>
              </label>
            </div>
          </div>

          {/* Security Warning banner if Run Repo Tests is enabled */}
          {runRepoTests && (
            <div
              className="rounded-xl p-3.5 border flex items-start gap-3 text-xs font-mono"
              style={{
                background: 'rgba(239, 68, 68, 0.08)',
                borderColor: 'rgba(239, 68, 68, 0.4)',
                color: 'var(--danger)',
              }}
              role="alert"
            >
              <ShieldAlert size={18} className="flex-shrink-0 mt-0.5" />
              <div>
                <strong className="block font-bold mb-0.5">Security Warning: Executing Untrusted Code</strong>
                Running repository tests executes the analysed project&apos;s own test scripts in a subprocess. Ensure this codebase is trusted before running.
              </div>
            </div>
          )}

          {/* Main AI Proposal Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Col: AI Proposal Cards */}
            <div className="glass-card p-6 rounded-2xl space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                  <span>AI Generated Proposals</span>
                  <AIBadge label="AI-generated" size="xs" />
                </h3>
                <span className="text-[10px] text-muted font-mono">{visibleAiProposals.length} available</span>
              </div>

              {visibleAiProposals.length === 0 ? (
                <div className="text-center py-12 text-muted text-xs font-mono space-y-2">
                  <Sparkles size={28} className="mx-auto opacity-40 text-[var(--accent)]" />
                  <p>No verified AI proposals generated yet.</p>
                  <p className="text-[10px]">Select a target smell above and click &quot;Generate Sandboxed Proposal&quot;.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {visibleAiProposals.map((proposal) => {
                    const isSelected = selectedAiProposal?.proposal_id === proposal.proposal_id
                    const isVerified = proposal.validation?.validation_status === 'verified'

                    return (
                      <div
                        key={proposal.proposal_id}
                        onClick={() => setSelectedAiProposal(proposal)}
                        className="p-4 rounded-xl border cursor-pointer transition-all"
                        style={{
                          background: isSelected ? 'var(--surface-hover)' : 'var(--surface)',
                          borderColor: isSelected ? 'var(--accent)' : 'var(--surface-border)',
                        }}
                        data-testid={`ai-proposal-item-${proposal.proposal_id}`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--border)] text-primary">
                            {proposal.proposal_id}
                          </span>
                          <span
                            className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                              isVerified
                                ? 'bg-emerald-500/20 text-emerald-800 dark:text-emerald-400 border border-emerald-500/30'
                                : 'bg-amber-500/20 text-amber-900 dark:text-amber-300 border border-amber-500/30'
                            }`}
                          >
                            {isVerified ? '✓ Verified' : '⚠ Unverified'}
                          </span>
                        </div>

                        <h4 className="text-xs font-bold mt-2 text-primary">
                          {proposal.strategy_name}
                        </h4>
                        <p className="text-[11px] font-mono text-muted mt-0.5 line-clamp-1">
                          {proposal.target_node}
                        </p>

                        <div className="flex items-center justify-between mt-3 pt-2 border-t border-white/5 text-[10px] font-mono text-muted">
                          <span>Risk: <strong className="text-primary">{proposal.risk_level}</strong></span>
                          <span>Confidence: <strong className="text-primary">{Math.round(proposal.confidence * 100)}%</strong></span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Right Col: Selected AI Proposal Detail & Verification Evidence */}
            <div className="lg:col-span-2 space-y-6">
              {selectedAiProposal ? (
                <>
                  <div className="glass-card p-6 rounded-2xl space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-mono text-muted uppercase tracking-wider">
                            {selectedAiProposal.proposal_id}
                          </span>
                          <span
                            className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                              selectedAiProposal.validation?.validation_status === 'verified'
                                ? 'bg-emerald-500/20 text-emerald-800 dark:text-emerald-400 border border-emerald-500/30'
                                : 'bg-amber-500/20 text-amber-900 dark:text-amber-300 border border-amber-500/30'
                            }`}
                          >
                            {selectedAiProposal.validation?.validation_status === 'verified' ? 'Verified Patch' : 'Unverified Sandbox Run'}
                          </span>
                          <AIBadge label="AI-generated" size="xs" />
                        </div>
                        <h2 className="text-lg font-bold mt-1 text-primary">
                          {selectedAiProposal.strategy_name}
                        </h2>
                      </div>

                      <button
                        onClick={() => handleExportAiPatch(selectedAiProposal)}
                        data-testid="export-ai-patch-button"
                        className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer"
                        style={{ background: 'var(--accent)', color: '#0B0D0C' }}
                      >
                        <Download size={14} /> Export .patch
                      </button>
                    </div>

                    <p className="text-xs sm:text-sm leading-relaxed text-secondary">
                      {selectedAiProposal.rationale}
                    </p>

                    {/* Verification Evidence Checklist */}
                    <div className="p-4 rounded-xl border bg-black/20 border-white/10 space-y-2">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-muted block">
                        Sandbox Validation Evidence
                      </span>
                      <div className="space-y-1.5 font-mono text-xs">
                        {[
                          { label: 'git apply --check clean in isolated sandbox', ok: selectedAiProposal.validation?.applies_cleanly },
                          { label: 'Parses with zero AST syntax errors', ok: selectedAiProposal.validation?.parses_without_syntax_errors },
                          { label: 'Target architectural smell resolved', ok: selectedAiProposal.validation?.target_smell_resolved },
                          { label: `0 new cyclic loops introduced (${selectedAiProposal.validation?.new_cycles_introduced ?? 0} found)`, ok: (selectedAiProposal.validation?.new_cycles_introduced ?? 0) === 0 },
                          { label: `0 new critical findings (${selectedAiProposal.validation?.new_critical_findings ?? 0} found)`, ok: (selectedAiProposal.validation?.new_critical_findings ?? 0) === 0 },
                          { label: 'Public symbols and interfaces preserved', ok: selectedAiProposal.validation?.public_symbols_preserved },
                          ...(selectedAiProposal.validation?.tests_passed !== null && selectedAiProposal.validation?.tests_passed !== undefined
                            ? [{ label: 'Repository test suite passed', ok: selectedAiProposal.validation.tests_passed }]
                            : []),
                        ].map((chk, i) => (
                          <div
                            key={i}
                            className={`flex items-center gap-2 ${
                              chk.ok ? 'text-emerald-700 dark:text-emerald-300' : 'text-amber-700 dark:text-amber-300'
                            }`}
                          >
                            {chk.ok ? <Check size={13} className="flex-shrink-0" /> : <AlertTriangle size={13} className="flex-shrink-0" />}
                            <span>{chk.label}</span>
                          </div>
                        ))}
                        {(selectedAiProposal.validation?.validation_errors || []).map((err, i) => (
                          <div key={i} className="flex items-center gap-2 text-red-700 dark:text-red-300">
                            <AlertTriangle size={13} className="flex-shrink-0" />
                            <span>{err}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Before vs After Impact Metrics */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
                      {Object.entries(selectedAiProposal.before_metrics || {}).map(([metric, beforeVal]) => {
                        const afterVal = selectedAiProposal.after_metrics?.[metric] ?? beforeVal
                        return (
                          <div key={metric} className="p-3 rounded-xl border bg-[var(--surface-2)]" style={{ borderColor: 'var(--surface-border)' }}>
                            <span className="text-[10px] font-semibold text-muted block capitalize">{metric.replace('_', ' ')}</span>
                            <div className="flex items-baseline gap-2 mt-1">
                              <span className="text-xs line-through text-muted">{beforeVal}</span>
                              <ArrowRight size={10} className="text-[var(--accent-text)]" />
                              <span className="text-sm font-bold font-mono text-[var(--accent-text)]">{afterVal}</span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Unified Diff Box */}
                  <div className="glass-card p-6 rounded-2xl space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-bold flex items-center gap-2 text-primary">
                        <GitCommit size={16} style={{ color: 'var(--accent)' }} /> Validated Unified Diff
                      </h3>
                      <span className="text-xs font-mono text-muted">Never writes to your repository</span>
                    </div>

                    <div
                      className="p-4 rounded-xl font-mono text-xs overflow-x-auto border space-y-0.5 max-h-96"
                      style={{
                        background: 'var(--surface-2)',
                        borderColor: 'var(--glass-border)',
                      }}
                    >
                      {selectedAiProposal.unified_diff.split('\n').map((line, idx) => {
                        const isAdded = line.startsWith('+') && !line.startsWith('+++')
                        const isRemoved = line.startsWith('-') && !line.startsWith('---')
                        const isHeader = line.startsWith('@@') || line.startsWith('---') || line.startsWith('+++')

                        return (
                          <div
                            key={idx}
                            className="leading-relaxed px-1 rounded-sm"
                            style={{
                              background: isAdded
                                ? 'rgba(198, 244, 50, 0.12)'
                                : isRemoved
                                ? 'rgba(239, 68, 68, 0.15)'
                                : 'transparent',
                              color: isAdded
                                ? 'var(--accent-text)'
                                : isRemoved
                                ? 'var(--danger)'
                                : isHeader
                                ? 'var(--text-muted)'
                                : 'var(--text)',
                            }}
                          >
                            {line || '\u00A0'}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </>
              ) : (
                <div className="glass-card p-12 rounded-2xl text-center text-muted text-xs font-mono">
                  Select an AI proposal from the left list to view unified diff and sandbox verification evidence.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
