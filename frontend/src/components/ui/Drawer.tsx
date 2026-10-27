import React, { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'

export interface DrawerProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  position?: 'right' | 'left'
  width?: string
}

export function Drawer({
  isOpen,
  onClose,
  title,
  children,
  position = 'right',
  width = 'max-w-md',
}: DrawerProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      document.body.style.overflow = 'hidden'
      window.addEventListener('keydown', handleKeyDown)
    }
    return () => {
      document.body.style.overflow = 'unset'
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  const initialOffset = position === 'right' ? '100%' : '-100%'

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex overflow-hidden">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-md"
          />
          <motion.div
            initial={{ x: initialOffset }}
            animate={{ x: 0 }}
            exit={{ x: initialOffset }}
            transition={{ type: 'spring', damping: 28, stiffness: 240 }}
            className={`relative ml-auto h-full w-full ${width} bg-[var(--card-bg)] border-l border-[var(--border)] shadow-2xl backdrop-blur-2xl z-10 flex flex-col font-sans`}
          >
            <div className="flex items-center justify-between p-6 border-b border-[var(--border)]">
              {title && (
                <h3 className="font-['Space_Grotesk'] text-lg font-bold uppercase tracking-tight text-[var(--text-primary)]">
                  {title}
                </h3>
              )}
              <button
                onClick={onClose}
                className="p-1.5 rounded-full text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-black/5 dark:hover:bg-white/5 transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
