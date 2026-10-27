import { useState } from 'react'
import type { AnalysisResult, GraphNode, Suggestion } from '../types'

interface Props {
  result: AnalysisResult | null
  selectedNode: GraphNode | null
  activeTab: 'smells' | 'suggestions' | 'node'
  onTabChange: (tab: 'smells' | 'suggestions' | 'node') => void
}

const EFFORT_COLORS = {
  low: 'text-green-400',
  medium: 'text-yellow-400',
  high: 'text-red-400',
}

const IMPACT_COLORS = {
  low: 'text-slate-400',
  medium: 'text-brand-400',
  high: 'text-accent-400',
}

function SuggestionCard({ s }: { s: Suggestion }) {
  const [open, setOpen] = useState(false)
  return (
    <div
      className="rounded-lg border border-surface-600 bg-surface-700 p-3 cursor-pointer
                 hover:border-brand-500 transition-colors duration-150"
      onClick={() => setOpen((o) => !o)}
    >
      <div className="flex items-start gap-2">
        <span className="text-lg">🛠️</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-white leading-snug">{s.title}</p>
          <div className="flex gap-3 mt-1">
            <span className={`text-[10px] ${EFFORT_COLORS[s.effort]}`}>Effort: {s.effort}</span>
            <span className={`text-[10px] ${IMPACT_COLORS[s.impact]}`}>Impact: {s.impact}</span>
          </div>
        </div>
        <span className="text-slate-500 text-xs">{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div className="mt-2 space-y-1.5 animate-fade-in">
          <p className="text-xs text-slate-300">{s.description}</p>
          {s.affected_files.length > 0 && (
            <div className="text-[10px] text-slate-500 space-y-0.5">
              {s.affected_files.slice(0, 3).map((f, i) => (
                <div key={i} className="font-mono truncate">📄 {f}</div>
              ))}
              {s.affected_files.length > 3 && (
                <div>…and {s.affected_files.length - 3} more</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function NodeDetail({ node }: { node: GraphNode }) {
  return (
    <div className="p-4 space-y-3 animate-fade-in">
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 rounded-full bg-brand-500" />
        <h3 className="text-sm font-bold text-white">{node.label}</h3>
      </div>
      <div className="space-y-2 text-xs">
        {[
          { label: 'Type', value: node.type },
          { label: 'ID', value: node.id },
          { label: 'File', value: node.file_path ?? '—' },
          { label: 'Lines', value: node.loc ? `${node.loc} loc` : '—' },
        ].map(({ label, value }) => (
          <div key={label} className="flex gap-2">
            <span className="text-slate-500 w-12 shrink-0">{label}</span>
            <span className="text-slate-200 font-mono truncate">{value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function Sidebar({ result, selectedNode, activeTab, onTabChange }: Props) {
  const tabs: { id: 'smells' | 'suggestions' | 'node'; label: string; count?: number }[] = [
    { id: 'smells', label: 'Smells', count: result?.smells.length },
    { id: 'suggestions', label: 'Fixes', count: result?.suggestions.length },
    { id: 'node', label: 'Node', count: selectedNode ? 1 : undefined },
  ]

  return (
    <div className="flex flex-col h-full">
      {/* Stats bar */}
      {result && (
        <div className="grid grid-cols-3 gap-2 p-4 border-b border-surface-700">
          {[
            { label: 'Nodes', value: result.node_count },
            { label: 'Edges', value: result.edge_count },
            { label: 'Smells', value: result.smells.length },
          ].map(({ label, value }) => (
            <div key={label} className="text-center">
              <div className="text-lg font-bold text-brand-400">{value}</div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-surface-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex-1 py-2.5 text-xs font-medium transition-colors
              ${activeTab === tab.id
                ? 'text-brand-400 border-b-2 border-brand-500'
                : 'text-slate-500 hover:text-slate-300'
              }`}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span className="ml-1 bg-surface-600 text-slate-400 text-[9px] px-1.5 py-0.5 rounded-full">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'node' && selectedNode && <NodeDetail node={selectedNode} />}
        {activeTab === 'node' && !selectedNode && (
          <div className="p-5 text-center text-slate-500 text-xs mt-8">
            Click a node in the graph to inspect it
          </div>
        )}
        {activeTab === 'suggestions' && result && (
          <div className="p-4 space-y-2 animate-fade-in">
            {result.suggestions.length === 0 ? (
              <div className="text-center text-slate-500 text-sm mt-8">
                <div className="text-3xl mb-2">🎉</div>
                <p>No suggestions needed!</p>
              </div>
            ) : (
              result.suggestions.map((s, i) => <SuggestionCard key={i} s={s} />)
            )}
          </div>
        )}
        {activeTab === 'smells' && !result && (
          <div className="p-5 text-center text-slate-500 text-xs mt-8">
            Run an analysis to see detected smells
          </div>
        )}
      </div>
    </div>
  )
}
