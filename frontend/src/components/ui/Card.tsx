import React from 'react'

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  variant?: 'glass' | 'solid' | 'elevated'
  hoverLift?: boolean
  className?: string
}

export function Card({
  children,
  variant = 'glass',
  hoverLift = true,
  className = '',
  ...props
}: CardProps) {
  const variantClasses = {
    glass:
      'bg-[var(--card-bg)] border border-[var(--border)] backdrop-blur-2xl shadow-[var(--shadow-glass)]',
    solid:
      'bg-[var(--bg-surface)] border border-[var(--border)] shadow-md',
    elevated:
      'bg-[var(--bg-elevated)] border border-[var(--border)] shadow-xl',
  }

  return (
    <div
      className={`rounded-3xl p-6 transition-[transform,box-shadow,border-color] duration-300 font-sans ${
        hoverLift ? 'hover:-translate-y-1 will-change-transform hover:border-white/25 dark:hover:border-white/20' : ''
      } ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}
