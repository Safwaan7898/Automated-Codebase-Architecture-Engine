import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from 'react'
import type { ReactNode } from 'react'
import { authApi } from '../api/client'
import type { User, Permission, LoginPayload, RegisterPayload } from '../types/auth'

interface AuthContextValue {
  user: User | null
  permissions: Permission[]
  isAuthenticated: boolean
  isLoading: boolean
  login: (data: LoginPayload) => Promise<void>
  register: (data: RegisterPayload) => Promise<User>
  registerAdmin: (data: Record<string, unknown>) => Promise<User>
  logout: () => Promise<void>
  hasPermission: (perm: Permission) => boolean
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [permissions, setPermissions] = useState<Permission[]>([])
  const [isLoading, setIsLoading] = useState(true) // starts true to check session

  const refreshUser = useCallback(async () => {
    try {
      const data = await authApi.me()
      setUser(data.user)
      setPermissions(data.permissions)
    } catch {
      setUser(null)
      setPermissions([])
    }
  }, [])

  // On mount: check if user has an active session via cookie
  useEffect(() => {
    refreshUser().finally(() => setIsLoading(false))
  }, [refreshUser])

  const login = useCallback(async (data: LoginPayload) => {
    await authApi.login(data)
    await refreshUser()
  }, [refreshUser])

  const register = useCallback(async (data: RegisterPayload): Promise<User> => {
    return authApi.register(data)
  }, [])

  const registerAdmin = useCallback(async (data: Record<string, unknown>): Promise<User> => {
    return authApi.registerAdmin(data)
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      setUser(null)
      setPermissions([])
    }
  }, [])

  const hasPermission = useCallback(
    (perm: Permission) => permissions.includes(perm),
    [permissions]
  )

  return (
    <AuthContext.Provider
      value={{
        user,
        permissions,
        isAuthenticated: !!user && user.status === 'active',
        isLoading,
        login,
        register,
        registerAdmin,
        logout,
        hasPermission,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
