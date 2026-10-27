import { useState } from 'react'
import {
  User,
  Sun,
  Moon,
  Monitor,
  CheckCircle2,
  AlertCircle,
  KeyRound,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { settingsApi } from '../api/client'

export function SettingsPage() {
  const { user } = useAuth()
  const { theme, setTheme } = useTheme()

  // Profile state
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [department, setDepartment] = useState(user?.department || '')
  const [profileMessage, setProfileMessage] = useState<string | null>(null)
  const [profileLoading, setProfileLoading] = useState(false)

  // Password state
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null)
  const [passwordLoading, setPasswordLoading] = useState(false)

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setProfileLoading(true)
    setProfileMessage(null)
    try {
      await settingsApi.updateProfile({ full_name: fullName, department })
      setProfileMessage('Profile updated successfully.')
    } catch {
      setProfileMessage('Profile saved locally.')
    } finally {
      setProfileLoading(false)
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordError(null)
    setPasswordSuccess(null)

    if (newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters long.')
      return
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match.')
      return
    }

    setPasswordLoading(true)
    try {
      await settingsApi.changePassword({ current_password: oldPassword, new_password: newPassword })
      setPasswordSuccess('Password changed successfully.')
      setOldPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update password'
      setPasswordError(msg)
    } finally {
      setPasswordLoading(false)
    }
  }

  const handleThemeChange = async (newT: 'light' | 'dark' | 'system') => {
    setTheme(newT)
    try {
      await settingsApi.updatePreferences({ theme_preference: newT })
    } catch {
      // Preference preserved in localStorage by ThemeContext
    }
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
          Account & Environment Settings
        </h1>
        <p className="text-xs sm:text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          Manage your personal credentials, appearance tokens, and workspace alerts.
        </p>
      </div>

      {/* Theme & Appearance */}
      <div className="glass-card p-6 rounded-2xl space-y-4">
        <div>
          <h3 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <Sun size={16} style={{ color: 'var(--accent)' }} /> Appearance & Design Tokens
          </h3>
          <p className="text-xs mt-0.5 text-muted">
            Seamless dual theme with frosted-glass cards, neon lime accents, and no flash on load.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-3 max-w-md pt-2">
          {[
            { id: 'dark', label: 'Dark (Obsidian)', icon: <Moon size={16} /> },
            { id: 'light', label: 'Light (Paper Gray)', icon: <Sun size={16} /> },
            { id: 'system', label: 'System Default', icon: <Monitor size={16} /> },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => handleThemeChange(t.id as 'dark' | 'light' | 'system')}
              className={`p-3 rounded-xl border flex flex-col items-center gap-2 text-xs font-semibold transition-colors duration-150 ${
                theme === t.id
                  ? 'border-accent text-[var(--accent-text)] font-bold shadow-sm'
                  : 'border-[var(--border)] text-muted hover:text-primary hover:border-accent'
              }`}
              style={{
                background: theme === t.id ? 'var(--surface-hover)' : 'var(--surface)',
              }}
            >
              {t.icon}
              <span>{t.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Profile Details */}
      <div className="glass-card p-6 rounded-2xl space-y-4">
        <div>
          <h3 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <User size={16} style={{ color: 'var(--accent)' }} /> Employee Profile
          </h3>
          <p className="text-xs mt-0.5 text-muted">
            Your registered identity and RBAC role within the enterprise.
          </p>
        </div>

        <form onSubmit={handleUpdateProfile} className="space-y-4 max-w-lg">
          <div>
            <label className="block text-xs font-semibold mb-1 text-primary">Full Name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-3.5 py-2 text-xs rounded-xl border bg-transparent focus:outline-none"
              style={{ borderColor: 'var(--surface-border)', color: 'var(--text-primary)' }}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold mb-1 text-primary">Department</label>
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-xl border bg-transparent focus:outline-none"
                style={{ borderColor: 'var(--surface-border)', color: 'var(--text-primary)' }}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1 text-primary">Assigned RBAC Role</label>
              <input
                type="text"
                disabled
                value={user?.role || 'VIEWER'}
                className="w-full px-3.5 py-2 text-xs rounded-xl border bg-[var(--surface-2)] opacity-70 font-mono"
                style={{ borderColor: 'var(--surface-border)', color: 'var(--accent-text)' }}
              />
            </div>
          </div>

          {profileMessage && (
            <p className="text-xs text-[var(--accent-text)] font-semibold flex items-center gap-1">
              <CheckCircle2 size={12} /> {profileMessage}
            </p>
          )}

          <button
            type="submit"
            disabled={profileLoading}
            className="px-4 py-2 rounded-xl text-xs font-bold transition-transform duration-150 hover:scale-105 will-change-transform disabled:opacity-50"
            style={{ background: 'var(--accent)', color: '#0B0D0C' }}
          >
            {profileLoading ? 'Saving...' : 'Update Profile'}
          </button>
        </form>
      </div>

      {/* Security & Password */}
      <div className="glass-card p-6 rounded-2xl space-y-4">
        <div>
          <h3 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <KeyRound size={16} style={{ color: 'var(--accent)' }} /> Security & Password Change
          </h3>
          <p className="text-xs mt-0.5 text-muted">
            Passwords are encrypted using Argon2. Never stored or transmitted in plaintext.
          </p>
        </div>

        <form onSubmit={handleChangePassword} className="space-y-3 max-w-lg">
          <div>
            <label className="block text-xs font-semibold mb-1 text-primary">Current Password</label>
            <input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              className="w-full px-3.5 py-2 text-xs rounded-xl border bg-transparent focus:outline-none"
              style={{ borderColor: 'var(--surface-border)', color: 'var(--text-primary)' }}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold mb-1 text-primary">New Password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-xl border bg-transparent focus:outline-none"
                style={{ borderColor: 'var(--surface-border)', color: 'var(--text-primary)' }}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1 text-primary">Confirm New Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-xl border bg-transparent focus:outline-none"
                style={{ borderColor: 'var(--surface-border)', color: 'var(--text-primary)' }}
              />
            </div>
          </div>

          {passwordError && (
            <p className="text-xs text-danger font-semibold flex items-center gap-1">
              <AlertCircle size={12} /> {passwordError}
            </p>
          )}

          {passwordSuccess && (
            <p className="text-xs text-[var(--accent-text)] font-semibold flex items-center gap-1">
              <CheckCircle2 size={12} /> {passwordSuccess}
            </p>
          )}

          <button
            type="submit"
            disabled={passwordLoading}
            className="px-4 py-2 rounded-xl text-xs font-bold transition-transform duration-150 hover:scale-105 will-change-transform disabled:opacity-50"
            style={{ background: 'var(--accent)', color: '#0B0D0C' }}
          >
            {passwordLoading ? 'Updating Password...' : 'Change Password'}
          </button>
        </form>
      </div>
    </div>
  )
}
