import type { Smell } from '../types'
import { AIExplainPanel } from './AIExplainPanel'
import { AIBadge } from './ui/AILabel'
import { aiApi } from '../api/client'

interface Props {
  smells: Smell[]
}

const SEVERITY_CONFIG = {
  critical: { bg: 'bg-red-500/15',   border: 'border-red-500/40',   dot: 'bg-red-500',    label: 'Critical' },
  high:     { bg: 'bg-orange-500/15', border: 'border-orange-500/40', dot: 'bg-orange-500', label: 'High' },
  medium:   { bg: 'bg-yellow-500/15', border: 'border-yellow-500/40', dot: 'bg-yellow-500', label: 'Medium' },
  low:      { bg: 'bg-blue-500/15',   border: 'border-blue-500/40',   dot: 'bg-blue-500',   label: 'Low' },
}

const SMELL_EMOJI: Record<string, string> = {
  god_module: '🐋',
  circular_import: '🔄',
  dead_code: '💀',
  deep_inheritance: '🌲',
  large_class: '🏋️',
  feature_envy: '👀',
  long_parameter_list: '📜',
  duplicate_code: '👥',
  missing_type_hints: '❓',
}

export function SmellList({ smells }: Props) {
  if (smells.length === 0) {
    return (
      <div className="p-5 text-center text-slate-500 text-sm animate-fade-in">
        <div className="text-3xl mb-2">✅</div>
        <p>No architectural smells detected!</p>
      </div>
    )
  }

  const sorted = [...smells].sort((a, b) => {
    const order = { critical: 0, high: 1, medium: 2, low: 3 }
    return (order[a.severity] ?? 4) - (order[b.severity] ?? 4)
  })

  return (
    <div className="p-4 space-y-2 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-1.5">
          <h3 className="text-sm font-semibold text-white">Architectural Smells</h3>
          <AIBadge label="AI-generated" size="xs" />
        </div>
        <span className="text-xs bg-surface-600 text-slate-300 px-2 py-0.5 rounded-full">
          {smells.length} found
        </span>
      </div>

      {sorted.map((smell, idx) => {
        const cfg = SEVERITY_CONFIG[smell.severity] ?? SEVERITY_CONFIG.low
        return (
          <div
            key={idx}
            className={`rounded-lg border p-3 space-y-1.5 transition-transform duration-200 hover:scale-[1.01] will-change-transform ${cfg.bg} ${cfg.border}`}
          >
            <div className="flex items-center gap-2">
              <span className="text-base">{SMELL_EMOJI[smell.type] ?? '⚠️'}</span>
              <span className="text-xs font-semibold text-white capitalize">
                {smell.type.replace(/_/g, ' ')}
              </span>
              <div className={`ml-auto w-2 h-2 rounded-full flex-shrink-0 ${cfg.dot}`} />
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">{smell.description}</p>

            <p className="text-[10px] font-mono text-slate-500 truncate">
              📄 {smell.file}
              {smell.line ? `:${smell.line}` : ''}
            </p>

            {smell.suggestion && (
              <div className="mt-1 text-[10px] text-slate-400 bg-black/20 rounded px-2 py-1">
                💡 {smell.suggestion}
              </div>
            )}

            <AIExplainPanel
              label="Explain Smell & Fix Outline"
              className="mt-1 pt-1 border-t border-white/5"
              fetch={async () => {
                try {
                  const res = await aiApi.explainSmell(
                    smell as unknown as Record<string, unknown>,
                    { file: smell.file }
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
        )
      })}
    </div>
  )
}
