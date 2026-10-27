import { useState } from 'react'
import { Info, Sparkles, AlertCircle, RefreshCw, Crosshair } from 'lucide-react'
import type { GraphNode, GraphEdge } from '../../types'
import { aiApi } from '../../api/client'

interface PackageMetric {
  name: string
  instability: number // I = Ce / (Ca + Ce)
  abstractness: number // A = Na / Nc
  distance: number // D = |A + I - 1|
  ca: number // Afferent (in-degree)
  ce: number // Efferent (out-degree)
  nodeCount: number
}

interface ScatterProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  loading?: boolean
  error?: string | null
}

export function InstabilityAbstractnessScatter({ nodes, edges: _edges, loading, error }: ScatterProps) {
  const [hoveredPkg, setHoveredPkg] = useState<PackageMetric | null>(null)
  const [focusedPkg, setFocusedPkg] = useState<PackageMetric | null>(null)
  const [aiExplanation, setAiExplanation] = useState<string | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiIsGenerated, setAiIsGenerated] = useState(false)

  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl flex flex-col items-center justify-center min-h-[340px] animate-pulse">
        <RefreshCw className="animate-spin text-accent mb-2" size={24} />
        <span className="text-xs text-muted">Calculating package instability & abstractness metrics...</span>
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
        <span className="text-xs">No package clusters available for Instability vs Abstractness plot</span>
      </div>
    )
  }

  // Group nodes by package prefix
  const pkgGroups = new Map<string, { nodes: GraphNode[]; ca: number; ce: number }>()

  nodes.forEach((n) => {
    const pkg = n.id.includes('.') ? n.id.split('.').slice(0, 2).join('.') : n.id
    if (!pkgGroups.has(pkg)) {
      pkgGroups.set(pkg, { nodes: [], ca: 0, ce: 0 })
    }
    const grp = pkgGroups.get(pkg)!
    grp.nodes.push(n)
    grp.ca += n.in_degree || 0
    grp.ce += n.out_degree || 0
  })

  // Compute Martin metrics per package
  const packages: PackageMetric[] = Array.from(pkgGroups.entries())
    .map(([name, data]) => {
      const totalCoupling = data.ca + data.ce
      const instability = totalCoupling > 0 ? Number((data.ce / totalCoupling).toFixed(2)) : 0.5
      // Abstractness heuristic: interfaces, bases, models, or types ratio
      const abstractNodes = data.nodes.filter(
        (n) =>
          n.type === 'interface' ||
          /base|interface|abstract|protocol|model|schema/i.test(n.id)
      ).length
      const abstractness = Number((abstractNodes / Math.max(1, data.nodes.length)).toFixed(2))
      const distance = Number(Math.abs(abstractness + instability - 1).toFixed(2))

      return {
        name,
        instability,
        abstractness,
        distance,
        ca: data.ca,
        ce: data.ce,
        nodeCount: data.nodes.length,
      }
    })
    .slice(0, 15)

  const handleAiExplain = async () => {
    setAiLoading(true)
    try {
      const avgDistance =
        packages.reduce((acc, p) => acc + p.distance, 0) / Math.max(1, packages.length)
      const res = await aiApi.explainMetric(
        'Robert C. Martin Instability vs Abstractness',
        Number(avgDistance.toFixed(2)),
        undefined,
        {
          packages_analyzed: packages.length,
          packages: packages.map((p) => ({
            name: p.name,
            I: p.instability,
            A: p.abstractness,
            D: p.distance,
          })),
        }
      )
      setAiExplanation(res.explanation)
      setAiIsGenerated(Boolean(res.is_ai_generated))
    } catch {
      setAiExplanation(
        'Packages close to the green diagonal main-sequence line balance stability and abstractness. Bottom-left (Zone of Pain) represents concrete, rigid components difficult to change. Top-right (Zone of Uselessness) denotes abstract modules without dependents.'
      )
      setAiIsGenerated(false)
    } finally {
      setAiLoading(false)
    }
  }

  const active = focusedPkg || hoveredPkg

  return (
    <div className="glass-card p-6 rounded-2xl space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[var(--border)] dark:border-white/5 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold tracking-wide" style={{ color: 'var(--text-primary)' }}>
              Instability (I) vs. Abstractness (A)
            </h3>
            <span className="badge badge-accent text-[9px] uppercase font-bold">Main Sequence</span>
          </div>
          <p className="text-xs text-muted mt-0.5">
            Package architecture balance based on Robert C. Martin&apos;s normalized distance metrics.
          </p>
        </div>

        <button
          onClick={handleAiExplain}
          disabled={aiLoading}
          aria-label="AI Explain Instability vs Abstractness plot"
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

      {/* SVG Scatter Plot Canvas */}
      <div className="relative w-full aspect-[2/1] min-h-[260px] max-h-[340px] bg-surface-2/40 dark:bg-black/30 rounded-xl border border-[var(--border)] dark:border-white/5 p-4 flex items-center justify-center">
        <svg
          viewBox="0 0 500 250"
          className="w-full h-full overflow-visible"
          role="img"
          aria-label="Scatter plot of packages on Instability vs Abstractness coordinates"
        >
          {/* Zone of Pain (Bottom Left: I < 0.35, A < 0.35) */}
          <polygon
            points="50,210 170,210 50,90"
            fill="rgba(239, 68, 68, 0.12)"
            stroke="rgba(239, 68, 68, 0.25)"
            strokeWidth="1"
          />
          <text
            x="60"
            y="200"
            fontSize="9"
            fontWeight="bold"
            fill="#ef4444"
            className="font-mono opacity-80"
          >
            ZONE OF PAIN (Rigid)
          </text>

          {/* Zone of Uselessness (Top Right: I > 0.65, A > 0.65) */}
          <polygon
            points="450,50 330,50 450,170"
            fill="rgba(245, 158, 11, 0.12)"
            stroke="rgba(245, 158, 11, 0.25)"
            strokeWidth="1"
          />
          <text
            x="440"
            y="65"
            fontSize="9"
            fontWeight="bold"
            fill="#f59e0b"
            textAnchor="end"
            className="font-mono opacity-80"
          >
            ZONE OF USELESSNESS
          </text>

          {/* Axes */}
          <line x1="50" y1="210" x2="450" y2="210" stroke="var(--border)" strokeWidth="1.5" />
          <line x1="50" y1="50" x2="50" y2="210" stroke="var(--border)" strokeWidth="1.5" />

          {/* Main Sequence Line: (I=0, A=1) to (I=1, A=0) => (50, 50) to (450, 210) */}
          <line
            x1="50"
            y1="50"
            x2="450"
            y2="210"
            stroke="#10b981"
            strokeWidth="2"
            strokeDasharray="4 4"
          />
          <text x="260" y="125" fontSize="8" fontWeight="bold" fill="#10b981" className="font-mono">
            Main Sequence (A + I = 1)
          </text>

          {/* Axis Labels */}
          <text x="250" y="235" fontSize="9" fill="var(--text-muted)" textAnchor="middle">
            Instability (I) → [0.0: Stable/Hard to Change → 1.0: Flexible]
          </text>
          <text
            x="20"
            y="130"
            fontSize="9"
            fill="var(--text-muted)"
            textAnchor="middle"
            transform="rotate(-90 20 130)"
          >
            Abstractness (A) ↑
          </text>

          {/* Plotted Packages */}
          {packages.map((pkg, idx) => {
            const cx = 50 + pkg.instability * 400
            const cy = 210 - pkg.abstractness * 160
            const isHighDist = pkg.distance > 0.35
            const dotColor = isHighDist ? '#ef4444' : '#0ea5e9'
            const isHovered = active?.name === pkg.name

            return (
              <g
                key={idx}
                tabIndex={0}
                role="button"
                aria-label={`Package ${pkg.name}: Instability ${pkg.instability}, Abstractness ${pkg.abstractness}, Distance ${pkg.distance}`}
                onMouseEnter={() => setHoveredPkg(pkg)}
                onMouseLeave={() => setHoveredPkg(null)}
                onFocus={() => setFocusedPkg(pkg)}
                onBlur={() => setFocusedPkg(null)}
                className="cursor-pointer focus:outline-none"
              >
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 7 : 5}
                  fill={dotColor}
                  stroke="#ffffff"
                  strokeWidth={isHovered ? 2.5 : 1.5}
                  className="transition-all duration-150"
                />
                <text
                  x={cx + 7}
                  y={cy + 3}
                  fontSize="8"
                  fontWeight="bold"
                  fill="var(--text-primary)"
                  className="font-mono select-none"
                >
                  {pkg.name.split('.').pop()}
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      {/* Active Package Inspector / Tooltip */}
      {active && (
        <div className="p-3 rounded-xl bg-surface-2 dark:bg-black/30 border border-[var(--border)] dark:border-white/10 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 font-mono">
          <div className="flex items-center gap-2">
            <Crosshair size={14} className="text-accent" />
            <span className="font-bold text-primary">{active.name}</span>
            <span className="text-muted">({active.nodeCount} modules)</span>
          </div>
          <div className="flex items-center gap-4 text-muted">
            <span>
              Instability (I): <b className="text-primary">{active.instability}</b>
            </span>
            <span>
              Abstractness (A): <b className="text-primary">{active.abstractness}</b>
            </span>
            <span>
              Dist from Main Seq (D):{' '}
              <b className={active.distance > 0.35 ? 'text-red-400' : 'text-emerald-400'}>
                {active.distance}
              </b>
            </span>
          </div>
        </div>
      )}

      {/* "How to read this" caption */}
      <div className="text-[11px] text-muted space-y-1 bg-surface-2/40 dark:bg-white/[0.02] p-3 rounded-xl border border-[var(--border)] dark:border-white/5">
        <span className="font-bold text-primary flex items-center gap-1">
          <Info size={12} /> How to read this plot:
        </span>
        <p>
          Optimal architectures sit along the dashed green Main Sequence line (A + I = 1), where stability matches abstraction. Modules deep in the red Zone of Pain are concrete components with high afferent coupling that are dangerous and rigid to alter. Modules in the amber Zone of Uselessness contain abstractions with no consumers.
        </p>
      </div>
    </div>
  )
}
