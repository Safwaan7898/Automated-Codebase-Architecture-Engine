import { motion, AnimatePresence } from 'framer-motion'
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  GitBranch,
  BarChart3,
  ShieldAlert,
  Wrench,
  FileText,
  Users,
  ScrollText,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Network,
  Lock,
  Sparkles,
  FolderKanban,
} from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'
import type { Permission } from '../../types/auth'
import { useState } from 'react'

interface NavItem {
  label: string
  icon: React.ReactNode
  to: string
  permission?: Permission
  badge?: string
  isPro?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { label: 'DASHBOARD',     icon: <LayoutDashboard size={15} />, to: '/dashboard' },
  { label: 'PROJECTS',      icon: <FolderKanban size={15} />,    to: '/projects',    permission: 'view:graph' },
  { label: 'INGESTION',     icon: <GitBranch size={15} />,       to: '/ingestion',   permission: 'run:ingestion' },
  { label: 'TOPOLOGY',      icon: <Network size={15} />,         to: '/graph',       permission: 'view:graph' },
  { label: 'METRICS',       icon: <BarChart3 size={15} />,       to: '/metrics',     permission: 'view:metrics' },
  { label: 'INSIGHTS',      icon: <Sparkles size={15} />,        to: '/insights',    permission: 'view:metrics' },
  { label: 'SECURITY',      icon: <ShieldAlert size={15} />,     to: '/security',    permission: 'view:smells' },
  { label: 'REFACTOR',      icon: <Wrench size={15} />,          to: '/refactor',    permission: 'view:refactor' },
  { label: 'REPORTS',       icon: <FileText size={15} />,        to: '/reports',     permission: 'view:reports' },
  { label: 'ANALYTICS PRO', icon: <BarChart3 size={15} />,       to: '/analytics',   permission: 'view:team_analytics', badge: 'PRO', isPro: true },
]

const ADMIN_ITEMS: NavItem[] = [
  { label: 'USER MGMT',   icon: <Users size={15} />,           to: '/admin/users', permission: 'manage:users' },
  { label: 'AUDIT LOG',   icon: <ScrollText size={15} />,      to: '/admin/audit', permission: 'view:audit_logs' },
]

const ROLE_LABELS: Record<string, string> = {
  ADMIN: 'ADMIN',
  ENGINEERING_MANAGER: 'ENG. MANAGER',
  SENIOR_DEVELOPER: 'SENIOR DEV',
  DEVELOPER: 'DEVELOPER',
  SECURITY_ANALYST: 'SECURITY',
  QA_ENGINEER: 'QA ENGINEER',
  VIEWER: 'VIEWER',
}

