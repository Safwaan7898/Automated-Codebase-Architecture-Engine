import { useState, useMemo } from 'react'
import { Info, Sparkles, AlertCircle, RefreshCw, Flame, Download } from 'lucide-react'
import type { GraphNode } from '../../types'
import { AIBadge, AIFallback } from '../ui/AILabel'
import { aiApi } from '../../api/client'

interface HotspotBubbleChartProps {
  nodes: GraphNode[]
  loading?: boolean
  error?: string | null
}

interface HotspotPoint {
  id: string
  label: string
  complexity: number
  risk: number
  loc: number
  radius: number
  x: number
  y: number
  color: string
}

export function HotspotBubbleChart({ nodes, loading, error }: HotspotBubbleChartProps) {
  const [selectedPoint, setSelectedPoint] = useState<HotspotPoint | null>(null)
  const [hoveredPoint, setHoveredPoint] = useState<HotspotPoint | null>(null)
  const [aiExplanation, setAiExplanation] = useState<string | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiIsGenerated, setAiIsGenerated] = useState(false)

  const points: HotspotPoint[] = useMemo(() => {
    if (!nodes || nodes.length === 0) return []

    return nodes.map((n) => {
      const cc = Math.max(1, Number(n.metrics?.complexity || (n as any).complexity || n.cyclomatic_complexity || 5))
      const risk = Math.min(100, Math.max(0, Number(n.risk_score ?? (cc * 2.5 + (n.loc ? Math.min(n.loc / 20, 40) : 10)))))
      const loc = Math.max(20, n.loc || 80)
      const radius = Math.min(32, Math.max(7, Math.sqrt(loc) * 0.9))

      let color = '#10B981' // Green
      if (risk > 65 || cc > 20) {
        color = '#EF4444' // Red
      } else if (risk > 35 || cc > 10) {
        color = '#F59E0B' // Amber
      }

      // Normalized coordinates within 640x340 viewBox (padding: 40px)
      const x = 50 + Math.min(540, (cc / 40) * 520)
      const y = 300 - Math.min(260, (risk / 100) * 240)

      return {
        id: n.id,
        label: n.label || n.id.split('/').pop() || n.id,
        complexity: cc,
        risk: Math.round(risk),
        loc,
        radius,
        x,
        y,
        color,
      }
    })
  }, [nodes])

  const topHotspots = useMemo(() => {
    return [...points].sort((a, b) => b.risk * b.complexity - a.risk * a.complexity).slice(0, 5)
  }, [points])

  const handleAiExplain = async () => {
    setAiLoading(true)
    try {
      const res = await aiApi.explainMetric(
        'architectural_hotspots',
        topHotspots[0]?.risk || 50,
        undefined,
        {
          top_hotspot: topHotspots[0]?.id,
          avg_complexity: (points.reduce((a, b) => a + b.complexity, 0) / (points.length || 1)).toFixed(1),
          total_modules: points.length,
        }
      )
      setAiExplanation(res.explanation)
      setAiIsGenerated(true)
    } catch {
      setAiExplanation(
        'Deterministic analysis: Hotspots in the top-right quadrant combine high cyclomatic complexity with high change risk. Prioritize modular decoupling on the top 3 highlighted hotspots to reduce maintenance overhead and regression probability.'
      )
      setAiIsGenerated(false)
    } finally {
      setAiLoading(false)
    }
  }

  const handleExportSvg = () => {
    const svgEl = document.getElementById('hotspot-bubble-svg')
    if (!svgEl) return
    const svgData = new XMLSerializer().serializeToString(svgEl)
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'archlens-hotspot-bubble-chart.svg'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl flex flex-col items-center justify-center min-h-[360px] animate-pulse">
        <RefreshCw className="animate-spin text-accent mb-2" size={24} />
        <span className="text-xs text-muted">Calculating module hotspot risk distribution...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass-card p-6 rounded-2xl flex flex-col items-center justify-center min-h-[360px] text-red-400">
        <AlertCircle size={24} className="mb-2" />
        <span className="text-xs">{error}</span>
      </div>
    )
  }

  if (points.length === 0) {
    return (
      <div className="glass-card p-6 rounded-2xl flex flex-col items-center justify-center min-h-[360px] text-muted">
        <Info size={24} className="mb-2 opacity-50" />
        <span className="text-xs">No module data available for Hotspot Bubble Chart</span>
      </div>
    )
  }

  return (
    <div className="glass-card p-6 rounded-2xl border border-[var(--border)] dark:border-white/5 space-y-4">
      {/* Title & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Flame size={18} className="text-red-500" />
            <h2 className="text-sm font-bold tracking-tight text-[var(--text-primary)]">
              Architectural Hotspot Bubble Chart
            </h2>
            <AIBadge label="AI-generated" size="xs" />
          </div>
          <p className="text-xs text-muted mt-0.5">
            Quadrant analysis: Cyclomatic Complexity (X) vs Composite Risk Score (Y) with bubble size proportional to LOC.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExportSvg}
            className="px-2.5 py-1 text-xs rounded-lg border border-[var(--border)] dark:border-white/10 hover:border-accent text-muted hover:text-primary transition-colors flex items-center gap-1 cursor-pointer"
            title="Export chart as SVG for documentation and PDF reports"
          >
            <Download size={12} />
            <span>SVG</span>
          </button>

          <button
            onClick={handleAiExplain}
            disabled={aiLoading}
            className="px-3 py-1 text-xs font-semibold rounded-lg bg-lime-500/10 dark:bg-accent/10 border border-lime-600/30 dark:border-accent/30 text-lime-800 dark:text-accent hover:bg-lime-500/20 dark:hover:bg-accent/20 transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <Sparkles size={13} />
            <span>{aiLoading ? 'Explaining...' : 'AI Explain'}</span>
          </button>
        </div>
      </div>

      {/* AI Explanation Banner */}
      {aiExplanation && (
        <div className="p-3.5 rounded-xl bg-lime-500/5 dark:bg-accent/5 border border-lime-600/20 dark:border-accent/20 text-xs space-y-1 animate-fade-in">
          <div className="flex items-center justify-between">
            <span className="font-bold flex items-center gap-1.5 text-lime-800 dark:text-accent text-[11px]">
              <Sparkles size={13} /> Hotspot Synthesis
            </span>
            {aiIsGenerated ? (
              <AIBadge label="AI-generated" size="xs" />
            ) : (
              <AIFallback message="Deterministic synthesis" />
            )}
          </div>
          <p className="text-muted leading-relaxed">{aiExplanation}</p>
        </div>
      )}

      {/* SVG Canvas */}
      <div className="relative w-full overflow-x-auto bg-surface-2 dark:bg-black/30 rounded-xl p-4 border border-[var(--border)] dark:border-white/5">
        <svg
          id="hotspot-bubble-svg"
          viewBox="0 0 640 340"
          className="w-full h-auto min-w-[500px] select-none"
          role="img"
          aria-label="Hotspot Bubble Chart showing module complexity versus risk score"
        >
          {/* Quadrant shading for high risk */}
          <rect x="320" y="20" width="280" height="140" fill="rgba(239, 68, 68, 0.05)" rx="4" />
          <text x="590" y="36" textAnchor="end" className="text-[9px] fill-red-400 font-mono font-bold">
            HIGH-RISK CRITICAL HOTSPOTS
          </text>

          {/* Grid lines */}
          <line x1="50" y1="20" x2="50" y2="300" stroke="currentColor" strokeOpacity="0.15" />
          <line x1="50" y1="300" x2="600" y2="300" stroke="currentColor" strokeOpacity="0.15" />
          <line x1="320" y1="20" x2="320" y2="300" stroke="currentColor" strokeDasharray="3 3" strokeOpacity="0.1" />
          <line x1="50" y1="160" x2="600" y2="160" stroke="currentColor" strokeDasharray="3 3" strokeOpacity="0.1" />

          {/* Axis labels */}
          <text x="325" y="325" textAnchor="middle" className="text-[10px] fill-muted font-mono uppercase tracking-wider">
            Cyclomatic Complexity →
          </text>
          <text x="18" y="160" textAnchor="middle" transform="rotate(-90 18 160)" className="text-[10px] fill-muted font-mono uppercase tracking-wider">
            Risk Score (0 - 100) →
          </text>

          {/* Bubbles */}
          {points.map((p) => {
            const isHovered = hoveredPoint?.id === p.id
            const isSelected = selectedPoint?.id === p.id

            return (
              <g
                key={p.id}
                tabIndex={0}
                role="button"
                aria-label={`Module ${p.label}: Complexity ${p.complexity}, Risk ${p.risk}, Volume ${p.loc} LOC`}
                className="cursor-pointer focus:outline-none"
                onClick={() => setSelectedPoint(p)}
                onMouseEnter={() => setHoveredPoint(p)}
                onMouseLeave={() => setHoveredPoint(null)}
                onFocus={() => setHoveredPoint(p)}
                onBlur={() => setHoveredPoint(null)}
              >
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={p.radius}
                  fill={p.color}
                  fillOpacity={isSelected ? 0.85 : isHovered ? 0.75 : 0.45}
                  stroke={p.color}
                  strokeWidth={isSelected ? 2.5 : isHovered ? 2 : 1}
                  className="transition-all duration-150"
                />
                {p.radius > 16 && (
                  <text
                    x={p.x}
                    y={p.y + 3}
                    textAnchor="middle"
                    className="text-[9px] fill-white font-mono pointer-events-none select-none font-bold"
                  >
                    {p.complexity}
                  </text>
                )}
              </g>
            )
          })}
        </svg>

        {/* Hover / Selection Tooltip Box */}
        {(hoveredPoint || selectedPoint) && (
          <div className="mt-3 p-3 rounded-lg bg-surface-1 dark:bg-black/60 border border-[var(--border)] dark:border-white/10 text-xs font-mono flex items-center justify-between flex-wrap gap-2 animate-fade-in">
            <div>
              <span className="text-muted">Selected Component: </span>
              <strong className="text-primary">{(hoveredPoint || selectedPoint)!.label}</strong>
              <span className="text-muted text-[10px] ml-2 font-mono">({(hoveredPoint || selectedPoint)!.id})</span>
            </div>
            <div className="flex items-center gap-3">
              <span>Complexity: <strong className="text-amber-400">{(hoveredPoint || selectedPoint)!.complexity}</strong></span>
              <span>Risk: <strong className="text-red-400">{(hoveredPoint || selectedPoint)!.risk}/100</strong></span>
              <span>Volume: <strong className="text-primary">{(hoveredPoint || selectedPoint)!.loc.toLocaleString()} LOC</strong></span>
            </div>
          </div>
        )}
      </div>

      {/* "How to read this" Caption */}
      <div className="p-3.5 rounded-xl bg-surface-2 dark:bg-white/[0.02] border border-[var(--border)] dark:border-white/5 text-xs text-muted flex items-start gap-2.5">
        <Info size={16} className="text-accent shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <strong className="text-[var(--text-primary)]">How to read this chart:</strong> Modules positioned in the upper-right quadrant exhibit both excessive branch complexity and high change risk score. Larger bubbles denote greater lines of code (LOC). Prioritize refactoring on large red bubbles in the upper quadrant, as changes to these files propagate disproportionate blast radius across dependent subsystems.
        </div>
      </div>
    </div>
  )
}
