import { useState, useMemo } from 'react'
import { Info, Sparkles, AlertCircle, RefreshCw, Target, ShieldAlert, ArrowRight } from 'lucide-react'
import type { GraphNode, GraphEdge } from '../../types'
import { aiApi } from '../../api/client'

interface BlastRadiusSimulatorProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  loading?: boolean
  error?: string | null
}

interface DepthNode {
  node: GraphNode
  depth: number
}

export function BlastRadiusSimulator({ nodes, edges, loading, error }: BlastRadiusSimulatorProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string>('')
  const [hoveredNode, setHoveredNode] = useState<DepthNode | null>(null)
  const [focusedNode, setFocusedNode] = useState<DepthNode | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [aiExplanation, setAiExplanation] = useState<string | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiIsGenerated, setAiIsGenerated] = useState(false)

  // Default selection when nodes arrive
  const activeNodeId = useMemo(() => {
    if (selectedNodeId && nodes.some((n) => n.id === selectedNodeId)) {
      return selectedNodeId
    }
    return nodes[0]?.id || ''
  }, [selectedNodeId, nodes])

  // Build reverse adjacency: who depends on whom
  // If A -> B (A imports B), modifying B impacts A!
  // So dependents of B are sources where target is B.
  const reverseAdjacency = useMemo(() => {
    const adj: Record<string, string[]> = {}
    edges.forEach((e) => {
      const s = typeof e.source === 'string' ? e.source : e.source?.id
      const t = typeof e.target === 'string' ? e.target : e.target?.id
      if (s && t) {
        if (!adj[t]) adj[t] = []
        if (!adj[t].includes(s)) {
          adj[t].push(s)
        }
      }
    })
    return adj
  }, [edges])

  // Node lookup map
  const nodeMap = useMemo(() => {
    const map = new Map<string, GraphNode>()
    nodes.forEach((n) => map.set(n.id, n))
    return map
  }, [nodes])

  // Compute BFS depths for activeNodeId
  const { depthMap, directCount, transitiveCount, totalImpacted, impactRatio } = useMemo(() => {
    const depths = new Map<string, number>()
    if (!activeNodeId) {
      return {
        depthMap: depths,
        directCount: 0,
        transitiveCount: 0,
        totalImpacted: 0,
        impactRatio: 0,
      }
    }

    depths.set(activeNodeId, 0)
    const queue: string[] = [activeNodeId]

    while (queue.length > 0) {
      const curr = queue.shift()!
      const currDepth = depths.get(curr)!
      const dependents = reverseAdjacency[curr] || []

      for (const dep of dependents) {
        if (!depths.has(dep)) {
          depths.set(dep, currDepth + 1)
          queue.push(dep)
        }
      }
    }

    let direct = 0
    let transitive = 0
    depths.forEach((depth, id) => {
      if (id === activeNodeId) return
      if (depth === 1) direct++
      else transitive++
    })

    const total = direct + transitive
    const ratio = nodes.length > 0 ? (total / nodes.length) * 100 : 0

    return {
      depthMap: depths,
      directCount: direct,
      transitiveCount: transitive,
      totalImpacted: total,
      impactRatio: ratio,
    }
  }, [activeNodeId, reverseAdjacency, nodes.length])

  // Nodes organized by rings
  const ring1Nodes = useMemo(() => {
    const list: DepthNode[] = []
    depthMap.forEach((depth, id) => {
      if (depth === 1) {
        const n = nodeMap.get(id)
        if (n) list.push({ node: n, depth: 1 })
      }
    })
    return list
  }, [depthMap, nodeMap])

  const ring2Nodes = useMemo(() => {
    const list: DepthNode[] = []
    depthMap.forEach((depth, id) => {
      if (depth >= 2) {
        const n = nodeMap.get(id)
        if (n) list.push({ node: n, depth })
      }
    })
    return list
  }, [depthMap, nodeMap])

  // Filtered nodes for selector
  const filteredNodes = useMemo(() => {
    if (!searchQuery.trim()) return nodes.slice(0, 50)
    const q = searchQuery.toLowerCase()
    return nodes
      .filter((n) => (n.label || n.id).toLowerCase().includes(q))
      .slice(0, 50)
  }, [nodes, searchQuery])

  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl flex flex-col items-center justify-center min-h-[380px] animate-pulse">
        <RefreshCw className="animate-spin text-accent mb-2" size={24} />
        <span className="text-xs text-muted">Calculating dependency propagation & blast radius...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass-card p-6 rounded-2xl flex flex-col items-center justify-center min-h-[380px] text-red-400">
        <AlertCircle size={24} className="mb-2" />
        <span className="text-xs">{error}</span>
      </div>
    )
  }

  if (!nodes || nodes.length === 0) {
    return (
      <div className="glass-card p-6 rounded-2xl flex flex-col items-center justify-center min-h-[380px] text-muted">
        <Info size={24} className="mb-2 opacity-50" />
        <span className="text-xs">No components available to compute blast radius</span>
      </div>
    )
  }

  const activeTargetNode = nodeMap.get(activeNodeId)
  const activeLabel = activeTargetNode?.label || activeTargetNode?.id.split('.').pop() || activeNodeId

  const handleAiExplain = async () => {
    setAiLoading(true)
    try {
      const res = await aiApi.explainMetric(
        'Blast Radius Risk',
        Number(impactRatio.toFixed(1)),
        undefined,
        {
          target_component: activeLabel,
          total_nodes: nodes.length,
          direct_dependents: directCount,
          transitive_dependents: transitiveCount,
          blast_radius_percentage: `${impactRatio.toFixed(1)}%`,
        }
      )
      setAiExplanation(res.explanation)
      setAiIsGenerated(Boolean(res.is_ai_generated))
    } catch {
      setAiExplanation(
        `Modifying '${activeLabel}' has a blast radius of ${impactRatio.toFixed(1)}% (${totalImpacted} of ${nodes.length} modules). Changes directly cascade to ${directCount} consumers, with secondary ripple effects to ${transitiveCount} downstream modules.`
      )
      setAiIsGenerated(false)
    } finally {
      setAiLoading(false)
    }
  }

  // Active inspected element
  const inspected = focusedNode || hoveredNode

  return (
    <div className="glass-card p-6 rounded-2xl space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--border)] dark:border-white/5 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold tracking-wide" style={{ color: 'var(--text-primary)' }}>
              Blast Radius Simulator
            </h3>
            <span className="badge badge-accent text-[9px] uppercase font-bold">BFS Depth Rings</span>
          </div>
          <p className="text-xs text-muted mt-0.5">
            Simulate change impact propagation: identifies direct consumers (Level 1) and transitive cascade risks (Level 2+).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleAiExplain}
            disabled={aiLoading}
            aria-label="AI Explain Blast Radius"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-accent/10 border border-accent/30 text-accent hover:bg-accent/20 transition-colors"
          >
            <Sparkles size={13} className={aiLoading ? 'animate-spin' : ''} />
            <span>{aiLoading ? 'Analyzing...' : 'AI Explain'}</span>
          </button>
        </div>
      </div>

      {/* Target Component Selector */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
        <label htmlFor="blast-radius-select" className="text-xs font-semibold flex items-center gap-1 text-muted shrink-0">
          <Target size={14} className="text-accent" /> Target Epicenter:
        </label>
        <div className="flex-1 flex items-center gap-2">
          <input
            type="text"
            placeholder="Filter modules..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-32 sm:w-44 px-2 py-1 text-xs rounded-lg border border-[var(--border)] dark:border-white/10 bg-surface-2 dark:bg-white/5 focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <select
            id="blast-radius-select"
            value={activeNodeId}
            onChange={(e) => setSelectedNodeId(e.target.value)}
            className="flex-1 px-2.5 py-1 text-xs rounded-lg border border-[var(--border)] dark:border-white/10 bg-surface-2 dark:bg-white/5 text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-accent font-mono truncate"
          >
            {filteredNodes.map((n) => (
              <option key={n.id} value={n.id} className="bg-surface text-xs">
                {n.label || n.id}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Metric Cards Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="p-3 rounded-xl bg-surface-2 dark:bg-white/[0.03] border border-[var(--border)] dark:border-white/5">
          <div className="text-[10px] text-muted font-semibold uppercase tracking-wider">Blast Radius</div>
          <div className="text-lg font-bold font-mono text-accent mt-0.5">{impactRatio.toFixed(1)}%</div>
          <div className="text-[10px] text-muted">of total codebase</div>
        </div>

        <div className="p-3 rounded-xl bg-surface-2 dark:bg-white/[0.03] border border-[var(--border)] dark:border-white/5">
          <div className="text-[10px] text-muted font-semibold uppercase tracking-wider">Total Affected</div>
          <div className="text-lg font-bold font-mono text-red-400 mt-0.5">
            {totalImpacted} <span className="text-xs font-normal text-muted">/ {nodes.length}</span>
          </div>
          <div className="text-[10px] text-muted">modules in cascade</div>
        </div>

        <div className="p-3 rounded-xl bg-surface-2 dark:bg-white/[0.03] border border-[var(--border)] dark:border-white/5">
          <div className="text-[10px] text-muted font-semibold uppercase tracking-wider">Level 1 (Direct)</div>
          <div className="text-lg font-bold font-mono text-amber-400 mt-0.5">{directCount}</div>
          <div className="text-[10px] text-muted">direct consumers</div>
        </div>

        <div className="p-3 rounded-xl bg-surface-2 dark:bg-white/[0.03] border border-[var(--border)] dark:border-white/5">
          <div className="text-[10px] text-muted font-semibold uppercase tracking-wider">Level 2+ (Transitive)</div>
          <div className="text-lg font-bold font-mono text-purple-400 mt-0.5">{transitiveCount}</div>
          <div className="text-[10px] text-muted">indirect ripple consumers</div>
        </div>
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

      {/* SVG Blast Radius Rings Visualizer */}
      <div className="relative border border-[var(--border)] dark:border-white/10 rounded-xl bg-surface-2 dark:bg-slate-950/40 p-4 flex flex-col items-center justify-center min-h-[300px] overflow-hidden">
        <svg
          viewBox="0 0 520 280"
          className="w-full max-w-lg h-auto select-none"
          role="img"
          aria-label={`Blast radius ring visualization centered on ${activeLabel}`}
        >
          {/* Background Grid Accent */}
          <circle cx="260" cy="140" r="130" fill="none" stroke="currentColor" strokeOpacity="0.03" strokeWidth="1" />
          <circle cx="260" cy="140" r="85" fill="none" stroke="currentColor" strokeOpacity="0.03" strokeWidth="1" />

          {/* Outer Ring: Level 2 Transitive */}
          <circle
            cx="260"
            cy="140"
            r="120"
            fill="none"
            stroke="#c084fc"
            strokeWidth="1.5"
            strokeDasharray="4 4"
            className="transition-all duration-300"
          />
          <text x="260" y="32" textAnchor="middle" fill="#c084fc" fontSize="9" fontWeight="700" letterSpacing="0.5">
            LEVEL 2+ TRANSITIVE CONSUMERS ({transitiveCount})
          </text>

          {/* Inner Ring: Level 1 Direct */}
          <circle
            cx="260"
            cy="140"
            r="70"
            fill="none"
            stroke="#fbbf24"
            strokeWidth="1.5"
            className="transition-all duration-300"
          />
          <text x="260" y="80" textAnchor="middle" fill="#fbbf24" fontSize="9" fontWeight="700" letterSpacing="0.5">
            LEVEL 1 DIRECT CONSUMERS ({directCount})
          </text>

          {/* Target Epicenter Circle */}
          <circle
            cx="260"
            cy="140"
            r="28"
            className="fill-accent/20 stroke-accent"
            strokeWidth="2.5"
          />
          <circle cx="260" cy="140" r="8" className="fill-accent animate-pulse" />
          <text
            x="260"
            y="144"
            textAnchor="middle"
            fontSize="8.5"
            fontWeight="800"
            fill="var(--text-primary)"
            className="pointer-events-none font-mono"
          >
            {activeLabel.length > 9 ? activeLabel.slice(0, 8) + '…' : activeLabel}
          </text>

          {/* Ring 1 Interactive Points */}
          {ring1Nodes.slice(0, 12).map((item, idx) => {
            const angle = (idx / Math.min(12, ring1Nodes.length)) * 2 * Math.PI - Math.PI / 2
            const px = 260 + 70 * Math.cos(angle)
            const py = 140 + 70 * Math.sin(angle)
            const isHovered = hoveredNode?.node.id === item.node.id
            const isFocused = focusedNode?.node.id === item.node.id

            return (
              <g
                key={item.node.id}
                tabIndex={0}
                role="button"
                aria-label={`Direct dependent: ${item.node.label || item.node.id}`}
                onMouseEnter={() => setHoveredNode(item)}
                onMouseLeave={() => setHoveredNode(null)}
                onFocus={() => setFocusedNode(item)}
                onBlur={() => setFocusedNode(null)}
                onClick={() => setSelectedNodeId(item.node.id)}
                className="cursor-pointer focus:outline-none"
              >
                <circle
                  cx={px}
                  cy={py}
                  r={isHovered || isFocused ? 7 : 5}
                  fill="#f59e0b"
                  stroke="#ffffff"
                  strokeWidth={1.5}
                  className="transition-all"
                />
              </g>
            )
          })}

          {/* Ring 2 Interactive Points */}
          {ring2Nodes.slice(0, 20).map((item, idx) => {
            const angle = (idx / Math.min(20, ring2Nodes.length)) * 2 * Math.PI - Math.PI / 4
            const px = 260 + 120 * Math.cos(angle)
            const py = 140 + 120 * Math.sin(angle)
            const isHovered = hoveredNode?.node.id === item.node.id
            const isFocused = focusedNode?.node.id === item.node.id

            return (
              <g
                key={item.node.id}
                tabIndex={0}
                role="button"
                aria-label={`Transitive dependent: ${item.node.label || item.node.id}`}
                onMouseEnter={() => setHoveredNode(item)}
                onMouseLeave={() => setHoveredNode(null)}
                onFocus={() => setFocusedNode(item)}
                onBlur={() => setFocusedNode(null)}
                onClick={() => setSelectedNodeId(item.node.id)}
                className="cursor-pointer focus:outline-none"
              >
                <circle
                  cx={px}
                  cy={py}
                  r={isHovered || isFocused ? 6 : 4}
                  fill="#a855f7"
                  stroke="#ffffff"
                  strokeWidth={1.5}
                  className="transition-all"
                />
              </g>
            )
          })}
        </svg>

        {/* Selected / Hovered Detail Card */}
        {inspected ? (
          <div className="mt-2 p-2.5 px-4 rounded-xl bg-surface/90 border border-accent/30 flex items-center justify-between gap-4 text-xs w-full max-w-md shadow-lg backdrop-blur-md">
            <div>
              <div className="font-bold flex items-center gap-1.5 font-mono text-[var(--text-primary)]">
                <span>{inspected.node.label || inspected.node.id}</span>
                <span
                  className={`text-[9px] px-1.5 py-0.5 rounded font-sans font-bold uppercase ${
                    inspected.depth === 1 ? 'bg-amber-500/20 text-amber-300' : 'bg-purple-500/20 text-purple-300'
                  }`}
                >
                  Level {inspected.depth} {inspected.depth === 1 ? 'Direct' : 'Transitive'}
                </span>
              </div>
              <div className="text-[10px] text-muted mt-0.5">
                LOC: {inspected.node.loc || '—'} · Type: {inspected.node.type || 'module'}
              </div>
            </div>
            <button
              onClick={() => setSelectedNodeId(inspected.node.id)}
              className="px-2 py-1 text-[10px] font-semibold rounded bg-accent/20 hover:bg-accent/30 text-accent flex items-center gap-1"
            >
              Simulate <ArrowRight size={10} />
            </button>
          </div>
        ) : (
          <div className="mt-2 text-[11px] text-muted flex items-center gap-1">
            <Info size={12} /> Hover or focus on any ring point to inspect cascade depth
          </div>
        )}
      </div>

      {/* "How to read this" Caption */}
      <div className="p-3 rounded-xl bg-surface-2 dark:bg-white/[0.02] border border-[var(--border)] dark:border-white/5 text-xs text-muted space-y-1">
        <span className="font-bold text-[var(--text-primary)] flex items-center gap-1">
          <ShieldAlert size={13} className="text-accent" /> How to read this simulation:
        </span>
        <p className="leading-relaxed">
          The center node is the proposed change epicenter. <strong>Level 1 (Inner Ring)</strong> represents direct consumers
          whose source code directly imports or depends on this component. <strong>Level 2+ (Outer Ring)</strong> represents
          indirect consumers affected via secondary dependency propagation. A high blast radius (&gt;25%) indicates a foundational
          coupling hub requiring strict contract testing and canary validation before refactoring.
        </p>
      </div>
    </div>
  )
}
