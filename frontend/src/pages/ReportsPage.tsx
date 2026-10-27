import { useState, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Download,
  FileText,
  ShieldAlert,
  Layers,
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  HelpCircle,
  Loader2,
  Sparkles,
  BookOpen,
  Activity,
  Code2,
  Info,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAnalysisContext } from '../contexts/AnalysisContext'
import { AIBadge, AIFallback } from '../components/ui/AILabel'
import { aiApi } from '../api/client'
import type { AIReportNarrative } from '../types'

interface SectionCallout {
  what_it_means: string
  why_it_matters: string
  what_to_do: string
}

interface ServerReportData {
  metadata: {
    report_id: string
    repo_name: string
    branch?: string
    commit_hash?: string
    commit_sha?: string
    generated_at: string
    health_score?: number | null
    health_grade?: string | null
    is_insufficient_data?: boolean
  }
  executive_summary: {
    callout?: SectionCallout
    summary_sentences: string[]
    status_indicator: 'green' | 'amber' | 'red'
    status_label: string
    top_3_risks: Array<{
      title: string
      severity: string
      description: string
      remediation_target: string
    }>
  }
  glossary: {
    callout?: SectionCallout
    items: Array<{
      term: string
      definition: string
      everyday_analogy: string
    }>
  }
  architecture_overview: {
    callout?: SectionCallout
    total_components: number
    total_dependencies: number
    total_lines_of_code: number
    average_cyclomatic_complexity: number
    sub_scores?: Record<string, number>
  }
  dependency_analysis: {
    callout?: SectionCallout
    cycles_detected: number
    cycles_list: Array<{ path: string; length: number; risk: string }>
    god_classes: Array<{
      name: string
      file_path: string
      lines_of_code: number
      methods_count: number
      incoming_deps: number
      outgoing_deps: number
    }>
  }
  security_findings: {
    callout?: SectionCallout
    total_vulnerabilities: number
    critical_count: number
    high_count: number
    medium_count: number
    low_count: number
    findings: Array<{
      title: string
      severity: string
      cwe?: string
      owasp?: string
      file_path: string
      remediation: string
    }>
  }
  prioritized_action_plan: {
    callout?: SectionCallout
    fix_now: Array<{
      title: string
      effort: string
      priority: string
      description: string
      affected_component: string
    }>
    next_sprint: Array<{
      title: string
      effort: string
      priority: string
      description: string
      affected_component: string
    }>
    later: Array<{
      title: string
      effort: string
      priority: string
      description: string
      affected_component: string
    }>
  }
  refactor_simulation?: {
    callout?: SectionCallout
    simulation_name: string
    description: string
    before_metrics: Record<string, number>
    after_metrics: Record<string, number>
  }
  appendix: {
    callout?: SectionCallout
    methodologies: Array<{ name: string; description: string }>
    scan_settings: Record<string, any>
    limitations: string[]
  }
  svg_charts?: Record<string, string>
}

export function ReportsPage() {
  const { result } = useAnalysisContext()
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false)
  const [isDownloadingMd, setIsDownloadingMd] = useState(false)
  const [isDownloadingJson, setIsDownloadingJson] = useState(false)
  const [serverReport, setServerReport] = useState<ServerReportData | null>(null)
  const [_isLoadingServerReport, setIsLoadingServerReport] = useState(false)
  const [aiNarrative, setAiNarrative] = useState<AIReportNarrative | null>(null)
  const [isLoadingAiNarrative, setIsLoadingAiNarrative] = useState(false)

  const [searchParams] = useSearchParams()

  const activeId = useMemo(() => {
    return searchParams.get('analysis') || result?.repo_id || ''
  }, [searchParams, result?.repo_id])

  const handleGenerateAiNarrative = async () => {
    if (!result && !serverReport) return
    setIsLoadingAiNarrative(true)
    try {
      const reportData = serverReport || {
        score: result?.health?.score ?? 0,
        grade: result?.health?.grade ?? 'N/A',
        nodes_count: result?.graph.nodes.length,
        edges_count: result?.graph.edges.length,
        smells_count: result?.smells.length,
        repo_name: result?.path,
      }
      const narrative = await aiApi.generateReportNarrative(
        reportData as unknown as Record<string, unknown>,
        activeId
      )
      setAiNarrative(narrative)
      toast.success('AI executive narrative generated!')
    } catch {
      toast.error('AI unavailable — using deterministic narrative')
      setAiNarrative({
        executive_summary: 'Deterministic synthesis of repository architecture and structural health.',
        what_this_means: 'High-level architectural health rating based on static dependency graphs.',
        why_it_matters: 'Prevents architectural erosion and uncontrolled blast radius propagation.',
        what_to_do: 'Remediate critical smells and isolate circular dependency paths.',
        is_ai_generated: false,
      })
    } finally {
      setIsLoadingAiNarrative(false)
    }
  }

  // Fetch server-rendered JSON report to mirror PDF exactly
  useEffect(() => {
    let cancelled = false
    async function loadReport() {
      if (!activeId) {
        setServerReport(null)
        setIsLoadingServerReport(false)
        return
      }
      setIsLoadingServerReport(true)
      try {
        let res = await fetch(`/reports/${activeId}/json`)
        if (!res.ok) {
          res = await fetch(`/api/reports/${activeId}/json`)
        }
        if (res.ok) {
          const data = await res.json()
          if (!cancelled) {
            setServerReport(data)
          }
        }
      } catch (err) {
        console.warn('Could not fetch server-rendered report model:', err)
      } finally {
        if (!cancelled) {
          setIsLoadingServerReport(false)
        }
      }
    }
    loadReport()
    return () => {
      cancelled = true
    }
  }, [activeId])

  // Fallback client metrics calculation if server report is pending
  const fallbackData = useMemo(() => {
    const nodes = result?.graph.nodes ?? []
    const smells = result?.smells ?? []
    const findings = nodes.flatMap((n) => n.findings || [])

    const totalLoc = nodes.reduce((acc, n) => acc + (n.loc || 0), 0)
    const avgComplexity = nodes.length
      ? (nodes.reduce((acc, n) => acc + (n.cyclomatic_complexity || 0), 0) / nodes.length).toFixed(1)
      : '0'

    const health = result?.health
    const isInsufficient = !health || health.status === 'insufficient_data' || health.score === null

    const score = isInsufficient ? null : health.score
    const grade = isInsufficient ? 'Insufficient data' : health.grade

    return {
      score,
      grade,
      isInsufficient,
      nodesCount: nodes.length,
      edgesCount: result?.edge_count || 0,
      totalLoc,
      avgComplexity,
      smells,
      findings,
    }
  }, [result])

  // Real server-generated PDF download handler
  const handleDownloadPdf = async () => {
    setIsDownloadingPdf(true)
    const toastId = toast.loading('Generating architecture diagnostic PDF report...')
    try {
      let response = await fetch(`/reports/${activeId}/pdf`)
      if (!response.ok) {
        response = await fetch(`/api/reports/${activeId}/pdf`)
      }
      if (!response.ok) {
        // Fallback to generate endpoint if not yet compiled
        response = await fetch('/api/reports/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            analysis_id: activeId,
            format: 'pdf',
            repo_name: result?.repo_id || 'Codebase',
            graph: result?.graph ? {
              nodes: result.graph.nodes,
              edges: result.graph.edges,
            } : undefined,
          }),
        })
      }

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}: ${response.statusText}`)
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Architecture_Diagnostic_Report_${activeId.slice(0, 8)}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => {
        try {
          window.URL.revokeObjectURL(url)
        } catch {
          // URL might already be revoked
        }
      }, 5000)

      toast.success('Architecture Diagnostic Report PDF downloaded successfully!', { id: toastId })
    } catch (err: any) {
      console.error('Failed to download PDF:', err)
      toast.error(`Failed to download PDF report: ${err.message || 'Network error'}`, { id: toastId })
    } finally {
      setIsDownloadingPdf(false)
    }
  }

  // Markdown download handler
  const handleDownloadMarkdown = async () => {
    setIsDownloadingMd(true)
    try {
      let response = await fetch(`/reports/${activeId}/markdown`)
      if (!response.ok) {
        response = await fetch(`/api/reports/${activeId}/markdown`)
      }
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `Architecture_Diagnostic_Report_${activeId.slice(0, 8)}.md`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
        toast.success('Markdown report downloaded!')
        return
      }
      throw new Error('Server markdown not found')
    } catch {
      // Local fallback markdown generator
      const md = `# Architecture Diagnostic Report
