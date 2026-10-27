import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  Grid,
  SquareChartGantt,
  ScatterChart,
  Target,
  Database,
  SlidersHorizontal,
  Flame,
  GitBranch,
  Code2,
} from 'lucide-react'
import { useAnalysisContext } from '../contexts/AnalysisContext'
import { DependencyStructureMatrix } from '../components/insights/DependencyStructureMatrix'
import { LocTreemap } from '../components/insights/LocTreemap'
import { InstabilityAbstractnessScatter } from '../components/insights/InstabilityAbstractnessScatter'
import { BlastRadiusSimulator } from '../components/insights/BlastRadiusSimulator'
import { HotspotBubbleChart } from '../components/insights/HotspotBubbleChart'
import { ChordArcDiagram } from '../components/insights/ChordArcDiagram'
import { LanguageBreakdownDonut } from '../components/insights/LanguageBreakdownDonut'

type InsightTab = 'all' | 'dsm' | 'treemap' | 'scatter' | 'blast' | 'hotspots' | 'chord' | 'languages'

export function InsightsPage() {
  const { result, loading, error, activeDataset, loadSample } = useAnalysisContext()
  const [activeTab, setActiveTab] = useState<InsightTab>('all')

  const nodes = useMemo(() => result?.graph.nodes ?? [], [result])
  const edges = useMemo(() => result?.graph.edges ?? [], [result])

  const summary = useMemo(() => {
    const totalLoc = nodes.reduce((acc, n) => acc + (n.loc || 0), 0)
    const avgCc = nodes.length
      ? (
          nodes.reduce((acc, n) => acc + Number(n.metrics?.complexity || (n as any).complexity || 8), 0) /
          nodes.length
        ).toFixed(1)
      : '0'
    const cycles = edges.filter((e) => e.is_cycle).length
    return { totalLoc, avgCc, cycles, totalNodes: nodes.length, totalEdges: edges.length }
  }, [nodes, edges])

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Architectural Insights
            </h1>
            <span className="badge badge-accent text-[10px] font-bold uppercase tracking-wider">Phase 7 &amp; 8</span>
            <span className="badge text-[10px] uppercase font-mono bg-surface-2 dark:bg-white/5 border border-[var(--border)] dark:border-white/10 text-muted">
              {activeDataset.toUpperCase()}
            </span>
          </div>
          <p className="text-xs sm:text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Deep architectural structure inspections: DSM, Martin Metrics, Hotspots, Layer Arcs, and Polyglot Breakdown.
          </p>
        </div>

        {/* Quick Sample Switcher if empty */}
        {(!result || nodes.length === 0) && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted flex items-center gap-1">
              <Database size={13} /> Load Sample:
            </span>
            <button
              onClick={() => loadSample('flask')}
              className="px-2.5 py-1 text-xs rounded-lg bg-surface-2 dark:bg-white/5 border border-[var(--border)] dark:border-white/10 hover:border-accent text-[var(--text-primary)] transition-colors"
            >
              Flask API
            </button>
            <button
              onClick={() => loadSample('spring')}
              className="px-2.5 py-1 text-xs rounded-lg bg-surface-2 dark:bg-white/5 border border-[var(--border)] dark:border-white/10 hover:border-accent text-[var(--text-primary)] transition-colors"
            >
              Spring Boot
            </button>
          </div>
        )}
      </div>

      {/* Summary KPI Strip */}
      {result && nodes.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="glass-card p-3 rounded-xl border border-[var(--border)] dark:border-white/5">
            <span className="text-[10px] text-muted uppercase font-bold tracking-wider">Modules</span>
            <div className="text-lg font-bold font-mono text-[var(--text-primary)]">{summary.totalNodes}</div>
          </div>
          <div className="glass-card p-3 rounded-xl border border-[var(--border)] dark:border-white/5">
            <span className="text-[10px] text-muted uppercase font-bold tracking-wider">Dependencies</span>
            <div className="text-lg font-bold font-mono text-accent">{summary.totalEdges}</div>
          </div>
          <div className="glass-card p-3 rounded-xl border border-[var(--border)] dark:border-white/5">
            <span className="text-[10px] text-muted uppercase font-bold tracking-wider">Total Volume</span>
            <div className="text-lg font-bold font-mono text-[var(--text-primary)]">{summary.totalLoc.toLocaleString()} LOC</div>
          </div>
          <div className="glass-card p-3 rounded-xl border border-[var(--border)] dark:border-white/5">
            <span className="text-[10px] text-muted uppercase font-bold tracking-wider">Avg Complexity</span>
            <div className="text-lg font-bold font-mono text-amber-400">CC {summary.avgCc}</div>
          </div>
          <div className="glass-card p-3 rounded-xl border border-[var(--border)] dark:border-white/5">
            <span className="text-[10px] text-muted uppercase font-bold tracking-wider">Cycles Detected</span>
            <div className={`text-lg font-bold font-mono ${summary.cycles > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
              {summary.cycles}
            </div>
          </div>
        </div>
      )}

      {/* View Filter Tabs */}
      <div className="flex items-center gap-1.5 p-1 rounded-xl bg-surface-2 dark:bg-white/[0.04] border border-[var(--border)] dark:border-white/10 w-fit overflow-x-auto max-w-full">
        <button
          onClick={() => setActiveTab('all')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'all'
              ? 'bg-accent text-slate-950 shadow-sm'
              : 'text-muted hover:text-[var(--text-primary)]'
          }`}
        >
          <SlidersHorizontal size={13} />
          <span>All Visualizations</span>
        </button>

        <button
          onClick={() => setActiveTab('hotspots')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'hotspots'
              ? 'bg-accent text-slate-950 shadow-sm'
              : 'text-muted hover:text-[var(--text-primary)]'
          }`}
        >
          <Flame size={13} />
          <span>Hotspot Bubbles</span>
        </button>

        <button
          onClick={() => setActiveTab('chord')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'chord'
              ? 'bg-accent text-slate-950 shadow-sm'
              : 'text-muted hover:text-[var(--text-primary)]'
          }`}
        >
          <GitBranch size={13} />
          <span>Layer Arcs</span>
        </button>

        <button
          onClick={() => setActiveTab('languages')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'languages'
              ? 'bg-accent text-slate-950 shadow-sm'
              : 'text-muted hover:text-[var(--text-primary)]'
          }`}
        >
          <Code2 size={13} />
          <span>Language Share</span>
        </button>

        <button
          onClick={() => setActiveTab('dsm')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'dsm'
              ? 'bg-accent text-slate-950 shadow-sm'
              : 'text-muted hover:text-[var(--text-primary)]'
          }`}
        >
          <Grid size={13} />
          <span>Dependency Matrix</span>
        </button>

        <button
          onClick={() => setActiveTab('treemap')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'treemap'
              ? 'bg-accent text-slate-950 shadow-sm'
              : 'text-muted hover:text-[var(--text-primary)]'
          }`}
        >
          <SquareChartGantt size={13} />
          <span>LOC Treemap</span>
        </button>

        <button
          onClick={() => setActiveTab('scatter')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'scatter'
              ? 'bg-accent text-slate-950 shadow-sm'
              : 'text-muted hover:text-[var(--text-primary)]'
          }`}
        >
          <ScatterChart size={13} />
          <span>Martin Metrics</span>
        </button>

        <button
          onClick={() => setActiveTab('blast')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'blast'
              ? 'bg-accent text-slate-950 shadow-sm'
              : 'text-muted hover:text-[var(--text-primary)]'
          }`}
        >
          <Target size={13} />
          <span>Blast Radius</span>
        </button>
      </div>

      {/* Main Content Area */}
      {activeTab === 'all' ? (
        <div className="space-y-6">
          {/* New P2 Insights */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
              <HotspotBubbleChart nodes={nodes} loading={loading} error={error} />
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
              <ChordArcDiagram nodes={nodes} edges={edges} loading={loading} error={error} />
            </motion.div>
          </div>

          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
            <LanguageBreakdownDonut nodes={nodes} loading={loading} error={error} />
          </motion.div>

          {/* Existing Visualizations */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
              <DependencyStructureMatrix nodes={nodes} edges={edges} loading={loading} error={error} />
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
              <LocTreemap nodes={nodes} loading={loading} error={error} />
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>
              <InstabilityAbstractnessScatter nodes={nodes} edges={edges} loading={loading} error={error} />
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
              <BlastRadiusSimulator nodes={nodes} edges={edges} loading={loading} error={error} />
            </motion.div>
          </div>
        </div>
      ) : activeTab === 'hotspots' ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <HotspotBubbleChart nodes={nodes} loading={loading} error={error} />
        </motion.div>
      ) : activeTab === 'chord' ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <ChordArcDiagram nodes={nodes} edges={edges} loading={loading} error={error} />
        </motion.div>
      ) : activeTab === 'languages' ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <LanguageBreakdownDonut nodes={nodes} loading={loading} error={error} />
        </motion.div>
      ) : activeTab === 'dsm' ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <DependencyStructureMatrix nodes={nodes} edges={edges} loading={loading} error={error} />
        </motion.div>
      ) : activeTab === 'treemap' ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <LocTreemap nodes={nodes} loading={loading} error={error} />
        </motion.div>
      ) : activeTab === 'scatter' ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <InstabilityAbstractnessScatter nodes={nodes} edges={edges} loading={loading} error={error} />
        </motion.div>
      ) : (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <BlastRadiusSimulator nodes={nodes} edges={edges} loading={loading} error={error} />
        </motion.div>
      )}
    </div>
  )
}
