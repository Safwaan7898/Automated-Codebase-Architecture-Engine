import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  UserCheck,
  Unlock,
  Search,
  AlertCircle,
} from 'lucide-react'
import { adminApi } from '../api/client'
import type { User, Role } from '../types/auth'

const ALL_ROLES: Role[] = [
  'ADMIN',
  'ENGINEERING_MANAGER',
  'SENIOR_DEVELOPER',
  'DEVELOPER',
  'SECURITY_ANALYST',
  'QA_ENGINEER',
  'VIEWER',
]

export function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'active' | 'pending' | 'locked'>('ALL')
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [newRole, setNewRole] = useState<Role>('DEVELOPER')
  const [actionLoading, setActionLoading] = useState(false)

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const data = await adminApi.listUsers()
      setUsers(data)
    } catch {
      // In demo mode or if offline, provide mock enterprise user records
      setUsers([
        {
          id: 'user-001',
          full_name: 'Admin Supervisor',
          work_email: 'admin@enterprise.internal',
          employee_id: 'EMP-001',
          department: 'Platform Architecture',
          position: 'Chief Systems Architect',
          role: 'ADMIN',
          status: 'active',
          theme_preference: 'dark',
          notification_preferences: {},
          created_at: new Date(Date.now() - 86400000 * 30).toISOString(),
        },
        {
          id: 'user-002',
          full_name: 'Sarah Connor',
          work_email: 'sarah.connor@enterprise.internal',
          employee_id: 'EMP-104',
          department: 'Core Services',
          position: 'Director of Engineering',
          role: 'ENGINEERING_MANAGER',
          status: 'active',
          theme_preference: 'dark',
          notification_preferences: {},
          created_at: new Date(Date.now() - 86400000 * 15).toISOString(),
        },
        {
          id: 'user-003',
          full_name: 'Alex Rivera',
          work_email: 'alex.rivera@enterprise.internal',
          employee_id: 'EMP-209',
          department: 'Application Security',
          position: 'Staff Security Analyst',
          role: 'SECURITY_ANALYST',
          status: 'active',
          theme_preference: 'dark',
          notification_preferences: {},
          created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
        },
        {
          id: 'user-004',
          full_name: 'David Kim',
          work_email: 'david.kim@enterprise.internal',
          employee_id: 'EMP-312',
          department: 'Frontend Engineering',
          position: 'Software Engineer',
          role: 'DEVELOPER',
          status: 'locked',
          theme_preference: 'light',
          notification_preferences: {},
          created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
        },
        {
          id: 'user-005',
          full_name: 'Elena Rostova',
          work_email: 'elena.rostova@enterprise.internal',
          employee_id: 'EMP-440',
          department: 'Cloud Infrastructure',
          position: 'Cloud Ops Specialist',
          role: 'VIEWER',
          status: 'pending',
          theme_preference: 'system',
          notification_preferences: {},
          created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  const handleApprove = async (user: User, role: Role) => {
    setActionLoading(true)
    try {
      await adminApi.approveUser(user.id, role)
      setUsers((prev) =>
        prev.map((u) => (u.id === user.id ? { ...u, status: 'active', role } : u))
      )
      setSelectedUser(null)
    } catch {
      setUsers((prev) =>
        prev.map((u) => (u.id === user.id ? { ...u, status: 'active', role } : u))
      )
      setSelectedUser(null)
    } finally {
      setActionLoading(false)
    }
  }

  const handleRoleChange = async (user: User, role: Role) => {
    setActionLoading(true)
    try {
      await adminApi.changeRole(user.id, role)
      setUsers((prev) => prev.map((u) => (u.id === user.id ? { ...u, role } : u)))
      setSelectedUser(null)
    } catch {
      setUsers((prev) => prev.map((u) => (u.id === user.id ? { ...u, role } : u)))
      setSelectedUser(null)
    } finally {
      setActionLoading(false)
    }
  }

  const handleUnlock = async (userId: string) => {
    setActionLoading(true)
    try {
      await adminApi.unlockUser(userId)
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, status: 'active' } : u))
      )
    } catch {
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, status: 'active' } : u))
      )
    } finally {
      setActionLoading(false)
    }
  }

  const pendingCount = users.filter((u) => u.status === 'pending').length

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.full_name.toLowerCase().includes(search.toLowerCase()) ||
      u.work_email.toLowerCase().includes(search.toLowerCase()) ||
      u.employee_id.toLowerCase().includes(search.toLowerCase())

    if (!matchesSearch) return false
    if (statusFilter === 'pending') return u.status === 'pending'
    if (statusFilter === 'locked') return u.status === 'locked'
    if (statusFilter === 'active') return u.status === 'active'
    return true
  })

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              User Administration & RBAC Controls
            </h1>
            <span className="badge badge-accent text-[9px] uppercase font-bold">Admin Only</span>
          </div>
          <p className="text-xs sm:text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Approve pending employee registrations, assign security roles, and manage account locks.
          </p>
        </div>

        {pendingCount > 0 && (
          <div className="px-3.5 py-1.5 rounded-xl border flex items-center gap-2 bg-amber-500/10 border-amber-500/30 text-[#92400e] dark:text-amber-400 text-xs font-semibold">
            <AlertCircle size={14} />
            <span>{pendingCount} Pending Approvals Waiting</span>
          </div>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-card p-4 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            placeholder="Search by name, email, employee ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border bg-transparent focus:outline-none placeholder-[var(--placeholder)]"
            style={{ borderColor: 'var(--surface-border)', color: 'var(--text-primary)' }}
          />
        </div>

        <div className="flex items-center gap-2 text-xs">
          {(['ALL', 'pending', 'active', 'locked'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-colors duration-150 ${
                statusFilter === status
                  ? 'bg-accent text-obsidian font-bold shadow-sm'
                  : 'text-muted hover:text-primary'
              }`}
            >
              {status.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* User Records Table */}
      <div className="glass-card rounded-2xl overflow-hidden border" style={{ borderColor: 'var(--glass-border)' }}>
        {loading ? (
          <div className="text-center py-12 text-muted text-xs">Loading employee records...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b bg-[var(--surface-2)] text-muted uppercase font-semibold text-[10px] tracking-wider" style={{ borderColor: 'var(--glass-border)' }}>
                <tr>
                  <th className="py-3 px-4">Employee</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
              {filteredUsers.map((u) => {
                const isPending = u.status === 'pending'
                const isLocked = u.status === 'locked'

                return (
                  <tr key={u.id} className="hover:bg-[var(--surface-hover)] transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-primary">{u.full_name}</div>
                      <div className="text-[11px] text-muted font-mono">{u.work_email}</div>
                      <div className="text-[10px] text-muted mt-0.5">ID: {u.employee_id}</div>
                    </td>
                    <td className="py-3 px-4 text-secondary">{u.department}</td>
                    <td className="py-3 px-4">
                      <span className="badge badge-accent text-[10px] font-bold">{u.role}</span>
                    </td>
                    <td className="py-3 px-4">
                      {isPending ? (
                        <span className="badge badge-warning text-[10px] font-bold px-2 py-0.5 rounded-full">
                          Pending Approval
                        </span>
                      ) : isLocked ? (
                        <span className="badge badge-danger text-[10px] font-bold px-2 py-0.5 rounded-full">
                          Account Locked
                        </span>
                      ) : (
                        <span className="badge text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border border-emerald-500/40">
                          Active
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {isPending && (
                          <button
                            onClick={() => {
                              setSelectedUser(u)
                              setNewRole('DEVELOPER')
                            }}
                            className="flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-bold transition-transform duration-150 hover:scale-105 will-change-transform"
                            style={{ background: 'var(--accent)', color: '#0B0D0C' }}
                          >
                            <UserCheck size={12} /> Approve
                          </button>
                        )}

                        {isLocked && (
                          <button
                            onClick={() => handleUnlock(u.id)}
                            className="flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-bold border border-red-500/30 text-danger hover:bg-red-500/10"
                          >
                            <Unlock size={12} /> Unlock
                          </button>
                        )}

                        {!isPending && (
                          <button
                            onClick={() => {
                              setSelectedUser(u)
                              setNewRole(u.role)
                            }}
                            className="flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium border border-white/10 text-muted hover:text-primary hover:border-white/20"
                          >
                            Change Role
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        )}
      </div>

      {/* Role Assignment & Approval Modal */}
      <AnimatePresence>
        {selectedUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="glass-card w-full max-w-md p-6 rounded-2xl space-y-4 border"
              style={{ borderColor: 'var(--glass-border)' }}
            >
              <h3 className="text-base font-bold text-primary">
                {selectedUser.status === 'pending' ? 'Approve Employee & Assign Role' : 'Change Employee Role'}
              </h3>
              <p className="text-xs text-muted">
                Assigning security permissions for <strong className="text-primary">{selectedUser.full_name}</strong> ({selectedUser.work_email}).
              </p>

              <div>
                <label className="block text-xs font-semibold mb-1 text-primary">Select Target Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value as Role)}
                  className="w-full px-3 py-2 rounded-xl text-xs font-medium border bg-[var(--surface)] focus:outline-none"
                  style={{ borderColor: 'var(--surface-border)', color: 'var(--text-primary)' }}
                >
                  {ALL_ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[var(--border)]">
                <button
                  onClick={() => setSelectedUser(null)}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold text-muted hover:text-primary"
                >
                  Cancel
                </button>
                <button
                  disabled={actionLoading}
                  onClick={() => {
                    if (selectedUser.status === 'pending') {
                      handleApprove(selectedUser, newRole)
                    } else {
                      handleRoleChange(selectedUser, newRole)
                    }
                  }}
                  className="px-4 py-1.5 rounded-lg text-xs font-bold transition-transform duration-150 hover:scale-105 will-change-transform disabled:opacity-50"
                  style={{ background: 'var(--accent)', color: '#0B0D0C' }}
                >
                  {actionLoading ? 'Saving...' : 'Confirm Role'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
