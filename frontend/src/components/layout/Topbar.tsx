import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { createPortal } from 'react-dom'
import {
  Search,
  Bell,
  Settings,
  LogOut,
  ChevronDown,
  Terminal,
} from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'
import { useTheme } from '../../contexts/ThemeContext'
import { useAnalysisContext } from '../../contexts/AnalysisContext'

const ROLE_BADGE: Record<string, { label: string; color: string; lightColor: string }> = {
  ADMIN:               { label: 'ADMIN', color: '#f967fb', lightColor: '#86198f' },
  ENGINEERING_MANAGER: { label: 'MANAGER', color: '#06b6d4', lightColor: '#0e7490' },
  SENIOR_DEVELOPER:    { label: 'SR DEV', color: '#a3e635', lightColor: '#3f6212' },
  DEVELOPER:           { label: 'DEVELOPER', color: '#38bdf8', lightColor: '#0284c7' },
  SECURITY_ANALYST:    { label: 'SECURITY', color: '#f43f5e', lightColor: '#be123c' },
  QA_ENGINEER:         { label: 'QA', color: '#818cf8', lightColor: '#4338ca' },
  VIEWER:              { label: 'VIEWER', color: '#94a3b8', lightColor: '#475569' },
}

export function Topbar() {
  const { user, logout } = useAuth()
  const { resolvedTheme } = useTheme()
  const { result } = useAnalysisContext()
  const navigate = useNavigate()
  const location = useLocation()
  const [profileOpen, setProfileOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const notifBtnRef = useRef<HTMLButtonElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const [popoverPos, setPopoverPos] = useState({ top: 64, right: 24 })

  const roleMeta = user ? (ROLE_BADGE[user.role] ?? { label: user.role, color: '#94a3b8', lightColor: '#475569' }) : null
  const activeColor = roleMeta ? (resolvedTheme === 'light' ? roleMeta.lightColor : roleMeta.color) : '#ffffff'

  const updatePopoverPos = () => {
    if (notifBtnRef.current) {
      const rect = notifBtnRef.current.getBoundingClientRect()
      setPopoverPos({
        top: rect.bottom + 8,
        right: Math.max(12, window.innerWidth - rect.right),
      })
    }
  }

  // Auto-close on route change
  useEffect(() => {
    setNotifOpen(false)
    setProfileOpen(false)
  }, [location.pathname])

  // Click-outside and Escape key handling for Telemetry popover
  useEffect(() => {
    if (!notifOpen) return
    updatePopoverPos()

    const handlePointerDown = (e: MouseEvent) => {
      const target = e.target as Node | null
      if (
        popoverRef.current &&
        !popoverRef.current.contains(target) &&
        notifBtnRef.current &&
        !notifBtnRef.current.contains(target)
      ) {
        setNotifOpen(false)
      }
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setNotifOpen(false)
      }
    }

    const handleResize = () => {
      updatePopoverPos()
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    window.addEventListener('resize', handleResize)

    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('resize', handleResize)
    }
  }, [notifOpen])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <header
      className="h-16 flex items-center px-6 gap-4 flex-shrink-0 z-30 border-b relative"
      style={{
        background: 'var(--topbar-bg)',
        borderColor: 'var(--topbar-border)',
        backdropFilter: 'blur(20px)',
      }}
    >
      {/* Live Engine Status Pill */}
      <div
        className="hidden sm:flex items-center gap-2 px-3 py-1 border rounded-full text-[10px] font-mono tracking-[0.2em] uppercase"
        style={{
          background: 'var(--topbar-pill-bg)',
          borderColor: 'var(--topbar-pill-border)',
          color: 'var(--topbar-pill-text)',
        }}
      >
        <span className="w-2 h-2 rounded-full bg-[#CCFF00] animate-pulse shadow-[0_0_8px_#CCFF00]" />
        <span>LIVE AST ENGINE ONLINE</span>
      </div>

      {/* Global Search */}
      <div className="relative flex-1 max-w-md">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted dark:text-white/40 pointer-events-none"
        />
        <input
          type="text"
          placeholder="SEARCH MODULES, AST NODES, FINDINGS…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="field pl-9 pr-3 h-9 text-xs uppercase tracking-[0.15em] font-mono rounded-[2px] w-full"
          aria-label="Global search"
        />
      </div>

      <div className="flex-1" />

      {/* Quick Launch Terminal Link */}
      <Link
        to="/ingestion"
        className="hidden md:flex items-center gap-2 px-3 py-1.5 text-[11px] font-bold tracking-[0.2em] uppercase text-accent-text border border-accent/40 hover:border-accent hover:bg-accent/10 rounded-[2px] transition-colors dark:text-[#CCFF00] dark:border-[#CCFF00]/40 dark:hover:border-[#CCFF00] dark:hover:bg-[#CCFF00]/10"
      >
        <Terminal size={13} />
        <span>ANALYZE REPO</span>
      </Link>

      {/* Notifications / Telemetry Popover Button */}
      <div className="relative">
        <button
          ref={notifBtnRef}
          onClick={() => {
            if (!notifOpen) updatePopoverPos()
            setNotifOpen(!notifOpen)
          }}
          className="w-9 h-9 rounded-[2px] flex items-center justify-center transition-colors relative border border-border bg-surface-2/40 hover:border-[#f967fb] text-text-muted hover:text-text dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-[#f967fb] dark:text-white/70 dark:hover:text-white"
          aria-label="Telemetry events feed"
          aria-expanded={notifOpen}
          aria-haspopup="dialog"
          id="telemetry-trigger-btn"
          data-testid="telemetry-trigger-btn"
        >
          <Bell size={14} />
          {result && (
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-[#f967fb] shadow-[0_0_6px_#f967fb]" />
          )}
        </button>
      </div>

      {/* Telemetry Popover Portal */}
      {typeof document !== 'undefined' &&
        createPortal(
          <AnimatePresence>
            {notifOpen && (
              <motion.div
                ref={popoverRef}
                initial={{ opacity: 0, y: -6, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -6, scale: 0.98 }}
                transition={{ duration: 0.15 }}
                style={{
                  position: 'fixed',
                  top: popoverPos.top,
                  right: popoverPos.right,
                  zIndex: 9999,
                }}
                className="w-80 glass-card p-4 border border-[#f967fb]/40 shadow-2xl backdrop-blur-2xl"
                role="dialog"
                aria-label="Telemetry events live feed"
                id="telemetry-popover"
                data-testid="telemetry-popover"
              >
                <div className="flex items-center justify-between mb-3 border-b border-border pb-2">
                  <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#f967fb] font-bold">
                    TELEMETRY EVENTS
                  </span>
                  <span className="text-[9px] text-text-muted font-mono">
                    {result ? (result.repo_id ? `ID: ${result.repo_id.slice(0, 8)}` : 'ACTIVE') : 'NO ACTIVE ANALYSIS'}
                  </span>
                </div>
                <div className="space-y-2.5">
                  {result && result.graph ? (
                    <>
                      <div className="p-2.5 bg-surface-2/40 border border-border rounded-[2px]">
                        <p className="text-xs font-bold text-text uppercase tracking-[0.05em]">AST Parse Complete</p>
                        <p className="text-[11px] text-text-muted mt-0.5">
                          Identified {result.graph.nodes?.length ?? 0} nodes & {result.graph.edges?.length ?? 0} edges
                        </p>
                        <span className="text-[9px] text-accent-text font-mono mt-1 block">
                          ANALYSIS ID: {result.repo_id || 'CURRENT'}
                        </span>
                      </div>
                      {(() => {
                        const cycleCount = (result.graph?.edges?.filter((e) => e.is_cycle)?.length ?? 0) || (Array.isArray(result.cycles) ? result.cycles.length : (typeof result.cycles === 'number' ? result.cycles : 0))
                        return (
                          <div className="p-2.5 bg-surface-2/40 border border-border rounded-[2px]">
                            <p className="text-xs font-bold text-text uppercase tracking-[0.05em]">Dependency Cycles</p>
                            <p className="text-[11px] text-text-muted mt-0.5">
                              {cycleCount} dependency cycle{cycleCount === 1 ? '' : 's'} discovered
                            </p>
                            <span className="text-[9px] text-text-muted font-mono mt-1 block">
                              STATUS: {cycleCount > 0 ? 'CYCLES DETECTED' : 'CLEAN'}
                            </span>
                          </div>
                        )
                      })()}
                      {result.files_excluded !== undefined && (
                        <div className="p-2.5 bg-surface-2/40 border border-border rounded-[2px]" data-testid="telemetry-files-excluded">
                          <p className="text-xs font-bold text-text uppercase tracking-[0.05em]">Scope Filter</p>
                          <p className="text-[11px] text-text-muted mt-0.5">
                            {result.files_excluded} files excluded
                          </p>
                          <span className="text-[9px] text-accent-text font-mono mt-1 block">
                            {result.include_tests ? 'TESTS INCLUDED' : 'TESTS & FIXTURES EXCLUDED'}
                          </span>
                        </div>
                      )}
                      {result.source_fingerprint && (
                        <div className="p-2.5 bg-surface-2/40 border border-border rounded-[2px]">
                          <p className="text-xs font-bold text-text uppercase tracking-[0.05em]">Fingerprint SHA-256</p>
                          <p className="text-[11px] text-text-muted mt-0.5 font-mono">
                            {result.source_fingerprint.slice(0, 16)}...
                          </p>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="p-4 text-center text-text-muted text-xs font-mono">
                      No active telemetry events for current session.
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>,
          document.body
        )}

      {/* Profile menu */}
      <div className="relative">
        <button
          onClick={() => setProfileOpen(!profileOpen)}
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-[2px] border border-border bg-surface-2/40 hover:border-accent transition-colors dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-[#a3e635]"
        >
          <div
            className="w-6 h-6 rounded-[2px] flex items-center justify-center font-bold text-[10px] font-mono"
            style={{
              background: roleMeta ? `${activeColor}25` : 'rgba(255,255,255,0.1)',
              color: activeColor,
              border: `1px solid ${activeColor}`,
            }}
          >
            {user?.full_name?.charAt(0) ?? 'U'}
          </div>
          <span className="hidden md:block text-xs font-bold text-text uppercase tracking-[0.1em] max-w-[120px] truncate">
            {user?.full_name?.split(' ')[0] ?? 'User'}
          </span>
          {roleMeta && (
            <span
              className="hidden lg:inline-block text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-[2px]"
              style={{
                color: activeColor,
                background: `${activeColor}15`,
                border: `1px solid ${activeColor}40`,
              }}
            >
              {roleMeta.label}
            </span>
          )}
          <ChevronDown size={12} className="text-text-muted" />
        </button>

        <AnimatePresence>
          {profileOpen && (
            <motion.div
              initial={{ opacity: 0, y: -4, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -4, scale: 0.98 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 top-12 w-64 glass-card p-3 z-50 border border-border shadow-xl"
            >
              <div className="p-2 border-b border-border mb-2">
                <p className="text-xs font-bold text-text uppercase tracking-wider truncate">
                  {user?.full_name}
                </p>
                <p className="text-[10px] text-text-muted font-mono truncate">{user?.work_email}</p>
                <span
                  className="inline-block text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-[2px] mt-1.5"
                  style={{
                    color: roleMeta?.color ?? '#ffffff',
                    background: `${roleMeta?.color ?? '#ffffff'}20`,
                    border: `1px solid ${roleMeta?.color ?? '#ffffff'}40`,
                  }}
                >
                  ROLE: {user?.role}
                </span>
              </div>

              <div className="space-y-1">
                <Link
                  to="/settings"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-2.5 px-2.5 py-2 text-xs uppercase tracking-[0.15em] text-text-muted hover:text-text hover:bg-surface-2/40 rounded-[2px] transition-colors"
                >
                  <Settings size={13} />
                  <span>PREFERENCES</span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2.5 px-2.5 py-2 text-xs uppercase tracking-[0.15em] text-danger hover:bg-danger/10 rounded-[2px] transition-colors"
                >
                  <LogOut size={13} />
                  <span>SIGN OUT</span>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </header>
  )
}
