import { useState } from 'react'
import { Info, Sparkles, AlertCircle, RefreshCw } from 'lucide-react'
import type { GraphNode, GraphEdge } from '../../types'
import { aiApi } from '../../api/client'

interface DSMProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  loading?: boolean
  error?: string | null
}

export function DependencyStructureMatrix({ nodes, edges, loading, error }: DSMProps) {
  const [hoveredCell, setHoveredCell] = useState<{ row: number; col: number } | null>(null)
  const [focusedCell, setFocusedCell] = useState<{ row: number; col: number } | null>(null)
  const [aiExplanation, setAiExplanation] = useState<string | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiIsGenerated, setAiIsGenerated] = useState(false)

  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl flex flex-col items-center justify-center min-h-[340px] animate-pulse">
        <RefreshCw className="animate-spin text-accent mb-2" size={24} />
        <span className="text-xs text-muted">Calculating Dependency Structure Matrix...</span>
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
        <span className="text-xs">No components available to construct Dependency Structure Matrix</span>
      </div>
    )
  }

  // Cap nodes for readable matrix display (top 14 by degree / centrality)
  const sortedNodes = [...nodes]
    .sort((a, b) => ((b.in_degree ?? 0) + (b.out_degree ?? 0)) - ((a.in_degree ?? 0) + (a.out_degree ?? 0)))
    .slice(0, 14)

  const n = sortedNodes.length
  const idMap = new Map(sortedNodes.map((node, i) => [node.id, i]))

  // Matrix calculation
  const matrix: number[][] = Array.from({ length: n }, () => Array(n).fill(0))
  const cycleMatrix: boolean[][] = Array.from({ length: n }, () => Array(n).fill(false))

  edges.forEach((e) => {
    const sId = typeof e.source === 'string' ? e.source : (e.source as any)?.id
    const tId = typeof e.target === 'string' ? e.target : (e.target as any)?.id
    if (idMap.has(sId) && idMap.has(tId)) {
      const i = idMap.get(sId)!
      const j = idMap.get(tId)!
      matrix[i][j] += 1
      if (e.is_cycle) {
        cycleMatrix[i][j] = true
      }
    }
  })

  // Check mutual cyclic dependencies
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      if (matrix[i][j] > 0 && matrix[j][i] > 0) {
        cycleMatrix[i][j] = true
        cycleMatrix[j][i] = true
      }
    }
  }

  const handleAiExplain = async () => {
    setAiLoading(true)
    try {
      const cycleCount = cycleMatrix.flat().filter(Boolean).length / 2
      const res = await aiApi.explainMetric(
        'Dependency Structure Matrix (DSM)',
        cycleCount,
        undefined,
        {
          nodes_count: n,
          total_dependencies: edges.length,
          cycles_detected: cycleCount,
        }
      )
      setAiExplanation(res.explanation)
      setAiIsGenerated(Boolean(res.is_ai_generated))
    } catch {
      setAiExplanation(
        'Dependency Structure Matrix tracks pairwise coupling. Entries below the diagonal indicate forward flow; entries above or symmetric indicate feedback loops and circular architectural cycles.'
      )
      setAiIsGenerated(false)
    } finally {
      setAiLoading(false)
    }
  }

  const activeCell = focusedCell || hoveredCell

  return (
    <div className="glass-card p-6 rounded-2xl space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[var(--border)] dark:border-white/5 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold tracking-wide" style={{ color: 'var(--text-primary)' }}>
              Dependency Structure Matrix (DSM)
            </h3>
            <span className="badge badge-accent text-[9px] uppercase font-bold">Coupling Grid</span>
          </div>
          <p className="text-xs text-muted mt-0.5">
            Row module depends on column module. Red highlights mark circular feedback loops.
          </p>
        </div>

        <button
          onClick={handleAiExplain}
          disabled={aiLoading}
          aria-label="AI Explain Dependency Structure Matrix"
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

      {/* Matrix Display */}
      <div className="overflow-x-auto pt-2" role="region" aria-label="DSM Grid Container">
        <div
          role="grid"
          aria-label="Dependency Structure Matrix Grid"
          className="inline-block min-w-full font-mono text-xs select-none"
        >
          {/* Column Header indices */}
          <div className="flex items-center mb-1">
            <div className="w-36 flex-shrink-0 text-right pr-3 text-[10px] font-bold text-muted">
              DEP →
            </div>
            {sortedNodes.map((_, colIdx) => (
              <div
                key={colIdx}
                className="w-7 h-6 flex items-center justify-center font-bold text-[10px] text-muted flex-shrink-0"
              >
                {colIdx + 1}
              </div>
            ))}
          </div>

          {/* Matrix Rows */}
          {sortedNodes.map((rowNode, rIdx) => {
            const rowLabel = rowNode.label || rowNode.id.split('.').pop() || rowNode.id
            return (
              <div key={rowNode.id} className="flex items-center py-0.5">
                {/* Row Header */}
                <div
                  className="w-36 flex-shrink-0 text-right pr-3 text-[11px] font-medium truncate"
                  style={{ color: 'var(--text-primary)' }}
                  title={`${rIdx + 1}. ${rowNode.id}`}
                >
                  <span className="text-muted text-[10px] mr-1.5">{rIdx + 1}.</span>
                  {rowLabel}
                </div>

                {/* Cells */}
                {sortedNodes.map((colNode, cIdx) => {
                  const isSelf = rIdx === cIdx
                  const count = matrix[rIdx][cIdx]
                  const isCycle = cycleMatrix[rIdx][cIdx]

                  let bgClass = 'bg-surface-2/40 dark:bg-white/[0.02] border border-[var(--border)]/40 dark:border-white/5'
                  let textClass = 'text-muted/30'

                  if (isSelf) {
                    bgClass = 'bg-slate-300 dark:bg-slate-800 border border-slate-400 dark:border-slate-700'
                    textClass = 'text-slate-500 font-bold'
                  } else if (isCycle) {
                    bgClass = 'bg-red-500/20 border border-red-500/50 shadow-[0_0_8px_rgba(239,68,68,0.25)]'
                    textClass = 'text-red-400 font-black'
                  } else if (count > 0) {
                    bgClass = 'bg-blue-500/15 border border-blue-500/40'
                    textClass = 'text-blue-400 font-bold'
                  }

                  const cellLabel = isSelf
                    ? 'Self'
                    : count > 0
                    ? `${rowLabel} calls ${colNode.label || colNode.id} (${count}x)${isCycle ? ' - Cyclic' : ''}`
                    : 'No dependency'

                  return (
                    <button
                      key={colNode.id}
                      role="gridcell"
                      aria-label={`Row ${rIdx + 1} Col ${cIdx + 1}: ${cellLabel}`}
                      tabIndex={0}
                      onMouseEnter={() => setHoveredCell({ row: rIdx, col: cIdx })}
                      onMouseLeave={() => setHoveredCell(null)}
                      onFocus={() => setFocusedCell({ row: rIdx, col: cIdx })}
                      onBlur={() => setFocusedCell(null)}
                      className={`w-7 h-7 m-0.5 rounded flex items-center justify-center text-[10px] transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-accent ${bgClass}`}
                    >
                      <span className={textClass}>{isSelf ? '•' : count > 0 ? count : ''}</span>
                    </button>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>

      {/* Active Cell Inspector / Tooltip */}
      {activeCell && (
        <div className="p-2.5 rounded-xl bg-surface-2 dark:bg-black/30 border border-[var(--border)] dark:border-white/10 text-xs flex items-center justify-between font-mono">
          <div className="flex items-center gap-2">
            <span className="text-muted">Selected Cell:</span>
            <span className="font-bold text-primary">
              [{activeCell.row + 1}, {activeCell.col + 1}]{' '}
              {sortedNodes[activeCell.row]?.label || sortedNodes[activeCell.row]?.id} →{' '}
              {sortedNodes[activeCell.col]?.label || sortedNodes[activeCell.col]?.id}
            </span>
          </div>
          <div>
            {activeCell.row === activeCell.col ? (
              <span className="text-muted">Diagonal Identity</span>
            ) : matrix[activeCell.row][activeCell.col] > 0 ? (
              <span
                className={`font-bold ${
                  cycleMatrix[activeCell.row][activeCell.col] ? 'text-red-400' : 'text-blue-400'
                }`}
              >
                {matrix[activeCell.row][activeCell.col]} Dependency Call(s){' '}
                {cycleMatrix[activeCell.row][activeCell.col] && '⚠️ Circular Loop'}
              </span>
            ) : (
              <span className="text-muted">Zero Calls</span>
            )}
          </div>
        </div>
      )}

      {/* "How to read this" caption */}
      <div className="text-[11px] text-muted space-y-1 bg-surface-2/40 dark:bg-white/[0.02] p-3 rounded-xl border border-[var(--border)] dark:border-white/5">
        <span className="font-bold text-primary flex items-center gap-1">
          <Info size={12} /> How to read this matrix:
        </span>
        <p>
          Each row represents a source component, and columns represent targets. Numbers in cells indicate the coupling call count. Red glowing cells highlight cyclic dependency loops where two components transitively or mutually depend on each other.
        </p>
      </div>
    </div>
  )
}
