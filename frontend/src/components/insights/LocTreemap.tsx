import { useState } from 'react'
import { Info, Sparkles, AlertCircle, RefreshCw, Layers } from 'lucide-react'
import type { GraphNode } from '../../types'
import { aiApi } from '../../api/client'

interface LocTreemapProps {
  nodes: GraphNode[]
  loading?: boolean
  error?: string | null
}

export function LocTreemap({ nodes, loading, error }: LocTreemapProps) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [aiExplanation, setAiExplanation] = useState<string | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiIsGenerated, setAiIsGenerated] = useState(false)

  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl flex flex-col items-center justify-center min-h-[340px] animate-pulse">
        <RefreshCw className="animate-spin text-accent mb-2" size={24} />
        <span className="text-xs text-muted">Computing code volume & complexity hierarchy...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass-card p-6 rounded-2xl flex flex-col items-center justify-center min-h-[340px] text-red-400">
        <AlertCircle size={24} className="mb-2" />
        <span className="text-xs">{error}</span>
      </div>
    )
  }

  if (!nodes || nodes.length === 0) {
    return (
      <div className="glass-card p-6 rounded-2xl flex flex-col items-center justify-center min-h-[340px] text-muted">
        <Info size={24} className="mb-2 opacity-50" />
        <span className="text-xs">No component modules available for LOC Treemap</span>
      </div>
    )
  }

  // Sort nodes by LOC (descending)
  const sorted = [...nodes]
    .map((n) => ({
      ...n,
      effectiveLoc: Math.max(10, n.loc || 50),
      complexity: Number(n.metrics?.complexity || (n as any).complexity || 8),
    }))
    .sort((a, b) => b.effectiveLoc - a.effectiveLoc)
    .slice(0, 16)

  const totalLoc = sorted.reduce((acc, curr) => acc + curr.effectiveLoc, 0) || 1

  const handleAiExplain = async () => {
    setAiLoading(true)
    try {
      const avgComplexity =
        sorted.reduce((acc, curr) => acc + curr.complexity, 0) / Math.max(1, sorted.length)
      const res = await aiApi.explainMetric(
        'Code Volume & Cyclomatic Complexity Treemap',
        Number(avgComplexity.toFixed(1)),
        undefined,
        {
          total_loc: totalLoc,
          modules_analyzed: sorted.length,
          highest_loc_module: sorted[0]?.label || sorted[0]?.id,
          max_complexity: Math.max(...sorted.map((s) => s.complexity)),
        }
      )
      setAiExplanation(res.explanation)
      setAiIsGenerated(Boolean(res.is_ai_generated))
    } catch {
      setAiExplanation(
        'Treemap partitions codebase surface area by volume (Lines of Code). High area combined with red/amber hue signifies god-classes and hotspot modules that carry disproportionate maintainability risk.'
      )
      setAiIsGenerated(false)
    } finally {
      setAiLoading(false)
    }
  }

  return (
    <div className="glass-card p-6 rounded-2xl space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[var(--border)] dark:border-white/5 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold tracking-wide" style={{ color: 'var(--text-primary)' }}>
              Hierarchical LOC Treemap
            </h3>
            <span className="badge badge-accent text-[9px] uppercase font-bold">Volume × Complexity</span>
          </div>
          <p className="text-xs text-muted mt-0.5">
            Tile size scales with Lines of Code (LOC); color represents Cyclomatic Complexity (CC).
          </p>
        </div>

        <button
          onClick={handleAiExplain}
          disabled={aiLoading}
          aria-label="AI Explain Code Volume Treemap"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-accent/10 border border-accent/30 text-accent hover:bg-accent/20 transition-colors"
        >
          <Sparkles size={13} className={aiLoading ? 'animate-spin' : ''} />
          <span>{aiLoading ? 'Analyzing...' : 'AI Explain'}</span>
        </button>
      </div>

      {/* AI Explanation Banner */}
      {aiExplanation && (
        <div className="p-3 rounded-xl bg-surface-2 dark:bg-white/[0.04] border border-[var(--border)] dark:border-white/10 text-xs space-y-1">
          <div className="flex items-center justify-between">
            <span className="font-bold flex items-center gap-1 text-accent">
              <Sparkles size={12} /> Architectural Insight
            </span>
            <span className="text-[10px] text-muted font-mono">
              {aiIsGenerated ? 'AI-generated' : 'Deterministic fallback'}
            </span>
          </div>
          <p className="text-muted leading-relaxed">{aiExplanation}</p>
        </div>
      )}

      {/* Treemap Mosaic Grid */}
      <div
        className="grid grid-cols-12 gap-1.5 min-h-[260px] p-2 bg-surface-2/40 dark:bg-black/30 rounded-xl border border-[var(--border)] dark:border-white/5"
        role="region"
        aria-label="LOC Treemap Visualization"
      >
        {sorted.map((node, idx) => {
          const pct = Math.max(2, Math.round((node.effectiveLoc / totalLoc) * 100))
          // Distribute columns dynamically based on relative weight
          let colSpan = 'col-span-3'
          if (idx === 0) colSpan = 'col-span-6 row-span-2'
          else if (idx === 1) colSpan = 'col-span-6'
          else if (idx === 2) colSpan = 'col-span-3'
          else if (idx === 3) colSpan = 'col-span-3'
          else if (pct >= 8) colSpan = 'col-span-4'

          const cc = node.complexity
          let bgStyle = {
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            borderColor: 'rgba(16, 185, 129, 0.4)',
            color: '#10b981',
          }
          if (cc >= 25) {
            bgStyle = {
              backgroundColor: 'rgba(239, 68, 68, 0.18)',
              borderColor: 'rgba(239, 68, 68, 0.5)',
              color: '#ef4444',
            }
          } else if (cc >= 12) {
            bgStyle = {
              backgroundColor: 'rgba(245, 158, 11, 0.18)',
              borderColor: 'rgba(245, 158, 11, 0.5)',
              color: '#f59e0b',
            }
          }

          const isSelected = selectedNode?.id === node.id

          return (
            <button
              key={node.id}
              onClick={() => setSelectedNode(node)}
              onFocus={() => setSelectedNode(node)}
              aria-label={`Module ${node.label || node.id}: ${node.effectiveLoc} lines of code, Cyclomatic complexity ${cc}`}
              className={`${colSpan} p-3 rounded-lg border flex flex-col justify-between text-left transition-all duration-150 relative overflow-hidden focus:outline-none focus:ring-2 focus:ring-accent ${
                isSelected ? 'ring-2 ring-accent scale-[0.99]' : 'hover:scale-[1.01]'
              }`}
              style={{
                backgroundColor: bgStyle.backgroundColor,
                borderColor: isSelected ? 'var(--accent)' : bgStyle.borderColor,
              }}
            >
              <div>
                <div className="flex items-center justify-between gap-1">
                  <span className="font-mono text-xs font-bold truncate text-primary">
                    {node.label || node.id.split('.').pop()}
                  </span>
                  <span className="text-[10px] font-mono font-black" style={{ color: bgStyle.color }}>
                    CC:{cc}
                  </span>
                </div>
                <div className="text-[10px] text-muted truncate mt-0.5">{node.layer || 'Domain'}</div>
              </div>

              <div className="flex items-center justify-between text-[10px] font-mono mt-2 pt-1 border-t border-[var(--border)]/30 dark:border-white/5">
                <span className="text-muted">{node.effectiveLoc.toLocaleString()} LOC</span>
                <span className="font-semibold text-primary">{pct}%</span>
              </div>
            </button>
          )
        })}
      </div>

      {/* Selected Node Inspector */}
      {selectedNode && (
        <div className="p-3 rounded-xl bg-surface-2 dark:bg-black/30 border border-[var(--border)] dark:border-white/10 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 font-mono">
          <div className="flex items-center gap-2">
            <Layers size={14} className="text-accent" />
            <span className="font-bold text-primary">{selectedNode.id}</span>
          </div>
          <div className="flex items-center gap-4 text-muted">
            <span>
              Volume: <b className="text-primary">{selectedNode.loc || 0} LOC</b>
            </span>
            <span>
              Complexity:{' '}
              <b
                className={
                  Number(selectedNode.metrics?.complexity ?? selectedNode.cyclomatic_complexity ?? 8) > 20
                    ? 'text-red-400'
                    : 'text-primary'
                }
              >
                {String(selectedNode.metrics?.complexity ?? selectedNode.cyclomatic_complexity ?? 8)}
              </b>
            </span>
            <span>
              Coupling:{' '}
              <b className="text-primary">
                In: {selectedNode.in_degree || 0} / Out: {selectedNode.out_degree || 0}
              </b>
            </span>
          </div>
        </div>
      )}

      {/* "How to read this" caption */}
      <div className="text-[11px] text-muted space-y-1 bg-surface-2/40 dark:bg-white/[0.02] p-3 rounded-xl border border-[var(--border)] dark:border-white/5">
        <span className="font-bold text-primary flex items-center gap-1">
          <Info size={12} /> How to read this treemap:
        </span>
        <p>
          Larger rectangles represent modules with greater code volume. Red rectangles signify high cyclomatic complexity (branching depth &gt; 25), amber indicates moderate risk (12-24), and green represents clean maintainable modules (&lt; 12).
        </p>
      </div>
    </div>
  )
}
