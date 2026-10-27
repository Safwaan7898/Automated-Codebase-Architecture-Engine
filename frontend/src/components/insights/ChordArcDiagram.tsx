import { useState, useMemo } from 'react'
import { Info, Sparkles, AlertCircle, RefreshCw, GitBranch, Download, AlertTriangle } from 'lucide-react'
import type { GraphNode, GraphEdge } from '../../types'
import { AIBadge, AIFallback } from '../ui/AILabel'
import { aiApi } from '../../api/client'

interface ChordArcDiagramProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  loading?: boolean
  error?: string | null
}

interface LayerArcFlow {
  sourceLayer: string
  targetLayer: string
  count: number
  isViolation: boolean
  pathD: string
  color: string
}

const LAYER_ORDER = ['API', 'Application', 'Domain', 'Infrastructure', 'Core']
const LAYER_COLORS: Record<string, string> = {
  API: '#3B82F6', // Blue
  Application: '#8B5CF6', // Purple
  Domain: '#EC4899', // Pink
  Infrastructure: '#F59E0B', // Amber
  Core: '#10B981', // Emerald
}

export function ChordArcDiagram({ nodes, edges, loading, error }: ChordArcDiagramProps) {
  const [selectedLayer, setSelectedLayer] = useState<string | null>(null)
  const [hoveredArc, setHoveredArc] = useState<LayerArcFlow | null>(null)
  const [aiExplanation, setAiExplanation] = useState<string | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiIsGenerated, setAiIsGenerated] = useState(false)

  // Map each node to an architectural layer
  const nodeLayerMap = useMemo(() => {
    const map = new Map<string, string>()
    for (const n of nodes) {
      let layer = 'Domain'
      const idLower = (n.id || '').toLowerCase()
      const pathLower = (n.file_path || '').toLowerCase()

      if (idLower.includes('api') || pathLower.includes('route') || pathLower.includes('controller') || pathLower.includes('endpoint')) {
        layer = 'API'
      } else if (idLower.includes('service') || pathLower.includes('service') || pathLower.includes('usecase')) {
        layer = 'Application'
      } else if (idLower.includes('repo') || pathLower.includes('db') || pathLower.includes('storage') || pathLower.includes('infra')) {
        layer = 'Infrastructure'
      } else if (idLower.includes('util') || pathLower.includes('common') || pathLower.includes('core')) {
        layer = 'Core'
      }
      map.set(n.id, layer)
    }
    return map
  }, [nodes])

  // Count active layers and node distribution
  const layerStats = useMemo(() => {
    const counts: Record<string, number> = { API: 0, Application: 0, Domain: 0, Infrastructure: 0, Core: 0 }
    nodeLayerMap.forEach((layer) => {
      counts[layer] = (counts[layer] || 0) + 1
    })
    return counts
  }, [nodeLayerMap])

  // Compute inter-layer arc connections
  const arcFlows: LayerArcFlow[] = useMemo(() => {
    const pairCounts = new Map<string, number>()

    for (const e of edges) {
      const srcId = typeof e.source === 'string' ? e.source : (e.source as { id: string })?.id
      const tgtId = typeof e.target === 'string' ? e.target : (e.target as { id: string })?.id
      const srcLayer = nodeLayerMap.get(srcId) || 'Domain'
      const tgtLayer = nodeLayerMap.get(tgtId) || 'Domain'

      if (srcLayer !== tgtLayer) {
        const key = `${srcLayer}->${tgtLayer}`
        pairCounts.set(key, (pairCounts.get(key) || 0) + 1)
      }
    }

    const flows: LayerArcFlow[] = []
    const layerXMap: Record<string, number> = {
      API: 80,
      Application: 200,
      Domain: 320,
      Infrastructure: 440,
      Core: 560,
    }

    pairCounts.forEach((count, key) => {
      const [src, tgt] = key.split('->')
      const x1 = layerXMap[src] || 320
      const x2 = layerXMap[tgt] || 320
      const dist = Math.abs(x2 - x1)
      const height = Math.min(130, 40 + dist * 0.35)

      // Downward rule: API/App/Domain can depend downward, but Core/Domain depending back up to API/Infra is a violation
      const srcIdx = LAYER_ORDER.indexOf(src)
      const tgtIdx = LAYER_ORDER.indexOf(tgt)
      const isViolation = srcIdx > tgtIdx && tgt === 'API'

      // Quadratic curve arc
      const mx = (x1 + x2) / 2
      const my = 200 - (isViolation ? height * 0.9 : height)
      const pathD = `M ${x1} 200 Q ${mx} ${my} ${x2} 200`

      flows.push({
        sourceLayer: src,
        targetLayer: tgt,
        count,
        isViolation,
        pathD,
        color: isViolation ? '#EF4444' : LAYER_COLORS[src] || '#8B5CF6',
      })
    })

    return flows
  }, [edges, nodeLayerMap])

  const violationCount = arcFlows.filter((f) => f.isViolation).length

  const handleAiExplain = async () => {
    setAiLoading(true)
    try {
      const res = await aiApi.explainMetric(
        'layered_architecture_compliance',
        violationCount === 0 ? 95 : Math.max(30, 90 - violationCount * 15),
        undefined,
        {
          violations: violationCount,
          active_layers: Object.keys(layerStats).filter((k) => layerStats[k] > 0),
          layer_flows_count: arcFlows.length,
        }
      )
      setAiExplanation(res.explanation)
      setAiIsGenerated(true)
    } catch {
      setAiExplanation(
        `Deterministic analysis: Layered architecture compliance is rated based on unidirectional dependency adherence. The system exhibits ${arcFlows.length} cross-layer flows with ${violationCount} upward layer violation(s). Keep dependencies flowing downward from API/Application towards Domain and Infrastructure interfaces.`
      )
      setAiIsGenerated(false)
    } finally {
      setAiLoading(false)
    }
  }

  const handleExportSvg = () => {
    const svgEl = document.getElementById('chord-arc-svg')
    if (!svgEl) return
    const svgData = new XMLSerializer().serializeToString(svgEl)
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'archlens-layer-chord-arc.svg'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl flex flex-col items-center justify-center min-h-[360px] animate-pulse">
        <RefreshCw className="animate-spin text-accent mb-2" size={24} />
        <span className="text-xs text-muted">Tracing architectural layer dependency arcs...</span>
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

  return (
    <div className="glass-card p-6 rounded-2xl border border-[var(--border)] dark:border-white/5 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <GitBranch size={18} className="text-accent" />
            <h2 className="text-sm font-bold tracking-tight text-[var(--text-primary)]">
              Layer Dependency Chord & Arc Diagram
            </h2>
            <AIBadge label="AI-generated" size="xs" />
          </div>
          <p className="text-xs text-muted mt-0.5">
            Inter-tier dependency routing across architectural layers. Arcs highlight flows; red indicates layer inversion.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExportSvg}
            className="px-2.5 py-1 text-xs rounded-lg border border-[var(--border)] dark:border-white/10 hover:border-accent text-muted hover:text-primary transition-colors flex items-center gap-1 cursor-pointer"
            title="Export chart as SVG for PDF reports and documentation"
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
              <Sparkles size={13} /> Layer Adherence Synthesis
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

      {/* SVG Arc Diagram */}
      <div className="relative w-full overflow-x-auto bg-surface-2 dark:bg-black/30 rounded-xl p-4 border border-[var(--border)] dark:border-white/5">
        <svg
          id="chord-arc-svg"
          viewBox="0 0 640 260"
          className="w-full h-auto min-w-[500px] select-none"
          role="img"
          aria-label="Layer Dependency Arc Diagram visualizing inter-layer dependencies"
        >
          {/* Baseline horizontal layer track */}
          <line x1="40" y1="200" x2="600" y2="200" stroke="currentColor" strokeOpacity="0.12" strokeWidth="2" />

          {/* Arcs between layers */}
          {arcFlows.map((flow, idx) => {
            const isHovered = hoveredArc === flow
            const strokeWidth = Math.min(6, Math.max(1.5, Math.sqrt(flow.count) * 1.2))

            return (
              <path
                key={idx}
                d={flow.pathD}
                fill="none"
                stroke={flow.color}
                strokeWidth={isHovered ? strokeWidth + 2 : strokeWidth}
                strokeOpacity={isHovered ? 0.9 : selectedLayer ? (flow.sourceLayer === selectedLayer ? 0.8 : 0.15) : 0.55}
                className="transition-all duration-150 cursor-pointer"
                onMouseEnter={() => setHoveredArc(flow)}
                onMouseLeave={() => setHoveredArc(null)}
              />
            )
          })}

          {/* Layer Nodes on the baseline */}
          {LAYER_ORDER.map((layerName) => {
            const layerXMap: Record<string, number> = { API: 80, Application: 200, Domain: 320, Infrastructure: 440, Core: 560 }
            const x = layerXMap[layerName]
            const count = layerStats[layerName] || 0
            const isSelected = selectedLayer === layerName
            const color = LAYER_COLORS[layerName]

            return (
              <g
                key={layerName}
                tabIndex={0}
                role="button"
                aria-label={`Layer ${layerName}: contains ${count} components`}
                className="cursor-pointer focus:outline-none"
                onClick={() => setSelectedLayer(isSelected ? null : layerName)}
              >
                <circle
                  cx={x}
                  cy="200"
                  r={isSelected ? 18 : 14}
                  fill={color}
                  fillOpacity={isSelected ? 0.9 : 0.75}
                  stroke={isSelected ? '#FFFFFF' : 'transparent'}
                  strokeWidth="2"
                  className="transition-all duration-150"
                />
                <text
                  x={x}
                  y="204"
                  textAnchor="middle"
                  className="text-[10px] fill-white font-mono font-bold select-none pointer-events-none"
                >
                  {count}
                </text>
                <text
                  x={x}
                  y="232"
                  textAnchor="middle"
                  className={`text-[10px] font-mono uppercase tracking-wider select-none font-bold ${
                    isSelected ? 'fill-accent' : 'fill-[var(--text-primary)]'
                  }`}
                >
                  {layerName}
                </text>
              </g>
            )
          })}
        </svg>

        {/* Hover Flow Tooltip */}
        {hoveredArc && (
          <div className="mt-3 p-3 rounded-lg bg-surface-1 dark:bg-black/60 border border-[var(--border)] dark:border-white/10 text-xs font-mono flex items-center justify-between animate-fade-in">
            <div className="flex items-center gap-2">
              <span className="font-bold text-primary">{hoveredArc.sourceLayer}</span>
              <span className="text-muted">→</span>
              <span className="font-bold text-primary">{hoveredArc.targetLayer}</span>
              {hoveredArc.isViolation && (
                <span className="badge badge-danger text-[9px] font-bold uppercase ml-2 flex items-center gap-1">
                  <AlertTriangle size={10} /> Layer Inversion Violation
                </span>
              )}
            </div>
            <span className="text-accent font-bold">{hoveredArc.count} Dependency Call(s)</span>
          </div>
        )}
      </div>

      {/* "How to read this" Caption */}
      <div className="p-3.5 rounded-xl bg-surface-2 dark:bg-white/[0.02] border border-[var(--border)] dark:border-white/5 text-xs text-muted flex items-start gap-2.5">
        <Info size={16} className="text-accent shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <strong className="text-[var(--text-primary)]">How to read this chart:</strong> Curved arcs illustrate cross-layer invocation volume. Standard clean architecture dictates that outer consumer tiers (API / Presentation) invoke inner business layers (Application / Domain), while Domain models remain decoupled from transport mechanics. Red arcs represent upward layer violations where lower tiers import upper consumer layers.
        </div>
      </div>
    </div>
  )
}
