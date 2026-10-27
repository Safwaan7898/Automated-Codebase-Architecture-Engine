import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  Layers,
  Activity,
  AlertTriangle,
  Flame,
  CheckCircle2,
  FileCode,
  ArrowUpRight,
} from 'lucide-react'
import { useAnalysisContext } from '../contexts/AnalysisContext'
import { AIExplainPanel } from '../components/AIExplainPanel'
import { AIBadge } from '../components/ui/AILabel'
import { aiApi } from '../api/client'

export function MetricsPage() {
  const { result } = useAnalysisContext()
  const [severityFilter, setSeverityFilter] = useState('ALL')
  const [typeFilter, setTypeFilter] = useState('ALL')

  const smells = useMemo(() => result?.smells ?? [], [result])

  const filteredSmells = useMemo(() => {
    return smells.filter((s) => {
      const matchSev = severityFilter === 'ALL' || s.severity === severityFilter
      const matchType = typeFilter === 'ALL' || s.type === typeFilter
      return matchSev && matchType
    })
  }, [smells, severityFilter, typeFilter])

  // Compute metrics from current graph nodes
  const metrics = useMemo(() => {
    const nodes = result?.graph.nodes ?? []
    const totalLoc = nodes.reduce((acc, n) => acc + (n.loc || 0), 0)
    const avgComplexity = nodes.length
      ? (nodes.reduce((acc, n) => acc + (n.cyclomatic_complexity || 0), 0) / nodes.length).toFixed(1)
      : '0'
    const peakComplexity = nodes.reduce((max, n) => Math.max(max, n.cyclomatic_complexity || 0), 0)
    const godClasses = smells.filter((s) => s.type === 'god_module' || s.type === 'large_class').length
    const cycles = (result?.graph.edges ?? []).filter((e) => e.is_cycle).length || smells.filter((s) => s.type === 'circular_import').length

    // Layer breakdown
    const layers: Record<string, number> = {}
    nodes.forEach((n) => {
      const l = n.layer || 'Default'
      layers[l] = (layers[l] || 0) + 1
    })

    return { totalLoc, avgComplexity, peakComplexity, godClasses, cycles, layers, totalNodes: nodes.length }
  }, [result, smells])

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
          Architecture Metrics & Code Smells
        </h1>
        <p className="text-xs sm:text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          Detailed structural health metrics, cyclomatic complexity distributions, and architectural debt analysis.
        </p>
      </div>

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-card p-5 rounded-2xl flex flex-col justify-between" data-testid="metric-card-loc">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
                Total Codebase LOC
              </span>
              <FileCode size={18} style={{ color: 'var(--accent)' }} />
            </div>
            <div className="text-2xl font-bold mt-2 font-mono" style={{ color: 'var(--text-primary)' }}>
              {metrics.totalLoc.toLocaleString()}
            </div>
            <p className="text-[11px] mt-1 text-muted">Across {metrics.totalNodes} analyzed modules</p>
          </div>
          <AIExplainPanel
            label="Explain LOC"
            className="mt-3 pt-2 border-t border-white/5"
            fetch={async () => {
              try {
                const res = await aiApi.explainMetric(
                  'Lines of Code',
                  metrics.totalLoc,
                  result?.repo_id,
                  { total_nodes: metrics.totalNodes, language: result?.language }
                )
                return { explanation: res.explanation ?? 'AI unavailable' }
              } catch {
                return null
              }
            }}
            enabled={!!result}
          />
        </div>

        <div className="glass-card p-5 rounded-2xl flex flex-col justify-between" data-testid="metric-card-complexity">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
                Avg. Complexity
              </span>
              <Activity size={18} style={{ color: 'var(--accent)' }} />
            </div>
            <div className="text-2xl font-bold mt-2 font-mono" style={{ color: 'var(--text-primary)' }}>
              {metrics.avgComplexity}
            </div>
            <p className="text-[11px] mt-1 text-muted">Peak cyclomatic score: {metrics.peakComplexity}</p>
          </div>
          <AIExplainPanel
            label="Explain Complexity"
            className="mt-3 pt-2 border-t border-white/5"
            fetch={async () => {
              try {
                const res = await aiApi.explainMetric(
                  'Cyclomatic Complexity',
                  parseFloat(metrics.avgComplexity) || 0,
                  result?.repo_id,
                  { peak_complexity: metrics.peakComplexity, total_nodes: metrics.totalNodes }
                )
                return { explanation: res.explanation ?? 'AI unavailable' }
              } catch {
                return null
              }
            }}
            enabled={!!result}
          />
        </div>

        <div className="glass-card p-5 rounded-2xl flex flex-col justify-between" data-testid="metric-card-god-classes">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
                God Classes
              </span>
              <Flame size={18} style={{ color: metrics.godClasses > 0 ? 'var(--danger)' : 'var(--text-muted)' }} />
            </div>
            <div
              className="text-2xl font-bold mt-2 font-mono"
              style={{ color: metrics.godClasses > 0 ? 'var(--danger)' : 'var(--text-primary)' }}
            >
              {metrics.godClasses}
            </div>
            <p className="text-[11px] mt-1 text-muted">High LOC & fan-in hotspots</p>
          </div>
          <AIExplainPanel
            label="Explain God Classes"
            className="mt-3 pt-2 border-t border-white/5"
            fetch={async () => {
              try {
                const res = await aiApi.explainMetric(
                  'God Modules & Large Classes',
                  metrics.godClasses,
                  result?.repo_id,
                  { total_nodes: metrics.totalNodes }
                )
                return { explanation: res.explanation ?? 'AI unavailable' }
              } catch {
                return null
              }
            }}
            enabled={!!result}
          />
        </div>

        <div className="glass-card p-5 rounded-2xl flex flex-col justify-between" data-testid="metric-card-cycles">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
                Cyclic Loops
              </span>
              <AlertTriangle size={18} style={{ color: metrics.cycles > 0 ? 'var(--danger)' : 'var(--accent)' }} />
            </div>
            <div
              className="text-2xl font-bold mt-2 font-mono"
              style={{ color: metrics.cycles > 0 ? 'var(--danger)' : 'var(--text-primary)' }}
            >
              {metrics.cycles}
            </div>
            <p className="text-[11px] mt-1 text-muted">Mutual dependency deadlocks</p>
          </div>
          <AIExplainPanel
            label="Explain Cycles"
            className="mt-3 pt-2 border-t border-white/5"
            fetch={async () => {
              try {
                const res = await aiApi.explainMetric(
                  'Cyclic Dependency Loops',
                  metrics.cycles,
                  result?.repo_id,
                  { total_nodes: metrics.totalNodes }
                )
                return { explanation: res.explanation ?? 'AI unavailable' }
              } catch {
                return null
              }
            }}
            enabled={!!result}
          />
        </div>
      </div>

      {/* Layer Distribution */}
      <div className="glass-card p-6 rounded-2xl">
        <h3 className="text-sm font-bold flex items-center gap-2 mb-4" style={{ color: 'var(--text-primary)' }}>
          <Layers size={16} style={{ color: 'var(--accent)' }} /> Architectural Layer Distribution
        </h3>
        <div className="space-y-3">
          {Object.entries(metrics.layers).map(([layer, count]) => {
            const percent = metrics.totalNodes ? Math.round((count / metrics.totalNodes) * 100) : 0
            return (
              <div key={layer}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {layer}
                  </span>
                  <span className="font-mono text-muted">
                    {count} components ({percent}%)
                  </span>
                </div>
                <div className="w-full h-2 rounded-full overflow-hidden bg-white/5">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${percent}%` }}
                    transition={{ duration: 0.6 }}
                    className="h-full rounded-full"
                    style={{ background: 'var(--accent)' }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Smells & Anti-Patterns Table */}
      <div className="glass-card p-6 rounded-2xl">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-5">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
                Detected Architecture Smells ({filteredSmells.length})
              </h3>
              <AIBadge label="AI-generated" size="xs" />
            </div>
            <p className="text-xs mt-0.5 text-muted">
              Anti-patterns, boundary violations, and modularity degradation
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap text-xs">
            {/* Filter Severity */}
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border bg-transparent font-medium"
              style={{ borderColor: 'var(--surface-border)', color: 'var(--text-primary)' }}
            >
              <option value="ALL">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            {/* Filter Type */}
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border bg-transparent font-medium"
              style={{ borderColor: 'var(--surface-border)', color: 'var(--text-primary)' }}
            >
              <option value="ALL">All Smell Types</option>
              <option value="god_module">God Module</option>
              <option value="circular_import">Circular Import</option>
              <option value="large_class">Large Class</option>
              <option value="dead_code">Dead Code</option>
              <option value="deep_inheritance">Deep Inheritance</option>
              <option value="feature_envy">Feature Envy</option>
              <option value="long_parameter_list">Long Parameter List</option>
              <option value="duplicate_code">Duplicate Code</option>
              <option value="missing_type_hints">Missing Type Hints</option>
            </select>
          </div>
        </div>

        {/* Smells List */}
        {filteredSmells.length === 0 ? (
          <div className="text-center py-10 text-muted text-xs">
            <CheckCircle2 size={32} className="mx-auto mb-2 opacity-50" style={{ color: 'var(--accent)' }} />
            No architectural smells found matching the filter criteria.
          </div>
        ) : (
          <div className="space-y-3">
            {filteredSmells.map((smell, index) => {
              const isCrit = smell.severity === 'critical'
              const isHigh = smell.severity === 'high'

              return (
                <div
                  key={index}
                  className="p-4 rounded-xl border transition-colors duration-150 hover:border-white/20"
                  style={{
                    background: 'var(--surface)',
                    borderColor: isCrit ? 'rgba(239, 68, 68, 0.4)' : 'var(--surface-border)',
                  }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`badge text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                            isCrit ? 'badge-danger' : isHigh ? 'badge-warning' : 'badge-accent'
                          }`}
                        >
                          {smell.severity}
                        </span>
                        <span className="text-xs font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>
                          {smell.type.replace('_', ' ').toUpperCase()}
                        </span>
                      </div>
                      <p className="text-xs text-muted font-mono">{smell.file}</p>
                    </div>

                    <a
                      href="/refactor"
                      className="flex items-center gap-1 text-[11px] font-bold px-2 py-1 rounded-md transition-colors text-[var(--accent-text)] dark:text-[#CCFF00]"
                      style={{ background: 'var(--surface-border)' }}
                    >
                      Plan Refactor <ArrowUpRight size={12} />
                    </a>
                  </div>

                  <p className="text-xs mt-2.5 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                    {smell.description}
                  </p>

                  <AIExplainPanel
                    label="Explain Smell & Fix"
                    className="mt-3 pt-2 border-t border-white/5"
                    fetch={async () => {
                      try {
                        const res = await aiApi.explainSmell(
                          smell as unknown as Record<string, unknown>,
                          { repo_id: result?.repo_id, language: result?.language }
                        )
                        return {
                          explanation: res.why_it_matters ?? 'AI unavailable',
                          fix: res.fix_outline ? `Fix Outline: ${res.fix_outline}` : undefined,
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
    </div>
  )
}
