import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Home,
  Upload,
  Activity,
  Network,
  AlertTriangle,
  Wrench,
  Shield,
  Settings,
  Users,
} from 'lucide-react'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { MagnificationDock, type DockItemData } from '../MagnificationDock'
import { useAuth } from '../../contexts/AuthContext'

export function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { hasPermission } = useAuth()

  const dockItems: DockItemData[] = [
    {
      icon: <Home size={18} />,
      label: 'Welcome',
      active: location.pathname === '/',
      onClick: () => navigate('/'),
    },
    {
      icon: <Upload size={18} />,
      label: 'Ingestion',
      active: location.pathname === '/ingestion',
      onClick: () => navigate('/ingestion'),
    },
    {
      icon: <Activity size={18} />,
      label: 'Dashboard',
      active: location.pathname === '/dashboard',
      onClick: () => navigate('/dashboard'),
    },
    {
      icon: <Network size={18} />,
      label: 'Topology',
      active: location.pathname === '/graph',
      onClick: () => navigate('/graph'),
    },
    {
      icon: <AlertTriangle size={18} />,
      label: 'Diagnostics',
      active: location.pathname === '/diagnostics',
      onClick: () => navigate('/diagnostics'),
    },
    {
      icon: <Wrench size={18} />,
      label: 'Refactor',
      active: location.pathname === '/refactor',
      onClick: () => navigate('/refactor'),
    },
    {
      icon: <Shield size={18} />,
      label: 'Security',
      active: location.pathname === '/security',
      onClick: () => navigate('/security'),
    },
    ...(hasPermission('manage:users' as any)
      ? [
          {
            icon: <Users size={18} />,
            label: 'Admin RBAC',
            active: location.pathname === '/admin',
            onClick: () => navigate('/admin'),
          },
        ]
      : []),
    {
      icon: <Settings size={18} />,
      label: 'Settings',
      active: location.pathname === '/settings',
      onClick: () => navigate('/settings'),
    },
  ]

  const DOCK_HEIGHT = 56

  return (
    <div
      className="flex h-screen overflow-hidden relative"
      style={{ background: 'var(--bg)', color: 'var(--text-primary)' }}
    >
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <Topbar />
        <main
          id="main-content"
          data-testid="main-content"
          className="flex-1 overflow-y-auto overflow-x-hidden"
          style={{
            paddingBottom: `${DOCK_HEIGHT + 74}px`,
            scrollbarGutter: 'stable',
          }}
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="min-h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>

        {/* Floating Liquid Chrome MagnificationDock */}
        <div className="fixed bottom-3 left-1/2 -translate-x-1/2 z-40 pointer-events-none overflow-visible">
          <MagnificationDock
            items={dockItems}
            panelHeight={DOCK_HEIGHT}
            baseItemSize={40}
            magnification={58}
            distance={160}
          />
        </div>
      </div>
    </div>
  )
}
