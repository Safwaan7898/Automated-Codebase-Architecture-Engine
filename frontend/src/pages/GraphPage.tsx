import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Maximize2,
  Minimize2,
  Layers,
  Search,
  Box,
  CircleDot,
  Zap,
  Sparkles,
  MessageSquare,
  X,
} from 'lucide-react'
import { ForceGraphView } from '../components/ForceGraphView'
import { NodeInspectorPanel } from '../components/NodeInspectorPanel'
import { AskArchLensPanel } from '../components/AskArchLensPanel'
import { AIBadge } from '../components/ui/AILabel'
import { aiApi } from '../api/client'
import { useAnalysisContext } from '../contexts/AnalysisContext'
import type { GraphNode, RefactorSuggestion, AINLSearchFilter } from '../types'

export function GraphPage() {
  const navigate = useNavigate()
  const {
    result,
    selectedNode,
    setSelectedNode,
    activeDataset,
    isLiveAnalysis,
    loadSample,
    repoList,
    loadRepoGraph,
    analyzeLiveCodebase,
    loading,
  } = useAnalysisContext()

  // Controls state
  const [searchQuery, setSearchQuery] = useState('')
  const [nlSearchQuery, setNlSearchQuery] = useState('')
  const [activeNLFilter, setActiveNLFilter] = useState<AINLSearchFilter | null>(null)
  const [isSearchingNL, setIsSearchingNL] = useState(false)
  const [isAskArchLensOpen, setIsAskArchLensOpen] = useState(false)
  const [selectedSeverity, setSelectedSeverity] = useState('ALL')
  const [selectedLayer, setSelectedLayer] = useState('ALL')
  const [is3DMode, setIs3DMode] = useState(false)
  const [isLayerBands, setIsLayerBands] = useState(true)
  const [clustersCollapsed, setClustersCollapsed] = useState(false)
  const [blastRadiusNodeId, setBlastRadiusNodeId] = useState<string | null>(null)
  const [fps, setFps] = useState(60)
  const [fullscreen, setFullscreen] = useState(false)

  // Live analysis bar input
  const [livePath, setLivePath] = useState(result?.path || '')
  const [analyzingLive, setAnalyzingLive] = useState(false)

  const handleNLSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!nlSearchQuery.trim() || isSearchingNL) return
    setIsSearchingNL(true)
    try {
      const filter = await aiApi.nlSearch(nlSearchQuery.trim(), result?.repo_id)
      setActiveNLFilter(filter)
    } catch {
      setActiveNLFilter(null)
    } finally {
      setIsSearchingNL(false)
    }
  }

  // Filtered graph derived deterministically from active NL filter
  const filteredGraph = useMemo(() => {
    if (!result?.graph) return null
    if (!activeNLFilter) return result.graph

    let nodes = result.graph.nodes
    if (activeNLFilter.name_contains) {
      const q = activeNLFilter.name_contains.toLowerCase()
      nodes = nodes.filter((n) => n.id.toLowerCase().includes(q) || n.label.toLowerCase().includes(q))
    }
    if (typeof activeNLFilter.min_complexity === 'number') {
      nodes = nodes.filter((n) => (n.cyclomatic_complexity || 0) >= activeNLFilter.min_complexity!)
    }
    if (typeof activeNLFilter.max_instability === 'number') {
      nodes = nodes.filter((n) => ((n as any).instability ?? (n.metrics?.instability as number) ?? 0) <= activeNLFilter.max_instability!)
    }
    if (activeNLFilter.smell_type) {
      const st = activeNLFilter.smell_type.toLowerCase()
      const matchingFiles = new Set(
        (result.smells || [])
          .filter((s) => s.type.toLowerCase().includes(st))
          .map((s) => s.file)
      )
      nodes = nodes.filter((n) => matchingFiles.has(n.file_path || n.id))
    }

    const validIds = new Set(nodes.map((n) => n.id))
    const edges = result.graph.edges.filter((e) => {
      const src = typeof e.source === 'string' ? e.source : (e.source as { id: string })?.id
      const tgt = typeof e.target === 'string' ? e.target : (e.target as { id: string })?.id
      return validIds.has(src) && validIds.has(tgt)
    })

    return { nodes, edges }
  }, [result?.graph, result?.smells, activeNLFilter])

  useEffect(() => {
    if (result?.path) {
      setLivePath(result.path)
    }
  }, [result?.path])

  const handleNodeClick = useCallback(
    (node: GraphNode) => {
      setSelectedNode(node)
      if (blastRadiusNodeId && blastRadiusNodeId !== node.id) {
        setBlastRadiusNodeId(null)
      }
    },
    [setSelectedNode, blastRadiusNodeId]
  )

  const handleHighlightBlastRadius = useCallback((nodeId: string) => {
    setBlastRadiusNodeId((prev) => (prev === nodeId ? null : nodeId))
  }, [])

  const handleRunLiveAnalysis = async () => {
    if (!livePath.trim()) return
    setAnalyzingLive(true)
    try {
      await analyzeLiveCodebase(livePath.trim(), 'auto')
    } finally {
      setAnalyzingLive(false)
    }
  }

  const allSuggestions: RefactorSuggestion[] = useMemo(() => {
    return result?.refactor_suggestions ?? []
  }, [result])

  return (
    <div className={`relative flex flex-col h-[calc(100vh-4rem)] p-3 gap-2.5 ${fullscreen ? 'fixed inset-0 z-50 h-screen bg-[var(--bg)] p-4' : ''}`}>
      {/* Top Brutalist Control Bar */}
      <div
        className="glass-card flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 rounded-[2px] border border-[var(--border)] flex-shrink-0"
      >
        {/* Left: Live workspace analyzer & dataset switchers */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Live Analysis Input (Supports local paths and GitHub URLs) */}
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-[var(--surface-2)]/60 dark:bg-black/60 border border-[var(--accent)]/40 focus-within:border-[var(--accent)] focus-within:shadow-[0_0_15px_rgba(204,255,0,0.4)] transition-colors duration-150">
            <input
              type="text"
              value={livePath}
              onChange={(e) => setLivePath(e.target.value)}
              placeholder="PATH OR GITHUB URL..."
              className="bg-transparent text-xs font-mono uppercase px-3 py-1.5 focus:outline-none w-64 text-[var(--text)] placeholder-[var(--placeholder)]"
            />
            <button
              onClick={handleRunLiveAnalysis}
              disabled={analyzingLive || loading}
              className="chrome-btn px-4 py-1.5 text-xs rounded-lg flex items-center gap-1 font-extrabold disabled:opacity-50 tracking-wider cursor-pointer"
              title="Run real-time AST analysis against this workspace or Git repository"
            >
              <Zap size={12} />
              {analyzingLive ? 'PARSING…' : 'ANALYZE'}
            </button>
          </div>

          {/* Benchmark Presets */}
          <div className="flex items-center gap-1 p-1 rounded-[2px] bg-[var(--surface-2)]/60 dark:bg-black/30 border border-[var(--border)] dark:border-white/10">
            <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-[var(--text-muted)] px-1.5">
              PRESETS:
            </span>
            <button
              onClick={() => loadSample('flask')}
              className={`px-2.5 py-1 text-xs rounded-[2px] font-bold tracking-[0.1em] uppercase transition-colors duration-150 ${
                activeDataset === 'flask' ? 'bg-[#a3e635] text-[#020617] shadow-[0_0_12px_rgba(163,230,53,0.5)]' : 'text-[var(--text-secondary)] hover:text-[var(--text)]'
              }`}
            >
              FLASK
            </button>
            <button
              onClick={() => loadSample('spring')}
              className={`px-2.5 py-1 text-xs rounded-[2px] font-bold tracking-[0.1em] uppercase transition-colors duration-150 ${
                activeDataset === 'spring' ? 'bg-[#06b6d4] text-[#020617] shadow-[0_0_12px_rgba(6,182,212,0.5)]' : 'text-[var(--text-secondary)] hover:text-[var(--text)]'
              }`}
            >
              SPRING
            </button>
            <button
              onClick={() => loadSample('vulnerable')}
              className={`px-2.5 py-1 text-xs rounded-[2px] font-bold tracking-[0.1em] uppercase transition-colors duration-150 ${
                activeDataset === 'vulnerable' ? 'bg-[#ef4444] text-white shadow-[0_0_12px_rgba(239,68,68,0.5)]' : 'text-[#dc2626] dark:text-[#ef4444] hover:bg-[#ef4444]/10'
              }`}
            >
              VULNERABLE
            </button>

            {repoList.length > 0 && (
              <select
                onChange={(e) => e.target.value && loadRepoGraph(e.target.value)}
                value={activeDataset === 'custom' ? result?.repo_id : ''}
                className="bg-[var(--surface)] text-xs px-2 py-0.5 rounded-[2px] border border-[var(--border)] font-mono text-[var(--text)] uppercase tracking-wider"
              >
                <option value="">CACHED REPOS…</option>
                {repoList.map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Quick Node Search */}
          <div className="relative flex items-center min-w-[150px]">
            <Search size={13} className="absolute left-2.5 text-[var(--text-muted)] pointer-events-none" />
            <input
              type="text"
              placeholder="SEARCH NODES…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="field pl-8 pr-2.5 py-1 text-xs rounded-[2px] uppercase font-mono tracking-wider w-full"
            />
          </div>

          {/* Natural Language AI Graph Filter */}
          <form onSubmit={handleNLSearch} className="relative flex items-center min-w-[200px]" data-testid="nl-search-form">
            <Sparkles size={13} className="absolute left-2.5 text-[var(--accent)] pointer-events-none" />
            <input
              type="text"
              placeholder="AI GRAPH QUERY…"
              value={nlSearchQuery}
              onChange={(e) => setNlSearchQuery(e.target.value)}
              className="field pl-8 pr-14 py-1 text-xs rounded-[2px] uppercase font-mono tracking-wider w-full"
              data-testid="nl-search-input"
              disabled={isSearchingNL}
            />
            <button
              type="submit"
              disabled={!nlSearchQuery.trim() || isSearchingNL}
              data-testid="nl-search-submit"
              className="absolute right-1 text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-[var(--accent)] text-black cursor-pointer disabled:opacity-40"
            >
              {isSearchingNL ? '…' : 'FILTER'}
            </button>
          </form>
        </div>

        {/* Right: Graph display toggles */}
        <div className="flex items-center gap-2 flex-wrap text-xs">
          {/* Ask ArchLens Panel Trigger */}
          <button
            onClick={() => setIsAskArchLensOpen(!isAskArchLensOpen)}
            data-testid="open-ask-archlens-button"
            className={`px-2.5 py-1 text-xs flex items-center gap-1.5 rounded-[2px] uppercase tracking-[0.1em] font-mono border transition-all cursor-pointer ${
              isAskArchLensOpen
                ? 'bg-[var(--accent)] text-black border-[var(--accent)] font-bold'
                : 'border-[var(--border)] text-[var(--text-secondary)] hover:border-[var(--accent)] hover:text-[var(--text)]'
            }`}
            title="Ask questions about this architecture with citation-grounded answers"
          >
            <MessageSquare size={13} />
            <span>Ask ArchLens</span>
            <AIBadge label="AI-generated" size="xs" />
          </button>

          {/* Layer Filter */}
          <select
            value={selectedLayer}
            onChange={(e) => setSelectedLayer(e.target.value)}
            className="field px-2.5 py-1 rounded-[2px] text-xs font-mono uppercase tracking-wider max-w-[140px]"
          >
            <option value="ALL">ALL LAYERS</option>
            <option value="Presentation">PRESENTATION</option>
            <option value="Service">SERVICE</option>
            <option value="Domain">DOMAIN</option>
            <option value="Data / Infrastructure">DATA / INFRA</option>
          </select>

          {/* Severity Filter */}
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="field px-2.5 py-1 rounded-[2px] text-xs font-mono uppercase tracking-wider max-w-[140px]"
          >
            <option value="ALL">ALL SEVERITY</option>
            <option value="critical">CRITICAL ONLY</option>
            <option value="high">HIGH +</option>
            <option value="vulnerable">VULNERABLE</option>
          </select>

          {/* 2D / 3D Mode */}
          <button
            onClick={() => setIs3DMode(!is3DMode)}
            className={`btn-ghost px-2.5 py-1 text-xs flex items-center gap-1 rounded-[2px] uppercase tracking-[0.15em] font-mono ${
              is3DMode ? 'border-[#06b6d4] text-[#0891b2] dark:text-[#06b6d4] shadow-[0_0_12px_rgba(6,182,212,0.4)]' : ''
            }`}
          >
            <Box size={13} />
            <span>{is3DMode ? '3D' : '2D'}</span>
          </button>

          {/* Layer Bands */}
          <button
            onClick={() => setIsLayerBands(!isLayerBands)}
            className={`btn-ghost px-2.5 py-1 text-xs flex items-center gap-1 rounded-[2px] uppercase tracking-[0.15em] font-mono ${
              isLayerBands ? 'border-[#a3e635] text-[#3f6212] dark:text-[#a3e635] shadow-[0_0_12px_rgba(163,230,53,0.4)]' : ''
            }`}
          >
            <Layers size={13} />
            <span>BANDS</span>
          </button>

          {/* Clusters */}
          <button
            onClick={() => setClustersCollapsed(!clustersCollapsed)}
            className={`btn-ghost px-2.5 py-1 text-xs flex items-center gap-1 rounded-[2px] uppercase tracking-[0.15em] font-mono ${
              clustersCollapsed ? 'border-[#f967fb] text-[#86198f] dark:text-[#f967fb] shadow-[0_0_12px_rgba(249,103,251,0.4)]' : ''
            }`}
          >
            <CircleDot size={13} />
            <span>CLUSTERS</span>
          </button>

          {/* Fullscreen Toggle */}
          <button
            onClick={() => setFullscreen(!fullscreen)}
            className="btn-ghost p-1.5 rounded-[2px] text-[var(--text-muted)] hover:text-[var(--text)]"
            title={fullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen'}
          >
            {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        </div>
      </div>

      {/* Active Natural Language Filter Banner */}
      {activeNLFilter && (
        <div
          className="flex items-center justify-between px-3.5 py-1.5 rounded-[2px] text-xs font-mono border backdrop-blur-md"
          style={{
            background: 'rgba(198,244,50,0.06)',
            borderColor: 'rgba(198,244,50,0.3)',
            color: 'var(--text-primary)',
          }}
          data-testid="active-nl-filter-banner"
        >
          <div className="flex items-center gap-2 flex-wrap">
            <AIBadge label="AI-generated" size="xs" />
            <span className="text-[11px] text-muted">Applied Filter:</span>
            {activeNLFilter.name_contains && (
              <span className="px-1.5 py-0.5 rounded bg-black/30 border border-white/10 text-[10px]">
                name ~ &quot;{activeNLFilter.name_contains}&quot;
              </span>
            )}
            {typeof activeNLFilter.min_complexity === 'number' && (
              <span className="px-1.5 py-0.5 rounded bg-black/30 border border-white/10 text-[10px]">
                complexity &ge; {activeNLFilter.min_complexity}
              </span>
            )}
            {typeof activeNLFilter.max_instability === 'number' && (
              <span className="px-1.5 py-0.5 rounded bg-black/30 border border-white/10 text-[10px]">
                instability &le; {activeNLFilter.max_instability}
              </span>
            )}
            {activeNLFilter.smell_type && (
              <span className="px-1.5 py-0.5 rounded bg-black/30 border border-white/10 text-[10px]">
                smell: {activeNLFilter.smell_type}
              </span>
            )}
          </div>
          <button
            onClick={() => setActiveNLFilter(null)}
            className="text-[10px] text-muted hover:text-white flex items-center gap-1 cursor-pointer font-bold"
          >
            <X size={11} /> CLEAR
          </button>
        </div>
      )}

      {/* Main Canvas Area */}
      <div
        className="relative flex-1 rounded-[2px] overflow-hidden border border-[var(--border)] glass-card shadow-glass"
      >
        {/* Force Directed Graph Canvas */}
        <ForceGraphView
          graph={filteredGraph}
          onNodeClick={handleNodeClick}
          selectedNodeId={selectedNode?.id ?? null}
          blastRadiusNodeId={blastRadiusNodeId}
          is3DMode={is3DMode}
          isLayerBands={isLayerBands}
          clustersCollapsed={clustersCollapsed}
          searchQuery={searchQuery}
          selectedSeverity={selectedSeverity}
          selectedLayer={selectedLayer}
          onFpsUpdate={setFps}
        />

        {/* Empty State Overlay */}
        {(!result || !result?.graph?.nodes?.length) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center bg-[var(--surface)]/90 dark:bg-black/80 backdrop-blur-md z-30 pointer-events-auto">
            <div className="w-14 h-14 rounded-full bg-[#CCFF00]/10 border border-[#CCFF00] flex items-center justify-center text-[var(--accent-text)] dark:text-[#CCFF00] mb-4 shadow-[0_0_20px_rgba(204,255,0,0.4)]">
              <Zap size={24} />
            </div>
            <h3 className="font-['Syne',sans-serif] text-xl font-black uppercase tracking-tight text-[var(--text)] dark:text-white mb-2">
              AWAITING CODEBASE INGESTION
            </h3>
            <p className="text-xs font-mono text-[var(--text-muted)] dark:text-white/60 max-w-md mb-6 leading-relaxed">
              No active repository graph loaded. Run live AST analysis using the toolbar above, or launch universal ingestion with a Git repository or zip archive.
            </p>
            <button
              onClick={() => navigate('/ingestion')}
              className="chrome-btn px-6 py-2.5 text-xs font-bold flex items-center gap-2 cursor-pointer"
            >
              <span>OPEN INGESTION PIPELINE</span>
            </button>
          </div>
        )}

        {/* Floating Real-Time Status HUD */}
        <div
          className="absolute top-4 left-4 pointer-events-none flex items-center gap-3 px-3.5 py-2 rounded-[2px] border text-xs backdrop-blur-xl shadow-glass"
          style={{
            background: 'var(--hud-bg)',
            borderColor: 'var(--hud-border)',
            color: 'var(--hud-text)',
          }}
        >
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                isLiveAnalysis ? 'bg-[#a3e635] shadow-[0_0_8px_#a3e635] animate-pulse' : 'bg-[#06b6d4]'
              }`}
            />
            <span className="font-bold tracking-[0.15em] uppercase text-[var(--text)] font-mono text-[10px]">
              {isLiveAnalysis ? 'LIVE AST ENGINE' : 'BENCHMARK DATA'}
            </span>
            <span className="font-mono text-[var(--text-muted)] text-[9px] uppercase">
              [{result?.repo_id?.slice(0, 8) || result?.path || 'WORKSPACE'}]
            </span>
          </div>

          <span className="opacity-20">|</span>

          <div className="flex items-center gap-1.5 font-mono text-xs">
            <span className="font-bold text-[#3f6212] dark:text-[#a3e635]">{result?.node_count ?? 0}</span>
            <span className="text-[10px] text-[var(--text-muted)]">NODES</span>
          </div>

          <span className="opacity-20">|</span>

          <div className="flex items-center gap-1.5 font-mono text-xs">
            <span className="font-bold text-[#0e7490] dark:text-[#06b6d4]">{result?.edge_count ?? 0}</span>
            <span className="text-[10px] text-[var(--text-muted)]">EDGES</span>
          </div>

          <span className="opacity-20">|</span>

          <div className="flex items-center gap-1 font-mono text-[10px] text-[var(--text-muted)]">
            <span>{fps} FPS</span>
          </div>
        </div>

        {/* Floating Brutalist Legend */}
        <div
          className="absolute bottom-4 left-4 p-3 rounded-[2px] border text-[10px] backdrop-blur-xl space-y-1 shadow-glass pointer-events-none font-mono uppercase tracking-wider"
          style={{
            background: 'var(--hud-bg)',
            borderColor: 'var(--hud-border)',
            color: 'var(--hud-text-muted)',
          }}
        >
          <div className="font-bold text-[9px] text-[#0e7490] dark:text-[#06b6d4] mb-1">
            ARCHITECTURAL LAYERS
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-none" style={{ background: '#38bdf8' }} /> PRESENTATION
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-none" style={{ background: '#a855f7' }} /> SERVICE
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-none" style={{ background: '#10b981' }} /> DOMAIN
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-none" style={{ background: '#f59e0b' }} /> INFRASTRUCTURE
          </div>
          <div className="flex items-center gap-2 pt-1 border-t border-[var(--border)] text-[#b91c1c] dark:text-[#ef4444]">
            <span className="w-2 h-2 rounded-none bg-[#ef4444] shadow-[0_0_8px_#ef4444] animate-pulse" /> CYCLIC / HIGH RISK
          </div>
        </div>

        {/* Node Inspector Side Sheet */}
        <AnimatePresence>
          {selectedNode && (
            <motion.div
              initial={{ x: 420, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 420, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="absolute top-0 right-0 bottom-0 w-96 max-w-[90vw] z-40 border-l"
              style={{
                background: 'rgba(2, 6, 23, 0.95)',
                backdropFilter: 'blur(28px)',
                borderColor: 'rgba(255, 255, 255, 0.15)',
              }}
            >
              <NodeInspectorPanel
                node={selectedNode}
                onClose={() => setSelectedNode(null)}
                onSelectNode={(id) => {
                  const target = result?.graph.nodes.find((n) => n.id === id)
                  if (target) setSelectedNode(target)
                }}
                onHighlightBlastRadius={handleHighlightBlastRadius}
                isBlastRadiusActive={blastRadiusNodeId === selectedNode.id}
                allSuggestions={allSuggestions}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Ask ArchLens Panel */}
        <AskArchLensPanel
          isOpen={isAskArchLensOpen}
          onClose={() => setIsAskArchLensOpen(false)}
          analysisId={result?.repo_id}
          onSelectNode={(id) => {
            const n = result?.graph.nodes.find((node) => node.id === id)
            if (n) setSelectedNode(n)
          }}
        />
      </div>
    </div>
  )
}
