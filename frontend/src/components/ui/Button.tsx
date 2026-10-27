import React, { forwardRef } from 'react'
import { Loader2 } from 'lucide-react'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      children,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    const sizeClasses = {
      sm: 'px-3 py-1.5 text-xs rounded-full gap-1.5',
      md: 'px-5 py-2.5 text-xs rounded-full gap-2',
      lg: 'px-7 py-3 text-sm rounded-full gap-2.5',
    }

    const variantClasses = {
      primary:
        'bg-[#C6F432] text-[#0B0D0C] font-bold shadow-[0_4px_20px_rgba(198,244,50,0.35)] hover:shadow-[0_0_25px_rgba(198,244,50,0.55)] border border-transparent',
      secondary:
        'bg-[var(--surface-2)] dark:bg-white/10 hover:bg-[var(--surface-hover)] dark:hover:bg-white/20 text-[var(--text-primary)] border border-[var(--border)] backdrop-blur-md',
      ghost:
        'bg-transparent hover:bg-black/5 dark:hover:bg-white/5 text-[var(--text-primary)] border border-transparent',
      danger:
        'bg-[#DC2626] dark:bg-[#FF2D20] text-white font-bold shadow-[0_4px_16px_rgba(255,45,32,0.4)] hover:shadow-[0_0_25px_rgba(255,45,32,0.6)] border border-transparent',
    }

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`inline-flex items-center justify-center font-['Space_Grotesk'] font-bold uppercase tracking-wider transition-[transform,opacity,color,background-color,border-color,box-shadow] duration-200 will-change-transform cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed select-none active:scale-[0.98] ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
        {...props}
      >
        {isLoading ? (
          <>
            <Loader2 size={size === 'sm' ? 12 : 14} className="animate-spin shrink-0" />
            <span>Loading...</span>
          </>
        ) : (
          <>
            {leftIcon && <span className="shrink-0">{leftIcon}</span>}
            <span>{children}</span>
            {rightIcon && <span className="shrink-0">{rightIcon}</span>}
          </>
        )}
      </button>
    )
  }
)

Button.displayName = 'Button'
