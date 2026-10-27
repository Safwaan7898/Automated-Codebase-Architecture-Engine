import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Eye,
  EyeOff,
  ArrowLeft,
  Shield,
  UserCheck,
  ArrowRight,
  Lock,
  Search,
  KeyRound,
  UserPlus,
  AlertTriangle,
  Clock,
  Sun,
  Moon,
  Laptop,
  RotateCw,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { authApi } from '../api/client'
import toast from 'react-hot-toast'

// ── Password strength helper ─────────────────────────────────────────────────
function passwordStrength(pw: string): { score: number; label: string; color: string } {
  let score = 0
  if (pw.length >= 8) score++
  if (pw.length >= 12) score++
  if (/[A-Z]/.test(pw)) score++
  if (/[0-9]/.test(pw)) score++
  if (/[^A-Za-z0-9]/.test(pw)) score++
  if (score <= 1) return { score, label: 'WEAK', color: '#ff2d20' }
  if (score <= 2) return { score, label: 'FAIR', color: '#ffb703' }
  if (score <= 3) return { score, label: 'GOOD', color: '#00F0FF' }
  return { score, label: 'STRONG', color: '#CCFF00' }
}

const DEPARTMENTS = [
  'Engineering Architecture',
  'Core Engine & Compilers',
  'InfoSec & AppSec',
  'Platform Infrastructure',
  'Quality & Test Verification',
  'Engineering Operations',
]

const POSITIONS = [
  'Software Engineer',
  'Senior Software Engineer',
  'Principal Architect',
  'Security Analyst',
  'QA Automation Lead',
  'Engineering Manager',
  'System Viewer',
]

type AuthTab = 'login' | 'register_employee' | 'register_admin' | 'check_status'

