import React from 'react'

export interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'accent' | 'danger' | 'warning' | 'outline'
  size?: 'sm' | 'md'
  className?: string
}

export function Badge({
  children,
  variant = 'default',
  size = 'md',
  className = '',
}: BadgeProps) {
  const sizeClasses = {
    sm: 'text-[9px] px-2 py-0.5',
    md: 'text-[10px] px-2.5 py-1',
  }

  const variantClasses = {
    default: 'bg-[var(--input-bg)] border border-[var(--border)] text-[var(--text-secondary)]',
    accent: 'bg-[#C6F432]/15 border border-[#C6F432] text-[#0B0D0C] dark:text-[#C6F432]',
    danger: 'bg-[#FF2D20]/15 border border-[#FF2D20] text-[#B91C1C] dark:text-[#FF2D20]',
    warning: 'bg-[#F59E0B]/15 border border-[#F59E0B] text-[#92400e] dark:text-[#F59E0B]',
    outline: 'border border-[var(--border)] text-[var(--text-primary)]',
  }

  return (
    <span
      className={`inline-flex items-center gap-1 font-mono uppercase tracking-wider font-bold rounded-full ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
    >
      {children}
    </span>
  )
}
