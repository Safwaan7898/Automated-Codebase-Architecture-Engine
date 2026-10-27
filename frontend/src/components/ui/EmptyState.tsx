import React from 'react'

export interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className = '',
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-3xl border border-[var(--border)] bg-[var(--card-bg)] backdrop-blur-xl ${className}`}
    >
      {icon && (
        <div className="w-14 h-14 rounded-2xl bg-[#C6F432]/10 border border-[#C6F432] flex items-center justify-center text-[#0B0D0C] dark:text-[#C6F432] mb-4 shadow-[0_0_20px_rgba(198,244,50,0.3)]">
          {icon}
        </div>
      )}
      <h3 className="font-['Space_Grotesk'] text-lg font-bold uppercase tracking-tight text-[var(--text-primary)] mb-1">
        {title}
      </h3>
      {description && (
        <p className="text-xs text-[var(--text-muted)] font-mono max-w-sm mb-6 leading-relaxed">
          {description}
        </p>
      )}
      {action && <div>{action}</div>}
    </div>
  )
}
