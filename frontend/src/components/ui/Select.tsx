import React, { forwardRef } from 'react'
import { ChevronDown } from 'lucide-react'

export interface SelectOption {
  value: string
  label: string
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  options: SelectOption[]
  error?: string
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, options, error, className = '', id, ...props }, ref) => {
    const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined)

    return (
      <div className="w-full flex flex-col gap-1.5 font-sans">
        {label && (
          <label
            htmlFor={selectId}
            className="text-[11px] font-['Space_Grotesk'] font-bold tracking-wider text-[var(--text-secondary)] uppercase"
          >
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          <select
            id={selectId}
            ref={ref}
            className={`w-full appearance-none bg-[var(--input-bg)] border rounded-xl px-4 py-2.5 pr-10 text-xs text-[var(--text-primary)] outline-none transition-colors duration-200 font-mono cursor-pointer ${
              error
                ? 'border-[#FF2D20] focus:ring-1 focus:ring-[#FF2D20]'
                : 'border-[var(--input-border)] focus:border-[#C6F432]'
            } ${className}`}
            {...props}
          >
            {options.map((opt) => (
              <option
                key={opt.value}
                value={opt.value}
                className="bg-[var(--bg-elevated)] text-[var(--text-primary)]"
              >
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown
            size={14}
            className="absolute right-3.5 text-[var(--text-muted)] pointer-events-none"
          />
        </div>
        {error && <span className="text-[10px] font-mono text-[#FF2D20]">{error}</span>}
      </div>
    )
  }
)

Select.displayName = 'Select'
