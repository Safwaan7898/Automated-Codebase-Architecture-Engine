import React, { useEffect, useState } from 'react'

export interface StatCardProps {
  label: string
  value: number
  suffix?: string
  prefix?: string
  change?: string
  trend?: 'up' | 'down' | 'neutral'
  icon?: React.ReactNode
  color?: string
  className?: string
}

export function StatCard({
  label,
  value,
  suffix = '',
  prefix = '',
  change,
  trend,
  icon,
  color,
  className = '',
}: StatCardProps) {
  const [count, setCount] = useState(0)

  useEffect(() => {
    const start = 0
    const end = value
    if (start === end) {
      setCount(end)
      return
    }

    const duration = 1000
    const frameRate = 1000 / 60
    const totalFrames = Math.round(duration / frameRate)
    let currentFrame = 0

    const timer = setInterval(() => {
      currentFrame++
      const progress = currentFrame / totalFrames
      // Ease out cubic
      const easeProgress = 1 - Math.pow(1 - progress, 3)
      setCount(Math.round(start + (end - start) * easeProgress))

      if (currentFrame >= totalFrames) {
        clearInterval(timer)
        setCount(end)
      }
    }, frameRate)

    return () => clearInterval(timer)
  }, [value])

  return (
    <div
      className={`p-6 rounded-3xl bg-[var(--card-bg)] border border-[var(--border)] backdrop-blur-2xl shadow-[var(--shadow-glass)] flex flex-col justify-between transition-[transform,box-shadow,border-color] duration-300 hover:-translate-y-1 will-change-transform ${className}`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-['Space_Grotesk'] font-bold uppercase tracking-wider text-[var(--text-muted)]">
          {label}
        </span>
        {icon && (
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center text-xs"
            style={{
              backgroundColor: color ? `${color}20` : 'var(--input-bg)',
              color: color || 'var(--accent)',
            }}
          >
            {icon}
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-1 my-1">
        {prefix && <span className="font-mono text-xl text-[var(--text-muted)]">{prefix}</span>}
        <span
          className="font-mono text-3xl sm:text-4xl font-bold tracking-tight"
          style={{ color: color || 'var(--text-primary)' }}
        >
          {count.toLocaleString()}
        </span>
        {suffix && <span className="font-mono text-sm text-[var(--text-muted)]">{suffix}</span>}
      </div>

      {change && (
        <div className="flex items-center gap-1.5 mt-2 text-[10px] font-mono">
          <span
            className={`font-bold ${
              trend === 'up'
                ? 'text-[var(--accent-text)]'
                : trend === 'down'
                ? 'text-[#DC2626] dark:text-[#FF2D20]'
                : 'text-[var(--text-muted)]'
            }`}
          >
            {change}
          </span>
          <span className="text-[var(--text-muted)]">vs last scan</span>
        </div>
      )}
    </div>
  )
}