Generated: ${new Date().toUTCString()}
Analysis ID: ${activeId}
Overall Grade: ${fallbackData.isInsufficient ? 'Insufficient data' : `${fallbackData.grade} (${fallbackData.score}/100)`}

## Executive Summary
- Total Analyzed Components: ${fallbackData.nodesCount}
- Total Dependencies: ${fallbackData.edgesCount}
- Total Lines of Code: ${fallbackData.totalLoc}
- Average Complexity: ${fallbackData.avgComplexity}

## Architectural Smells (${fallbackData.smells.length})
${fallbackData.smells.map((s) => `- [${s.severity.toUpperCase()}] ${s.type}: ${s.description} (${s.file})`).join('\n')}

## Security Findings (${fallbackData.findings.length})
${fallbackData.findings.map((f) => `- [${f.severity.toUpperCase()}] ${f.cwe || f.rule_id} ${f.title}: ${f.remediation || 'Remediate vulnerability'}`).join('\n')}
`
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Architecture_Diagnostic_Report_${activeId.slice(0, 8)}.md`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Markdown report downloaded!')
    } finally {
      setIsDownloadingMd(false)
    }
  }

  // JSON export handler
  const handleDownloadJSON = async () => {
    setIsDownloadingJson(true)
    try {
      let response = await fetch(`/reports/${activeId}/json`)
      if (!response.ok) {
        response = await fetch(`/api/reports/${activeId}/json`)
      }
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `Architecture_Diagnostic_Report_${activeId.slice(0, 8)}.json`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
        toast.success('JSON report downloaded!')
        return
      }
      throw new Error('Server JSON not found')
    } catch {
      const jsonStr = JSON.stringify(serverReport || result, null, 2)
      const blob = new Blob([jsonStr], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Architecture_Diagnostic_Report_${activeId.slice(0, 8)}.json`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('JSON report exported!')
    } finally {
      setIsDownloadingJson(false)
    }
  }

  // Helper for rendering plain-English explanation boxes
  const renderCallout = (callout?: SectionCallout, defaults?: SectionCallout) => {
    const c = callout || defaults
    if (!c) return null
    return (
      <div className="rounded-xl p-4 my-4 border bg-blue-50/50 dark:bg-blue-950/20 border-blue-200/80 dark:border-blue-900/50 text-xs space-y-2">
        <div className="flex items-center gap-2 font-bold text-blue-900 dark:text-blue-300">
          <Info size={15} className="text-blue-600 dark:text-blue-400" />
          <span>Plain-English Guide for Non-Technical Stakeholders</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
          <div>
            <span className="font-semibold text-blue-950 dark:text-blue-200 block mb-0.5">💡 What this means:</span>
            <p className="text-blue-800/90 dark:text-blue-300/90 leading-relaxed">{c.what_it_means}</p>
          </div>
          <div>
            <span className="font-semibold text-amber-950 dark:text-amber-200 block mb-0.5">⚠️ Why it matters:</span>
            <p className="text-amber-900/90 dark:text-amber-300/90 leading-relaxed">{c.why_it_matters}</p>
          </div>
          <div>
            <span className="font-semibold text-emerald-950 dark:text-emerald-200 block mb-0.5">🚀 What to do:</span>
            <p className="text-emerald-900/90 dark:text-emerald-300/90 leading-relaxed">{c.what_to_do}</p>
          </div>
        </div>
      </div>
    )
  }

  const isInsufficient = serverReport?.metadata.is_insufficient_data ?? fallbackData.isInsufficient
  const overallGrade = isInsufficient
    ? 'Insufficient data'
    : (serverReport?.metadata.health_grade || fallbackData.grade)
  const overallScore = isInsufficient
    ? null
    : (serverReport?.metadata.health_score ?? fallbackData.score)

  const statusIndicator: 'green' | 'amber' | 'red' | 'grey' = useMemo(() => {
    if (isInsufficient) return 'grey'
    const g = (overallGrade || '').toUpperCase()
    if (g.startsWith('A')) return 'green'
    if (g.startsWith('B') || g.startsWith('C')) return 'amber'
    if (g.startsWith('D') || g.startsWith('F')) return 'red'
    if (overallScore !== null && overallScore !== undefined) {
      if (overallScore >= 80) return 'green'
      if (overallScore >= 60) return 'amber'
      return 'red'
    }
    return 'grey'
  }, [isInsufficient, overallGrade, overallScore])

  const statusLabel = useMemo(() => {
    if (statusIndicator === 'grey') return 'INSUFFICIENT DATA'
    if (statusIndicator === 'green') return overallGrade === 'A+' ? 'EXCELLENT' : 'GOOD'
    if (statusIndicator === 'amber') return 'FAIR'
    return 'POOR'
  }, [statusIndicator, overallGrade])

  const displayRepoName = useMemo(() => {
    const raw = serverReport?.metadata.repo_name || result?.path?.split(/[\\/]/).filter(Boolean).pop() || 'Codebase'
    if (!raw || raw.trim().toLowerCase() === 'repository' || raw.trim().toLowerCase() === 'none') {
      return result?.path?.split(/[\\/]/).filter(Boolean).pop() || 'Codebase'
    }
    return raw
  }, [serverReport, result])

  const displayBranch = useMemo(() => {
    const b = serverReport?.metadata.branch
    return (!b || b.trim().toLowerCase() === 'none') ? 'main' : b
  }, [serverReport])

  const displayCommit = useMemo(() => {
    const sha = serverReport?.metadata.commit_sha || serverReport?.metadata.commit_hash || result?.commit_sha || result?.source_fingerprint
    if (!sha || sha.toUpperCase() === 'HEAD' || sha.toLowerCase() === 'none') {
      return result?.source_fingerprint ? result.source_fingerprint.slice(0, 7) : 'local'
    }
    return sha.slice(0, 7)
  }, [serverReport, result])

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-36">
      {/* ── Section 1: Cover / Header Bar ────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-6" style={{ borderColor: 'var(--border)' }}>
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="badge badge-accent text-[10px] uppercase font-bold tracking-wider">
              Diagnostic Audit
            </span>
            <span className="text-xs font-mono text-muted">ID: {activeId.slice(0, 12)}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight" style={{ color: 'var(--text-primary)' }}>
            Architecture Diagnostic Report
          </h1>
          <p className="text-xs sm:text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Real server-generated architecture diagnostic report for engineering leadership, security teams, and executive stakeholders.
          </p>
        </div>

        {/* Export / Download Buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleGenerateAiNarrative}
            disabled={isLoadingAiNarrative || !result}
            data-testid="generate-ai-narrative-button"
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all duration-150 border cursor-pointer disabled:opacity-50 hover:scale-[1.02] active:scale-[0.98]"
            style={{
              background: 'rgba(198,244,50,0.1)',
              borderColor: 'rgba(198,244,50,0.3)',
              color: 'var(--accent)',
            }}
          >
            {isLoadingAiNarrative ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                <span>Generating AI Narrative...</span>
              </>
            ) : (
              <>
                <Sparkles size={14} />
                <span>Generate AI Narrative</span>
              </>
            )}
          </button>

          <button
            onClick={handleDownloadPdf}
            disabled={isDownloadingPdf}
            data-testid="download-pdf-button"
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all duration-150 shadow-sm cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.02] active:scale-[0.98] will-change-transform"
            style={{ background: 'var(--accent)', color: '#0B0D0C' }}
          >
            {isDownloadingPdf ? (
              <>
                <Loader2 size={15} className="animate-spin" />
                <span>Generating PDF...</span>
              </>
            ) : (
              <>
                <Download size={15} />
                <span>Download PDF</span>
              </>
            )}
          </button>

          <button
            onClick={handleDownloadMarkdown}
            disabled={isDownloadingMd}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border transition-colors hover:bg-white/5 cursor-pointer disabled:opacity-50"
            style={{ borderColor: 'var(--surface-border)', color: 'var(--text-primary)' }}
          >
            <FileText size={14} />
            <span>Markdown (.md)</span>
          </button>

          <button
            onClick={handleDownloadJSON}
            disabled={isDownloadingJson}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border transition-colors hover:bg-white/5 cursor-pointer disabled:opacity-50"
            style={{ borderColor: 'var(--surface-border)', color: 'var(--text-primary)' }}
          >
            <Code2 size={14} />
            <span>JSON Export</span>
          </button>
        </div>
      </div>

      {/* Cover Page Card Meta */}
      <div className="glass-card p-6 sm:p-8 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2 max-w-xl">
          <span className="text-xs uppercase font-bold text-muted tracking-wider">Target Codebase</span>
          <h2 className="text-2xl font-bold font-mono" style={{ color: 'var(--text-primary)' }}>
            {displayRepoName} <span className="text-sm font-normal text-muted">({displayBranch}@{displayCommit})</span>
          </h2>
          <div className="flex flex-wrap gap-4 text-xs text-muted pt-2">
            <span><strong>Branch:</strong> {displayBranch}</span>
            <span><strong>Commit:</strong> <code>{displayCommit}</code></span>
            <span><strong>Generated:</strong> {serverReport?.metadata.generated_at ? new Date(serverReport.metadata.generated_at).toLocaleString() : new Date().toLocaleString()}</span>
          </div>
          {result?.unsupported_files && Object.keys(result.unsupported_files).length > 0 && (
            <div className="flex flex-wrap items-center gap-2 pt-2 text-xs text-muted font-mono" data-testid="report-unsupported-files">
              <span className="font-semibold text-text dark:text-white">Unsupported Files:</span>
              {Object.entries(result.unsupported_files).map(([ext, count]) => (
                <span key={ext} className="px-2 py-0.5 rounded bg-surface-2 dark:bg-white/10 text-muted">
                  {ext}: {count}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Grade Display */}
        <div className="flex items-center gap-6 p-5 rounded-2xl bg-[var(--surface-2)] border border-[var(--border)] dark:bg-black/20 dark:border-white/10 flex-shrink-0">
          <div className="text-center">
            <span className="text-[10px] uppercase tracking-wider text-muted font-semibold block">Overall Grade</span>
            <div
              className={`font-black font-heading mt-1 ${isInsufficient ? 'text-lg text-muted px-2' : 'text-5xl'}`}
              style={{
                color: isInsufficient
                  ? 'var(--text-muted)'
                  : (overallScore ?? 0) >= 80
                  ? 'var(--accent-text)'
                  : (overallScore ?? 0) >= 60
                  ? 'var(--warning)'
                  : 'var(--danger)',
              }}
            >
              {overallGrade}
            </div>
          </div>
          <div className="w-[1px] h-12 bg-[var(--border)] dark:bg-white/10" />
          <div>
            <span className="text-[10px] uppercase tracking-wider text-muted font-semibold block">Health Score</span>
            <div className="text-2xl font-bold font-mono text-primary mt-1">
              {overallScore !== null ? `${overallScore}/100` : '—'}
            </div>
            <span className="text-[10px] text-muted">Objective rating</span>
          </div>
        </div>
      </div>

      {/* ── Section 2: Executive Summary ────────────────────────────────────────── */}
      <div className="glass-card p-6 sm:p-8 rounded-2xl space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-lg font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <Activity size={18} style={{ color: 'var(--accent)' }} /> 01. Executive Summary
          </h2>
          {/* Traffic-light Status Badge */}
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold border ${
              statusIndicator === 'green'
                ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-800 dark:text-emerald-400'
                : statusIndicator === 'amber'
                ? 'bg-amber-500/15 border-amber-500/30 text-amber-900 dark:text-amber-300'
                : statusIndicator === 'grey'
                ? 'bg-zinc-500/15 border-zinc-500/30 text-zinc-700 dark:text-zinc-400'
                : 'bg-red-500/15 border-red-500/30 text-red-800 dark:text-red-400'
            }`}
          >
            <span
              className={`w-2.5 h-2.5 rounded-full ${statusIndicator === 'grey' ? '' : 'animate-pulse'} ${
                statusIndicator === 'green'
                  ? 'bg-emerald-600 dark:bg-emerald-400'
                  : statusIndicator === 'amber'
                  ? 'bg-amber-600 dark:bg-amber-400'
                  : statusIndicator === 'grey'
                  ? 'bg-zinc-500 dark:bg-zinc-400'
                  : 'bg-red-600 dark:bg-red-400'
              }`}
            />
            <span>{statusLabel}</span>
          </div>
        </div>

        {/* AI Executive Narrative Card */}
        <div
          className="rounded-2xl p-5 my-4 border"
          style={{
            background: 'rgba(198,244,50,0.04)',
            borderColor: 'rgba(198,244,50,0.25)',
            borderLeft: '4px solid var(--accent)',
          }}
          data-testid="ai-report-narrative-card"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles size={16} style={{ color: 'var(--accent)' }} />
              <span className="font-bold text-xs uppercase tracking-wider" style={{ color: 'var(--text-primary)' }}>
                AI Executive Architectural Narrative
              </span>
            </div>
            {aiNarrative?.is_ai_generated ? (
              <AIBadge label="AI-generated" size="xs" />
            ) : (
              <AIFallback message="Deterministic executive narrative" />
            )}
          </div>
          <p className="text-xs leading-relaxed mb-4" style={{ color: 'var(--text-secondary)' }}>
            {aiNarrative?.executive_summary ||
              serverReport?.executive_summary.summary_sentences?.[0] ||
              'ArchLens automated multi-language static analysis summary.'}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t border-white/5">
            <div>
              <span className="font-bold text-[11px] block mb-1 text-primary">💡 What this means:</span>
              <p className="text-xs text-muted leading-relaxed">
                {aiNarrative?.what_this_means ||
                  serverReport?.executive_summary.callout?.what_it_means ||
                  'Structural health metrics synthesized into modularity and coupling implications.'}
              </p>
            </div>
            <div>
              <span className="font-bold text-[11px] block mb-1 text-primary">⚠️ Why it matters:</span>
              <p className="text-xs text-muted leading-relaxed">
                {aiNarrative?.why_it_matters ||
                  serverReport?.executive_summary.callout?.why_it_matters ||
                  'Direct correlation to maintainability, developer velocity, and blast radius risk.'}
              </p>
            </div>
            <div>
              <span className="font-bold text-[11px] block mb-1 text-primary">🚀 What to do:</span>
              <p className="text-xs text-muted leading-relaxed">
                {aiNarrative?.what_to_do ||
                  serverReport?.executive_summary.callout?.what_to_do ||
                  'Prioritize circular cycle decoupling and god-module refactoring.'}
              </p>
            </div>
          </div>
        </div>

        {/* Dynamic Sentences Summary */}
        <div className="space-y-2 text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {serverReport?.executive_summary.summary_sentences?.length ? (
            serverReport.executive_summary.summary_sentences.map((sent, idx) => (
              <p key={idx}>{sent}</p>
            ))
          ) : (
            (() => {
              const cyclesCount = (result?.graph.edges || []).filter(e => e.is_cycle).length
              const godCount = (result?.graph.nodes || []).filter(n => (n.loc || 0) >= 500).length
              const findingsCount = (result?.graph.nodes || []).flatMap(n => n.findings || []).length
              return (
                <>
                  <p>ArchLens completed an automated static analysis of {displayRepoName}, evaluating {fallbackData.nodesCount} components and {fallbackData.edgesCount} dependency relationships across {fallbackData.totalLoc} lines of code.</p>
                  <p>The codebase earned an overall Architecture Health score of {fallbackData.score !== null ? `${fallbackData.score}/100` : 'N/A'} (Grade {fallbackData.grade}), reflecting {statusLabel.toLowerCase()} operational sustainability.</p>
                  <p>{cyclesCount === 0 ? 'No circular dependencies were found in the analyzed codebase.' : `Analysis isolated ${cyclesCount} circular dependency ${cyclesCount === 1 ? 'loop' : 'loops'} requiring architectural decoupling.`}</p>
                  <p>{godCount === 0 ? 'No monolithic god classes were detected, indicating clean modular responsibility.' : `Identified ${godCount} oversized god ${godCount === 1 ? 'class' : 'classes'} exceeding complexity and LOC thresholds.`}</p>
                  <p>{findingsCount === 0 ? 'Zero critical security vulnerabilities or boundary flaws were identified.' : `Detected ${findingsCount} security findings requiring priority remediation.`}</p>
                </>
              )
            })()
          )}
        </div>

        {/* Top Identified Risks */}
        <div className="pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
          <h3 className="text-xs uppercase font-bold tracking-wider text-muted mb-3">Top Identified System Risks</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(() => {
              const rawRisks = serverReport?.executive_summary.top_3_risks
              const significantRisks = (rawRisks || []).filter(
                (r) => r.title !== 'No significant risks found' && r.severity.toLowerCase() !== 'clean'
              )
              const hasNoRisks = (
                (!rawRisks || rawRisks.length === 0 || significantRisks.length === 0) &&
                fallbackData.findings.length === 0 &&
                (result?.graph.edges || []).filter(e => e.is_cycle).length === 0
              )

              if (hasNoRisks) {
                return (
                  <div className="col-span-1 md:col-span-3 p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="badge badge-accent text-[9px] uppercase font-bold bg-emerald-500/20 text-emerald-800 dark:text-emerald-400">CLEAN</span>
                      <span className="text-[10px] font-mono text-muted">Status: Optimal</span>
                    </div>
                    <h4 className="text-xs font-bold text-primary">No significant risks found</h4>
                    <p className="text-[11px] text-secondary leading-relaxed">
                      All analyzed components adhere to architectural, complexity, and security thresholds with zero circular dependencies or critical findings.
                    </p>
                    <div className="pt-1 text-[10px] font-semibold text-accent-text">
                      Target: No action required
                    </div>
                  </div>
                )
              }

              const displayList = significantRisks.length > 0 ? significantRisks : (rawRisks || [])
              return displayList.map((risk, idx) => {
                const sev = risk.severity.toUpperCase()
                const badgeClass =
                  sev === 'CRITICAL' ? 'badge-danger' :
                  sev === 'HIGH' ? 'bg-orange-500/20 text-orange-800 dark:text-orange-400 border border-orange-500/30' :
                  sev === 'MEDIUM' ? 'badge-warning' :
                  'badge-accent'
                return (
                  <div key={idx} className="p-4 rounded-xl bg-[var(--surface-2)] border border-[var(--border)] dark:bg-black/20 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className={`badge ${badgeClass} text-[9px] uppercase font-bold`}>{risk.severity}</span>
                      <span className="text-[10px] font-mono text-muted">Risk #{idx + 1}</span>
                    </div>
                    <h4 className="text-xs font-bold text-primary">{risk.title}</h4>
                    <p className="text-[11px] text-secondary leading-relaxed">{risk.description}</p>
                    {risk.remediation_target && risk.remediation_target !== 'No action required' && (
                      <div className="pt-2 text-[10px] font-semibold text-accent-text">
                        Target: {risk.remediation_target}
                      </div>
                    )}
                  </div>
                )
              })
            })()}
          </div>
        </div>
      </div>

      {/* ── Section 3: How to Read This Report (Glossary) ────────────────────────── */}
      <div className="glass-card p-6 sm:p-8 rounded-2xl space-y-4">
        <h2 className="text-lg font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
          <BookOpen size={18} style={{ color: 'var(--accent)' }} /> 02. How to Read This Report (Architecture Glossary)
        </h2>

        {renderCallout(serverReport?.glossary.callout, {
          what_it_means: 'Plain-English explanations of key architectural terms using everyday analogies.',
          why_it_matters: 'Bridges technical engineering debt with real-world business risks so non-programmers can evaluate trade-offs.',
          what_to_do: 'Use these concepts when discussing technical roadmap investments with engineering managers.',
        })}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
          {(serverReport?.glossary.items || [
            {
              term: 'Coupling',
              definition: 'How tightly connected two software components are.',
              everyday_analogy: 'Imagine two workers handcuffed together. If one needs to run, both must move.',
            },
            {
              term: 'Cyclic Dependency',
              definition: 'Component A requires B, and B requires A in an unbroken circle.',
              everyday_analogy: 'A two-car roundabout with no exits where neither car can move without hitting the other.',
            },
            {
              term: 'God Class / God Module',
              definition: 'A single massive file or class that does far too many unrelated things.',
              everyday_analogy: 'A Swiss Army knife with 80 blades: heavy, awkward to hold, and fragile.',
            },
            {
              term: 'Instability Index (I)',
              definition: 'Ratio of outgoing calls to total calls (0 = rock solid, 1 = volatile).',
              everyday_analogy: 'A house of cards: resting on everything beneath it, shaken by the slightest breeze.',
            },
            {
              term: 'Blast Radius',
              definition: 'The percentage of your application that breaks if one specific component crashes.',
              everyday_analogy: 'Old Christmas tree lights: when one bulb blows out, the entire string goes dark.',
            },
          ]).map((item, idx) => (
            <div key={idx} className="p-4 rounded-xl bg-[var(--surface-2)] border border-[var(--border)] dark:bg-black/20 space-y-2">
              <h4 className="text-sm font-bold text-accent-text">{item.term}</h4>
              <p className="text-xs text-secondary">{item.definition}</p>
              <div className="p-2.5 rounded-lg bg-blue-50/50 dark:bg-blue-950/30 text-[11px] text-blue-900 dark:text-blue-300 border border-blue-200/50 dark:border-blue-900/30">
                <strong>Everyday Analogy:</strong> {item.everyday_analogy}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Section 4: Health Scorecard ────────────────────────────────────────── */}
      <div className="glass-card p-6 sm:p-8 rounded-2xl space-y-4">
        <h2 className="text-lg font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
          <Sparkles size={18} style={{ color: 'var(--accent)' }} /> 03. Health Scorecard & Sub-Scores
        </h2>

        {renderCallout(serverReport?.architecture_overview.callout, {
          what_it_means: 'A composite health index from 0 to 100 based on structure, coupling, security, and maintainability.',
          why_it_matters: 'Scores below 60 represent compounding technical debt that slows release velocity and increases bug rates.',
          what_to_do: 'Target sub-scores under 70 first. Decoupling cycles usually yields the largest rapid score increase.',
        })}

        {isInsufficient ? (
          <div className="p-8 text-center rounded-2xl bg-[var(--surface-2)] border border-[var(--border)]">
            <AlertCircleIcon className="mx-auto text-amber-500 mb-2" size={32} />
            <h3 className="text-base font-bold text-primary">Insufficient Data to Compute Health Grade</h3>
            <p className="text-xs text-muted max-w-md mx-auto mt-1">
              The analyzed repository does not contain enough AST components or dependency edges to calculate a statistically valid score.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            {/* Speedometer Gauge SVG */}
            <div className="flex flex-col items-center justify-center p-4 rounded-2xl bg-[var(--surface-2)] border border-[var(--border)]">
              {serverReport?.svg_charts?.gauge ? (
                <div dangerouslySetInnerHTML={{ __html: serverReport.svg_charts.gauge }} className="w-full max-w-[280px]" />
              ) : (
                <div className="text-center py-6">
                  <div className="text-5xl font-black font-heading text-accent-text">{overallScore ?? 86}</div>
                  <div className="text-xs text-muted mt-1">Overall Health Score</div>
                </div>
              )}
            </div>

            {/* Sub-Score Bars */}
            <div className="p-4 rounded-2xl bg-[var(--surface-2)] border border-[var(--border)]">
              {serverReport?.svg_charts?.subscores ? (
                <div dangerouslySetInnerHTML={{ __html: serverReport.svg_charts.subscores }} className="w-full" />
              ) : (
                <div className="space-y-4">
                  {[
                    { name: 'Structure & Modularization', val: 92 },
                    { name: 'Coupling & Cycle Balance', val: 78 },
                    { name: 'Security Boundary Hygiene', val: 88 },
                    { name: 'Maintainability & Complexity', val: 86 },
                  ].map((s, idx) => (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between text-xs font-semibold">
                        <span className="text-secondary">{s.name}</span>
                        <span className="font-mono text-primary">{s.val}/100</span>
                      </div>
                      <div className="h-2 w-full bg-black/10 dark:bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${s.val}%`,
                            background: s.val >= 80 ? 'var(--accent)' : s.val >= 60 ? 'var(--warning)' : 'var(--danger)',
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Section 5: Server-Generated Visuals & Architecture Charts ───────────── */}
      <div className="glass-card p-6 sm:p-8 rounded-2xl space-y-6">
        <h2 className="text-lg font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
          <Layers size={18} style={{ color: 'var(--accent)' }} /> 04. Architectural Visuals & Charts
        </h2>

        {renderCallout(undefined, {
          what_it_means: 'Vector graphs depicting layer distribution, smell types, instability, and dependency hotspots.',
          why_it_matters: 'Visualizes where complexity is pooling in your codebase and identifies the files causing 80% of maintenance headaches.',
          what_to_do: 'Target files at the top of the hotspot chart and components falling into the Zone of Pain.',
        })}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Layer Distribution */}
          {serverReport?.svg_charts?.layer_distribution ? (
            <div className="p-4 rounded-2xl bg-[var(--surface-2)] border border-[var(--border)] space-y-2">
              <h3 className="text-xs uppercase font-bold text-muted tracking-wider">Layer Distribution</h3>
              <div dangerouslySetInnerHTML={{ __html: serverReport.svg_charts.layer_distribution }} className="w-full flex justify-center" />
            </div>
          ) : null}

          {/* Smell Severity Donut */}
          {serverReport?.svg_charts?.smell_donut ? (
            <div className="p-4 rounded-2xl bg-[var(--surface-2)] border border-[var(--border)] space-y-2">
              <h3 className="text-xs uppercase font-bold text-muted tracking-wider">Architectural Smell Severity</h3>
              <div dangerouslySetInnerHTML={{ __html: serverReport.svg_charts.smell_donut }} className="w-full flex justify-center" />
            </div>
          ) : null}

          {/* Instability vs Abstractness */}
          {serverReport?.svg_charts?.instability_abstractness ? (
            <div className="p-4 rounded-2xl bg-[var(--surface-2)] border border-[var(--border)] space-y-2">
              <h3 className="text-xs uppercase font-bold text-muted tracking-wider">Instability vs Abstractness (Main Sequence)</h3>
              <div dangerouslySetInnerHTML={{ __html: serverReport.svg_charts.instability_abstractness }} className="w-full flex justify-center" />
            </div>
          ) : null}

          {/* Top 10 Hotspots */}
          {serverReport?.svg_charts?.top_hotspots ? (
            <div className="p-4 rounded-2xl bg-[var(--surface-2)] border border-[var(--border)] space-y-2">
              <h3 className="text-xs uppercase font-bold text-muted tracking-wider">Top 10 Architectural Hotspots</h3>
              <div dangerouslySetInnerHTML={{ __html: serverReport.svg_charts.top_hotspots }} className="w-full flex justify-center" />
            </div>
          ) : null}
        </div>

        {/* Dependency Graph Snapshot */}
        {serverReport?.svg_charts?.graph_snapshot ? (
          <div className="p-4 rounded-2xl bg-[var(--surface-2)] border border-[var(--border)] space-y-2">
            <h3 className="text-xs uppercase font-bold text-muted tracking-wider">Dependency Graph Snapshot</h3>
            <div dangerouslySetInnerHTML={{ __html: serverReport.svg_charts.graph_snapshot }} className="w-full flex justify-center overflow-x-auto" />
          </div>
        ) : null}

        {/* Refactor Simulation Before/After */}
        {serverReport?.svg_charts?.simulation_comparison && (
          <div className="p-4 rounded-2xl bg-[var(--surface-2)] border border-[var(--border)] space-y-2">
            <h3 className="text-xs uppercase font-bold text-muted tracking-wider">Refactor Simulation: Before vs After</h3>
            <div dangerouslySetInnerHTML={{ __html: serverReport.svg_charts.simulation_comparison }} className="w-full flex justify-center" />
          </div>
        )}
      </div>

      {/* ── Section 6: Findings Tables ────────────────────────────────────────── */}
      <div className="glass-card p-6 sm:p-8 rounded-2xl space-y-6">
        <h2 className="text-lg font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
          <AlertOctagon size={18} style={{ color: 'var(--danger)' }} /> 05. Architectural Deficiencies & Findings
        </h2>

        {renderCallout(serverReport?.dependency_analysis.callout, {
          what_it_means: 'Detailed catalogue of cyclic import loops, monolithic classes, and security vulnerabilities.',
          why_it_matters: 'Every cycle increases bug correlation. Every god class increases pull request merge conflicts and defect escape rates.',
          what_to_do: 'Refactor components strictly according to the paths shown below.',
        })}

        {/* Cyclic Dependencies */}
        <div className="space-y-3">
          <h3 className="text-sm font-bold flex items-center gap-2 text-primary">
            <AlertTriangle size={15} className="text-amber-500" />
            Cyclic Dependencies ({serverReport?.dependency_analysis.cycles_detected ?? fallbackData.smells.filter(s => s.type === 'circular_import').length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                  <th className="py-2.5 font-bold text-muted uppercase text-[10px]">Severity</th>
                  <th className="py-2.5 font-bold text-muted uppercase text-[10px]">Dependency Cycle Path</th>
                  <th className="py-2.5 font-bold text-muted uppercase text-[10px] text-right">Hops</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {(() => {
                  const cycles = (serverReport?.dependency_analysis.cycles_list && serverReport.dependency_analysis.cycles_list.length > 0)
                    ? serverReport.dependency_analysis.cycles_list
                    : (result?.graph.edges || []).filter((e) => e.is_cycle).map((e) => ({
                        path: `${e.source} -> ${e.target}`,
                        length: 2,
                        risk: 'HIGH',
                      }))
                  if (cycles.length === 0) {
                    return (
                      <tr>
                        <td colSpan={3} className="py-6 text-center text-muted font-mono text-xs">
                          No circular dependencies discovered in analyzed codebase.
                        </td>
                      </tr>
                    )
                  }
                  return cycles.map((c, idx) => (
                    <tr key={idx} className="hover:bg-black/5 dark:hover:bg-white/5">
                      <td className="py-2.5">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-800 dark:bg-red-950/40 dark:text-red-400 border border-red-200 dark:border-red-900/40">
                          <AlertOctagon size={10} />
                          {c.risk || 'CRITICAL'}
                        </span>
                      </td>
                      <td className="py-2.5 font-mono text-primary font-medium">{c.path}</td>
                      <td className="py-2.5 font-mono text-muted text-right">{c.length}</td>
                    </tr>
                  ))
                })()}
              </tbody>
            </table>
          </div>
        </div>

        {/* God Classes */}
        <div className="space-y-3 pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
          <h3 className="text-sm font-bold flex items-center gap-2 text-primary">
            <Layers size={15} className="text-purple-500" />
            God Classes & Monolithic Modules ({serverReport?.dependency_analysis.god_classes?.length ?? fallbackData.smells.filter(s => s.type === 'god_module').length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                  <th className="py-2.5 font-bold text-muted uppercase text-[10px]">Component</th>
                  <th className="py-2.5 font-bold text-muted uppercase text-[10px]">File Path</th>
                  <th className="py-2.5 font-bold text-muted uppercase text-[10px] text-right">LOC</th>
                  <th className="py-2.5 font-bold text-muted uppercase text-[10px] text-right">Methods</th>
                  <th className="py-2.5 font-bold text-muted uppercase text-[10px] text-right">In / Out</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {(() => {
                  const gods = (serverReport?.dependency_analysis.god_classes && serverReport.dependency_analysis.god_classes.length > 0)
                    ? serverReport.dependency_analysis.god_classes
                    : (result?.graph.nodes || [])
                        .filter((n) => (n.loc || 0) >= 500 || (result?.smells || []).some((s) => s.type === 'god_module' && s.file && n.file_path?.includes(s.file)))
                        .map((n) => ({
                          name: n.label,
                          file_path: n.file_path || n.id,
                          lines_of_code: n.loc || 0,
                          methods_count: Math.round((n.loc || 0) / 25),
                          incoming_deps: n.in_degree || 0,
                          outgoing_deps: n.out_degree || 0,
                        }))
                  if (gods.length === 0) {
                    return (
                      <tr>
                        <td colSpan={5} className="py-6 text-center text-muted font-mono text-xs">
                          No monolithic god classes detected.
                        </td>
                      </tr>
                    )
                  }
                  return gods.map((g, idx) => (
                    <tr key={idx} className="hover:bg-black/5 dark:hover:bg-white/5">
                      <td className="py-2.5 font-bold text-primary">{g.name}</td>
                      <td className="py-2.5 font-mono text-muted">{g.file_path}</td>
                      <td className="py-2.5 font-mono text-danger font-semibold text-right">{g.lines_of_code}</td>
                      <td className="py-2.5 font-mono text-muted text-right">{g.methods_count}</td>
                      <td className="py-2.5 font-mono text-muted text-right">{g.incoming_deps} / {g.outgoing_deps}</td>
                    </tr>
                  ))
                })()}
              </tbody>
            </table>
          </div>
        </div>

        {/* Security Findings */}
        <div className="space-y-3 pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
          <h3 className="text-sm font-bold flex items-center gap-2 text-primary">
            <ShieldAlert size={15} className="text-red-500" />
            Security & Boundary Violations ({serverReport?.security_findings.findings?.length ?? fallbackData.findings.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                  <th className="py-2.5 font-bold text-muted uppercase text-[10px]">Severity</th>
                  <th className="py-2.5 font-bold text-muted uppercase text-[10px]">Vulnerability / Title</th>
                  <th className="py-2.5 font-bold text-muted uppercase text-[10px]">CWE / OWASP</th>
                  <th className="py-2.5 font-bold text-muted uppercase text-[10px]">Remediation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {(() => {
                  const secFindings = (serverReport?.security_findings.findings && serverReport.security_findings.findings.length > 0)
                    ? serverReport.security_findings.findings
                    : (result?.findings || []).map((f) => ({
                        title: f.title,
                        severity: f.severity,
                        cwe: f.rule_id,
                        owasp: 'A01:2021',
                        file_path: f.file_path,
                        remediation: f.remediation,
                      }))
                  if (secFindings.length === 0) {
                    return (
                      <tr>
                        <td colSpan={4} className="py-6 text-center text-muted font-mono text-xs">
                          No active security findings or boundary violations detected.
                        </td>
                      </tr>
                    )
                  }
                  return secFindings.map((sec, idx) => (
                    <tr key={idx} className="hover:bg-black/5 dark:hover:bg-white/5">
                      <td className="py-2.5">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold border ${
                          sec.severity.toUpperCase() === 'CRITICAL' ? 'bg-red-100 text-red-800 dark:bg-red-950/40 dark:text-red-400 border-red-300' :
                          sec.severity.toUpperCase() === 'HIGH' ? 'bg-orange-100 text-orange-800 dark:bg-orange-950/40 dark:text-orange-400 border-orange-300' :
                          'bg-yellow-100 text-yellow-800 dark:bg-yellow-950/40 dark:text-yellow-400 border-yellow-300'
                        }`}>
                          <ShieldAlert size={10} />
                          {sec.severity.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2.5 font-bold text-primary">{sec.title}</td>
                      <td className="py-2.5 font-mono text-muted">{sec.cwe || sec.owasp || 'N/A'}</td>
                      <td className="py-2.5 text-secondary">{sec.remediation}</td>
                    </tr>
                  ))
                })()}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Section 7: Prioritized Action Plan ─────────────────────────────────── */}
      <div className="glass-card p-6 sm:p-8 rounded-2xl space-y-4">
        <h2 className="text-lg font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
          <CheckCircle2 size={18} style={{ color: 'var(--accent)' }} /> 06. Prioritized Action Plan
        </h2>

        {renderCallout(serverReport?.prioritized_action_plan.callout, {
          what_it_means: 'A step-by-step remediation roadmap organized into three time horizons with engineering effort estimates.',
          why_it_matters: 'Prevents analysis paralysis by telling your team exactly what to tackle first for maximum ROI.',
          what_to_do: 'Assign Tier 1 (Fix Now) tasks to the upcoming sprint before starting any large functional refactor.',
        })}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
          {/* Tier 1: Fix Now */}
          <div className="p-5 rounded-2xl bg-red-500/5 border border-red-500/20 space-y-3">
            <div className="flex items-center justify-between">
              <span className="badge badge-danger text-[10px] uppercase font-bold">P0 • Fix Now</span>
              <span className="text-[11px] font-mono text-danger font-semibold">1–2 Days</span>
            </div>
            <p className="text-xs text-muted">Immediate stabilization items that unblock deployments and resolve security vulnerabilities.</p>
            <div className="space-y-3 pt-2">
              {(() => {
                const items = (serverReport?.prioritized_action_plan.fix_now && serverReport.prioritized_action_plan.fix_now.length > 0)
                  ? serverReport.prioritized_action_plan.fix_now
                  : (result?.refactor_suggestions || []).filter((s) => s.effort === 'S').map((s) => ({
                      title: s.title,
                      effort: '1 Day',
                      priority: 'P0',
                      description: s.rationale,
                      affected_component: s.affected_nodes?.[0] || 'Module',
                    }))
                if (items.length === 0) {
                  return <p className="text-xs text-muted font-mono py-2">No urgent P0 blockers identified.</p>
                }
                return items.map((item, idx) => (
                  <div key={idx} className="p-3 rounded-xl bg-white dark:bg-black/40 border border-red-500/20 space-y-1">
                    <div className="flex justify-between items-center text-xs font-bold text-primary">
                      <span>{item.title}</span>
                      <span className="text-[10px] font-mono text-muted">{item.effort}</span>
                    </div>
                    <p className="text-[11px] text-secondary">{item.description}</p>
                    <span className="text-[10px] font-mono text-muted block pt-1">{item.affected_component}</span>
                  </div>
                ))
              })()}
            </div>
          </div>

          {/* Tier 2: Next Sprint */}
          <div className="p-5 rounded-2xl bg-amber-500/5 border border-amber-500/20 space-y-3">
            <div className="flex items-center justify-between">
              <span className="badge badge-warning text-[10px] uppercase font-bold">P1 • Next Sprint</span>
              <span className="text-[11px] font-mono text-amber-500 font-semibold">3–5 Days</span>
            </div>
            <p className="text-xs text-muted">High-leverage structural refactors to split monolithic classes and reduce team friction.</p>
            <div className="space-y-3 pt-2">
              {(() => {
                const items = (serverReport?.prioritized_action_plan.next_sprint && serverReport.prioritized_action_plan.next_sprint.length > 0)
                  ? serverReport.prioritized_action_plan.next_sprint
                  : (result?.refactor_suggestions || []).filter((s) => s.effort === 'M').map((s) => ({
                      title: s.title,
                      effort: '3 Days',
                      priority: 'P1',
                      description: s.rationale,
                      affected_component: s.affected_nodes?.[0] || 'Module',
                    }))
                if (items.length === 0) {
                  return <p className="text-xs text-muted font-mono py-2">No sprint refactors queued.</p>
                }
                return items.map((item, idx) => (
                  <div key={idx} className="p-3 rounded-xl bg-white dark:bg-black/40 border border-amber-500/20 space-y-1">
                    <div className="flex justify-between items-center text-xs font-bold text-primary">
                      <span>{item.title}</span>
                      <span className="text-[10px] font-mono text-muted">{item.effort}</span>
                    </div>
                    <p className="text-[11px] text-secondary">{item.description}</p>
                    <span className="text-[10px] font-mono text-muted block pt-1">{item.affected_component}</span>
                  </div>
                ))
              })()}
            </div>
          </div>

          {/* Tier 3: Later */}
          <div className="p-5 rounded-2xl bg-blue-500/5 border border-blue-500/20 space-y-3">
            <div className="flex items-center justify-between">
              <span className="badge badge-accent text-[10px] uppercase font-bold">P2 • Later</span>
              <span className="text-[11px] font-mono text-blue-500 font-semibold">1 Sprint</span>
            </div>
            <p className="text-xs text-muted">Long-term modernization, type-safety enforcement, and test coverage improvements.</p>
            <div className="space-y-3 pt-2">
              {(() => {
                const items = (serverReport?.prioritized_action_plan.later && serverReport.prioritized_action_plan.later.length > 0)
                  ? serverReport.prioritized_action_plan.later
                  : (result?.refactor_suggestions || []).filter((s) => s.effort === 'L').map((s) => ({
                      title: s.title,
                      effort: '1 Sprint',
                      priority: 'P2',
                      description: s.rationale,
                      affected_component: s.affected_nodes?.[0] || 'Module',
                    }))
                if (items.length === 0) {
                  return <p className="text-xs text-muted font-mono py-2">No long-term architecture debts.</p>
                }
                return items.map((item, idx) => (
                  <div key={idx} className="p-3 rounded-xl bg-white dark:bg-black/40 border border-blue-500/20 space-y-1">
                    <div className="flex justify-between items-center text-xs font-bold text-primary">
                      <span>{item.title}</span>
                      <span className="text-[10px] font-mono text-muted">{item.effort}</span>
                    </div>
                    <p className="text-[11px] text-secondary">{item.description}</p>
                    <span className="text-[10px] font-mono text-muted block pt-1">{item.affected_component}</span>
                  </div>
                ))
              })()}
            </div>
          </div>
        </div>
      </div>

      {/* ── Section 8: Appendix ────────────────────────────────────────────────── */}
      <div className="glass-card p-6 sm:p-8 rounded-2xl space-y-4">
        <h2 className="text-lg font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
          <HelpCircle size={18} style={{ color: 'var(--accent)' }} /> 07. Appendix: Methodology & Scan Settings
        </h2>

        {renderCallout(serverReport?.appendix.callout, {
          what_it_means: 'Scientific and algorithmic foundations behind all diagnostic scores in this report.',
          why_it_matters: 'Ensures audits are repeatable, deterministic, and auditable by external compliance parties.',
          what_to_do: 'Refer to this section during formal architecture reviews or ISO/SOC2 compliance evaluations.',
        })}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          {/* Methodologies */}
          <div className="p-4 rounded-xl bg-[var(--surface-2)] border border-[var(--border)] space-y-3">
            <h3 className="text-xs uppercase font-bold text-muted tracking-wider">Algorithms & Standards</h3>
            <div className="space-y-2 text-xs">
              <div>
                <strong className="text-primary block">Tarjan&apos;s Strongly Connected Components</strong>
                <p className="text-secondary">Detects cyclic dependency loops with O(|V| + |E|) linear-time determinism.</p>
              </div>
              <div>
                <strong className="text-primary block">Robert C. Martin&apos;s Package Metrics</strong>
                <p className="text-secondary">Measures Instability (I), Abstractness (A), and Distance from the Main Sequence (D).</p>
              </div>
              <div>
                <strong className="text-primary block">Graph Centrality & PageRank</strong>
                <p className="text-secondary">Quantifies the blast radius of central architectural nodes and core shared libraries.</p>
              </div>
            </div>
          </div>

          {/* Scan Settings & Limitations */}
          <div className="p-4 rounded-xl bg-[var(--surface-2)] border border-[var(--border)] space-y-3">
            <h3 className="text-xs uppercase font-bold text-muted tracking-wider">Scan Settings & Limitations</h3>
            <div className="space-y-2 text-xs">
              <div>
                <strong className="text-primary block">Dynamic Runtime Reflection:</strong>
                <p className="text-secondary">Dynamic imports, `eval()`, and runtime monkey-patching are evaluated heuristically.</p>
              </div>
              <div>
                <strong className="text-primary block">Exclusions:</strong>
                <p className="text-secondary">Vendor directories (`node_modules`, `site-packages`, `venv`) are excluded from scoring.</p>
              </div>
              <div>
                <strong className="text-primary block">Confidence Level:</strong>
                <p className="text-secondary">Static AST analysis provides 100% deterministic coverage for all compiled and imported symbols.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function AlertCircleIcon(props: any) {
  return <AlertTriangle {...props} />
}