export function AuthPage({ initialMode = 'login' }: { initialMode?: 'login' | 'register' }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, isAuthenticated, login, register, registerAdmin, logout } = useAuth()
  const { theme, setTheme } = useTheme()

  // Tab mode
  const [tab, setTab] = useState<AuthTab>(
    initialMode === 'register' ? 'register_employee' : 'login'
  )

  // Login form state
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [showLoginPassword, setShowLoginPassword] = useState(false)
  const [loginLoading, setLoginLoading] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)

  // Employee Registration state
  const [empFullName, setEmpFullName] = useState('')
  const [empEmail, setEmpEmail] = useState('')
  const [empEmployeeId, setEmpEmployeeId] = useState('')
  const [empDepartment, setEmpDepartment] = useState(DEPARTMENTS[0])
  const [empPosition, setEmpPosition] = useState(POSITIONS[0])
  const [empPassword, setEmpPassword] = useState('')
  const [showEmpPassword, setShowEmpPassword] = useState(false)
  const [empLoading, setEmpLoading] = useState(false)
  const [empSuccess, setEmpSuccess] = useState<any | null>(null)

  // Admin Registration state
  const [adminFullName, setAdminFullName] = useState('')
  const [adminEmail, setAdminEmail] = useState('')
  const [adminEmployeeId, setAdminEmployeeId] = useState('ADM-')
  const [adminDepartment, setAdminDepartment] = useState('Architecture & Security Operations')
  const [adminPosition, setAdminPosition] = useState('Principal System Architect')
  const [adminKey, setAdminKey] = useState('')
  const [adminPassword, setAdminPassword] = useState('')
  const [showAdminPassword, setShowAdminPassword] = useState(false)
  const [adminLoading, setAdminLoading] = useState(false)

  // Status check tool state
  const [statusLookupInput, setStatusLookupInput] = useState('')
  const [statusLoading, setStatusLoading] = useState(false)
  const [statusResult, setStatusResult] = useState<any | null>(null)

  // Handle Login
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoginLoading(true)
    setLoginError(null)
    try {
      await login({ work_email: loginEmail, password: loginPassword })
      toast.success('Access granted. Welcome to ArchLens.')
      const from = (location.state as any)?.from?.pathname || '/dashboard'
      navigate(from, { replace: true })
    } catch (err: any) {
      let msg = err.response?.data?.detail || err.message || 'Login failed.'
      if (err.code === 'ECONNABORTED' || msg.includes('timeout') || err.message?.includes('Network Error')) {
        msg = 'Server not responding. Please verify the backend service is running and retry.'
      } else if (err.response?.status === 401) {
        msg = 'Incorrect email or password.'
      }
      setLoginError(msg)
      toast.error(msg)
    } finally {
      setLoginLoading(false)
    }
  }

  // Handle Employee Registration
  const handleEmployeeRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setEmpLoading(true)
    try {
      const created = await register({
        full_name: empFullName,
        work_email: empEmail,
        password: empPassword,
        employee_id: empEmployeeId,
        department: empDepartment,
        position: empPosition,
      })
      setEmpSuccess(created)
      toast.success('Registration submitted for administrator approval!')
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Registration failed.'
      toast.error(msg)
    } finally {
      setEmpLoading(false)
    }
  }

  // Handle Admin Provisioning
  const handleAdminRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setAdminLoading(true)
    try {
      await registerAdmin({
        full_name: adminFullName,
        work_email: adminEmail,
        password: adminPassword,
        employee_id: adminEmployeeId,
        department: adminDepartment,
        position: adminPosition,
        admin_key: adminKey,
      })
      toast.success('Administrator provisioned! You may now sign in.')
      setLoginEmail(adminEmail)
      setLoginPassword(adminPassword)
      setTab('login')
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Admin provisioning failed.'
      toast.error(msg)
    } finally {
      setAdminLoading(false)
    }
  }

  // Handle Status Lookup
  const handleStatusCheck = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!statusLookupInput.trim()) return
    setStatusLoading(true)
    try {
      const res = await authApi.checkStatus(statusLookupInput.trim())
      setStatusResult(res)
    } catch (err: any) {
      toast.error('Could not query status service.')
    } finally {
      setStatusLoading(false)
    }
  }

  const empStrength = passwordStrength(empPassword)
  const adminStrength = passwordStrength(adminPassword)

  return (
    <div className="min-h-screen bg-[var(--agencia-bg)] text-[var(--agencia-text)] flex flex-col justify-between selection:bg-[var(--agencia-lime)] selection:text-[var(--agencia-obsidian)] relative overflow-hidden font-sans transition-colors duration-300">
      {/* ── Top Marquee ─────────────────────────────────────────────── */}
      <div className="relative z-20 w-full bg-[var(--agencia-surface)]/60 border-b border-[var(--agencia-border)] py-2 overflow-hidden flex select-none">
        <div className="animate-marquee whitespace-nowrap flex gap-8 items-center text-[10px] font-mono tracking-[0.25em] uppercase text-[var(--accent-text)]">
          <span>⚡ RBAC ACCESS GATEWAY</span>
          <span className="text-[var(--agencia-text-muted)]">{'//'}</span>
          <span>ADMIN VERIFICATION REQUIRED FOR LOGIN</span>
          <span className="text-[var(--agencia-text-muted)]">{'//'}</span>
          <span>AGENCIA LUXURY-BRUTALIST ARCHITECTURE</span>
          <span className="text-[var(--agencia-text-muted)]">{'//'}</span>
          <span>ENTERPRISE ENCRYPTION & TOKEN ROTATION</span>
          <span className="text-[var(--agencia-text-muted)]">{'//'}</span>
          <span>ZERO PLACEHOLDER DATA</span>
          <span className="text-[var(--agencia-text-muted)]">{'//'}</span>
          <span>REAL-TIME AST INGESTION ENGINE</span>
          <span className="text-[var(--agencia-text-muted)]">{'//'}</span>
          <span>CONFIDENTIAL SYSTEM ACCESS ONLY</span>
        </div>
      </div>

      {/* ── Navigation Header ────────────────────────────────────────────── */}
      <header className="relative z-20 max-w-6xl w-full mx-auto px-6 py-6 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-8 h-8 rounded-lg bg-[var(--agencia-lime)] flex items-center justify-center text-[var(--agencia-obsidian)] font-display font-black text-lg shadow-[0_0_15px_rgba(198,244,50,0.4)]">
            A
          </div>
          <span className="font-display text-2xl font-black tracking-wider text-[var(--agencia-text)]">
            ARCHLENS<span className="text-[var(--accent-text)]">.</span>
          </span>
        </Link>

        <div className="flex items-center gap-4">
          {/* Theme Toggle */}
          <div className="flex items-center p-1 rounded-full border border-[var(--agencia-border)] bg-[var(--agencia-surface)]">
            <button
              onClick={() => setTheme('light')}
              className={`p-1.5 rounded-full transition-colors ${
                theme === 'light'
                  ? 'bg-[var(--agencia-lime)] text-[var(--agencia-obsidian)]'
                  : 'text-[var(--agencia-text-muted)] hover:text-[var(--agencia-text)]'
              }`}
              title="Light Theme"
            >
              <Sun className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setTheme('dark')}
              className={`p-1.5 rounded-full transition-colors ${
                theme === 'dark'
                  ? 'bg-[var(--agencia-lime)] text-[var(--agencia-obsidian)]'
                  : 'text-[var(--agencia-text-muted)] hover:text-[var(--agencia-text)]'
              }`}
              title="Dark Theme"
            >
              <Moon className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setTheme('system')}
              className={`p-1.5 rounded-full transition-colors ${
                theme === 'system'
                  ? 'bg-[var(--agencia-lime)] text-[var(--agencia-obsidian)]'
                  : 'text-[var(--agencia-text-muted)] hover:text-[var(--agencia-text)]'
              }`}
              title="System Theme"
            >
              <Laptop className="w-3.5 h-3.5" />
            </button>
          </div>

          <Link
            to="/"
            className="flex items-center gap-2 text-xs font-mono tracking-widest text-[var(--agencia-text-muted)] hover:text-[var(--accent-text)] transition-colors"
          >
            <ArrowLeft size={14} />
            <span>RETURN TO HOME</span>
          </Link>
        </div>
      </header>

      {/* ── Main Content Area ────────────────────────────────────────────── */}
      <main className="relative z-10 max-w-5xl w-full mx-auto px-4 py-8 flex flex-col items-center justify-start min-h-[calc(100vh-140px)]" style={{ scrollbarGutter: 'stable' }}>
        {/* If user is already authenticated */}
        {isAuthenticated && user ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="liquid-card p-8 sm:p-10 max-w-xl w-full text-center relative shadow-2xl"
          >
            <div className="w-16 h-16 mx-auto rounded-full bg-[#CCFF00]/10 border border-[#CCFF00] flex items-center justify-center text-[var(--accent-text)] dark:text-[#CCFF00] mb-6 shadow-[0_0_20px_rgba(204,255,0,0.4)]">
              <UserCheck size={32} />
            </div>
            <h2 className="acid-title text-2xl sm:text-3xl mb-2 text-[var(--text)]">ACTIVE SESSION</h2>
            <p className="text-xs font-mono text-[var(--text-muted)] tracking-wider mb-6">
              Authenticated as <span className="text-[var(--accent-text)] font-bold">{user.work_email}</span> ({user.role})
            </p>

            <div className="grid grid-cols-2 gap-3 mb-8 text-left text-xs bg-[var(--surface-2)] dark:bg-black/60 p-4 rounded-xl border border-[var(--border)] dark:border-white/10 font-mono">
              <div>
                <span className="text-[var(--text-muted)] block">NAME:</span>
                <span className="font-bold text-[var(--text)]">{user.full_name}</span>
              </div>
              <div>
                <span className="text-[var(--text-muted)] block">BADGE ID:</span>
                <span className="font-bold text-[var(--accent-text)]">{user.employee_id}</span>
              </div>
              <div>
                <span className="text-[var(--text-muted)] block">DEPARTMENT:</span>
                <span className="text-[var(--text)]">{user.department}</span>
              </div>
              <div>
                <span className="text-[var(--text-muted)] block">ROLE:</span>
                <span className="badge-acid inline-block text-[10px]">{user.role}</span>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={() => navigate('/dashboard')}
                className="chrome-btn px-6 py-2.5 text-xs font-bold"
              >
                ENTER DASHBOARD
              </button>
              <button
                onClick={() => logout()}
                className="px-6 py-2.5 rounded-full border border-[var(--border)] dark:border-white/20 hover:border-red-500 hover:text-red-400 text-xs font-mono tracking-wider transition-colors"
              >
                SIGN OUT
              </button>
            </div>
          </motion.div>
        ) : (
          <div className="w-full max-w-xl">
            {/* Title & Slogan */}
            <div className="text-center mb-8">
              <span className="badge-acid text-[10px] uppercase tracking-widest inline-flex items-center gap-1.5 mb-3">
                <Shield size={10} /> ZERO-TRUST RBAC ENGINE
              </span>
              <h1 className="acid-title text-3xl sm:text-4xl md:text-5xl tracking-[-0.04em] text-[var(--text)]">
                SECURITY ACCESS
              </h1>
              <p className="text-xs sm:text-sm font-sans text-[var(--text-muted)] mt-2 max-w-md mx-auto">
                Granular role-based controls. Self-registrations require administrator approval before login.
              </p>
            </div>

            {/* Tab Navigation Controls */}
            <div className="grid grid-cols-4 gap-1.5 p-1.5 bg-[var(--surface-2)] dark:bg-[#0A0A0A] border border-[var(--border)] dark:border-white/15 rounded-2xl mb-8">
              {[
                { id: 'login', label: 'SIGN IN', icon: <Lock size={12} /> },
                { id: 'register_employee', label: 'EMPLOYEE REG', icon: <UserPlus size={12} /> },
                { id: 'register_admin', label: 'ADMIN KEY', icon: <KeyRound size={12} /> },
                { id: 'check_status', label: 'STATUS CHECK', icon: <Search size={12} /> },
              ].map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    setTab(item.id as AuthTab)
                    setLoginError(null)
                    setEmpSuccess(null)
                  }}
                  className={`flex flex-col sm:flex-row items-center justify-center gap-1.5 py-2.5 px-2 rounded-xl text-[10px] sm:text-[11px] font-mono tracking-wider transition-colors ${
                    tab === item.id
                      ? 'bg-gradient-to-r from-white via-zinc-200 to-white text-black font-extrabold shadow-[0_0_15px_rgba(204,255,0,0.5)] border border-[#CCFF00]'
                      : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface)]'
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              ))}
            </div>

            {/* ── TAB 1: LOGIN ────────────────────────────────────────────── */}
            {tab === 'login' && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="liquid-card p-6 sm:p-8 min-h-[640px] flex flex-col justify-between"
                data-testid="auth-card"
              >
                <div className="flex items-center justify-between border-b border-[var(--border)] dark:border-white/10 pb-4 mb-6">
                  <div>
                    <h2 className="acid-title text-xl text-[var(--text)]">CREDENTIAL LOGIN</h2>
                    <p className="text-[11px] text-[var(--text-muted)] font-mono mt-0.5">
                      Enter authorized corporate email & password
                    </p>
                  </div>
                  <span className="w-2.5 h-2.5 rounded-full bg-[#CCFF00] shadow-[0_0_8px_#CCFF00]" />
                </div>

                {/* Login Error / Pending Alert */}
                {loginError && (
                  <div className="mb-6 p-4 rounded-xl border border-red-500/50 bg-red-950/40 text-red-200 text-xs flex items-start gap-3">
                    <AlertTriangle size={18} className="text-red-400 shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <strong className="block font-bold text-red-300 mb-1">
                        {loginError.includes('pending')
                          ? 'REGISTRATION PENDING APPROVAL'
                          : loginError.includes('not responding')
                          ? 'CONNECTION TIMEOUT'
                          : 'AUTHENTICATION FAILED'}
                      </strong>
                      <span>{loginError}</span>
                      {loginError.includes('pending') && (
                        <div className="mt-2">
                          <button
                            type="button"
                            onClick={() => {
                              setStatusLookupInput(loginEmail)
                              setTab('check_status')
                            }}
                            className="underline text-red-300 hover:text-white font-mono text-[11px]"
                          >
                            Check your approval status →
                          </button>
                        </div>
                      )}
                      {loginError.includes('not responding') && (
                        <div className="mt-2">
                          <button
                            type="button"
                            onClick={(e) => handleLoginSubmit(e)}
                            className="inline-flex items-center gap-1.5 px-3 py-1 bg-red-800/80 hover:bg-red-700 text-white rounded font-mono text-[11px] transition-colors"
                          >
                            <RotateCw size={12} />
                            Retry
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <form onSubmit={handleLoginSubmit} className="space-y-4">
                  <div>
                    <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] mb-1.5 uppercase">
                      Work Email
                    </label>
                    <input
                      type="email"
                      required
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      placeholder="e.g. employee@company.com"
                      className="w-full bg-[var(--surface)] dark:bg-black/60 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl px-4 py-2.5 text-xs text-[var(--text)] placeholder-[var(--text-muted)] outline-none transition-colors font-mono"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-[11px] font-mono tracking-wider text-[var(--text-secondary)] uppercase">
                        Password
                      </label>
                      <button
                        type="button"
                        onClick={() => setShowLoginPassword(!showLoginPassword)}
                        className="text-[10px] font-mono text-[var(--text-muted)] hover:text-[var(--text)] flex items-center gap-1"
                      >
                        {showLoginPassword ? <EyeOff size={11} /> : <Eye size={11} />}
                        <span>{showLoginPassword ? 'HIDE' : 'SHOW'}</span>
                      </button>
                    </div>
                    <input
                      type={showLoginPassword ? 'text' : 'password'}
                      required
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full bg-[var(--surface)] dark:bg-black/60 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl px-4 py-2.5 text-xs text-[var(--text)] placeholder-[var(--text-muted)] outline-none transition-colors font-mono"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loginLoading}
                    className="chrome-btn w-full py-3 text-xs font-black tracking-widest mt-6 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    {loginLoading ? (
                      <span>VERIFYING CREDENTIALS...</span>
                    ) : (
                      <>
                        <span>AUTHENTICATE & ENTER</span>
                        <ArrowRight size={14} />
                      </>
                    )}
                  </button>
                </form>

                <div className="mt-6 pt-4 border-t border-[var(--border)] dark:border-white/10 text-center flex items-center justify-between text-[11px] font-mono text-[var(--text-muted)] dark:text-white/60">
                  <span>New team member?</span>
                  <button
                    onClick={() => setTab('register_employee')}
                    className="text-[var(--accent-text)] dark:text-[#CCFF00] hover:underline cursor-pointer"
                  >
                    Register Employee Account →
                  </button>
                </div>
              </motion.div>
            )}

            {/* ── TAB 2: EMPLOYEE REGISTRATION ────────────────────────────── */}
            {tab === 'register_employee' && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="liquid-card p-6 sm:p-8 min-h-[640px] flex flex-col justify-between"
                data-testid="auth-card"
              >
                {empSuccess ? (
                  <div className="text-center py-6">
                    <div className="w-16 h-16 mx-auto rounded-full bg-[#CCFF00]/10 border border-[#CCFF00] flex items-center justify-center text-[var(--accent-text)] dark:text-[#CCFF00] mb-4 shadow-[0_0_20px_rgba(204,255,0,0.4)]">
                      <Clock size={32} />
                    </div>
                    <h3 className="acid-title text-2xl mb-2 text-[var(--text)]">REGISTRATION SUBMITTED</h3>
                    <p className="text-xs text-[var(--text-secondary)] max-w-md mx-auto mb-6 leading-relaxed">
                      Your employee account has been created in <span className="text-[#ffb703] font-bold uppercase">PENDING</span> status.
                      An administrator must verify your corporate ID and assign your permissions before you can log in.
                    </p>

                    <div className="bg-[var(--surface-2)] dark:bg-black/60 border border-[var(--border)] dark:border-white/15 rounded-xl p-4 max-w-sm mx-auto text-left text-xs font-mono space-y-2 mb-6">
                      <div className="flex justify-between">
                        <span className="text-[var(--text-muted)]">NAME:</span>
                        <span className="text-[var(--text)] font-bold">{empSuccess.full_name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[var(--text-muted)]">EMAIL:</span>
                        <span className="text-[#00F0FF]">{empSuccess.work_email}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[var(--text-muted)]">EMPLOYEE ID:</span>
                        <span className="text-[var(--accent-text)] dark:text-[#CCFF00] font-bold">{empSuccess.employee_id}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[var(--text-muted)]">STATUS:</span>
                        <span className="text-[#ffb703] font-bold">AWAITING APPROVAL</span>
                      </div>
                    </div>

                    <div className="flex gap-3 justify-center">
                      <button
                        onClick={() => {
                          setStatusLookupInput(empSuccess.employee_id)
                          setTab('check_status')
                        }}
                        className="chrome-btn px-6 py-2.5 text-xs font-bold"
                      >
                        TRACK STATUS
                      </button>
                      <button
                        onClick={() => {
                          setLoginEmail(empSuccess.work_email)
                          setTab('login')
                        }}
                        className="px-6 py-2.5 rounded-full border border-[var(--border)] dark:border-white/20 text-xs font-mono text-[var(--text-muted)] hover:text-[var(--text)]"
                      >
                        BACK TO LOGIN
                      </button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="border-b border-[var(--border)] dark:border-white/10 pb-4 mb-6">
                      <h2 className="acid-title text-xl text-[var(--text)]">EMPLOYEE REGISTRATION</h2>
                      <p className="text-[11px] text-[var(--text-muted)] font-mono mt-0.5">
                        Self-registration for developers, analysts, and engineers
                      </p>
                      <div className="mt-3 p-3 bg-[var(--surface-2)] dark:bg-white/[0.03] border border-[var(--border)] dark:border-white/10 rounded-lg text-[11px] text-[var(--text-secondary)] flex items-start gap-2">
                        <Clock size={14} className="text-[var(--accent-text)] dark:text-[#CCFF00] shrink-0 mt-0.5" />
                        <span>
                          <strong>Company Policy:</strong> Accounts are assigned <span className="text-[var(--accent-text)] dark:text-[#CCFF00]">VIEWER</span> by default and locked until an Administrator reviews and grants active role permissions.
                        </span>
                      </div>
                    </div>

                    <form onSubmit={handleEmployeeRegister} className="space-y-4">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] mb-1.5 uppercase">
                            Full Legal Name
                          </label>
                          <input
                            type="text"
                            required
                            value={empFullName}
                            onChange={(e) => setEmpFullName(e.target.value)}
                            placeholder="e.g. Jane Doe"
                            className="w-full bg-[var(--surface)] dark:bg-black/60 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl px-4 py-2 text-xs text-[var(--text)] placeholder-[var(--text-muted)] outline-none"
                          />
                        </div>

                        <div>
                          <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] mb-1.5 uppercase">
                            Corporate Work Email
                          </label>
                          <input
                            type="email"
                            required
                            value={empEmail}
                            onChange={(e) => setEmpEmail(e.target.value)}
                            placeholder="jane@company.com"
                            className="w-full bg-[var(--surface)] dark:bg-black/60 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl px-4 py-2 text-xs text-[var(--text)] placeholder-[var(--text-muted)] outline-none font-mono"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div>
                          <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] mb-1.5 uppercase">
                            Employee ID
                          </label>
                          <input
                            type="text"
                            required
                            value={empEmployeeId}
                            onChange={(e) => setEmpEmployeeId(e.target.value.toUpperCase())}
                            placeholder="EMP-1042"
                            className="w-full bg-[var(--surface)] dark:bg-black/60 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl px-4 py-2 text-xs text-[var(--text)] placeholder-[var(--text-muted)] outline-none font-mono uppercase"
                          />
                        </div>

                        <div>
                          <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] mb-1.5 uppercase">
                            Department
                          </label>
                          <select
                            value={empDepartment}
                            onChange={(e) => setEmpDepartment(e.target.value)}
                            className="w-full bg-[var(--surface)] dark:bg-black/80 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl px-3 py-2 text-xs text-[var(--text)] outline-none"
                          >
                            {DEPARTMENTS.map((d) => (
                              <option key={d} value={d} className="bg-[var(--surface)] text-[var(--text)]">
                                {d}
                              </option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] mb-1.5 uppercase">
                            Target Position
                          </label>
                          <select
                            value={empPosition}
                            onChange={(e) => setEmpPosition(e.target.value)}
                            className="w-full bg-[var(--surface)] dark:bg-black/80 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl px-3 py-2 text-xs text-[var(--text)] outline-none"
                          >
                            {POSITIONS.map((p) => (
                              <option key={p} value={p} className="bg-[var(--surface)] text-[var(--text)]">
                                {p}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <label className="text-[11px] font-mono tracking-wider text-[var(--text-secondary)] uppercase">
                            Secure Password (min 8 chars)
                          </label>
                          <div className="flex items-center gap-3">
                            <span
                              className="text-[10px] font-mono font-bold"
                              style={{ color: empStrength.color }}
                            >
                              STRENGTH: {empStrength.label}
                            </span>
                            <button
                              type="button"
                              onClick={() => setShowEmpPassword(!showEmpPassword)}
                              className="text-[10px] font-mono text-[var(--text-muted)] hover:text-[var(--text)]"
                            >
                              {showEmpPassword ? 'HIDE' : 'SHOW'}
                            </button>
                          </div>
                        </div>
                        <input
                          type={showEmpPassword ? 'text' : 'password'}
                          required
                          value={empPassword}
                          onChange={(e) => setEmpPassword(e.target.value)}
                          placeholder="••••••••••••"
                          className="w-full bg-[var(--surface)] dark:bg-black/60 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl px-4 py-2 text-xs text-[var(--text)] placeholder-[var(--text-muted)] outline-none font-mono"
                        />
                      </div>

                      <button
                        type="submit"
                        disabled={empLoading || empPassword.length < 8}
                        className="chrome-btn w-full py-3 text-xs font-black tracking-widest mt-4 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-40"
                      >
                        {empLoading ? <span>SUBMITTING REGISTRATION...</span> : <span>SUBMIT FOR ADMIN APPROVAL</span>}
                      </button>
                    </form>
                  </div>
                )}
              </motion.div>
            )}

            {/* ── TAB 3: ADMIN PROVISIONING ───────────────────────────────── */}
            {tab === 'register_admin' && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="liquid-card p-6 sm:p-8 min-h-[640px] flex flex-col justify-between"
                data-testid="auth-card"
              >
                <div className="border-b border-[var(--border)] dark:border-white/10 pb-4 mb-6">
                  <div className="flex items-center gap-2 text-[#FF00FF] mb-1">
                    <KeyRound size={16} />
                    <span className="text-[11px] font-mono tracking-widest uppercase font-bold">
                      EXECUTIVE SECURITY CLEARANCE
                    </span>
                  </div>
                  <h2 className="acid-title text-xl text-[var(--text)]">ADMINISTRATOR PROVISIONING</h2>
                  <p className="text-[11px] text-[var(--text-muted)] font-mono mt-0.5">
                    Requires Master Security Authorization Key for instant active ADMIN rights
                  </p>
                </div>

                <form onSubmit={handleAdminRegister} className="space-y-4">
                  {/* Master Key Input */}
                  <div className="p-4 rounded-xl border border-[#FF00FF]/40 bg-[#FF00FF]/5 mb-4">
                    <label className="block text-[11px] font-mono tracking-wider text-[#FF00FF] mb-1.5 uppercase font-bold">
                      Master Admin Authorization Key
                    </label>
                    <input
                      type="password"
                      required
                      value={adminKey}
                      onChange={(e) => setAdminKey(e.target.value)}
                      placeholder="Enter security master authorization key"
                      className="w-full bg-[var(--surface)] dark:bg-black/90 border border-[#FF00FF]/50 focus:border-[#CCFF00] rounded-xl px-4 py-2.5 text-xs text-[var(--text)] placeholder-[var(--text-muted)] outline-none font-mono"
                    />
                    <span className="text-[10px] font-mono text-[var(--text-muted)] mt-1 block">
                      Admin provisioning requires authorization key configured by system administrator.
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] mb-1.5 uppercase">
                        Admin Full Name
                      </label>
                      <input
                        type="text"
                        required
                        value={adminFullName}
                        onChange={(e) => setAdminFullName(e.target.value)}
                        placeholder="e.g. Eleanor Vance"
                        className="w-full bg-[var(--surface)] dark:bg-black/60 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl px-4 py-2 text-xs text-[var(--text)] placeholder-[var(--text-muted)] outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] mb-1.5 uppercase">
                        Admin Email
                      </label>
                      <input
                        type="email"
                        required
                        value={adminEmail}
                        onChange={(e) => setAdminEmail(e.target.value)}
                        placeholder="admin@archlens.io"
                        className="w-full bg-[var(--surface)] dark:bg-black/60 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl px-4 py-2 text-xs text-[var(--text)] placeholder-[var(--text-muted)] outline-none font-mono"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] mb-1.5 uppercase">
                        Department
                      </label>
                      <input
                        type="text"
                        value={adminDepartment}
                        onChange={(e) => setAdminDepartment(e.target.value)}
                        className="w-full bg-[var(--surface)] dark:bg-black/60 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl px-4 py-2 text-xs text-[var(--text)] outline-none font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] mb-1.5 uppercase">
                        Position / Role
                      </label>
                      <input
                        type="text"
                        value={adminPosition}
                        onChange={(e) => setAdminPosition(e.target.value)}
                        className="w-full bg-[var(--surface)] dark:bg-black/60 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl px-4 py-2 text-xs text-[var(--text)] outline-none font-mono"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] mb-1.5 uppercase">
                        Badge ID
                      </label>
                      <input
                        type="text"
                        required
                        value={adminEmployeeId}
                        onChange={(e) => setAdminEmployeeId(e.target.value.toUpperCase())}
                        placeholder="ADM-001"
                        className="w-full bg-[var(--surface)] dark:bg-black/60 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl px-4 py-2 text-xs text-[var(--text)] placeholder-[var(--text-muted)] outline-none font-mono uppercase"
                      />
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <label className="text-[11px] font-mono tracking-wider text-[var(--text-secondary)] uppercase">
                          Password
                        </label>
                        <div className="flex items-center gap-3">
                          <span className="text-[10px] font-mono font-bold" style={{ color: adminStrength.color }}>
                            {adminStrength.label}
                          </span>
                          <button
                            type="button"
                            onClick={() => setShowAdminPassword(!showAdminPassword)}
                            className="text-[10px] font-mono text-[var(--text-muted)] hover:text-[var(--text)]"
                          >
                            {showAdminPassword ? 'HIDE' : 'SHOW'}
                          </button>
                        </div>
                      </div>
                      <input
                        type={showAdminPassword ? 'text' : 'password'}
                        required
                        value={adminPassword}
                        onChange={(e) => setAdminPassword(e.target.value)}
                        placeholder="••••••••••••"
                        className="w-full bg-[var(--surface)] dark:bg-black/60 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl px-4 py-2 text-xs text-[var(--text)] placeholder-[var(--text-muted)] outline-none font-mono"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={adminLoading || !adminKey.trim() || adminPassword.length < 8}
                    className="chrome-btn w-full py-3 text-xs font-black tracking-widest mt-4 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-40"
                  >
                    {adminLoading ? <span>PROVISIONING ADMINISTRATOR...</span> : <span>AUTHORIZE & ACTIVATE ADMIN</span>}
                  </button>
                </form>
              </motion.div>
            )}

            {/* ── TAB 4: STATUS CHECKER TOOL ──────────────────────────────── */}
            {tab === 'check_status' && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="liquid-card p-6 sm:p-8 min-h-[640px] flex flex-col justify-between"
                data-testid="auth-card"
              >
                <div className="border-b border-[var(--border)] dark:border-white/10 pb-4 mb-6">
                  <h2 className="acid-title text-xl text-[var(--text)]">REGISTRATION APPROVAL STATUS</h2>
                  <p className="text-[11px] text-[var(--text-muted)] font-mono mt-0.5">
                    Query real-time authorization status by corporate email or Employee ID
                  </p>
                </div>

                <form onSubmit={handleStatusCheck} className="flex gap-2 mb-6">
                  <div className="relative flex-1">
                    <input
                      type="text"
                      required
                      value={statusLookupInput}
                      onChange={(e) => setStatusLookupInput(e.target.value)}
                      placeholder="Enter Employee ID (e.g. EMP-1042) or work email..."
                      className="w-full bg-[var(--surface)] dark:bg-black/60 border border-[var(--border)] dark:border-white/15 focus:border-[var(--accent)] rounded-xl pl-4 pr-10 py-2.5 text-xs text-[var(--text)] placeholder-[var(--text-muted)] outline-none font-mono"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={statusLoading || !statusLookupInput.trim()}
                    className="chrome-btn px-6 py-2.5 text-xs font-bold shrink-0 disabled:opacity-40"
                  >
                    {statusLoading ? 'QUERYING...' : 'VERIFY'}
                  </button>
                </form>

                {/* Status Result Display */}
                {statusResult && (
                  <div className="p-5 rounded-2xl bg-[var(--surface-2)] dark:bg-black/80 border border-[var(--border)] dark:border-white/15 space-y-3 font-mono text-xs">
                    <div className="flex items-center justify-between pb-3 border-b border-[var(--border)] dark:border-white/10">
                      <span className="text-[var(--text-muted)] uppercase">VERIFICATION RESULT</span>
                      {statusResult.found ? (
                        statusResult.status === 'active' ? (
                          <span className="badge-acid text-[10px]">ACTIVE / APPROVED</span>
                        ) : (
                          <span className="badge-pink text-[10px]">PENDING APPROVAL</span>
                        )
                      ) : (
                        <span className="text-red-400 font-bold">NOT REGISTERED</span>
                      )}
                    </div>

                    {statusResult.found ? (
                      <>
                        <div className="grid grid-cols-2 gap-2 text-[11px]">
                          <div>
                            <span className="text-[var(--text-muted)] block">APPLICANT:</span>
                            <span className="text-[var(--text)] font-bold">{statusResult.full_name}</span>
                          </div>
                          <div>
                            <span className="text-[var(--text-muted)] block">BADGE ID:</span>
                            <span className="text-[var(--accent-text)] dark:text-[#CCFF00]">{statusResult.employee_id}</span>
                          </div>
                          <div>
                            <span className="text-[var(--text-muted)] block">DEPARTMENT:</span>
                            <span className="text-[var(--text)]">{statusResult.department}</span>
                          </div>
                          <div>
                            <span className="text-[var(--text-muted)] block">ASSIGNED ROLE:</span>
                            <span className="text-[#00F0FF] font-bold">{statusResult.role}</span>
                          </div>
                        </div>

                        <div className="p-3 rounded-lg bg-[var(--surface-2)] dark:bg-white/[0.02] border border-[var(--border)] dark:border-white/10 text-[11px] text-[var(--text-secondary)]">
                          {statusResult.message}
                        </div>

                        {statusResult.status === 'active' && (
                          <button
                            onClick={() => {
                              setLoginEmail(statusLookupInput)
                              setTab('login')
                            }}
                            className="chrome-btn w-full py-2.5 text-xs font-bold mt-2"
                          >
                            PROCEED TO LOGIN →
                          </button>
                        )}
                      </>
                    ) : (
                      <div className="text-red-300 py-2">
                        {statusResult.message}
                        <button
                          onClick={() => setTab('register_employee')}
                          className="block text-[var(--accent-text)] dark:text-[#CCFF00] underline mt-2 text-[11px]"
                        >
                          Click here to submit employee registration →
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </motion.div>
            )}
          </div>
        )}
      </main>

      {/* ── Bottom Acid Marquee ─────────────────────────────────────────── */}
      <footer className="relative z-20 w-full bg-[#0A0A0A] border-t border-white/10 py-3 overflow-hidden select-none">
        <div className="animate-marquee whitespace-nowrap flex gap-8 items-center text-[10px] font-mono tracking-[0.25em] uppercase text-white/50">
          <span>ARCHLENS ARCHITECTURE ENGINE</span>
          <span className="text-[#CCFF00]">•</span>
          <span>ENTERPRISE STATIC AST ANALYSIS</span>
          <span className="text-[#CCFF00]">•</span>
          <span>TAMPER-PROOF AUDIT TRAIL</span>
          <span className="text-[#CCFF00]">•</span>
          <span>ARGON2 / BCRYPT PASSWORD PROTECTION</span>
          <span className="text-[#CCFF00]">•</span>
          <span>HTTPONLY ACCESS TOKENS</span>
          <span className="text-[#CCFF00]">•</span>
          <span>AUTOMATED CYCLIC REFACTORING</span>
        </div>
      </footer>
    </div>
  )
}
export default AuthPage
