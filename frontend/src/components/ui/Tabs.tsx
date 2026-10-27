import React from 'react'
import { motion } from 'framer-motion'

export interface TabItem {
  id: string
  label: string
  icon?: React.ReactNode
  badge?: string | number
}

export interface TabsProps {
  tabs: TabItem[]
  activeTab: string
  onChange: (id: string) => void
  variant?: 'pill' | 'underline'
  className?: string
}

export function Tabs({
  tabs,
  activeTab,
  onChange,
  variant = 'pill',
  className = '',
}: TabsProps) {
  if (variant === 'underline') {
    return (
      <div className={`flex items-center gap-6 border-b border-[var(--border)] ${className}`}>
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => onChange(tab.id)}
              className={`relative pb-3 text-xs font-['Space_Grotesk'] font-bold tracking-wider uppercase transition-colors flex items-center gap-2 cursor-pointer ${
                isActive ? 'text-[var(--text-primary)]' : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
              }`}
            >
              {tab.icon && <span>{tab.icon}</span>}
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-[var(--border)] text-[var(--text-muted)] font-mono">
                  {tab.badge}
                </span>
              )}
              {isActive && (
                <motion.div
                  layoutId="underline"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#C6F432]"
                />
              )}
            </button>
          )
        })}
      </div>
    )
  }

  return (
    <div
      className={`inline-flex items-center gap-1 p-1 rounded-full bg-[var(--input-bg)] border border-[var(--border)] backdrop-blur-md ${className}`}
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`relative px-4 py-1.5 rounded-full text-xs font-['Space_Grotesk'] font-bold tracking-wider uppercase transition-colors duration-200 flex items-center gap-1.5 cursor-pointer z-10 ${
              isActive
                ? 'text-[#0B0D0C]'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            {isActive && (
              <motion.div
                layoutId="pill-active"
                className="absolute inset-0 bg-[#C6F432] rounded-full -z-10 shadow-sm"
                transition={{ type: 'spring', stiffness: 350, damping: 30 }}
              />
            )}
            {tab.icon && <span className="shrink-0">{tab.icon}</span>}
            <span>{tab.label}</span>
            {tab.badge !== undefined && (
              <span
                className={`text-[9px] px-1.5 py-0.2 rounded-full font-mono ${
                  isActive ? 'bg-[#0B0D0C]/20 text-[#0B0D0C]' : 'bg-[var(--border)] text-[var(--text-muted)]'
                }`}
              >
                {tab.badge}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
