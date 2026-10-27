import { useState, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  Activity,
  Zap,
  Globe,
  Upload,
  AlertCircle,
  FileQuestion,
  RefreshCw,
  FolderArchive,
  Clock,
  GitBranch,
  ShieldCheck,
} from 'lucide-react'
import { useAnalysisContext } from '../contexts/AnalysisContext'
import { AIExplainPanel } from '../components/AIExplainPanel'
import { AIBadge } from '../components/ui/AILabel'
import { aiApi } from '../api/client'

type HealthCategory = 'POOR' | 'FAIR' | 'GOOD' | 'EXCELLENT'

export function DashboardPage() {
  const navigate = useNavigate()
  const {
    result,
    notFoundId,
    lastIngestError,
    repoList,
    recentAnalyses,
    loadRepoGraph,
    clearAnalysis,
  } = useAnalysisContext()

  // Real-time calculation from actual AST parsed repository
  const {
    nodeCount,
    edgeCount,
    cycleCount,
    smellCount,
    healthScore,
    healthGrade,
    isInsufficient,
    healthCategory,
  } = useMemo(() => {
    if (!result) {
      return {
        nodeCount: 0,
        edgeCount: 0,
        cycleCount: 0,
        smellCount: 0,
        healthScore: null,
        healthGrade: null,
        isInsufficient: true,
        healthCategory: null as HealthCategory | null,
        healthColor: '#6b7280',
      }
    }

    const nodes = result.graph?.nodes ?? []
    const edges = result.graph?.edges ?? []
    const smells = result.smells ?? []
    const cycles = edges.filter((e) => e.is_cycle).length
    const vulns = nodes.filter((n) => n.is_vulnerable || (n.risk_score ?? 0) >= 60).length

    // Health score is computed ONLY in the backend.
    // Insufficient data applies ONLY when there are zero analysable files or zero nodes.
    // Dashboard must never show "NOT ENOUGH DATA" next to non-zero cards: derive both from nodes.length.
    const health = result.health
    const insufficient = nodes.length === 0 || health?.status === 'insufficient_data'
    const derivedScore = !insufficient
      ? (health?.score !== null && health?.score !== undefined ? health.score : 100.0)
      : null
    const derivedGrade = !insufficient
      ? (health?.grade || (derivedScore !== null && derivedScore >= 90 ? 'A+' : 'A'))
      : null

    let cat: HealthCategory | null = null
    let col = '#6b7280'

    if (!insufficient && derivedScore !== null) {
      if (derivedScore >= 90) {
        cat = 'EXCELLENT'
        col = '#55a630'
      } else if (derivedScore >= 75) {
        cat = 'GOOD'
        col = '#aacc00'
      } else if (derivedScore >= 60) {
        cat = 'FAIR'
        col = '#ffb703'
      } else {
        cat = 'POOR'
        col = '#ff2d20'
      }
    }

    return {
      nodeCount: nodes.length,
      edgeCount: edges.length,
      cycleCount: cycles,
      smellCount: smells.length,
      vulnCount: vulns,
      healthScore: derivedScore,
      healthGrade: derivedGrade,
      isInsufficient: insufficient,
      healthCategory: cat,
      healthColor: col,
    }
  }, [result])

  // Allow manual override for simulation / inspection
  const [selectedOverride, setSelectedOverride] = useState<HealthCategory | null>(null)

  const activeCategory: HealthCategory | null = selectedOverride || healthCategory
  const activeColor = useMemo(() => {
    if (!activeCategory) return '#6b7280'
    switch (activeCategory) {
      case 'POOR':
        return '#ff2d20'
      case 'FAIR':
        return '#ffb703'
      case 'GOOD':
        return '#aacc00'
      case 'EXCELLENT':
        return '#55a630'
    }
  }, [activeCategory])

  const activePercentage = useMemo(() => {
    if (selectedOverride) {
      switch (selectedOverride) {
        case 'POOR':
          return 45
        case 'FAIR':
          return 68
        case 'GOOD':
          return 82
        case 'EXCELLENT':
          return 95
      }
    }
    return healthScore ?? 0
  }, [selectedOverride, healthScore])

  // 16 segmented cells calculation
  const totalCells = 16
  const activeCellCount = result && !isInsufficient ? Math.round((activePercentage / 100) * totalCells) : 0

  // Calculate needle position percentage (0% to 100%)
  const needlePosition = result && !isInsufficient ? Math.min(100, Math.max(0, (activePercentage / 100) * 100)) : 0

  const isNoSupportedFiles = useMemo(() => {
    if (lastIngestError?.error) {
      const err = lastIngestError.error.toLowerCase()
      return err.includes('no python or java files') || err.includes('no valid source files') || err.includes('no supported')
    }
    return false
  }, [lastIngestError])

  return (
    <div className="min-h-screen bg-bg dark:bg-[#050505] text-text dark:text-white py-10 px-4 flex flex-col items-center selection:bg-accent selection:text-accent-contrast dark:selection:bg-[#CCFF00] dark:selection:text-[#000000] font-['Manrope',sans-serif] relative overflow-hidden pb-36">
      {/* ── Background Noise & Radial Atmosphere ──────────────────────── */}
      <div className="fixed inset-0 pointer-events-none noise-overlay z-0 opacity-20" />
      <div
        className="fixed top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] pointer-events-none z-0"
        style={{
          background: `radial-gradient(circle at 50% 0%, ${activeColor}22 0%, transparent 70%)`,
        }}
      />

      {/* ── Header Bar ─────────────────────────────────────────────────── */}
      <div className="relative z-10 max-w-4xl w-full flex flex-col sm:flex-row items-center justify-between gap-4 mb-8">
        <div>
          <span className="badge-acid text-[10px] uppercase font-mono tracking-widest inline-flex items-center gap-1.5 mb-1.5">
            <Zap size={10} /> REAL-TIME ARCHITECTURE TELEMETRY
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold uppercase tracking-tight text-text dark:text-white font-['Manrope',sans-serif]">
            SYSTEM RISK MONITOR
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/ingestion"
            className="chrome-btn px-4 py-2 text-xs font-bold inline-flex items-center gap-1.5"
          >
            <Upload size={12} />
            <span>INGEST NEW CODEBASE</span>
          </Link>
          <Link
            to="/graph"
            className="px-4 py-2 rounded-full border border-border dark:border-white/20 hover:border-accent dark:hover:border-[#CCFF00] text-xs font-mono tracking-wider transition-colors duration-150 text-text dark:text-white"
          >
            TOPOLOGY GRAPH →
          </Link>
        </div>
      </div>

      {/* ── STATE 0: NOT FOUND STATE (invalid ?analysis=<id>) ────────── */}
      {notFoundId && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          data-testid="not-found-state"
          className="relative z-10 max-w-[760px] w-full p-8 sm:p-12 text-center rounded-[48px] bg-surface dark:bg-[#0a0a0a] border border-amber-500/40 shadow-2xl mb-12"
        >
          <div className="w-16 h-16 mx-auto rounded-full bg-amber-500/15 border border-amber-500 flex items-center justify-center text-amber-400 mb-6 shadow-sm">
            <FileQuestion size={32} />
          </div>
          <h2 className="text-3xl font-bold uppercase tracking-tight mb-2 text-text dark:text-white">
            Analysis Not Found
          </h2>
          <p className="text-xs sm:text-sm text-text-muted dark:text-white/70 max-w-lg mx-auto mb-6 font-mono leading-relaxed">
            No analysis record was found for ID <code className="text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded font-mono">{notFoundId}</code>. It may have expired or not yet been analyzed.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
            <button
              onClick={() => {
                clearAnalysis()
                navigate('/ingestion')
              }}
              className="chrome-btn px-8 py-3.5 text-xs font-black tracking-widest flex items-center gap-2 cursor-pointer"
            >
              <Upload size={14} />
              <span>INGEST A CODEBASE</span>
            </button>
            <button
              onClick={clearAnalysis}
              className="px-6 py-3 rounded-full border border-border dark:border-white/20 hover:border-accent text-xs font-mono tracking-wider transition-colors duration-150 text-text dark:text-white cursor-pointer"
            >
              CLEAR & START FRESH
            </button>
          </div>
        </motion.div>
      )}

      {/* ── STATE (ii): NO SUPPORTED SOURCE FILES FOUND ──────────────── */}
      {!notFoundId && !result && isNoSupportedFiles && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          data-testid="no-supported-files-state"
          className="relative z-10 max-w-[760px] w-full p-8 sm:p-12 text-center rounded-[48px] bg-surface dark:bg-[#0a0a0a] border border-amber-500/40 shadow-2xl mb-12"
        >
          <div className="w-16 h-16 mx-auto rounded-full bg-amber-500/15 border border-amber-500 flex items-center justify-center text-amber-400 mb-6 shadow-sm">
            <FolderArchive size={32} />
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold uppercase tracking-tight mb-2 text-text dark:text-white">
            Analysis finished but no supported source files were found
          </h2>
          <div className="text-xs text-text-muted dark:text-white/70 max-w-xl mx-auto mb-6 font-mono space-y-2 bg-surface-2 dark:bg-black/60 p-4 rounded-xl border border-border dark:border-white/10 text-left">
            <div>
              <strong>Files scanned:</strong> {lastIngestError?.metadata?.file_count ?? 0} file(s)
            </div>
            <div>
              <strong>Primary detected language:</strong> {lastIngestError?.metadata?.primary_language || 'Unknown / Unsupported'}
            </div>
            <div>
              <strong>Reason:</strong> Only Python (.py) and Java (.java) source code are currently supported for deep AST topological parsing. Archives containing only binary assets, documents, nested empty folders, or unsupported languages are skipped.
            </div>
            {lastIngestError?.metadata?.warnings && lastIngestError.metadata.warnings.length > 0 && (
              <div className="text-amber-400">
                <strong>Warnings:</strong> {lastIngestError.metadata.warnings.join(' ')}
              </div>
            )}
          </div>
          <div className="flex justify-center">
            <button
              onClick={() => navigate('/ingestion')}
              className="chrome-btn px-8 py-3.5 text-xs font-black tracking-widest flex items-center gap-2 cursor-pointer"
            >
              <Upload size={14} />
              <span>INGEST ANOTHER ARCHIVE OR REPOSITORY</span>
            </button>
          </div>
        </motion.div>
      )}

      {/* ── STATE (iii): ANALYSIS FAILED (WITH RETRY BUTTON) ─────────── */}
      {!notFoundId && !result && !isNoSupportedFiles && lastIngestError && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          data-testid="analysis-failed-state"
          className="relative z-10 max-w-[760px] w-full p-8 sm:p-12 text-center rounded-[48px] bg-surface dark:bg-[#0a0a0a] border border-red-500/50 shadow-2xl mb-12"
        >
          <div className="w-16 h-16 mx-auto rounded-full bg-red-500/15 border border-red-500 flex items-center justify-center text-red-400 mb-6 shadow-sm">
            <AlertCircle size={32} />
          </div>
          <h2 className="text-3xl font-bold uppercase tracking-tight mb-3 text-red-400">
            Analysis failed
          </h2>
          <p className="text-xs sm:text-sm text-red-300/90 max-w-lg mx-auto mb-8 font-mono leading-relaxed bg-red-950/30 p-4 rounded-xl border border-red-500/30">
            {lastIngestError.error}
          </p>
          <div className="flex justify-center gap-3">
            <button
              onClick={() => navigate('/ingestion')}
              className="chrome-btn px-8 py-3.5 text-xs font-black tracking-widest flex items-center gap-2 cursor-pointer"
            >
              <RefreshCw size={14} />
              <span>RETRY INGESTION</span>
            </button>
          </div>
        </motion.div>
      )}

      {/* ── STATE (i): NO REPOSITORY ANALYSED YET (CLEAN START) ──────── */}
      {!notFoundId && !result && !lastIngestError && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          data-testid="empty-clean-start"
          className="relative z-10 max-w-[760px] w-full p-8 sm:p-12 text-center rounded-[48px] bg-surface dark:bg-[#0a0a0a] border border-border dark:border-white/15 shadow-2xl mb-12"
        >
          <div className="w-16 h-16 mx-auto rounded-full bg-accent/15 border border-accent flex items-center justify-center text-accent-text dark:text-[#CCFF00] dark:bg-[#CCFF00]/10 dark:border-[#CCFF00] mb-6 shadow-sm dark:shadow-[0_0_25px_rgba(204,255,0,0.4)]">
            <Activity size={32} />
          </div>
          <h2 className="text-3xl font-bold uppercase tracking-tight mb-3 font-['Manrope',sans-serif] text-text dark:text-white">
            No repository analysed yet
          </h2>
          <p className="text-xs sm:text-sm text-text-muted dark:text-white/70 max-w-lg mx-auto mb-8 font-mono leading-relaxed">
            Welcome to ArchLens. Connect a live GitHub repository, upload a source archive (.zip, .tar.gz), or inspect a local directory to generate dependency topology in real-time.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center items-center mb-8">
            <button
              onClick={() => navigate('/ingestion')}
              className="chrome-btn px-8 py-3.5 text-xs font-black tracking-widest flex items-center gap-2 cursor-pointer"
            >
              <Globe size={14} />
              <span>INGEST FROM GITHUB</span>
              <ArrowRight size={14} />
            </button>
            <button
              onClick={() => navigate('/ingestion')}
              className="px-6 py-3 rounded-full border border-border dark:border-white/20 hover:border-accent dark:hover:border-[#CCFF00] text-xs font-mono tracking-wider transition-colors duration-150 text-text dark:text-white cursor-pointer flex items-center gap-2"
            >
              <Upload size={14} />
              <span>UPLOAD ARCHIVE</span>
            </button>
          </div>

          {/* Recent Analyses List (User must explicitly click to open) */}
          {((recentAnalyses && recentAnalyses.length > 0) || repoList.length > 0) && (
            <div className="pt-6 border-t border-[var(--border)] dark:border-white/10 text-left w-full">
              <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted dark:text-white/60 flex items-center gap-1.5 mb-3">
                <Clock size={12} />
                Recent Analyses (Click to open):
              </span>
              <div className="flex flex-col gap-2 w-full">
                {(recentAnalyses && recentAnalyses.length > 0
                  ? recentAnalyses.slice(0, 5)
                  : repoList.slice(0, 5).map((id) => ({
                      id,
                      repo_name: id.length > 20 ? `${id.slice(0, 8)}...${id.slice(-6)}` : id,
                      branch: 'main',
                      commit_sha: null,
                      created_at: new Date().toISOString(),
                      score: null,
                      grade: null,
                      include_tests: false,
                    }))
                ).map((item) => (
                  <button
                    key={item.id}
                    onClick={() => {
                      loadRepoGraph(item.id)
                      const url = new URL(window.location.href)
                      url.searchParams.set('analysis', item.id)
                      window.history.pushState({}, '', url.toString())
                    }}
                    className="p-3 rounded-xl text-left bg-surface-2 dark:bg-white/[0.03] border border-border dark:border-white/10 hover:border-accent dark:hover:border-[#CCFF00] transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-2 group w-full"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-bold text-xs text-text dark:text-white group-hover:text-accent dark:group-hover:text-[#CCFF00] transition-colors">
                        {item.repo_name}
                      </span>
                      {item.branch && (
                        <span className="text-[11px] font-mono text-text-muted dark:text-white/60 flex items-center gap-1 bg-surface-3 dark:bg-white/5 px-2 py-0.5 rounded">
                          <GitBranch size={10} />
                          {item.branch}
                        </span>
                      )}
                      {item.commit_sha && (
                        <span className="text-[10px] font-mono text-text-muted dark:text-white/50 bg-surface-3 dark:bg-white/5 px-1.5 py-0.5 rounded">
                          {item.commit_sha}
                        </span>
                      )}
                      {item.include_tests ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                          tests included
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-neutral-500/15 text-text-muted dark:text-white/50 border border-border dark:border-white/10">
                          no tests
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 self-end sm:self-auto font-mono text-xs">
                      {item.created_at && (
                        <span className="text-[10px] text-text-muted dark:text-zinc-300">
                          {new Date(item.created_at).toLocaleDateString(undefined, {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })}
                        </span>
                      )}
                      {item.score !== null && item.score !== undefined ? (
                        <span className="font-bold text-accent-text dark:text-[#CCFF00] bg-accent/10 dark:bg-[#CCFF00]/10 px-2 py-0.5 rounded border border-accent/20 dark:border-[#CCFF00]/20">
                          {item.score}%
                        </span>
                      ) : (
                        <span className="text-text-muted dark:text-zinc-300">—</span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* ── RISK GAUGE PORTRAIT CARD ──────────────────────────────────── */}
      {/* Renders real data if result exists, or neutral empty gauge when awaiting ingestion */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        data-testid="risk-gauge-card"
        className="relative z-10 max-w-[760px] w-full mb-12 p-[3px] rounded-[64px] shadow-[0_20px_60px_rgba(0,0,0,0.9)]"
        style={{
          background: result && !isInsufficient
            ? 'linear-gradient(135deg, rgba(170,204,0,0.8) 0%, rgba(255,255,255,0.1) 40%, rgba(255,183,3,0.5) 70%, rgba(251,133,0,0.8) 100%)'
            : 'linear-gradient(135deg, rgba(107,114,128,0.4) 0%, rgba(255,255,255,0.05) 50%, rgba(107,114,128,0.2) 100%)',
        }}
      >
        {/* Inner Solid Card */}
        <div className="relative w-full rounded-[61px] bg-surface dark:bg-[#0a0a0a] overflow-hidden p-8 sm:p-12 flex flex-col items-center justify-between min-h-[640px] border border-border dark:border-none">
          {/* Atmospheric Bottom Glow with Noise Leak */}
          <div
            className="absolute -bottom-16 left-1/2 -translate-x-1/2 w-[120%] h-[350px] pointer-events-none rounded-[100%] transition-colors duration-700 blur-2xl opacity-60"
            style={{
              background: `radial-gradient(ellipse at 50% 100%, ${activeColor}70 0%, transparent 75%)`,
            }}
          />

          {/* 1. RISK / HEALTH HEADER */}
          <div className="relative z-10 flex flex-col items-center text-center mt-2">
            <span className="font-['Inter',sans-serif] font-[300] text-[20px] sm:text-[24px] tracking-[0.2em] text-text-muted dark:text-white/70 uppercase">
              {!result ? 'Status' : isInsufficient ? 'Status' : 'Health Grade'}
            </span>
            <motion.h2
              key={!result ? 'empty' : isInsufficient ? 'insufficient' : (healthGrade || activeCategory || 'grade')}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4 }}
              className={`font-['Manrope',sans-serif] font-[700] uppercase tracking-tight text-text dark:text-white leading-none my-1 select-none ${
                !result
                  ? 'text-4xl sm:text-5xl text-neutral-400 py-3'
                  : isInsufficient
                  ? 'text-4xl sm:text-5xl md:text-6xl text-amber-400 py-3'
                  : 'text-6xl sm:text-7xl md:text-[98px]'
              }`}
              style={{
                textShadow: result && !isInsufficient ? `0 0 24px ${activeColor}80, 0 0 60px ${activeColor}40` : 'none',
              }}
            >
              {!result ? 'Awaiting Ingestion' : isInsufficient ? 'Not enough data' : (healthGrade || (activeCategory === 'EXCELLENT' ? 'A' : activeCategory === 'GOOD' ? 'B' : activeCategory === 'FAIR' ? 'C' : 'F'))}
            </motion.h2>
          </div>

          {/* 2. SEGMENTED GAUGE SECTION */}
          <div className="relative z-10 w-full max-w-xl my-6">
            {/* Needle Indicator Container */}
            <div className="relative w-full h-[48px] mb-2">
              <motion.div
                className="absolute bottom-0 flex flex-col items-center -translate-x-1/2 needle-indicator"
                style={{
                  left: `${result && !isInsufficient ? needlePosition : 0}%`,
                  transitionTimingFunction: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
                }}
              >
                {/* Vertical needle line */}
                <div
                  className="w-[2px] h-[36px] rounded-t-full shadow-[0_0_10px_#ffffff]"
                  style={{ background: result && !isInsufficient ? activeColor : '#6b7280' }}
                />
                {/* Circular dot with glow */}
                <div
                  className="w-[12px] h-[12px] rounded-full border-2 border-border shadow-[0_0_12px_#ffffff]"
                  style={{ background: result && !isInsufficient ? activeColor : '#6b7280' }}
                />
              </motion.div>
            </div>

            {/* 16-Cell Horizontal Grid */}
            <div
              className="grid grid-cols-16 gap-[7px] w-full"
              style={{ gridTemplateColumns: 'repeat(16, minmax(0, 1fr))' }}
            >
              {Array.from({ length: totalCells }).map((_, index) => {
                const isActive = result && !isInsufficient && index < activeCellCount
                return (
                  <div
                    key={index}
                    className="h-[24px] rounded-[5px] transition-colors duration-300"
                    style={{
                      border: '1px solid var(--grid-cell-border, rgba(255, 255, 255, 0.14))',
                      background: isActive ? activeColor : 'var(--grid-cell-bg, rgba(255, 255, 255, 0.045))',
                      borderColor: isActive ? 'var(--grid-cell-border-active, rgba(255, 255, 255, 0.4))' : 'var(--grid-cell-border, rgba(255, 255, 255, 0.14))',
                      boxShadow: isActive
                        ? `0 0 12px ${activeColor}90, inset 0 0 8px rgba(255,255,255,0.3)`
                        : 'none',
                    }}
                  />
                )
              })}
            </div>

            {/* 4 Health Labels Below Grid */}
            <div className="flex justify-between items-center mt-3 text-[10px] font-['Inter',sans-serif] uppercase tracking-[0.16em] text-text-muted dark:text-white/60">
              <span className={activeCategory === 'POOR' ? 'text-[#b91c1c] dark:text-[#ff2d20] font-bold' : ''}>
                Poor
              </span>
              <span className={activeCategory === 'FAIR' ? 'text-[#92400e] dark:text-[#ffb703] font-bold' : ''}>Fair</span>
              <span className={activeCategory === 'GOOD' ? 'text-[#3f6212] dark:text-[#aacc00] font-bold' : ''}>
                Good
              </span>
              <span className={activeCategory === 'EXCELLENT' ? 'text-[#15803d] dark:text-[#55a630] font-bold' : ''}>
                Excellent
              </span>
            </div>
          </div>

          {/* 3. PERCENTAGE VALUE DISPLAY */}
          <div className="relative z-10 flex flex-col items-center text-center my-2 select-none">
            <div className="flex items-baseline">
              <span
                className="font-['Inter',sans-serif] font-[200] text-[100px] sm:text-[130px] md:text-[150px] leading-none tracking-tight text-[var(--text)] dark:text-white [text-shadow:0_2px_12px_rgba(0,0,0,0.15)]"
              >
                {!result ? '—' : isInsufficient ? '—' : activePercentage}
              </span>
              {result && !isInsufficient && (
                <span className="font-['Inter',sans-serif] font-[300] text-[70px] sm:text-[90px] md:text-[100px] leading-none text-[var(--text)] dark:text-white/90 ml-1">
                  %
                </span>
              )}
            </div>
            {/* Displayed strictly once: 'Architecture Health' (never duplicate 'Not enough data') */}
            <span className="font-['Inter',sans-serif] text-[15px] sm:text-[17px] tracking-[0.15em] text-[var(--text-muted)] dark:text-white/70 uppercase -mt-2">
              Architecture Health
            </span>
          </div>

          {/* 4. BOTTOM CONTROL BAR */}
          <div className="relative z-10 flex flex-wrap items-center justify-center gap-2.5 mt-8 w-full max-w-md">
            {!result ? (
              <button
                onClick={() => navigate('/ingestion')}
                className="chrome-btn px-6 py-2.5 text-xs font-bold tracking-widest flex items-center gap-2 cursor-pointer"
              >
                <Upload size={12} />
                <span>START INGESTION</span>
              </button>
            ) : (
              (['POOR', 'FAIR', 'GOOD', 'EXCELLENT'] as const).map((level) => {
                const isActive = activeCategory === level
                const btnColor =
                  level === 'POOR'
                    ? '#ff2d20'
                    : level === 'FAIR'
                    ? '#ffb703'
                    : level === 'GOOD'
                    ? '#aacc00'
                    : '#55a630'

                return (
                  <button
                    key={level}
                    onClick={() =>
                      setSelectedOverride(selectedOverride === level ? null : level)
                    }
                    className="px-4 py-2 rounded-full text-[10px] font-bold tracking-widest uppercase transition-colors duration-150 cursor-pointer"
                    style={{
                      background: 'var(--btn-risk-bg, rgba(0, 0, 0, 0.5))',
                      backdropFilter: 'blur(4px)',
                      border: `1px solid ${isActive ? btnColor : 'var(--btn-risk-border, rgba(255, 255, 255, 0.1))'}`,
                      color: isActive ? btnColor : 'var(--btn-risk-text, rgba(255, 255, 255, 0.7))',
                      boxShadow: isActive ? `0 0 14px ${btnColor}40` : 'none',
                    }}
                  >
                    {level}
                  </button>
                )
              })
            )}
            {selectedOverride && (
              <button
                onClick={() => setSelectedOverride(null)}
                className="px-3 py-1.5 rounded-full text-[9px] font-mono text-text-muted hover:text-text uppercase transition-colors"
              >
                Reset Auto
              </button>
            )}
          </div>
        </div>
      </motion.div>

      {/* ── SUB-SCORE BREAKDOWN & SCORE REASON (Under the Gauge) ────── */}
      {result && (
        <div className="relative z-10 max-w-4xl w-full mb-8 font-mono">
          {/* One-Line Reason Card */}
          <div className="p-4 sm:p-5 rounded-2xl bg-surface dark:bg-[#0a0a0a] border border-border dark:border-white/10 shadow-lg mb-4 flex items-start gap-3">
            <div className="mt-0.5 text-accent dark:text-[#CCFF00]">
              <ShieldCheck size={18} />
            </div>
            <div className="flex-1">
              <span className="text-[10px] text-text-muted dark:text-white/50 tracking-widest uppercase block mb-1">
                ARCHITECTURAL HEALTH REASON
              </span>
              <p className="text-xs sm:text-sm text-text dark:text-white leading-relaxed font-sans font-medium">
                {result.health?.summary ||
                  (isInsufficient
                    ? 'Not enough data to compute architecture health score.'
                    : `Grade ${healthGrade || 'A+'} (${healthScore ?? 100.0}/100.0) — Architecture reflects decoupled modules, low complexity, and clean dependency acyclicity.`)}
              </p>
            </div>
          </div>

          {/* Sub-Score Breakdown Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {[
              { key: 'cycles', name: 'Cycles', weight: '25%', score: result.health?.sub_scores?.cycles },
              { key: 'coupling', name: 'Coupling', weight: '20%', score: result.health?.sub_scores?.coupling },
              { key: 'complexity', name: 'Complexity', weight: '20%', score: result.health?.sub_scores?.complexity },
              { key: 'smells', name: 'Smells', weight: '20%', score: result.health?.sub_scores?.smells },
              { key: 'security', name: 'Security', weight: '15%', score: result.health?.sub_scores?.security },
            ].map((sub) => {
              const val = sub.score !== undefined && sub.score !== null ? sub.score : (isInsufficient ? null : 100.0)
              const scoreCol =
                val === null
                  ? '#6b7280'
                  : val >= 90
                  ? '#55a630'
                  : val >= 75
                  ? '#aacc00'
                  : val >= 60
                  ? '#ffb703'
                  : '#ff2d20'

              return (
                <div
                  key={sub.key}
                  className="p-3.5 rounded-xl bg-surface dark:bg-[#0a0a0a] border border-border dark:border-white/10 flex flex-col justify-between"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-text-muted dark:text-white/60 uppercase tracking-wider font-bold">
                      {sub.name}
                    </span>
                    <span className="text-[9px] text-text-muted dark:text-white/40 font-mono">
                      {sub.weight}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-1 my-1">
                    <span className="text-xl font-extrabold" style={{ color: scoreCol }}>
                      {val !== null ? val : '—'}
                    </span>
                    {val !== null && <span className="text-[10px] text-text-muted dark:text-white/50">/100</span>}
                  </div>
                  {/* Mini progress track */}
                  <div className="w-full bg-border/40 dark:bg-white/10 h-1.5 rounded-full overflow-hidden mt-1">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${val !== null ? Math.min(100, Math.max(0, val)) : 0}%`,
                        backgroundColor: scoreCol,
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── REAL CODEBASE TELEMETRY CARDS (Beneath Gauge) ─────────────── */}
      {result && (
        <div className="relative z-10 max-w-4xl w-full grid grid-cols-2 sm:grid-cols-4 gap-4 mb-16">
          <div className="p-5 rounded-2xl bg-surface dark:bg-[#0a0a0a] border border-border dark:border-white/10 shadow-lg font-mono">
            <span className="text-[10px] text-text-muted dark:text-white/50 tracking-widest uppercase block mb-1">
              PARSED COMPONENTS
            </span>
            <span className="text-3xl font-bold text-accent-text dark:text-[#CCFF00]" data-testid="parsed-nodes-count">{nodeCount}</span>
            <span className="text-[10px] text-text-muted dark:text-white/40 block mt-1">Modules & Classes</span>
          </div>

          <div className="p-5 rounded-2xl bg-surface dark:bg-[#0a0a0a] border border-border dark:border-white/10 shadow-lg font-mono">
            <span className="text-[10px] text-text-muted dark:text-white/50 tracking-widest uppercase block mb-1">
              DEPENDENCY EDGES
            </span>
            <span className="text-3xl font-bold text-sky-600 dark:text-[#00F0FF]">{edgeCount}</span>
            <span className="text-[10px] text-text-muted dark:text-white/40 block mt-1">AST Import Linkages</span>
          </div>

          <div className="p-5 rounded-2xl bg-surface dark:bg-[#0a0a0a] border border-border dark:border-white/10 shadow-lg font-mono">
            <span className="text-[10px] text-text-muted dark:text-white/50 tracking-widest uppercase block mb-1">
              CIRCULAR LOOPS
            </span>
            <span
              className={`text-3xl font-bold ${
                cycleCount > 0 ? 'text-[#ff2d20]' : 'text-[#55a630]'
              }`}
            >
              {cycleCount}
            </span>
            <span className="text-[10px] text-text-muted dark:text-white/40 block mt-1">Tarjan SCC Cycles</span>
          </div>

          <div className="p-5 rounded-2xl bg-surface dark:bg-[#0a0a0a] border border-border dark:border-white/10 shadow-lg font-mono">
            <span className="text-[10px] text-text-muted dark:text-white/50 tracking-widest uppercase block mb-1">
              ARCH SMELLS
            </span>
            <span
              className={`text-3xl font-bold ${
                smellCount > 0 ? 'text-[#ffb703]' : 'text-[#55a630]'
              }`}
            >
              {smellCount}
            </span>
            <span className="text-[10px] text-text-muted dark:text-white/40 block mt-1">Design Anti-Patterns</span>
          </div>

          {/* Scope Filter / Excluded Files Scan Details */}
          {result.files_excluded !== undefined && (
            <div
              data-testid="scan-details-scope"
              className="p-5 rounded-2xl bg-surface dark:bg-[#0a0a0a] border border-border dark:border-white/10 shadow-lg font-mono col-span-2 sm:col-span-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div>
                <span className="text-[10px] text-text-muted dark:text-white/50 tracking-widest uppercase block mb-1">
                  SCAN DETAILS / SCOPE FILTER
                </span>
                <span className="text-xl font-bold text-accent-text dark:text-[#CCFF00]" data-testid="files-excluded-count">
                  {result.files_excluded} files excluded
                </span>
                <span className="text-[11px] text-text-muted dark:text-white/40 block mt-0.5">
                  {result.include_tests ? 'Tests included in analysis' : 'Tests, fixtures, and samples excluded from analysis scope'}
                </span>
              </div>
              <div className="text-left sm:text-right text-[11px] text-text-muted dark:text-white/50 font-mono space-y-0.5 border-t sm:border-t-0 pt-2 sm:pt-0 border-border dark:border-white/10">
                <div>Parser version: <strong className="text-text dark:text-white">{result.parser_version || '1.5.0'}</strong></div>
                <div>Settings hash: <strong className="text-text dark:text-white">{result.settings_hash ? result.settings_hash.slice(0, 12) : 'default'}</strong></div>
                <div>Fingerprint: <strong className="text-text dark:text-white">{result.source_fingerprint ? result.source_fingerprint.slice(0, 12) + '...' : 'none'}</strong></div>
              </div>
            </div>
          )}

          {/* Language Support & Unsupported Files Table */}
          <div
            data-testid="language-support-table"
            className="p-5 rounded-2xl bg-surface dark:bg-[#0a0a0a] border border-border dark:border-white/10 shadow-lg font-mono col-span-2 sm:col-span-4"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] text-text-muted dark:text-white/50 tracking-widest uppercase block">
                LANGUAGE SUPPORT & FILE INVENTORY
              </span>
              <span className="text-[11px] text-accent-text dark:text-[#CCFF00] font-bold uppercase">
                Primary: {result.language || 'auto'}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="rounded-xl bg-surface-2 dark:bg-black/40 p-3 border border-border dark:border-white/10">
                <span className="text-[10px] text-text-muted dark:text-white/40 uppercase tracking-wider block mb-2 font-bold">
                  Supported Languages Detected
                </span>
                {result.languages && result.languages.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {result.languages.map((lang) => (
                      <span
                        key={lang}
                        className="px-2.5 py-1 rounded-md text-[11px] font-bold uppercase bg-accent/10 text-accent-text dark:text-[#CCFF00] border border-accent/20"
                      >
                        {lang}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-text-muted dark:text-white/50 text-[11px]">
                    {result.language && result.language !== 'auto' ? result.language.toUpperCase() : 'Python / Java / JS'}
                  </span>
                )}
              </div>

              <div className="rounded-xl bg-surface-2 dark:bg-black/40 p-3 border border-border dark:border-white/10">
                <span className="text-[10px] text-text-muted dark:text-white/40 uppercase tracking-wider block mb-2 font-bold">
                  Unsupported Files Inventory
                </span>
                {result.unsupported_files && Object.keys(result.unsupported_files).length > 0 ? (
                  <div className="space-y-1 max-h-28 overflow-y-auto pr-1">
                    {Object.entries(result.unsupported_files).map(([ext, count]) => (
                      <div key={ext} className="flex justify-between items-center text-[11px]">
                        <span className="text-text-muted dark:text-white/70 font-mono">{ext || '(no ext)'}</span>
                        <span className="font-bold text-text dark:text-white">{count} file{count > 1 ? 's' : ''}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <span className="text-text-muted dark:text-white/50 text-[11px]">
                    No unsupported files detected in active scope.
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── AI EXECUTIVE SUMMARY CARD ──────────────────────────────────── */}
      {result && !isInsufficient && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="relative z-10 max-w-4xl w-full mb-8"
          data-testid="ai-executive-summary-card"
        >
          <div
            className="p-5 rounded-2xl font-mono"
            style={{
              background: 'rgba(198,244,50,0.04)',
              border: '1px solid rgba(198,244,50,0.2)',
              borderLeft: '3px solid var(--accent)',
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                Executive Status Briefing
              </span>
              <AIBadge label="AI-generated" />
            </div>
            <AIExplainPanel
              label="Generate Executive Summary"
              fetch={async () => {
                try {
                  const topHotspots = (result?.graph?.nodes ?? [])
                    .sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0))
                    .slice(0, 3)
                    .map((n) => n.id)
                  const summary = await aiApi.getDashboardSummary(
                    healthScore ?? 0,
                    healthGrade ?? 'N/A',
                    smellCount,
                    cycleCount,
                    topHotspots
                  )
                  return { explanation: summary.summary ?? 'AI unavailable' }
                } catch {
                  return null
                }
              }}
              enabled={!!result && !isInsufficient}
            />
          </div>
        </motion.div>
      )}
    </div>
  )
}
export default DashboardPage
