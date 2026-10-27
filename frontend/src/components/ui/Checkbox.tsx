import React, { forwardRef } from 'react'
import { Check } from 'lucide-react'

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  description?: string
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, description, checked, onChange, className = '', id, disabled, ...props }, ref) => {
    const checkId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined)

    return (
      <label
        htmlFor={checkId}
        className={`inline-flex items-start gap-3 cursor-pointer select-none ${
          disabled ? 'opacity-40 cursor-not-allowed' : ''
        } ${className}`}
      >
        <div className="relative flex items-center justify-center mt-0.5">
          <input
            id={checkId}
            ref={ref}
            type="checkbox"
            checked={checked}
            onChange={onChange}
            disabled={disabled}
            className="peer sr-only"
            {...props}
          />
          <div className="w-4 h-4 rounded-[4px] border border-[var(--input-border)] bg-[var(--input-bg)] peer-checked:bg-[#C6F432] peer-checked:border-[#C6F432] transition-colors duration-150 flex items-center justify-center shadow-sm">
            {checked && <Check size={12} className="text-[#0B0D0C] stroke-[3]" />}
          </div>
        </div>
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
      </label>
    )
  }
)

Checkbox.displayName = 'Checkbox'
