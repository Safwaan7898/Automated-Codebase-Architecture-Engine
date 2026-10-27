import { useState, useMemo } from 'react'
import { Info, Sparkles, AlertCircle, RefreshCw, Code2, Download } from 'lucide-react'
import type { GraphNode } from '../../types'
import { AIBadge, AIFallback } from '../ui/AILabel'
import { aiApi } from '../../api/client'

interface LanguageBreakdownDonutProps {
  nodes: GraphNode[]
  languages?: Record<string, number>
  loading?: boolean
  error?: string | null
}

interface LanguageSlice {
  language: string
  files: number
  loc: number
  percentage: number
  locPercentage: number
  color: string
  startAngle: number
  endAngle: number
}

const LANGUAGE_PALETTE: Record<string, string> = {
  python: '#3B82F6', // Blue
  typescript: '#3178C6', // TS Blue
  javascript: '#F7DF1E', // Yellow
  go: '#00ADD8', // Cyan
  golang: '#00ADD8',
  java: '#ED8B00', // Orange
  rust: '#DEA584', // Rust Brown
  c: '#555555',
  cpp: '#F34B7D',
  csharp: '#178600',
  html: '#E34F26',
  css: '#1572B6',
  ruby: '#CC342D',
  php: '#4F5D95',
  shell: '#89E051',
  unknown: '#9CA3AF',
}

function getLanguageColor(lang: string, index: number): string {
  const normalized = lang.toLowerCase().trim()
  if (LANGUAGE_PALETTE[normalized]) {
    return LANGUAGE_PALETTE[normalized]
  }
  const fallbackColors = ['#10B981', '#6366F1', '#EC4899', '#8B5CF6', '#14B8A6', '#F59E0B']
  return fallbackColors[index % fallbackColors.length]
}

