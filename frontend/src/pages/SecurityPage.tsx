import { useState, useMemo } from 'react'
import {
  ShieldAlert,
  AlertTriangle,
  Flame,
  Lock,
  CheckCircle,
  Radio,
} from 'lucide-react'
import { useAnalysisContext } from '../contexts/AnalysisContext'
import { AIExplainPanel } from '../components/AIExplainPanel'
import { AIBadge } from '../components/ui/AILabel'
import { aiApi } from '../api/client'
import type { DiagnosticFinding } from '../types'

export function SecurityPage() {
  const { result, loadSample } = useAnalysisContext()
  const [selectedFinding, setSelectedFinding] = useState<DiagnosticFinding | null>(null)
  const [blastNodeId, setBlastNodeId] = useState<string | null>(null)

  // Extract all security findings
  const findings: DiagnosticFinding[] = useMemo(() => {
    const list: DiagnosticFinding[] = []
    if (result?.findings && result.findings.length > 0) {
      list.push(...result.findings)
    }
    result?.graph?.nodes?.forEach((n) => {
      if (n.findings && n.findings.length > 0) {
        list.push(...n.findings)
      }
    })
    const seen = new Set<string>()
    return list.filter((f) => {
      if (seen.has(f.id)) return false
      seen.add(f.id)
      return true
    })
  }, [result])

  // Circular dependency smell detection
  const circularSmells = useMemo(() => {
    return result?.smells.filter((s) => s.type === 'circular_import') ?? []
  }, [result])

  // High risk nodes
  const highRiskNodes = useMemo(() => {
    return (result?.graph.nodes ?? []).filter((n) => (n.risk_score ?? 0) >= 60 || n.is_vulnerable)
  }, [result])

  // Downstream blast radius calculation for chosen node
  const blastRadiusDownstream = useMemo(() => {
    if (!blastNodeId || !result) return []
    const edges = result.graph.edges
    const visited = new Set<string>()
    const queue = [blastNodeId]

    while (queue.length > 0) {
      const curr = queue.shift()!
      edges.forEach((e) => {
        const sourceId = typeof e.source === 'string' ? e.source : (e.source as { id: string })?.id
        const targetId = typeof e.target === 'string' ? e.target : (e.target as { id: string })?.id
        if (sourceId === curr && targetId && !visited.has(targetId)) {
          visited.add(targetId)
          queue.push(targetId)
        }
      })
    }
    return Array.from(visited)
  }, [blastNodeId, result])

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Vulnerabilities & Architectural Risks
            </h1>
            <AIBadge label="AI-generated" size="xs" />
          </div>
          <p className="text-xs sm:text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Dedicated security analysis console: CWE vulnerability findings, circular dependency loops, and blast radius impact.
          </p>
        </div>

        {findings.length === 0 && (
          <button
            onClick={() => loadSample('vulnerable')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-colors duration-150"
            style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)', color: 'var(--danger)' }}
          >
            <ShieldAlert size={14} /> Load Security Benchmark Fixture
          </button>
        )}
      </div>

      {/* Red Risk Highlight Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Critical CVEs */}
        <div
          className="glass-card p-5 rounded-2xl border"
          style={{
            borderColor: findings.length > 0 ? 'rgba(239, 68, 68, 0.4)' : 'var(--glass-border)',
            background: findings.length > 0 ? 'rgba(239, 68, 68, 0.05)' : 'var(--card-bg)',
          }}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
              Identified CWE Findings
            </span>
            <ShieldAlert size={18} style={{ color: 'var(--danger)' }} />
          </div>
          <div className="text-3xl font-bold mt-2 font-mono" style={{ color: 'var(--danger)' }}>
            {findings.length}
          </div>
          <p className="text-[11px] mt-1 text-muted">
            {findings.filter((f) => f.severity === 'critical').length} Critical,{' '}
            {findings.filter((f) => f.severity === 'high').length} High
          </p>
        </div>

        {/* Circular Dependency Loops */}
        <div
          className="glass-card p-5 rounded-2xl border"
          style={{
            borderColor: circularSmells.length > 0 ? 'rgba(239, 68, 68, 0.4)' : 'var(--glass-border)',
            background: circularSmells.length > 0 ? 'rgba(239, 68, 68, 0.05)' : 'var(--card-bg)',
          }}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
              Circular Cycles
            </span>
            <AlertTriangle size={18} style={{ color: 'var(--danger)' }} />
          </div>
          <div className="text-3xl font-bold mt-2 font-mono" style={{ color: 'var(--danger)' }}>
            {circularSmells.length}
          </div>
          <p className="text-[11px] mt-1 text-muted">Mutual dependency deadlocks obstructing isolation</p>
        </div>

        {/* High Blast Radius Components */}
        <div
          className="glass-card p-5 rounded-2xl border"
          style={{
            borderColor: highRiskNodes.length > 0 ? 'rgba(239, 68, 68, 0.4)' : 'var(--glass-border)',
            background: highRiskNodes.length > 0 ? 'rgba(239, 68, 68, 0.05)' : 'var(--card-bg)',
          }}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
              High-Risk Nodes
            </span>
            <Flame size={18} style={{ color: 'var(--danger)' }} />
          </div>
          <div className="text-3xl font-bold mt-2 font-mono" style={{ color: 'var(--danger)' }}>
            {highRiskNodes.length}
          </div>
          <p className="text-[11px] mt-1 text-muted">Components with Risk Score ≥ 60</p>
        </div>
      </div>

      {/* Main Content Grid: Findings & Blast Radius */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Findings List (2 cols) */}
        <div className="lg:col-span-2 glass-card p-6 rounded-2xl space-y-4">
          <h3 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <Lock size={16} style={{ color: 'var(--danger)' }} /> Security Findings & CWE Audit
          </h3>

          {findings.length === 0 ? (
            <div className="text-center py-12 text-muted text-xs">
              <CheckCircle size={32} className="mx-auto mb-2 opacity-60" style={{ color: 'var(--accent)' }} />
              No security vulnerabilities or CWE violations detected in the current codebase!
            </div>
          ) : (
            <div className="space-y-3">
              {findings.map((f) => {
                const isSelected = selectedFinding?.id === f.id
                return (
                  <div
                    key={f.id}
                    onClick={() => setSelectedFinding(f)}
                    className="p-4 rounded-xl border cursor-pointer transition-transform duration-150 hover:scale-[1.01] will-change-transform"
                    style={{
                      background: isSelected ? 'rgba(239, 68, 68, 0.12)' : 'var(--surface)',
                      borderColor: isSelected ? 'var(--danger)' : 'rgba(239, 68, 68, 0.3)',
                    }}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="badge badge-danger text-[10px] uppercase font-bold">
                            {f.severity}
                          </span>
                          <span className="badge text-[10px] font-mono border" style={{ borderColor: 'rgba(239, 68, 68, 0.4)', color: 'var(--danger)' }}>
                            {f.cwe || f.rule_id}
                          </span>
                          <span className="text-[11px] font-mono text-muted">{f.owasp}</span>
                        </div>
                        <h4 className="text-sm font-bold mt-2" style={{ color: 'var(--text-primary)' }}>
                          {f.title}
                        </h4>
                        <p className="text-xs font-mono mt-0.5 text-muted">
                          {f.file_path} {f.line_number && `: Line ${f.line_number}`}
                        </p>
                      </div>

                      <span
                        className={`text-xs font-bold px-2 py-1 rounded transition-colors ${
                          isSelected ? 'text-white' : 'text-red-700 dark:text-red-400'
                        }`}
                        style={{
                          background: isSelected ? 'var(--danger)' : 'rgba(239, 68, 68, 0.2)',
                        }}
                      >
                        Inspect
                      </span>
                    </div>

                    {/* Code Snippet Highlight */}
                    {f.code_snippet && (
                      <div
                        className="mt-3 p-3 rounded-lg font-mono text-xs overflow-x-auto border"
                        style={{
                          background: 'var(--surface-2)',
                          borderColor: 'rgba(239, 68, 68, 0.3)',
                          color: 'var(--danger)',
                        }}
                      >
                        <code>{f.code_snippet}</code>
                      </div>
                    )}

                    {/* Remediation */}
                    {f.remediation && (
                      <div className="mt-3 text-xs p-2.5 rounded-lg bg-[var(--surface-2)] border border-[var(--border)] space-y-1">
                        <span className="font-semibold text-[var(--accent-text)] block">Recommended Remediation:</span>
                        <p className="text-muted font-mono text-[11px]">{f.remediation}</p>
                      </div>
                    )}

                    {/* AI Security Finding Enrichment */}
                    <AIExplainPanel
                      label="Enrich with AI (Explanation & FP Likelihood)"
                      className="mt-3 pt-2 border-t border-white/5"
                      fetch={async () => {
                        try {
                          const res = await aiApi.enrichSecurity(
                            f as unknown as Record<string, unknown>,
                            f.code_snippet
                          )
                          return {
                            explanation: res.explanation ?? 'AI unavailable',
                            fix: res.suggested_fix ? `Suggested Fix:\n${res.suggested_fix}` : undefined,
                            fp_likelihood: res.false_positive_likelihood,
                            fp_reason: res.false_positive_reason,
                          }
                        } catch {
                          return null
                        }
                      }}
                      enabled={!!result}
                    />
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Right Col: Blast Radius Simulator & Circular Dependencies */}
        <div className="space-y-6">
          {/* Circular Dependencies Card */}
          <div className="glass-card p-6 rounded-2xl space-y-3">
            <h3 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <AlertTriangle size={16} style={{ color: 'var(--danger)' }} /> Circular Cycles
            </h3>
            {circularSmells.length === 0 ? (
              <p className="text-xs text-muted">No circular dependencies found.</p>
            ) : (
              <div className="space-y-2">
                {circularSmells.map((c, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-xl border text-xs space-y-1"
                    style={{ background: 'var(--surface)', borderColor: 'rgba(239, 68, 68, 0.3)' }}
                  >
                    <span className="badge badge-danger text-[9px] uppercase font-bold">CYCLE DETECTED</span>
                    <p className="leading-relaxed mt-1" style={{ color: 'var(--text-secondary)' }}>
                      {c.description}
                    </p>
                    <AIExplainPanel
                      label="AI Cycle Explanation"
                      className="mt-2 pt-2 border-t border-white/5"
                      fetch={async () => {
                        try {
                          const res = await aiApi.explainSmell(
                            c as unknown as Record<string, unknown>,
                            { repo_id: result?.repo_id }
                          )
                          return {
                            explanation: res.why_it_matters ?? 'AI unavailable',
                            fix: res.fix_outline,
                          }
                        } catch {
                          return null
                        }
                      }}
                      enabled={!!result}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Blast Radius Impact Calculator */}
          <div className="glass-card p-6 rounded-2xl space-y-4">
            <div>
              <h3 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                <Radio size={16} style={{ color: 'var(--danger)' }} /> Blast Radius Calculator
              </h3>
              <p className="text-xs mt-1 text-muted">
                Select a compromised component to compute all transitive downstream consumers.
              </p>
            </div>

            <select
              value={blastNodeId ?? ''}
              onChange={(e) => setBlastNodeId(e.target.value || null)}
              className="w-full px-3 py-2 rounded-xl text-xs font-mono border bg-[var(--surface)]"
              style={{ borderColor: 'var(--surface-border)', color: 'var(--text-primary)' }}
            >
              <option value="">Select component for blast radius...</option>
              {result?.graph.nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.label} (Risk: {n.risk_score})
                </option>
              ))}
            </select>

            {blastNodeId && (
              <div className="space-y-2 pt-2 border-t border-[var(--border)]">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-muted">Impacted Downstream Nodes:</span>
                  <span className="font-bold text-danger font-mono">{blastRadiusDownstream.length}</span>
                </div>
                {blastRadiusDownstream.length === 0 ? (
                  <p className="text-xs text-muted">No downstream nodes affected.</p>
                ) : (
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {blastRadiusDownstream.map((id) => (
                      <div
                        key={id}
                        className="p-2 rounded-lg text-xs font-mono border"
                        style={{ background: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)', color: 'var(--danger)' }}
                      >
                        {id}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
