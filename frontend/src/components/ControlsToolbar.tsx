import React from 'react'
import {
  Search,
  Layers,
  Box,
  CircleDot,
  RotateCcw,
  Sliders,
  Filter,
  Zap,
  FileDown,
} from 'lucide-react'

interface ControlsToolbarProps {
  searchQuery: string
  onSearchChange: (q: string) => void
  selectedSeverity: string
  onSeverityChange: (s: string) => void
  selectedLayer: string
  onLayerChange: (l: string) => void
  is3DMode: boolean
  onToggle3D: () => void
  isLayerBands: boolean
  onToggleLayerBands: () => void
  clustersCollapsed: boolean
  onToggleClusters: () => void
  timelineStep: number
  onTimelineChange: (step: number) => void
  onResetView: () => void
  nodeCount: number
  edgeCount: number
  fps?: number
  wsConnected: boolean
  onOpenReports?: () => void
}

export const ControlsToolbar: React.FC<ControlsToolbarProps> = ({
  searchQuery,
  onSearchChange,
  selectedSeverity,
  onSeverityChange,
  selectedLayer,
  onLayerChange,
  is3DMode,
  onToggle3D,
  isLayerBands,
  onToggleLayerBands,
  clustersCollapsed,
  onToggleClusters,
  timelineStep,
  onTimelineChange,
  onResetView,
  nodeCount,
  edgeCount,
  fps = 60,
  wsConnected,
  onOpenReports,
}) => {
  return (
    <div className="w-full bg-[#0a0a0a]/95 backdrop-blur-md border-b border-white/10 px-4 md:px-8 py-3 flex flex-wrap items-center justify-between gap-4 z-30">
      {/* Left: Search & Quick Filters */}
      <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[280px]">
        {/* Search Input */}
        <div className="relative min-w-[220px] max-w-xs flex-1">
          <Search className="w-4 h-4 text-white/40 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            id="graph-search-input"
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search nodes, classes, modules…"
            className="w-full bg-[#141414] border border-white/10 rounded-full pl-9 pr-4 py-1.5 text-xs font-mono text-white placeholder-white/65 focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>

        {/* Severity Filter */}
        <div className="flex items-center gap-1.5">
          <Filter className="w-3.5 h-3.5 text-white/40 hidden sm:block" />
          <select
            id="severity-filter-select"
            value={selectedSeverity}
            onChange={(e) => onSeverityChange(e.target.value)}
            className="bg-[#141414] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs font-mono text-white/80 focus:outline-none cursor-pointer"
          >
            <option value="all">Risk: All Severities</option>
            <option value="critical">🔴 Critical Risk (80+)</option>
            <option value="high">🟠 High Risk (60-79)</option>
            <option value="medium">🟡 Medium Risk (30-59)</option>
            <option value="vulnerable">⚠️ All Vulnerable</option>
            <option value="clean">🟢 Clean Nodes</option>
          </select>
        </div>

        {/* Layer Filter */}
        <div>
          <select
            id="layer-filter-select"
            value={selectedLayer}
            onChange={(e) => onLayerChange(e.target.value)}
            className="bg-[#141414] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs font-mono text-white/80 focus:outline-none cursor-pointer"
          >
            <option value="all">Layers: All Bands</option>
            <option value="Presentation">Presentation Layer</option>
            <option value="Service">Service Layer</option>
            <option value="Domain">Domain Layer</option>
            <option value="Data / Infrastructure">Data / Infra Layer</option>
          </select>
        </div>
      </div>

      {/* Center: Graph Layout Toggles */}
      <div className="flex items-center gap-2">
        {/* 2D / 3D Toggle */}
        <button
          id="toggle-2d-3d-btn"
          onClick={onToggle3D}
          className={`px-3 py-1.5 rounded-lg border text-xs font-mono uppercase tracking-wider flex items-center gap-1.5 transition-colors duration-150 cursor-pointer ${
            is3DMode
              ? 'bg-blue-600/30 border-blue-500 text-blue-300 font-semibold shadow-blue-glow'
              : 'bg-[#141414] border-white/10 text-white/70 hover:text-white'
          }`}
          title="Toggle 2D Canvas vs 3D WebGL Force Simulation"
        >
          <Box className="w-3.5 h-3.5" />
          <span>{is3DMode ? '3D WebGL' : '2D Canvas'}</span>
        </button>

        {/* Layer Bands Layout Toggle */}
        <button
          id="toggle-layer-bands-btn"
          onClick={onToggleLayerBands}
          className={`px-3 py-1.5 rounded-lg border text-xs font-mono uppercase tracking-wider flex items-center gap-1.5 transition-colors duration-150 cursor-pointer ${
            isLayerBands
              ? 'bg-amber-500/20 border-amber-500 text-amber-300 font-semibold'
              : 'bg-[#141414] border-white/10 text-white/70 hover:text-white'
          }`}
          title="Toggle horizontal architectural layer bands"
        >
          <Layers className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Layer View</span>
        </button>

        {/* Cluster Collapse/Expand */}
        <button
          onClick={onToggleClusters}
          className={`px-3 py-1.5 rounded-lg border text-xs font-mono uppercase tracking-wider flex items-center gap-1.5 transition-colors duration-150 cursor-pointer ${
            clustersCollapsed
              ? 'bg-purple-500/20 border-purple-500 text-purple-300'
              : 'bg-[#141414] border-white/10 text-white/70 hover:text-white'
          }`}
          title="Collapse or expand Louvain community clusters"
        >
          <CircleDot className="w-3.5 h-3.5" />
          <span className="hidden md:inline">{clustersCollapsed ? 'Expand' : 'Clusters'}</span>
        </button>

        {/* Reset View */}
        <button
          onClick={onResetView}
          className="p-1.5 rounded-lg bg-[#141414] border border-white/10 text-white/70 hover:text-white transition-colors cursor-pointer"
          title="Reset zoom & camera"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>

        {/* Generate / Download Report Modal Button */}
        {onOpenReports && (
          <button
            id="toolbar-download-report-btn"
            onClick={onOpenReports}
            className="px-2.5 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/40 text-blue-300 text-xs font-mono uppercase tracking-wider flex items-center gap-1.5 transition-colors duration-150 cursor-pointer"
            title="Download Report & View Audit History"
          >
            <FileDown className="w-3.5 h-3.5 text-blue-400" />
            <span className="hidden lg:inline">Report</span>
          </button>
        )}
      </div>

      {/* Right: Timeline Slider, Status & FPS */}
      <div className="flex items-center gap-4">
        {/* Timeline Slider */}
        <div className="flex items-center gap-2">
          <Sliders className="w-3.5 h-3.5 text-white/40" />
          <span className="text-[10px] font-mono text-white/40 uppercase">Timeline:</span>
          <input
            type="range"
            min={1}
            max={5}
            value={timelineStep}
            onChange={(e) => onTimelineChange(Number(e.target.value))}
            className="w-20 md:w-28 accent-blue-500 cursor-pointer"
            title="Scrub architectural timeline (Git commits / ingestion stages)"
          />
          <span className="text-[10px] font-mono text-blue-400 font-bold">
            v{timelineStep}.0
          </span>
        </div>

        {/* Live WebSocket Badge */}
        <div className="flex items-center gap-2 pl-3 border-l border-white/10">
          <div
            className={`w-2 h-2 rounded-full ${
              wsConnected ? 'bg-emerald-500 shadow-[0_0_8px_#10b981]' : 'bg-amber-500'
            }`}
          />
          <span className="text-[10px] font-mono uppercase tracking-wider text-white/60 hidden xl:inline">
            {wsConnected ? 'LIVE WS' : 'POLLING'}
          </span>
        </div>

        {/* Metrics Counter Pill */}
        <div className="hidden lg:flex items-center gap-2 bg-white/5 border border-white/10 px-2.5 py-1 rounded-full text-[11px] font-mono text-white/70">
          <span>{nodeCount} Nodes</span>
          <span className="text-white/20">|</span>
          <span>{edgeCount} Edges</span>
          <span className="text-white/20">|</span>
          <span className="text-emerald-400 font-bold flex items-center gap-1">
            <Zap className="w-3 h-3" />
            {fps} FPS
          </span>
        </div>
      </div>
    </div>
  )
}