export function LanguageBreakdownDonut({
  nodes,
  languages: initialLanguages,
  loading,
  error,
}: LanguageBreakdownDonutProps) {
  const [selectedLang, setSelectedLang] = useState<string | null>(null)
  const [hoveredLang, setHoveredLang] = useState<string | null>(null)
  const [aiExplanation, setAiExplanation] = useState<string | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiIsGenerated, setAiIsGenerated] = useState(false)

  // Aggregate stats per language
  const { slices, totalFiles, totalLoc } = useMemo(() => {
    const fileCounts: Record<string, number> = {}
    const locCounts: Record<string, number> = {}

    // First use nodes if available
    if (nodes && nodes.length > 0) {
      for (const n of nodes) {
        let lang = n.language || 'unknown'
        if (lang === 'unknown' && n.file_path) {
          const ext = n.file_path.split('.').pop()?.toLowerCase()
          if (ext === 'py') lang = 'python'
          else if (ext === 'ts' || ext === 'tsx') lang = 'typescript'
          else if (ext === 'js' || ext === 'jsx') lang = 'javascript'
          else if (ext === 'go') lang = 'go'
          else if (ext === 'java') lang = 'java'
        }
        fileCounts[lang] = (fileCounts[lang] || 0) + 1
        locCounts[lang] = (locCounts[lang] || 0) + (n.loc || 50)
      }
    } else if (initialLanguages && Object.keys(initialLanguages).length > 0) {
      for (const [lang, count] of Object.entries(initialLanguages)) {
        fileCounts[lang] = count
        locCounts[lang] = count * 100 // Estimate
      }
    }

    const tFiles = Object.values(fileCounts).reduce((a, b) => a + b, 0)
    const tLoc = Object.values(locCounts).reduce((a, b) => a + b, 0)

    const entries = Object.entries(fileCounts).sort((a, b) => b[1] - a[1])
    let currentAngle = 0

    const computedSlices: LanguageSlice[] = entries.map(([lang, count], idx) => {
      const percentage = tFiles > 0 ? (count / tFiles) * 100 : 0
      const locPercentage = tLoc > 0 ? ((locCounts[lang] || 0) / tLoc) * 100 : 0
      const angleSpan = (percentage / 100) * 360
      const startAngle = currentAngle
      const endAngle = currentAngle + angleSpan
      currentAngle = endAngle

      return {
        language: lang,
        files: count,
        loc: locCounts[lang] || 0,
        percentage: Math.round(percentage * 10) / 10,
        locPercentage: Math.round(locPercentage * 10) / 10,
        color: getLanguageColor(lang, idx),
        startAngle,
        endAngle,
      }
    })

    return { slices: computedSlices, totalFiles: tFiles, totalLoc: tLoc }
  }, [nodes, initialLanguages])

  const activeSlice = useMemo(() => {
    const target = hoveredLang || selectedLang
    if (target) {
      return slices.find((s) => s.language === target) || null
    }
    return slices[0] || null
  }, [hoveredLang, selectedLang, slices])

  const handleAiExplain = async () => {
    setAiLoading(true)
    try {
      const res = await aiApi.explainMetric(
        'polyglot_language_distribution',
        slices[0]?.percentage || 100,
        undefined,
        {
          primary_language: slices[0]?.language,
          total_languages: slices.length,
          total_loc: totalLoc,
          languages: slices.map((s) => `${s.language} (${s.percentage}%)`).join(', '),
        }
      )
      setAiExplanation(res.explanation)
      setAiIsGenerated(true)
    } catch {
      setAiExplanation(
        `Deterministic analysis: Codebase is predominantly composed of ${slices[0]?.language || 'unknown'} (${slices[0]?.percentage || 100}% of files, ${slices[0]?.loc.toLocaleString() || 0} LOC). Across ${slices.length} detected languages, polyglot boundaries introduce foreign function interface (FFI) and cross-runtime serialization complexity.`
      )
      setAiIsGenerated(false)
    } finally {
      setAiLoading(false)
    }
  }

  const handleExportSvg = () => {
    const svgEl = document.getElementById('language-donut-svg')
    if (!svgEl) return
    const svgData = new XMLSerializer().serializeToString(svgEl)
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'archlens-language-breakdown.svg'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div className="glass-card p-8 rounded-2xl flex flex-col items-center justify-center min-h-[320px] text-muted">
        <RefreshCw size={24} className="animate-spin text-accent mb-2" />
        <span className="text-xs font-mono">Aggregating polyglot language distribution...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass-card p-6 rounded-2xl border-red-500/20 text-red-400 flex items-center gap-2 text-xs">
        <AlertCircle size={16} />
        <span>Failed to compute language breakdown: {error}</span>
      </div>
    )
  }

  if (slices.length === 0) {
    return (
      <div className="glass-card p-8 rounded-2xl text-center text-muted min-h-[280px] flex flex-col items-center justify-center">
        <Code2 size={36} className="opacity-30 mb-2" />
        <div className="text-sm font-bold text-[var(--text-primary)]">No Language Data</div>
        <div className="text-xs text-muted mt-1">Load or ingest a repository to view source language composition.</div>
      </div>
    )
  }

  // Helper function to create SVG donut arc path
  const createArcPath = (startDeg: number, endDeg: number, outerR: number, innerR: number, cx: number, cy: number) => {
    // If nearly a full circle, SVG arc needs small delta to avoid start=end collapse
    const delta = endDeg - startDeg
    const effectiveEnd = delta >= 359.99 ? startDeg + 359.99 : endDeg

    const startRad = ((startDeg - 90) * Math.PI) / 180
    const endRad = ((effectiveEnd - 90) * Math.PI) / 180

    const x1 = cx + outerR * Math.cos(startRad)
    const y1 = cy + outerR * Math.sin(startRad)
    const x2 = cx + outerR * Math.cos(endRad)
    const y2 = cy + outerR * Math.sin(endRad)

    const x3 = cx + innerR * Math.cos(endRad)
    const y3 = cy + innerR * Math.sin(endRad)
    const x4 = cx + innerR * Math.cos(startRad)
    const y4 = cy + innerR * Math.sin(startRad)

    const largeArc = delta > 180 ? 1 : 0

    return `M ${x1} ${y1} A ${outerR} ${outerR} 0 ${largeArc} 1 ${x2} ${y2} L ${x3} ${y3} A ${innerR} ${innerR} 0 ${largeArc} 0 ${x4} ${y4} Z`
  }

  return (
    <div className="glass-card rounded-2xl p-6 border border-[var(--border)] dark:border-white/10 space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Code2 size={18} className="text-accent" />
            <h2 className="text-base font-bold tracking-tight text-[var(--text-primary)]">
              Language Breakdown & Polyglot Share
            </h2>
            <span className="badge text-[10px] font-mono bg-surface-2 dark:bg-white/5 border border-[var(--border)] text-muted">
              {slices.length} {slices.length === 1 ? 'Language' : 'Languages'}
            </span>
          </div>
          <p className="text-xs text-muted">
            Proportional codebase volume across programming languages measured by file density and line counts.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportSvg}
            className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-surface-2 dark:bg-white/5 border border-[var(--border)] dark:border-white/10 hover:border-accent text-muted hover:text-[var(--text-primary)] flex items-center gap-1.5 transition-colors"
            title="Export vector SVG"
          >
            <Download size={12} />
            <span className="hidden sm:inline">Export SVG</span>
          </button>

          <button
            onClick={handleAiExplain}
            disabled={aiLoading}
            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-lime-500/15 dark:bg-accent/15 border border-lime-600/30 dark:border-accent/30 text-lime-800 dark:text-accent hover:bg-lime-500/25 dark:hover:bg-accent/25 flex items-center gap-1.5 transition-all shadow-sm"
          >
            {aiLoading ? <RefreshCw size={12} className="animate-spin" /> : <Sparkles size={12} />}
            <span>Explain Breakdown</span>
          </button>
        </div>
      </div>

      {/* AI Explanation Banner */}
      {aiExplanation && (
        <div className="p-4 rounded-xl bg-surface-2 dark:bg-white/[0.03] border border-lime-600/20 dark:border-accent/20 space-y-2 animate-fade-in">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-lime-800 dark:text-accent flex items-center gap-1.5">
              <Sparkles size={13} /> Polyglot Architectural Insights
            </span>
            {aiIsGenerated ? (
              <AIBadge label="AI-generated" size="xs" />
            ) : (
              <AIFallback message="Deterministic fallback" />
            )}
          </div>
          <p className="text-xs text-muted leading-relaxed">{aiExplanation}</p>
        </div>
      )}

      {/* Main Grid: Donut Chart + Table */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* Left: SVG Donut (5 cols) */}
        <div className="lg:col-span-5 flex flex-col items-center justify-center relative">
          <svg
            id="language-donut-svg"
            viewBox="0 0 320 320"
            className="w-64 h-64 sm:w-72 sm:h-72 select-none"
            aria-label="Language Breakdown Donut Chart"
          >
            <g transform="translate(0, 0)">
              {slices.map((slice) => {
                const isSelected = selectedLang === slice.language
                const isHovered = hoveredLang === slice.language
                const outerR = isSelected || isHovered ? 145 : 140
                const innerR = 90
                const pathD = createArcPath(slice.startAngle, slice.endAngle, outerR, innerR, 160, 160)

                return (
                  <path
                    key={slice.language}
                    d={pathD}
                    fill={slice.color}
                    fillOpacity={isSelected || isHovered ? 0.95 : 0.8}
                    stroke="var(--bg-primary, #0f172a)"
                    strokeWidth={2}
                    className="cursor-pointer transition-all duration-200 outline-none focus:stroke-accent focus:stroke-4"
                    tabIndex={0}
                    role="button"
                    aria-label={`${slice.language}: ${slice.percentage}% (${slice.files} files, ${slice.loc} LOC)`}
                    onMouseEnter={() => setHoveredLang(slice.language)}
                    onMouseLeave={() => setHoveredLang(null)}
                    onClick={() => setSelectedLang(selectedLang === slice.language ? null : slice.language)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        setSelectedLang(selectedLang === slice.language ? null : slice.language)
                      }
                    }}
                  />
                )
              })}

              {/* Donut Hole Center Text */}
              <circle cx={160} cy={160} r={86} fill="var(--bg-surface, #1e293b)" opacity={0.6} />
              {activeSlice ? (
                <>
                  <text
                    x={160}
                    y={145}
                    textAnchor="middle"
                    className="text-xs uppercase font-bold tracking-wider fill-muted"
                  >
                    {activeSlice.language}
                  </text>
                  <text
                    x={160}
                    y={172}
                    textAnchor="middle"
                    className="text-2xl font-bold font-mono fill-[var(--text-primary)]"
                  >
                    {activeSlice.percentage}%
                  </text>
                  <text
                    x={160}
                    y={192}
                    textAnchor="middle"
                    className="text-[11px] font-mono fill-muted"
                  >
                    {activeSlice.files} files / {activeSlice.loc.toLocaleString()} LOC
                  </text>
                </>
              ) : (
                <>
                  <text
                    x={160}
                    y={150}
                    textAnchor="middle"
                    className="text-xs uppercase font-bold tracking-wider fill-muted"
                  >
                    Total Volume
                  </text>
                  <text
                    x={160}
                    y={175}
                    textAnchor="middle"
                    className="text-xl font-bold font-mono fill-[var(--text-primary)]"
                  >
                    {totalLoc.toLocaleString()}
                  </text>
                  <text
                    x={160}
                    y={195}
                    textAnchor="middle"
                    className="text-[11px] font-mono fill-muted"
                  >
                    {totalFiles} modules
                  </text>
                </>
              )}
            </g>
          </svg>
        </div>

        {/* Right: Breakdown Table (7 cols) */}
        <div className="lg:col-span-7 space-y-2 overflow-x-auto">
          <table className="w-full text-left text-xs font-mono border-collapse">
            <thead>
              <tr className="border-b border-[var(--border)] dark:border-white/10 text-muted text-[10px] uppercase font-bold">
                <th className="pb-2 pl-2">Language</th>
                <th className="pb-2 text-right">Files</th>
                <th className="pb-2 text-right">Lines (LOC)</th>
                <th className="pb-2 text-right">Share</th>
                <th className="pb-2 pr-2 pl-4">Distribution</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]/50 dark:divide-white/5">
              {slices.map((slice) => {
                const isSelected = selectedLang === slice.language
                const isHovered = hoveredLang === slice.language

                return (
                  <tr
                    key={slice.language}
                    onClick={() => setSelectedLang(selectedLang === slice.language ? null : slice.language)}
                    onMouseEnter={() => setHoveredLang(slice.language)}
                    onMouseLeave={() => setHoveredLang(null)}
                    tabIndex={0}
                    role="row"
                    className={`cursor-pointer transition-colors duration-150 ${
                      isSelected || isHovered
                        ? 'bg-accent/10 dark:bg-white/[0.06]'
                        : 'hover:bg-surface-2 dark:hover:bg-white/[0.02]'
                    }`}
                  >
                    <td className="py-2 pl-2 font-bold flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: slice.color }}
                      />
                      <span className="capitalize text-[var(--text-primary)]">{slice.language}</span>
                    </td>
                    <td className="py-2 text-right text-muted">{slice.files.toLocaleString()}</td>
                    <td className="py-2 text-right text-muted">{slice.loc.toLocaleString()}</td>
                    <td className="py-2 text-right font-bold text-accent">{slice.percentage}%</td>
                    <td className="py-2 pr-2 pl-4">
                      <div className="w-full bg-surface-2 dark:bg-white/5 h-2 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-300"
                          style={{
                            width: `${slice.percentage}%`,
                            backgroundColor: slice.color,
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* "How to read this" Caption */}
      <div className="p-3.5 rounded-xl bg-surface-2 dark:bg-white/[0.02] border border-[var(--border)] dark:border-white/5 text-xs text-muted flex items-start gap-2.5">
        <Info size={16} className="text-accent shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <strong className="text-[var(--text-primary)]">How to read this chart:</strong> Multi-language (polyglot) codebases require separate toolchains, build environments, and parser rules. Concentrated architectures (90%+ single language) exhibit lower boundary overhead, whereas split architectures benefit from strict layer decoupling and interface contracts to prevent leaky cross-runtime dependencies.
        </div>
      </div>
    </div>
  )
}
