export interface SwitchProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  description?: string
  disabled?: boolean
  className?: string
}

export function Switch({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  className = '',
}: SwitchProps) {
  return (
    <label
      className={`inline-flex items-center justify-between gap-4 cursor-pointer select-none ${
        disabled ? 'opacity-40 cursor-not-allowed' : ''
      } ${className}`}
      onClick={(e) => {
        if (disabled) return
        e.preventDefault()
        onChange(!checked)
      }}
    >
      {(label || description) && (
        <div className="flex flex-col">
          {label && (
            <span className="text-xs font-['Space_Grotesk'] font-bold text-[var(--text-primary)]">
              {label}
            </span>
          )}
          {description && (
            <span className="text-[11px] font-mono text-[var(--text-muted)] mt-0.5">
              {description}
            </span>
          )}
        </div>
      )}
      <div
        className={`w-10 h-6 rounded-full transition-colors duration-200 relative p-0.5 border ${
          checked
            ? 'bg-[#C6F432] border-[#C6F432]'
            : 'bg-[var(--input-bg)] border-[var(--input-border)]'
        }`}
      >
        <div
          className={`w-4.5 h-4.5 rounded-full transition-transform duration-200 shadow-md ${
            checked
              ? 'translate-x-4 bg-[#0B0D0C]'
              : 'translate-x-0 bg-[var(--text-muted)]'
          }`}
        />
      </div>
    </label>
  )
}
