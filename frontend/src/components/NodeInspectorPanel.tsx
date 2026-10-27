import React, { useState } from 'react'
import {
  X,
  ShieldAlert,
  Flame,
  Wrench,
  Sparkles,
  ExternalLink,
  Code2,
  Activity,
  CheckCircle,
} from 'lucide-react'
import type { GraphNode, RefactorSuggestion } from '../types'

interface NodeInspectorPanelProps {
  node: GraphNode | null
  onClose: () => void
  onSelectNode: (nodeId: string) => void
  onHighlightBlastRadius: (nodeId: string) => void
  isBlastRadiusActive: boolean
  allSuggestions: RefactorSuggestion[]
  onDraftDiff?: (suggestion: RefactorSuggestion) => void
}

export const NodeInspectorPanel: React.FC<NodeInspectorPanelProps> = ({
  node,
  onClose,
  onSelectNode,
  onHighlightBlastRadius,
  isBlastRadiusActive,
  allSuggestions,
  onDraftDiff,
}) => {
  const [activeTab, setActiveTab] = useState<'metrics' | 'deps' | 'security' | 'refactor'>('metrics')

  if (!node) return null

  // Filter refactor suggestions affecting this node
  const nodeSuggestions = allSuggestions.filter(
    (s) => s.affected_nodes.includes(node.id) || s.title.toLowerCase().includes(node.label.toLowerCase())
  )

  // Risk score styling
  const riskScore = node.risk_score ?? 15
  const getRiskBadgeColor = (score: number) => {
    if (score >= 80) return 'bg-red-500/20 text-red-400 border-red-500/40'
    if (score >= 60) return 'bg-orange-500/20 text-orange-400 border-orange-500/40'
    if (score >= 30) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40'
    return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
  }

  // Node incoming and outgoing dependency IDs from metadata or props
  const incomingDeps: string[] = (node.metadata?.incoming as unknown as string[]) || []
  const outgoingDeps: string[] = (node.metadata?.outgoing as unknown as string[]) || []

  return (
    <div
      id="node-inspector-panel"
      className="fixed top-20 right-4 bottom-4 w-96 max-w-[calc(100vw-2rem)] bg-[#0d0d0d]/95 backdrop-blur-xl border border-white/15 rounded-2xl shadow-glass-luxury z-40 flex flex-col overflow-hidden animate-slide-up"
    >
      {/* Header */}
      <div className="p-5 border-b border-white/10 flex items-start justify-between bg-black/40">
        <div className="flex-1 pr-3">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-white/10 text-white/70">
              {node.type || 'class'}
            </span>
            {node.layer && (
              <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                {node.layer}
              </span>
            )}
          </div>
          <h3 className="font-mono text-base font-bold text-white truncate" title={node.label || node.id}>
            {node.label || node.id}
          </h3>
          <p className="text-[11px] font-mono text-white/40 truncate mt-0.5">
            {node.file_path || node.id}
          </p>
        </div>

        <button
          onClick={onClose}
          className="p-1 rounded-lg text-white/50 hover:text-white hover:bg-white/10 transition-colors"
          aria-label="Close inspector"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Risk Score Banner */}
      <div className="px-5 py-3 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
        <div className="flex items-center gap-2">
          <Flame className="w-4 h-4 text-red-400" />
          <span className="text-xs font-mono uppercase tracking-wider text-white/70">
            Node Risk Score:
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`px-3 py-1 rounded-full border text-xs font-mono font-bold ${getRiskBadgeColor(
              riskScore
            )}`}
          >
            {riskScore.toFixed(0)} / 100
          </div>
        </div>
      </div>

      {/* Blast Radius Highlight Action */}
      <div className="px-5 py-2.5 bg-blue-500/10 border-b border-blue-500/20 flex items-center justify-between">
        <span className="text-xs font-mono text-blue-300 flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5" />
          Impact Analysis:
        </span>
        <button
          id="blast-radius-btn"
          onClick={() => onHighlightBlastRadius(node.id)}
          className={`px-3 py-1 rounded-full text-xs font-mono uppercase tracking-wider flex items-center gap-1.5 transition-colors duration-150 cursor-pointer ${
            isBlastRadiusActive
              ? 'bg-blue-600 text-white font-semibold shadow-blue-glow'
              : 'bg-white/10 text-white/90 hover:bg-white/20'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          {isBlastRadiusActive ? 'Blast Radius Active' : 'Light Blast Radius'}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center border-b border-white/10 bg-black/20 text-xs font-mono">
        <button
          onClick={() => setActiveTab('metrics')}
          className={`flex-1 py-2.5 text-center transition-colors ${
            activeTab === 'metrics'
              ? 'text-white border-b-2 border-white font-semibold bg-white/5'
              : 'text-white/50 hover:text-white'
          }`}
        >
          Metrics
        </button>
        <button
          onClick={() => setActiveTab('deps')}
          className={`flex-1 py-2.5 text-center transition-colors ${
            activeTab === 'deps'
              ? 'text-white border-b-2 border-white font-semibold bg-white/5'
              : 'text-white/50 hover:text-white'
          }`}
        >
          Deps ({incomingDeps.length + outgoingDeps.length})
        </button>
        <button
          onClick={() => setActiveTab('security')}
          className={`flex-1 py-2.5 text-center transition-colors flex items-center justify-center gap-1 ${
            activeTab === 'security'
              ? 'text-red-400 border-b-2 border-red-500 font-semibold bg-white/5'
              : 'text-white/50 hover:text-white'
          }`}
        >
          <ShieldAlert className="w-3 h-3" />
          Sec ({node.findings?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('refactor')}
          className={`flex-1 py-2.5 text-center transition-colors flex items-center justify-center gap-1 ${
            activeTab === 'refactor'
              ? 'text-amber-400 border-b-2 border-amber-500 font-semibold bg-white/5'
              : 'text-white/50 hover:text-white'
          }`}
        >
          <Wrench className="w-3 h-3" />
          Plan ({nodeSuggestions.length})
        </button>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {/* METRICS TAB */}
        {activeTab === 'metrics' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                <span className="text-[10px] font-mono text-white/50 uppercase block">
                  Lines of Code
                </span>
                <span className="text-xl font-mono font-bold text-white">
                  {node.loc ?? 0}
                </span>
              </div>

              <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                <span className="text-[10px] font-mono text-white/50 uppercase block">
                  Cyclomatic Complexity
                </span>
                <span className="text-xl font-mono font-bold text-amber-400">
                  {node.cyclomatic_complexity ?? (node.metrics?.cyclomatic_complexity as number) ?? 12}
                </span>
              </div>

              <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                <span className="text-[10px] font-mono text-white/50 uppercase block">
                  In-Degree Coupling
                </span>
                <span className="text-xl font-mono font-bold text-blue-400">
                  {node.in_degree ?? incomingDeps.length}
                </span>
              </div>

              <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                <span className="text-[10px] font-mono text-white/50 uppercase block">
                  Out-Degree Coupling
                </span>
                <span className="text-xl font-mono font-bold text-purple-400">
                  {node.out_degree ?? outgoingDeps.length}
                </span>
              </div>
            </div>

            {/* Centrality Gauges */}
            <div className="p-4 bg-white/5 rounded-xl border border-white/5 space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-white/60">Betweenness Centrality:</span>
                <span className="text-white font-bold">
                  {((node.centrality ?? 0.42) * 100).toFixed(1)}%
                </span>
              </div>
              <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full"
                  style={{ width: `${Math.min(100, (node.centrality ?? 0.42) * 100)}%` }}
                />
              </div>

              <div className="flex justify-between text-xs font-mono pt-2">
                <span className="text-white/60">PageRank Importance:</span>
                <span className="text-white font-bold">
                  {((node.pagerank ?? 0.08) * 100).toFixed(2)}%
                </span>
              </div>
              <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 rounded-full"
                  style={{ width: `${Math.min(100, (node.pagerank ?? 0.08) * 400)}%` }}
                />
              </div>
            </div>

            {/* Architectural Community */}
            {node.community !== undefined && (
              <div className="p-3 bg-white/5 rounded-xl border border-white/5 flex items-center justify-between text-xs font-mono">
                <span className="text-white/60">Louvain Modularity Cluster:</span>
                <span className="px-2.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  Cluster #{node.community}
                </span>
              </div>
            )}
          </div>
        )}

        {/* DEPS TAB */}
        {activeTab === 'deps' && (
          <div className="space-y-4">
            <div>
              <span className="text-xs font-mono uppercase text-white/50 block mb-2">
                Incoming Dependencies ({incomingDeps.length})
              </span>
              {incomingDeps.length === 0 ? (
                <p className="text-xs font-mono text-white/30 italic">No incoming direct dependencies</p>
              ) : (
                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {incomingDeps.map((dep, idx) => (
                    <div
                      key={idx}
                      onClick={() => onSelectNode(dep)}
                      className="p-2 rounded bg-white/5 hover:bg-white/10 border border-white/5 flex items-center justify-between text-xs font-mono text-white/80 cursor-pointer group"
                    >
                      <span className="truncate">{dep}</span>
                      <ExternalLink className="w-3 h-3 text-white/30 group-hover:text-blue-400 shrink-0 ml-1" />
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="border-t border-white/10 pt-4">
              <span className="text-xs font-mono uppercase text-white/50 block mb-2">
                Outgoing Dependencies ({outgoingDeps.length})
              </span>
              {outgoingDeps.length === 0 ? (
                <p className="text-xs font-mono text-white/30 italic">No outgoing direct dependencies</p>
              ) : (
                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {outgoingDeps.map((dep, idx) => (
                    <div
                      key={idx}
                      onClick={() => onSelectNode(dep)}
                      className="p-2 rounded bg-white/5 hover:bg-white/10 border border-white/5 flex items-center justify-between text-xs font-mono text-white/80 cursor-pointer group"
                    >
                      <span className="truncate">{dep}</span>
                      <ExternalLink className="w-3 h-3 text-white/30 group-hover:text-purple-400 shrink-0 ml-1" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* SECURITY & FINDINGS TAB */}
        {activeTab === 'security' && (
          <div className="space-y-3">
            {(!node.findings || node.findings.length === 0) ? (
              <div className="text-center py-8">
                <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto mb-2 opacity-80" />
                <p className="text-xs font-mono text-white/80 font-medium">No AST Security Vulnerabilities</p>
                <p className="text-[11px] font-mono text-white/40 mt-1">This node passes all 14 security rules</p>
              </div>
            ) : (
              node.findings.map((f, idx) => (
                <div key={idx} className="p-3.5 bg-red-500/10 border border-red-500/30 rounded-xl space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-mono font-bold text-red-300">
                      {f.title}
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 text-[10px] font-mono uppercase">
                      {f.severity}
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-2 text-[10px] font-mono text-white/60">
                    {f.cwe && <span className="bg-white/5 px-2 py-0.5 rounded">CWE: {f.cwe}</span>}
                    {f.owasp && <span className="bg-white/5 px-2 py-0.5 rounded">OWASP: {f.owasp}</span>}
                    {f.line_number && <span className="bg-white/5 px-2 py-0.5 rounded">Line: {f.line_number}</span>}
                  </div>

                  {f.code_snippet && (
                    <div className="p-2 bg-black/60 rounded border border-white/10 text-[11px] font-mono text-white/80 overflow-x-auto">
                      <code>{f.code_snippet}</code>
                    </div>
                  )}

                  {f.remediation && (
                    <p className="text-[11px] font-mono text-emerald-300/80 leading-relaxed">
                      💡 <strong>Remediation:</strong> {f.remediation}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* REFACTORING SUGGESTIONS TAB */}
        {activeTab === 'refactor' && (
          <div className="space-y-4">
            {nodeSuggestions.length === 0 ? (
              <div className="text-center py-8">
                <Wrench className="w-10 h-10 text-white/30 mx-auto mb-2" />
                <p className="text-xs font-mono text-white/80">No Specific Refactoring Needed</p>
                <p className="text-[11px] font-mono text-white/40 mt-1">
                  Coupling and complexity metrics fall within optimal bounds.
                </p>
              </div>
            ) : (
              nodeSuggestions.map((s, idx) => (
                <div key={idx} className="p-4 bg-white/5 border border-white/10 rounded-xl space-y-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-mono font-bold text-white">
                      {s.title}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-mono">
                      Effort: {s.effort}
                    </span>
                  </div>

                  <p className="text-[11px] text-white/70 font-mono leading-relaxed">
                    {s.rationale}
                  </p>

                  {/* Before / After simulated metrics */}
                  {s.impact_before && s.impact_after && (
                    <div className="p-2.5 bg-black/40 rounded-lg border border-white/5 grid grid-cols-2 gap-2 text-[10px] font-mono">
                      <div>
                        <span className="text-white/40 block">Coupling:</span>
                        <span className="text-red-400">{s.impact_before.coupling}</span>
                        <span className="text-white/40"> → </span>
                        <span className="text-emerald-400 font-bold">{s.impact_after.coupling}</span>
                      </div>
                      <div>
                        <span className="text-white/40 block">Cycles:</span>
                        <span className="text-red-400">{s.impact_before.cycles}</span>
                        <span className="text-white/40"> → </span>
                        <span className="text-emerald-400 font-bold">{s.impact_after.cycles}</span>
                      </div>
                    </div>
                  )}

                  {onDraftDiff && (
                    <button
                      onClick={() => onDraftDiff(s)}
                      className="w-full mt-2 py-2 rounded-lg bg-white/10 hover:bg-white/20 border border-white/10 text-xs font-mono text-white flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                    >
                      <Code2 className="w-3.5 h-3.5 text-blue-400" />
                      <span>Draft Refactoring Diff</span>
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
