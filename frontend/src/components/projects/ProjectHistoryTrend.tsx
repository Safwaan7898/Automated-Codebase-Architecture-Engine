import { useState } from 'react'
import { Info, TrendingUp } from 'lucide-react'
import type { ProjectHistoryItem } from '../../types'

interface ProjectHistoryTrendProps {
  history: ProjectHistoryItem[]
}

export function ProjectHistoryTrend({ history }: ProjectHistoryTrendProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  if (!history || history.length === 0) {
    return (
      <div className="p-4 rounded-xl border border-[var(--border)] dark:border-white/5 bg-surface-2 dark:bg-white/[0.02] text-xs text-muted text-center">
        No historical runs recorded for this project yet.
      </div>
    )
  }

  // Chronological order (oldest to newest)
  const items = [...history].reverse()
  const n = items.length

  const width = 500
  const height = 180
  const padX = 40
  const padY = 24
  const plotW = width - padX * 2
  const plotH = height - padY * 2

  // Score points (0 to 100)
  const scorePoints = items.map((item, idx) => {
    const x = n > 1 ? padX + (idx / (n - 1)) * plotW : padX + plotW / 2
    const score = Math.max(0, Math.min(100, item.score))
    const y = padY + (1 - score / 100) * plotH
    return { x, y, score, item }
  })

  const scorePathD =
    scorePoints.length > 1
      ? scorePoints.reduce((acc, pt, idx) => `${acc} ${idx === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`, '')
      : ''

  const activeItem = hoveredIndex !== null ? items[hoveredIndex] : items[items.length - 1]

  return (
    <div className="space-y-3 p-4 rounded-xl border border-[var(--border)] dark:border-white/5 bg-surface-2 dark:bg-white/[0.02]">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-bold text-[var(--text-primary)]">
          <TrendingUp size={14} className="text-accent" />
          <span>Historical Health & Debt Trends</span>
        </div>
        <span className="text-[10px] text-muted font-mono">{items.length} analysis runs recorded</span>
      </div>

      {/* SVG Trend Chart */}
      <div className="relative border border-[var(--border)] dark:border-white/5 rounded-lg bg-surface dark:bg-black/20 p-2 overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto select-none"
          role="img"
          aria-label="Health score historical trend chart"
        >
          {/* Grid lines */}
          <line x1={padX} y1={padY} x2={width - padX} y2={padY} stroke="currentColor" strokeOpacity="0.06" />
          <line
            x1={padX}
            y1={padY + plotH / 2}
            x2={width - padX}
            y2={padY + plotH / 2}
            stroke="currentColor"
            strokeOpacity="0.06"
          />
          <line
            x1={padX}
            y1={padY + plotH}
            x2={width - padX}
            y2={padY + plotH}
            stroke="currentColor"
            strokeOpacity="0.06"
          />

          {/* Y Axis labels */}
          <text x={padX - 8} y={padY + 4} textAnchor="end" fontSize="8" fill="var(--text-muted)" className="font-mono">
            100
          </text>
          <text
            x={padX - 8}
            y={padY + plotH / 2 + 3}
            textAnchor="end"
            fontSize="8"
            fill="var(--text-muted)"
            className="font-mono"
          >
            50
          </text>
          <text
            x={padX - 8}
            y={padY + plotH + 3}
            textAnchor="end"
            fontSize="8"
            fill="var(--text-muted)"
            className="font-mono"
          >
            0
          </text>

          {/* Score line */}
          {scorePathD && (
            <path
              d={scorePathD}
              fill="none"
              stroke="#10b981"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Interactive Data Points */}
          {scorePoints.map((pt, idx) => {
            const isHovered = hoveredIndex === idx
            return (
              <g
                key={pt.item.analysis_id}
                onMouseEnter={() => setHoveredIndex(idx)}
                onMouseLeave={() => setHoveredIndex(null)}
                tabIndex={0}
                role="button"
                aria-label={`Run on ${new Date(pt.item.created_at).toLocaleDateString()}: Score ${pt.score}`}
                onFocus={() => setHoveredIndex(idx)}
                onBlur={() => setHoveredIndex(null)}
                className="cursor-pointer focus:outline-none"
              >
                <circle
                  cx={pt.x}
                  cy={pt.y}
                  r={isHovered ? 6 : 4}
                  fill={isHovered ? '#10b981' : '#ffffff'}
                  stroke="#10b981"
                  strokeWidth="2"
                  className="transition-all"
                />
              </g>
            )
          })}
        </svg>

        {/* Active hovered point banner */}
        {activeItem && (
          <div className="mt-2 p-2 rounded-lg bg-surface-2 dark:bg-white/5 border border-[var(--border)] dark:border-white/10 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono">
            <div className="flex items-center gap-2">
              <span className="font-bold text-[var(--text-primary)]">
                {new Date(activeItem.created_at).toLocaleDateString()} {new Date(activeItem.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              <span className="badge badge-accent text-[9px] uppercase font-bold">{activeItem.commit_sha}</span>
            </div>
            <div className="flex items-center gap-3 text-muted">
              <span>
                Score: <strong className="text-emerald-400">{activeItem.score}</strong>
              </span>
              <span>
                Cycles: <strong className={activeItem.cycles > 0 ? 'text-red-400' : 'text-primary'}>{activeItem.cycles}</strong>
              </span>
              <span>
                Smells: <strong className={activeItem.smells > 0 ? 'text-amber-400' : 'text-primary'}>{activeItem.smells}</strong>
              </span>
              <span>
                Modules: <strong className="text-primary">{activeItem.node_count}</strong>
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="text-[10px] text-muted flex items-center gap-1">
        <Info size={11} /> Hover or focus on points along the timeline to inspect architectural metric evolutions.
      </div>
    </div>
  )
}