export function Sidebar() {
  const { user, hasPermission, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 64 : 240 }}
      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
      className="flex-shrink-0 h-full flex flex-col border-r relative z-30"
      style={{
        background: 'var(--sidebar-bg)',
        borderColor: 'var(--sidebar-border)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
      }}
    >
      {/* Header Logo */}
      <div
        className="flex items-center h-16 px-3.5 border-b flex-shrink-0 border-border dark:border-white/[0.08]"
      >
        <Link to="/dashboard" className="flex items-center gap-2.5 flex-shrink-0 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#CCFF00] to-white p-0.5 shadow-[0_0_15px_rgba(204,255,0,0.4)] flex-shrink-0 transition-transform group-hover:scale-105 duration-300 will-change-transform">
            <div className="w-full h-full bg-surface-2 dark:bg-black rounded-[6px] flex items-center justify-center">
              <Network size={16} className="text-accent-text dark:text-[#CCFF00]" />
            </div>
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="font-['Syne',sans-serif] text-lg font-[900] tracking-[-0.04em] uppercase whitespace-nowrap flex-shrink-0 text-text dark:text-white"
              >
                ARCHLENS<span className="text-accent-text dark:text-[#CCFF00]">.</span>
              </motion.span>
            )}
          </AnimatePresence>
        </Link>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="ml-auto p-1 text-text-muted dark:text-white/50 hover:text-accent-text dark:hover:text-[#CCFF00] transition-colors flex-shrink-0"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto" style={{ scrollbarGutter: 'stable' }}>
        {NAV_ITEMS.map((item) => {
          const allowed = !item.permission || hasPermission(item.permission)
          // Strictly only the current route can be active AND only if allowed
          const isActive = allowed && location.pathname === item.to
          const isAnalyticsProLocked = item.isPro && !allowed
          const fullLabel = item.badge ? `${item.label} ${item.badge}` : item.label

          return (
            <NavLink
              key={item.to}
              data-testid={item.isPro ? 'sidebar-analytics-pro' : undefined}
              to={item.to}
              onClick={(e) => {
                if (!allowed) e.preventDefault()
              }}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-[11px] font-mono font-bold tracking-[0.18em] uppercase transition-colors duration-150 ${
                isActive
                  ? 'bg-accent/15 text-accent-text border border-accent/40 shadow-sm dark:bg-[#CCFF00]/10 dark:text-[#CCFF00] dark:border-[#CCFF00] dark:shadow-[0_0_15px_rgba(204,255,0,0.3)]'
                  : isAnalyticsProLocked
                  ? 'bg-amber-500/10 border border-amber-500/40 text-amber-400/90 dark:bg-[#f59e0b]/10 dark:border-[#f59e0b]/40 dark:text-[#fcd34d] cursor-not-allowed shadow-[0_0_10px_rgba(245,158,11,0.15)]'
                  : allowed
                  ? 'text-text-muted hover:text-text hover:bg-surface-2/40 border border-transparent dark:text-white/70 dark:hover:text-white dark:hover:bg-white/[0.04]'
                  : 'opacity-30 cursor-not-allowed border border-transparent text-text-muted dark:text-white/25'
              }`}
              aria-disabled={!allowed}
              title={
                collapsed
                  ? isAnalyticsProLocked
                    ? 'ANALYTICS PRO (LOCKED)'
                    : fullLabel
                  : isAnalyticsProLocked
                  ? 'Leadership Access Required (Analytics PRO)'
                  : fullLabel
              }
            >
              <span className="flex-shrink-0">
                {isAnalyticsProLocked ? <Lock size={15} className="text-amber-400 dark:text-[#fcd34d]" /> : item.icon}
              </span>
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    className="min-w-0 flex-1 whitespace-nowrap overflow-visible"
                    title={fullLabel}
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
              {!collapsed && item.badge && (
                <span
                  title={item.isPro ? 'Analytics PRO Feature' : item.badge}
                  className={`ml-auto shrink-0 text-[8px] px-1 py-0.5 rounded-[2px] font-mono tracking-tight leading-none ${
                    isAnalyticsProLocked
                      ? 'bg-amber-500/20 border border-amber-500 text-amber-400 dark:text-[#fcd34d] font-bold shadow-[0_0_8px_rgba(245,158,11,0.3)]'
                      : 'bg-[#06b6d4]/20 border border-[#06b6d4] text-[#155e75] dark:text-[#06b6d4]'
                  }`}
                >
                  {item.badge}
                </span>
              )}
              {!collapsed && !allowed && !item.isPro && (
                <span className="text-[10px] opacity-40">🔒</span>
              )}
            </NavLink>
          )
        })}

        {/* Admin Section */}
        {hasPermission('manage:users') && (
          <div className="pt-4 mt-4 border-t border-border dark:border-white/[0.08]">
            {!collapsed && (
              <p className="px-3 mb-2 text-[10px] font-mono tracking-[0.2em] uppercase text-[#86198f] dark:text-[#f967fb]">
                ADMIN CONTROL
              </p>
            )}
            {ADMIN_ITEMS.map((item) => {
              const isActive = location.pathname === item.to
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={`flex items-center gap-3 px-3 py-2 rounded-[2px] text-[11px] font-bold tracking-[0.2em] uppercase transition-colors duration-150 ${
                    isActive
                      ? 'bg-[#f967fb]/10 text-[#86198f] dark:text-[#f967fb] border border-[#f967fb] shadow-[0_0_15px_rgba(249,103,251,0.3)]'
                      : 'text-text-muted hover:text-text hover:bg-surface-2/40 border border-transparent dark:text-white/70 dark:hover:text-white dark:hover:bg-white/[0.04]'
                  }`}
                  title={collapsed ? item.label : undefined}
                >
                  <span className="flex-shrink-0 text-[#86198f] dark:text-[#f967fb]">{item.icon}</span>
                  <AnimatePresence>
                    {!collapsed && (
                      <motion.span
                        initial={{ opacity: 0, width: 0 }}
                        animate={{ opacity: 1, width: 'auto' }}
                        exit={{ opacity: 0, width: 0 }}
                        className="flex-1 whitespace-nowrap overflow-hidden"
                      >
                        {item.label}
                      </motion.span>
                    )}
                  </AnimatePresence>
                </NavLink>
              )
            })}
          </div>
        )}
      </nav>

      {/* User profile bottom dock */}
      {user && (
        <div className="p-3 border-t border-border dark:border-white/[0.08] flex-shrink-0 bg-surface-2/20 dark:bg-white/[0.02]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-[2px] bg-[#a3e635]/20 border border-[#a3e635] flex items-center justify-center font-bold text-xs text-[#3f6212] dark:text-[#a3e635] flex-shrink-0 font-mono">
              {user.full_name?.charAt(0) || 'U'}
            </div>
            <AnimatePresence>
              {!collapsed && (
                <motion.div
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  className="flex-1 min-w-0 overflow-hidden"
                >
                  <p className="text-xs font-bold text-text dark:text-white truncate uppercase tracking-[0.05em]">
                    {user.full_name}
                  </p>
                  <p className="text-[10px] text-text-muted dark:text-[#06b6d4] font-mono tracking-wider truncate">
                    {ROLE_LABELS[user.role] ?? user.role}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
            {!collapsed && (
              <button
                onClick={handleLogout}
                className="p-1.5 text-text-muted dark:text-white/40 hover:text-danger dark:hover:text-[#ef4444] transition-colors"
                title="LOG OUT"
              >
                <LogOut size={14} />
              </button>
            )}
          </div>
        </div>
      )}
    </motion.aside>
  )
}
