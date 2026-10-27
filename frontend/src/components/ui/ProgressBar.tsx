export interface ProgressBarProps {
  value: number // 0 to 100
  label?: string
  color?: string
  showValue?: boolean
  className?: string
}

export function ProgressBar({
  value,
  label,
  color = '#C6F432',
  showValue = true,
  className = '',
}: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value))

  return (
    <div className={`w-full flex flex-col gap-1.5 font-sans ${className}`}>
      {(label || showValue) && (
        <div className="flex items-center justify-between text-[11px] font-mono">
          {label && <span className="text-[var(--text-secondary)] uppercase">{label}</span>}
          {showValue && <span className="text-[var(--text-primary)] font-bold">{clamped}%</span>}
        </div>
      )}
      <div className="w-full h-2 rounded-full bg-[var(--input-bg)] border border-[var(--border)] overflow-hidden p-0.5">
        <div
          className="h-full rounded-full transition-[width] duration-300 ease-out shadow-sm"
          style={{
            width: `${clamped}%`,
            backgroundColor: color,
            boxShadow: `0 0 10px ${color}80`,
          }}
        />
      </div>
    </div>
  )
}
