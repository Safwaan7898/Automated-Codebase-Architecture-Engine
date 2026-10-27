import React, { forwardRef } from 'react'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, leftIcon, rightIcon, className = '', id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined)

    return (
      <div className="w-full flex flex-col gap-1.5 font-sans">
        {label && (
          <label
            htmlFor={inputId}
            className="text-[11px] font-['Space_Grotesk'] font-bold tracking-wider text-[var(--text-secondary)] uppercase"
          >
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {leftIcon && (
            <div className="absolute left-3.5 text-[var(--text-muted)] pointer-events-none flex items-center">
              {leftIcon}
            </div>
          )}
          <input
            id={inputId}
            ref={ref}
            className={`w-full bg-[var(--input-bg)] border rounded-xl px-4 py-2.5 text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-colors duration-200 font-mono ${
              leftIcon ? 'pl-10' : ''
            } ${rightIcon ? 'pr-10' : ''} ${
              error
                ? 'border-[#FF2D20] focus:ring-1 focus:ring-[#FF2D20]'
                : 'border-[var(--input-border)] focus:border-[#C6F432] focus:ring-1 focus:ring-[#C6F432]/40'
            } ${className}`}
            {...props}
          />
          {rightIcon && (
            <div className="absolute right-3.5 text-[var(--text-muted)] flex items-center">
              {rightIcon}
            </div>
          )}
        </div>
        {error && <span className="text-[10px] font-mono text-[#FF2D20]">{error}</span>}
        {!error && helperText && (
          <span className="text-[10px] font-mono text-[var(--text-muted)]">{helperText}</span>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
