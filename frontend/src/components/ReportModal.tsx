import React, { useState, useEffect } from 'react'
import {
  X,
  FileText,
  History,
  Download,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  Cpu,
  Sparkles,
  Loader2,
} from 'lucide-react'
import { api, triggerBlobDownload } from '../api/client'
import type { AnalysisResult, ReportHistoryItem } from '../types'

interface ReportModalProps {
  isOpen: boolean
  onClose: () => void
  currentAnalysis: AnalysisResult | null
}

export const ReportModal: React.FC<ReportModalProps> = ({
  isOpen,
  onClose,
  currentAnalysis,
}) => {
  const [activeTab, setActiveTab] = useState<'generate' | 'history'>('generate')
  const [selectedFormat, setSelectedFormat] = useState<'pdf' | 'html' | 'json'>('pdf')
  const [targetRepo, setTargetRepo] = useState<'active' | 'flask' | 'spring'>('active')
  const [customPath, setCustomPath] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationSuccess, setGenerationSuccess] = useState<string | null>(null)
  const [generationError, setGenerationError] = useState<string | null>(null)

  // History state
  const [historyItems, setHistoryItems] = useState<ReportHistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  // Load history when tab opens
  const fetchHistory = async () => {
    setHistoryLoading(true)
    try {
      const data = await api.getReportHistory()
      setHistoryItems(data.reports || [])
    } catch {
      // ignore
    } finally {
      setHistoryLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      fetchHistory()
      setGenerationSuccess(null)
      setGenerationError(null)
    }
  }, [isOpen])

  if (!isOpen) return null

  // Handle Generate Report
  const handleGenerate = async (formatOverride?: 'pdf' | 'html' | 'json') => {
    const fmt = formatOverride || selectedFormat
    setIsGenerating(true)
    setGenerationSuccess(null)
    setGenerationError(null)

    try {
      let repoPath = '.'
      let repoName = currentAnalysis?.repo_id || 'Codebase'
      let graphPayload: Record<string, unknown> | undefined = undefined

      if (targetRepo === 'flask') {
        repoPath = 'samples/python-flask'
        repoName = 'Python Flask Sample'
      } else if (targetRepo === 'spring') {
        repoPath = 'samples/java-spring'
        repoName = 'Java Spring Sample'
      } else if (targetRepo === 'active' && currentAnalysis) {
        repoName = currentAnalysis.repo_id || 'Active Codebase'
        repoPath = currentAnalysis.path || '.'
        // If it's a loaded graph in memory
        if (currentAnalysis.graph) {
          graphPayload = {
            nodes: currentAnalysis.graph.nodes,
            edges: currentAnalysis.graph.edges,
          }
        }
      }

      if (customPath.trim()) {
        repoPath = customPath.trim()
        repoName = customPath.trim().split(/[\\/]/).pop() || 'Custom Repository'
        graphPayload = undefined
      }

      const result = await api.generateReport({
        repo_path: repoPath,
        repo_name: repoName,
        format: fmt,
        graph: graphPayload,
        query_osv: false,
      })

      triggerBlobDownload(result.blob, result.filename)
      setGenerationSuccess(`Generated and downloaded ${result.filename}!`)
      fetchHistory() // Refresh history list
    } catch (err: unknown) {
      setGenerationError(err instanceof Error ? err.message : 'Failed to generate report. Please try again.')
    } finally {
      setIsGenerating(false)
    }
  }

  // Handle Download Existing from History
  const handleDownloadHistory = async (reportId: string, format: 'pdf' | 'html' | 'json') => {
    setDownloadingId(`${reportId}-${format}`)
    try {
      const res = await api.downloadExistingReport(reportId, format)
      triggerBlobDownload(res.blob, res.filename)
    } catch {
      alert(`Could not download report in format ${format.toUpperCase()}.`)
    } finally {
      setDownloadingId(null)
    }
  }

  const getGradeBadge = (grade: string) => {
    const g = grade.toUpperCase()
    if (g === 'A') return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
    if (g === 'B') return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
    if (g === 'C') return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
    return 'bg-red-500/20 text-red-400 border-red-500/30'
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-[#0c0c0c] border border-white/15 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-[#121212]/70">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold font-display tracking-wider text-white uppercase">
                Architecture & Security Intelligence Report
              </h2>
              <p className="text-xs font-mono text-white/50">
                Generate 7-section executive grade audits (PDF, HTML, JSON)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Tab switchers */}
            <div className="flex items-center p-1 bg-black/40 rounded-xl border border-white/10">
              <button
                onClick={() => setActiveTab('generate')}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono uppercase tracking-wider flex items-center gap-2 transition-colors duration-150 ${
                  activeTab === 'generate'
                    ? 'bg-blue-600 text-white font-semibold shadow-md'
                    : 'text-white/60 hover:text-white'
                }`}
              >
                <Download className="w-3.5 h-3.5" />
                Generate
              </button>
              <button
                onClick={() => {
                  setActiveTab('history')
                  fetchHistory()
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono uppercase tracking-wider flex items-center gap-2 transition-colors duration-150 ${
                  activeTab === 'history'
                    ? 'bg-blue-600 text-white font-semibold shadow-md'
                    : 'text-white/60 hover:text-white'
                }`}
              >
                <History className="w-3.5 h-3.5" />
                History ({historyItems.length})
              </button>
            </div>

            <button
              id="report-modal-close-btn"
              aria-label="Close modal"
              onClick={onClose}
              className="p-2 rounded-xl text-white/50 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {activeTab === 'generate' ? (
            <div className="space-y-6">
              {/* Target Codebase Selection */}
              <div>
                <label className="block text-xs font-mono uppercase tracking-widest text-white/50 mb-3">
                  1. Select Target Codebase
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setTargetRepo('active')
                      setCustomPath('')
                    }}
                    className={`p-3.5 rounded-xl border text-left transition-colors duration-150 ${
                      targetRepo === 'active' && !customPath
                        ? 'border-blue-500 bg-blue-500/10 text-white shadow-sm'
                        : 'border-white/10 bg-[#141414] text-white/70 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-sm">Active Graph</span>
                      {targetRepo === 'active' && !customPath && (
                        <CheckCircle2 className="w-4 h-4 text-blue-400" />
                      )}
                    </div>
                    <p className="text-xs font-mono text-white/40 truncate">
                      {currentAnalysis?.repo_id || 'Current Ingested Model'}
                    </p>
                    <div className="mt-2 text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                      <span>{currentAnalysis?.node_count || 0} nodes</span>
                      <span>•</span>
                      <span>{currentAnalysis?.edge_count || 0} edges</span>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setTargetRepo('flask')
                      setCustomPath('')
                    }}
                    className={`p-3.5 rounded-xl border text-left transition-colors duration-150 ${
                      targetRepo === 'flask' && !customPath
                        ? 'border-blue-500 bg-blue-500/10 text-white shadow-sm'
                        : 'border-white/10 bg-[#141414] text-white/70 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-sm">Python Flask</span>
                      {targetRepo === 'flask' && !customPath && (
                        <CheckCircle2 className="w-4 h-4 text-blue-400" />
                      )}
                    </div>
                    <p className="text-xs font-mono text-white/40">samples/python-flask</p>
                    <div className="mt-2 text-[10px] font-mono text-blue-400">
                      Python 3.11 · AST & Metrics
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setTargetRepo('spring')
                      setCustomPath('')
                    }}
                    className={`p-3.5 rounded-xl border text-left transition-colors duration-150 ${
                      targetRepo === 'spring' && !customPath
                        ? 'border-blue-500 bg-blue-500/10 text-white shadow-sm'
                        : 'border-white/10 bg-[#141414] text-white/70 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-sm">Java Spring</span>
                      {targetRepo === 'spring' && !customPath && (
                        <CheckCircle2 className="w-4 h-4 text-blue-400" />
                      )}
                    </div>
                    <p className="text-xs font-mono text-white/40">samples/java-spring</p>
                    <div className="mt-2 text-[10px] font-mono text-purple-400">
                      Java 17 · Spring Boot
                    </div>
                  </button>
                </div>

                <div className="mt-3">
                  <input
                    type="text"
                    value={customPath}
                    onChange={(e) => setCustomPath(e.target.value)}
                    placeholder="Or enter custom local repository path (e.g. ./my-app)…"
                    className="w-full bg-[#141414] border border-white/10 rounded-xl px-4 py-2.5 text-xs font-mono text-white placeholder-white/65 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Format Selection */}
              <div>
                <label className="block text-xs font-mono uppercase tracking-widest text-white/50 mb-3">
                  2. Select Export Format
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div
                    onClick={() => setSelectedFormat('pdf')}
                    className={`p-4 rounded-xl border cursor-pointer transition-colors duration-150 ${
                      selectedFormat === 'pdf'
                        ? 'border-blue-500 bg-blue-500/10 text-white'
                        : 'border-white/10 bg-[#141414] text-white/70 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-sm flex items-center gap-2">
                        <FileText className="w-4 h-4 text-red-400" />
                        PDF Document
                      </span>
                      {selectedFormat === 'pdf' && (
                        <span className="w-2 h-2 rounded-full bg-blue-500" />
                      )}
                    </div>
                    <p className="text-xs text-white/50">
                      Jinja2 print stylesheet with WeasyPrint, vector charts, page numbers & TOC.
                    </p>
                    <div className="mt-3 text-[10px] font-mono text-blue-400 font-semibold uppercase">
                      Recommended for Stakeholders
                    </div>
                  </div>

                  <div
                    onClick={() => setSelectedFormat('html')}
                    className={`p-4 rounded-xl border cursor-pointer transition-colors duration-150 ${
                      selectedFormat === 'html'
                        ? 'border-blue-500 bg-blue-500/10 text-white'
                        : 'border-white/10 bg-[#141414] text-white/70 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-sm flex items-center gap-2">
                        <ExternalLink className="w-4 h-4 text-emerald-400" />
                        HTML Interactive
                      </span>
                      {selectedFormat === 'html' && (
                        <span className="w-2 h-2 rounded-full bg-blue-500" />
                      )}
                    </div>
                    <p className="text-xs text-white/50">
                      Self-contained responsive HTML report with embedded styles and graph renders.
                    </p>
                    <div className="mt-3 text-[10px] font-mono text-emerald-400 font-semibold uppercase">
                      Instant Web Preview
                    </div>
                  </div>

                  <div
                    onClick={() => setSelectedFormat('json')}
                    className={`p-4 rounded-xl border cursor-pointer transition-colors duration-150 ${
                      selectedFormat === 'json'
                        ? 'border-blue-500 bg-blue-500/10 text-white'
                        : 'border-white/10 bg-[#141414] text-white/70 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-sm flex items-center gap-2">
                        <Cpu className="w-4 h-4 text-purple-400" />
                        JSON Structured Data
                      </span>
                      {selectedFormat === 'json' && (
                        <span className="w-2 h-2 rounded-full bg-blue-500" />
                      )}
                    </div>
                    <p className="text-xs text-white/50">
                      Raw AST findings, Tarjan cycles, Martin instability metrics, and refactor AST plans.
                    </p>
                    <div className="mt-3 text-[10px] font-mono text-purple-400 font-semibold uppercase">
                      CI/CD & API Integrations
                    </div>
                  </div>
                </div>
              </div>

              {/* Report Contents Breakdown Preview */}
              <div className="bg-[#121212] border border-white/10 rounded-xl p-4">
                <div className="text-xs font-mono uppercase tracking-widest text-white/50 mb-3 flex items-center gap-2">
                  <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                  Included 7-Section Architecture Audit Scope
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono text-white/70">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>1. Executive Summary & Health Score (0-100)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>2. Architecture Overview & Headless Graph</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>3. Dependency Cycles & Martin Instability</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>4. Security Findings with CWE & Remediation</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>5. Code Quality & Complexity Distribution</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>6. Prioritized Refactoring Roadmap (S/M/L)</span>
                  </div>
                  <div className="flex items-center gap-2 sm:col-span-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>7. Methodology & Algorithmic Appendix</span>
                  </div>
                </div>
              </div>

              {/* Status messages */}
              {generationSuccess && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center gap-3 text-emerald-400 text-xs font-mono">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  <span>{generationSuccess}</span>
                </div>
              )}

              {generationError && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-3 text-red-400 text-xs font-mono">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                  <span>{generationError}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-2">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleGenerate('pdf')}
                    disabled={isGenerating}
                    className="px-4 py-2.5 bg-white text-black font-semibold text-xs font-mono uppercase tracking-wider rounded-xl hover:bg-white/90 disabled:opacity-50 transition-colors duration-150 flex items-center gap-2 shadow-lg"
                  >
                    {isGenerating && selectedFormat === 'pdf' ? (
                      <Loader2 className="w-4 h-4 animate-spin text-black" />
                    ) : (
                      <Download className="w-4 h-4" />
                    )}
                    One-Click PDF
                  </button>

                  <button
                    type="button"
                    onClick={() => handleGenerate('html')}
                    disabled={isGenerating}
                    className="px-4 py-2.5 bg-[#1a1a1a] hover:bg-[#252525] text-white font-medium text-xs font-mono uppercase tracking-wider rounded-xl border border-white/10 disabled:opacity-50 transition-colors duration-150 flex items-center gap-2"
                  >
                    {isGenerating && selectedFormat === 'html' ? (
                      <Loader2 className="w-4 h-4 animate-spin text-white" />
                    ) : (
                      <ExternalLink className="w-4 h-4" />
                    )}
                    HTML
                  </button>

                  <button
                    type="button"
                    onClick={() => handleGenerate('json')}
                    disabled={isGenerating}
                    className="px-4 py-2.5 bg-[#1a1a1a] hover:bg-[#252525] text-white font-medium text-xs font-mono uppercase tracking-wider rounded-xl border border-white/10 disabled:opacity-50 transition-colors duration-150 flex items-center gap-2"
                  >
                    {isGenerating && selectedFormat === 'json' ? (
                      <Loader2 className="w-4 h-4 animate-spin text-white" />
                    ) : (
                      <Cpu className="w-4 h-4" />
                    )}
                    JSON
                  </button>
                </div>

                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-mono text-white/50 hover:text-white"
                >
                  Close
                </button>
              </div>
            </div>
          ) : (
            /* History Tab */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono uppercase tracking-widest text-white/50">
                  Previously Compiled Reports ({historyItems.length})
                </span>
                <button
                  onClick={fetchHistory}
                  disabled={historyLoading}
                  className="p-1.5 rounded-lg bg-[#141414] border border-white/10 text-white/60 hover:text-white transition-colors"
                  title="Refresh history"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${historyLoading ? 'animate-spin' : ''}`} />
                </button>
              </div>

              {historyLoading ? (
                <div className="py-12 flex flex-col items-center justify-center gap-3 text-white/40 font-mono text-xs">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
                  Loading report archive…
                </div>
              ) : historyItems.length === 0 ? (
                <div className="py-12 text-center border border-dashed border-white/10 rounded-2xl bg-[#121212]/50">
                  <FileText className="w-10 h-10 text-white/20 mx-auto mb-3" />
                  <p className="text-sm font-semibold text-white/70">No saved reports found</p>
                  <p className="text-xs font-mono text-white/40 mt-1">
                    Click &quot;Generate&quot; to compile an executive audit.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {historyItems.map((item) => (
                    <div
                      key={item.report_id}
                      className="p-4 bg-[#141414] border border-white/10 rounded-xl hover:border-white/20 transition-colors duration-150 flex flex-col md:flex-row md:items-center justify-between gap-4"
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className={`w-10 h-10 rounded-xl border flex items-center justify-center font-display text-lg font-bold flex-shrink-0 ${getGradeBadge(
                            item.grade
                          )}`}
                        >
                          {item.grade}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="font-semibold text-sm text-white">
                              {item.repo_name}
                            </h4>
                            <span className="text-[10px] font-mono text-white/40 bg-white/5 px-2 py-0.5 rounded">
                              {item.report_id}
                            </span>
                          </div>
                          <div className="flex flex-wrap items-center gap-3 mt-1 text-xs font-mono text-white/50">
                            <span>Score: <b className="text-white">{item.health_score.toFixed(1)}/100</b></span>
                            <span>•</span>
                            <span>{item.components} components</span>
                            <span>•</span>
                            <span className={item.cycles > 0 ? 'text-amber-400' : 'text-white/50'}>
                              {item.cycles} cycles
                            </span>
                            <span>•</span>
                            <span className={item.critical_vulnerabilities > 0 ? 'text-red-400' : 'text-white/50'}>
                              {item.critical_vulnerabilities} critical
                            </span>
                            <span>•</span>
                            <span>{item.generated_at ? new Date(item.generated_at).toLocaleString() : ''}</span>
                          </div>
                        </div>
                      </div>

                      {/* Download Buttons for this historical report */}
                      <div className="flex items-center gap-2 self-end md:self-center">
                        <button
                          onClick={() => handleDownloadHistory(item.report_id, 'pdf')}
                          disabled={downloadingId === `${item.report_id}-pdf`}
                          className="px-2.5 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-mono text-white flex items-center gap-1.5 transition-colors"
                          title="Download PDF"
                        >
                          {downloadingId === `${item.report_id}-pdf` ? (
                            <Loader2 className="w-3 h-3 animate-spin text-white" />
                          ) : (
                            <Download className="w-3 h-3 text-red-400" />
                          )}
                          PDF
                        </button>

                        <button
                          onClick={() => handleDownloadHistory(item.report_id, 'html')}
                          disabled={downloadingId === `${item.report_id}-html`}
                          className="px-2.5 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-mono text-white flex items-center gap-1.5 transition-colors"
                          title="Download HTML"
                        >
                          {downloadingId === `${item.report_id}-html` ? (
                            <Loader2 className="w-3 h-3 animate-spin text-white" />
                          ) : (
                            <ExternalLink className="w-3 h-3 text-emerald-400" />
                          )}
                          HTML
                        </button>

                        <button
                          onClick={() => handleDownloadHistory(item.report_id, 'json')}
                          disabled={downloadingId === `${item.report_id}-json`}
                          className="px-2.5 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-mono text-white flex items-center gap-1.5 transition-colors"
                          title="Download JSON"
                        >
                          {downloadingId === `${item.report_id}-json` ? (
                            <Loader2 className="w-3 h-3 animate-spin text-white" />
                          ) : (
                            <Cpu className="w-3 h-3 text-purple-400" />
                          )}
                          JSON
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
