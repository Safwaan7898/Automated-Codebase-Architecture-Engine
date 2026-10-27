import React, { useState } from 'react'
import {
  ShieldAlert,
  AlertTriangle,
  Flame,
  CheckCircle2,
  Search,
  ArrowRight,
} from 'lucide-react'
import { AIExplainPanel } from './AIExplainPanel'
import { AIBadge } from './ui/AILabel'
import { aiApi } from '../api/client'
import type { DiagnosticFinding, Smell, GraphNode } from '../types'

interface DiagnosticsSmellPanelProps {
  findings: DiagnosticFinding[]
  smells: Smell[]
  nodes: GraphNode[]
  onSelectNode: (nodeId: string) => void
}

export const DiagnosticsSmellPanel: React.FC<DiagnosticsSmellPanelProps> = ({
  findings,
  smells,
  nodes,
  onSelectNode,
}) => {
  const [activeFilter, setActiveFilter] = useState<'all' | 'security' | 'smells' | 'riskiest'>('all')
  const [searchTerm, setSearchTerm] = useState('')

  // Top 5 riskiest nodes
  const riskiestNodes = [...nodes]
    .sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0))
    .slice(0, 10)

  // Filtered findings
  const filteredFindings = findings.filter(
    (f) =>
      f.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.file_path.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (f.cwe && f.cwe.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  // Filtered smells
  const filteredSmells = smells.filter(
    (s) =>
      s.type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.file.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.description.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <section id="diagnostics-section" className="py-20 px-6 md:px-12 max-w-7xl mx-auto w-full border-t border-white/5">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-mono uppercase tracking-widest text-red-400 block">
              02 // DIAGNOSTICS & RISK ENGINE
            </span>
            <AIBadge label="AI-generated" size="xs" />
          </div>
          <h2 className="agencia-display text-4xl md:text-6xl text-white tracking-wider">
            SECURITY FINDINGS & DESIGN SMELLS
          </h2>
        </div>

        {/* Filter buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setActiveFilter('all')}
            className={`px-3.5 py-1.5 rounded-full text-xs font-mono uppercase tracking-wider transition-colors duration-150 ${
              activeFilter === 'all'
                ? 'bg-white text-black font-semibold'
                : 'bg-white/5 hover:bg-white/10 text-white/70'
            }`}
          >
            All Audits ({findings.length + smells.length})
          </button>
          <button
            onClick={() => setActiveFilter('security')}
            className={`px-3.5 py-1.5 rounded-full text-xs font-mono uppercase tracking-wider flex items-center gap-1.5 transition-colors duration-150 ${
              activeFilter === 'security'
                ? 'bg-red-500 text-white font-semibold'
                : 'bg-red-500/10 hover:bg-red-500/20 text-red-300'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            Security Rules ({findings.length})
          </button>
          <button
            onClick={() => setActiveFilter('smells')}
            className={`px-3.5 py-1.5 rounded-full text-xs font-mono uppercase tracking-wider flex items-center gap-1.5 transition-colors duration-150 ${
              activeFilter === 'smells'
                ? 'bg-amber-500 text-black font-semibold'
                : 'bg-amber-500/10 hover:bg-amber-500/20 text-amber-300'
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            Design Smells ({smells.length})
          </button>
          <button
            onClick={() => setActiveFilter('riskiest')}
            className={`px-3.5 py-1.5 rounded-full text-xs font-mono uppercase tracking-wider flex items-center gap-1.5 transition-colors duration-150 ${
              activeFilter === 'riskiest'
                ? 'bg-purple-500 text-white font-semibold'
                : 'bg-purple-500/10 hover:bg-purple-500/20 text-purple-300'
            }`}
          >
            <Flame className="w-3.5 h-3.5" />
            Top Riskiest Nodes
          </button>
        </div>
      </div>

      {/* Grid of Findings */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Findings & Smells List */}
        <div className="lg:col-span-2 space-y-4">
          {/* Search bar inside panel */}
          <div className="relative mb-4">
            <Search className="w-4 h-4 text-white/40 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search findings by rule, CWE, or file..."
              className="w-full bg-[#111111] border border-white/10 rounded-xl pl-9 pr-4 py-2.5 text-xs font-mono text-white placeholder-white/65 focus:outline-none focus:border-white/30"
            />
          </div>

          {(activeFilter === 'all' || activeFilter === 'security') &&
            filteredFindings.map((f, idx) => (
              <div
                key={`finding-${idx}`}
                className="p-5 bg-[#0f0f0f] border border-red-500/30 rounded-2xl space-y-3 hover:border-red-500/60 transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-red-400 shrink-0" />
                    <h4 className="font-mono text-sm font-bold text-white">{f.title}</h4>
                  </div>
                  <span className="px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 border border-red-500/30 text-[10px] font-mono uppercase font-bold">
                    {f.severity}
                  </span>
                </div>

                <div className="flex flex-wrap gap-2 text-xs font-mono text-white/50">
                  <span className="bg-white/5 px-2.5 py-0.5 rounded border border-white/5">
                    {f.file_path} {f.line_number ? `:${f.line_number}` : ''}
                  </span>
                  {f.cwe && (
                    <span className="bg-red-500/10 text-red-300 px-2.5 py-0.5 rounded border border-red-500/20">
                      CWE-{f.cwe}
                    </span>
                  )}
                  {f.owasp && (
                    <span className="bg-purple-500/10 text-purple-300 px-2.5 py-0.5 rounded border border-purple-500/20">
                      OWASP: {f.owasp}
                    </span>
                  )}
                </div>

                {f.code_snippet && (
                  <pre className="p-3 bg-black/60 rounded-xl border border-white/10 text-xs font-mono text-red-300/90 overflow-x-auto">
                    <code>{f.code_snippet}</code>
                  </pre>
                )}

                {f.remediation && (
                  <p className="text-xs font-mono text-emerald-400/90 leading-relaxed bg-emerald-500/5 p-2.5 rounded-lg border border-emerald-500/20">
                    💡 <strong>Remediation:</strong> {f.remediation}
                  </p>
                )}

                <AIExplainPanel
                  label="Enrich with AI"
                  className="mt-2 pt-2 border-t border-white/5"
                  fetch={async () => {
                    try {
                      const res = await aiApi.enrichSecurity(
                        f as unknown as Record<string, unknown>,
                        f.code_snippet
                      )
                      return {
                        explanation: res.explanation ?? 'AI unavailable',
                        fix: res.suggested_fix ? `Suggested Fix:\n${res.suggested_fix}` : undefined,
                        fp_likelihood: res.false_positive_likelihood,
                        fp_reason: res.false_positive_reason,
                      }
                    } catch {
                      return null
                    }
                  }}
                />
              </div>
            ))}

          {(activeFilter === 'all' || activeFilter === 'smells') &&
            filteredSmells.map((s, idx) => (
              <div
                key={`smell-${idx}`}
                className="p-5 bg-[#0f0f0f] border border-amber-500/30 rounded-2xl space-y-2.5 hover:border-amber-500/60 transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                    <h4 className="font-mono text-sm font-bold text-white capitalize">
                      {s.type.replace(/_/g, ' ')}
                    </h4>
                  </div>
                  <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[10px] font-mono uppercase">
                    {s.severity}
                  </span>
                </div>

                <p className="text-xs font-mono text-white/70 leading-relaxed">
                  {s.description}
                </p>

                <div className="flex items-center justify-between text-xs font-mono text-white/40 pt-1">
                  <span className="truncate">{s.file}</span>
                  {s.suggestion && (
                    <span className="text-blue-400 text-[11px]">→ {s.suggestion}</span>
                  )}
                </div>

                <AIExplainPanel
                  label="Explain Smell & Fix Outline"
                  className="mt-2 pt-2 border-t border-white/5"
                  fetch={async () => {
                    try {
                      const res = await aiApi.explainSmell(
                        s as unknown as Record<string, unknown>,
                        { file: s.file }
                      )
                      return {
                        explanation: res.why_it_matters ?? 'AI unavailable',
                        fix: res.fix_outline,
                      }
                    } catch {
                      return null
                    }
                  }}
                />
              </div>
            ))}

          {filteredFindings.length === 0 && filteredSmells.length === 0 && (
            <div className="p-12 text-center bg-[#0a0a0a] rounded-2xl border border-white/5">
              <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3 opacity-80" />
              <h3 className="font-mono text-sm text-white font-bold">Zero Violations Found</h3>
              <p className="text-xs font-mono text-white/50 mt-1">
                The analyzed codebase passes all AST security rules and architectural thresholds.
              </p>
            </div>
          )}
        </div>

        {/* Right Col: Top Riskiest Nodes Leaderboard */}
        <div className="space-y-4">
          <div className="p-5 bg-[#0f0f0f] border border-white/10 rounded-2xl">
            <h3 className="agencia-display text-xl tracking-wider text-white mb-1 flex items-center gap-2">
              <Flame className="w-4 h-4 text-red-500" />
              NODE RISK LEADERBOARD
            </h3>
            <p className="text-xs font-mono text-white/50 mb-4">
              Composite score (Severity + Centrality + Complexity)
            </p>

            <div className="space-y-2">
              {riskiestNodes.map((n, idx) => (
                <div
                  key={idx}
                  onClick={() => onSelectNode(n.id)}
                  className="p-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 flex items-center justify-between cursor-pointer group transition-colors duration-150"
                >
                  <div className="truncate pr-2">
                    <span className="text-xs font-mono text-white font-medium block truncate group-hover:text-blue-400">
                      {n.label || n.id}
                    </span>
                    <span className="text-[10px] font-mono text-white/40 block truncate">
                      {n.file_path || n.type}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                        (n.risk_score ?? 0) >= 80
                          ? 'bg-red-500/20 text-red-400'
                          : (n.risk_score ?? 0) >= 60
                          ? 'bg-orange-500/20 text-orange-400'
                          : 'bg-yellow-500/20 text-yellow-400'
                      }`}
                    >
                      {(n.risk_score ?? 15).toFixed(0)}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-white/30 group-hover:text-white group-hover:translate-x-0.5 transition-transform duration-150 will-change-transform" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* OSV.dev Integration Banner */}
          <div className="p-5 bg-gradient-to-br from-blue-950/40 to-black border border-blue-500/20 rounded-2xl space-y-2">
            <span className="text-[10px] font-mono uppercase tracking-widest text-blue-400 block">
              REAL-TIME CVE FEED
            </span>
            <h4 className="font-mono text-sm font-bold text-white">
              OSV.dev Open Source Vulnerabilities
            </h4>
            <p className="text-xs font-mono text-white/60 leading-relaxed">
              Every analyzed manifest (pom.xml, requirements.txt, build.gradle) is cross-referenced
              live against the distributed OSV.dev vulnerability database.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
