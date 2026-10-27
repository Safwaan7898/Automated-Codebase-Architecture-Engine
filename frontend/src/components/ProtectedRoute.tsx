import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import type { Permission } from '../types/auth'

interface ProtectedRouteProps {
  permission?: Permission
  redirectTo?: string
}

export function ProtectedRoute({ permission, redirectTo = '/login' }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, hasPermission } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center h-screen"
        style={{ background: 'var(--bg)' }}
      >
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-2 h-2 rounded-full"
              style={{
                background: 'var(--accent)',
                animation: `bounce-dot 1.4s ease-in-out ${i * 0.2}s infinite`,
              }}
            />
          ))}
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />
  }

  if (permission && !hasPermission(permission)) {
    return (
      <div
        className="flex flex-col items-center justify-center h-full py-24 gap-4"
        style={{ color: 'var(--text-secondary)' }}
      >
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl"
          style={{ background: 'var(--danger-dim)', border: '1px solid var(--danger)' }}
        >
          🔒
        </div>
        <div className="text-center max-w-sm">
          <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
            Access Restricted
          </h2>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Your role doesn&apos;t have permission to view this page.
            Contact an administrator to request access.
          </p>
        </div>
      </div>
    )
  }

  return <Outlet />
}

/** Public auth route: renders login/register freely without forced redirects */
export function PublicRoute() {
  const { isLoading } = useAuth()

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center h-screen"
        style={{ background: 'var(--bg)' }}
      >
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-2 h-2 rounded-full"
              style={{
                background: 'var(--accent)',
                animation: `bounce-dot 1.4s ease-in-out ${i * 0.2}s infinite`,
              }}
            />
          ))}
        </div>
      </div>
    )
  }

  return <Outlet />
}
