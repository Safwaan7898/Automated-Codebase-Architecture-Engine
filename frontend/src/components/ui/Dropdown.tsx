import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export interface DropdownItem {
  id: string
  label: string
  icon?: React.ReactNode
  onClick: () => void
  danger?: boolean
}

export interface DropdownProps {
  trigger: React.ReactNode
  items: DropdownItem[]
  align?: 'left' | 'right'
}

export function Dropdown({ trigger, items, align = 'right' }: DropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <div onClick={() => setIsOpen(!isOpen)} className="cursor-pointer">
        {trigger}
      </div>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -4 }}
            transition={{ duration: 0.15 }}
            className={`absolute ${
              align === 'right' ? 'right-0' : 'left-0'
            } mt-2 w-48 rounded-2xl border border-[var(--border)] bg-[var(--card-bg)] backdrop-blur-2xl p-1.5 shadow-2xl z-50 font-sans`}
          >
            {items.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  item.onClick()
                  setIsOpen(false)
                }}
                className={`w-full flex items-center gap-2.5 px-3 py-2 text-xs font-['Space_Grotesk'] font-bold uppercase tracking-wider rounded-xl transition-colors cursor-pointer ${
                  item.danger
                    ? 'text-[#FF2D20] hover:bg-[#FF2D20]/10'
                    : 'text-[var(--text-primary)] hover:bg-black/5 dark:hover:bg-white/5'
                }`}
              >
                {item.icon && <span className="shrink-0">{item.icon}</span>}
                <span>{item.label}</span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
