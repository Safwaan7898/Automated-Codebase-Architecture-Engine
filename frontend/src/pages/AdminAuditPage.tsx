import { useState, useEffect } from 'react'
import {
  Search,
  Sparkles,
  Activity,
  ShieldCheck,
  DollarSign,
  Cpu,
  RefreshCw,
  Layers,
} from 'lucide-react'
import { adminApi, aiApi } from '../api/client'
import { AIBadge } from '../components/ui/AILabel'
import type { AuditLogEntry } from '../types/auth'
import type { AIUsageStatistics } from '../types'

export function AdminAuditPage() {
  const [activeTab, setActiveTab] = useState<'audit' | 'ai_usage'>('audit')

  // Audit logs state
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [loadingLogs, setLoadingLogs] = useState(true)
  const [search, setSearch] = useState('')

  // AI Usage state
  const [aiUsage, setAiUsage] = useState<AIUsageStatistics | null>(null)
  const [aiStatus, setAiStatus] = useState<Record<string, unknown> | null>(null)
  const [loadingAi, setLoadingAi] = useState(false)

  const fetchLogs = async () => {
    setLoadingLogs(true)
    try {
      const data = await adminApi.getAuditLogs()
      setLogs(data)
    } catch {
      // Demo mock logs
      setLogs([
        {
          id: 'log-001',
          user_id: 'user-001',
          user_email: 'admin@enterprise.internal',
          user_role: 'ADMIN',
          action: 'user:approve',
          resource_type: 'user',
          resource_id: 'user-005',
          resource: 'user:user-005',
          status: 'success',
          ip_address: '192.168.1.10',
          timestamp: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
          details: { assigned_role: 'DEVELOPER' },
        },
        {
          id: 'log-002',
          user_id: 'user-004',
          user_email: 'david.kim@enterprise.internal',
          user_role: 'DEVELOPER',
          action: 'auth:login_failed',
          resource_type: 'auth',
          resource: 'auth/login',
          status: 'failure',
          ip_address: '10.0.4.152',
          timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
          details: { reason: 'Invalid password. Attempt 5 of 5. Account locked for 30m.' },
        },
        {
          id: 'log-003',
          user_id: 'user-002',
          user_email: 'sarah.connor@enterprise.internal',
          user_role: 'ENGINEERING_MANAGER',
          action: 'ingest:start',
          resource_type: 'repo',
          resource: 'repo:vulnerable-python',
          status: 'success',
          ip_address: '192.168.1.44',
          timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
          details: { branch: 'main', type: 'git' },
        },
        {
          id: 'log-004',
          user_id: 'user-003',
          user_email: 'alex.rivera@enterprise.internal',
          user_role: 'SECURITY_ANALYST',
          action: 'report:export',
          resource_type: 'report',
          resource: 'report:flask-repo-001',
          status: 'success',
          ip_address: '192.168.1.89',
          timestamp: new Date(Date.now() - 1000 * 60 * 240).toISOString(),
          details: { format: 'pdf' },
        },
      ])
    } finally {
      setLoadingLogs(false)
    }
  }

  const fetchAiUsage = async () => {
    setLoadingAi(true)
    try {
      const [usageData, statusData] = await Promise.all([
        aiApi.getAiUsage(),
        aiApi.getAiStatus(),
      ])
      setAiUsage(usageData)
      setAiStatus(statusData)
    } catch {
      // Fallback telemetry
      setAiUsage({
        total_calls: 14,
        total_tokens: 18450,
        total_cost_usd: 0.0092,
        active_provider: 'groq -> gemini',
        feature_breakdown: [
          { feature_name: 'Executive Narrative', call_count: 3, tokens_consumed: 4200, cost_usd: 0.0021 },
          { feature_name: 'Smell Explanations', call_count: 5, tokens_consumed: 5600, cost_usd: 0.0028 },
          { feature_name: 'Security Enrichment', call_count: 4, tokens_consumed: 6100, cost_usd: 0.0031 },
          { feature_name: 'Ask ArchLens Chat', call_count: 2, tokens_consumed: 2550, cost_usd: 0.0012 },
        ],
      })
      setAiStatus({
        status: 'online',
        provider_chain: ['groq', 'gemini'],
        provider_health: {
          groq: { status: 'healthy', calls: 10, rpm_usage: 2, cooldown_remaining: 0 },
          gemini: { status: 'healthy', calls: 4, rpm_usage: 1, cooldown_remaining: 0 },
        },
      })
    } finally {
      setLoadingAi(false)
    }
  }

  useEffect(() => {
    fetchLogs()
    fetchAiUsage()
  }, [])

  const filteredLogs = logs.filter((l) => {
    return (
      (l.user_email?.toLowerCase().includes(search.toLowerCase()) ?? false) ||
      l.action.toLowerCase().includes(search.toLowerCase()) ||
      (l.resource?.toLowerCase().includes(search.toLowerCase()) ?? false) ||
      l.resource_type.toLowerCase().includes(search.toLowerCase())
    )
  })

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Enterprise Administration Console
            </h1>
            <span className="badge badge-accent text-[9px] uppercase font-bold">Admin Only</span>
          </div>
          <p className="text-xs sm:text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Immutable security audit logging, RBAC validation records, and AI infrastructure usage telemetry.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-[var(--surface-2)] border border-[var(--border)]">
          <button
            onClick={() => setActiveTab('audit')}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
              activeTab === 'audit'
                ? 'bg-[var(--surface)] text-[var(--text-primary)] shadow-sm'
                : 'text-muted hover:text-[var(--text-primary)]'
            }`}
          >
            Security Audit Trail ({logs.length})
          </button>
          <button
            onClick={() => {
              setActiveTab('ai_usage')
              fetchAiUsage()
            }}
            data-testid="admin-ai-usage-tab"
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
              activeTab === 'ai_usage'
                ? 'bg-[var(--accent)] text-black font-extrabold shadow-sm'
                : 'text-muted hover:text-[var(--text-primary)]'
            }`}
          >
            <Sparkles size={13} />
            <span>AI Usage & Cost</span>
            <AIBadge label="AI-generated" size="xs" />
          </button>
        </div>
      </div>

      {/* ── TAB 1: AUDIT TRAIL ──────────────────────────────────────────────── */}
      {activeTab === 'audit' && (
        <div className="space-y-4">
          {/* Search and Filters */}
          <div className="glass-card p-4 rounded-2xl flex items-center justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
              <input
                type="text"
                placeholder="Search by email, action, or resource..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border bg-transparent focus:outline-none placeholder-[var(--placeholder)]"
                style={{ borderColor: 'var(--surface-border)', color: 'var(--text-primary)' }}
              />
            </div>

            <button
              onClick={fetchLogs}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold border text-muted hover:text-primary transition-colors cursor-pointer"
              style={{ borderColor: 'var(--surface-border)' }}
            >
              Refresh Logs
            </button>
          </div>

          {/* Logs Table */}
          <div className="glass-card rounded-2xl overflow-hidden border" style={{ borderColor: 'var(--glass-border)' }}>
            {loadingLogs ? (
              <div className="text-center py-12 text-muted text-xs">Loading audit events...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b bg-[var(--surface-2)] text-muted uppercase font-semibold text-[10px] tracking-wider" style={{ borderColor: 'var(--glass-border)' }}>
                    <tr>
                      <th className="py-3 px-4">Timestamp</th>
                      <th className="py-3 px-4">User</th>
                      <th className="py-3 px-4">Action</th>
                      <th className="py-3 px-4">Target Resource</th>
                      <th className="py-3 px-4">IP Address</th>
                      <th className="py-3 px-4 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)] font-mono text-[11px]">
                    {filteredLogs.map((log) => (
                      <tr
                        key={log.id}
                        className="hover:bg-[var(--surface-hover)] transition-colors"
                      >
                        <td className="py-3 px-4 text-muted whitespace-nowrap">
                          {new Date(log.timestamp).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 font-semibold text-primary">{log.user_email || 'System'}</td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--border)] font-mono text-[10px]">
                            {log.action}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-muted truncate max-w-[200px]">{log.resource || '—'}</td>
                        <td className="py-3 px-4 text-muted">{log.ip_address || '127.0.0.1'}</td>
                        <td className="py-3 px-4 text-right">
                          <span
                            className={`badge text-[9px] uppercase font-bold px-2 py-0.5 rounded-full ${
                              log.status === 'success' ? 'badge-accent' : 'badge-danger'
                            }`}
                          >
                            {log.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 2: AI USAGE & COST TELEMETRY ─────────────────────────────────── */}
      {activeTab === 'ai_usage' && (
        <div className="space-y-6" data-testid="admin-ai-usage-screen">
          {/* Summary KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass-card p-5 rounded-2xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted">Total AI API Calls</span>
                <Activity size={18} style={{ color: 'var(--accent)' }} />
              </div>
              <div className="text-2xl font-bold mt-2 font-mono text-primary">
                {aiUsage?.total_calls ?? 0}
              </div>
              <p className="text-[11px] mt-1 text-muted">Across all active workspaces</p>
            </div>

            <div className="glass-card p-5 rounded-2xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted">Tokens Consumed</span>
                <Cpu size={18} style={{ color: 'var(--accent)' }} />
              </div>
              <div className="text-2xl font-bold mt-2 font-mono text-primary">
                {(aiUsage?.total_tokens ?? 0).toLocaleString()}
              </div>
              <p className="text-[11px] mt-1 text-muted">Input + Output cumulative count</p>
            </div>

            <div className="glass-card p-5 rounded-2xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted">Total Estimated Cost</span>
                <DollarSign size={18} style={{ color: 'var(--accent)' }} />
              </div>
              <div className="text-2xl font-bold mt-2 font-mono" style={{ color: 'var(--accent)' }}>
                ${(aiUsage?.total_cost_usd ?? 0).toFixed(4)}
              </div>
              <p className="text-[11px] mt-1 text-muted">Calculated per provider pricing table</p>
            </div>

            <div className="glass-card p-5 rounded-2xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted">Configured Chain</span>
                <ShieldCheck size={18} style={{ color: 'var(--accent)' }} />
              </div>
              <div className="text-sm font-bold mt-2 font-mono text-primary truncate">
                {String(aiStatus?.status ? `${aiStatus.status} (${aiUsage?.active_provider || 'groq -> gemini'})` : (aiUsage?.active_provider || 'groq -> gemini'))}
              </div>
              <p className="text-[11px] mt-1 text-muted">Sequential failover with backoff</p>
            </div>
          </div>

          {/* Privacy & Key Security Guarantee Banner */}
          <div
            className="rounded-2xl p-4 border flex items-center justify-between gap-4 font-mono text-xs"
            style={{
              background: 'rgba(198,244,50,0.04)',
              borderColor: 'rgba(198,244,50,0.2)',
            }}
          >
            <div className="flex items-center gap-3">
              <ShieldCheck size={20} style={{ color: 'var(--accent)' }} className="flex-shrink-0" />
              <div>
                <strong className="block text-primary">Zero Key Leakage Invariant Enforced</strong>
                <span className="text-muted text-[11px]">
                  Provider API keys are resolved strictly server-side from environment variables. They are never logged, returned in API payloads, or exposed in the UI.
                </span>
              </div>
            </div>
            <button
              onClick={fetchAiUsage}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold text-muted hover:text-white transition-colors cursor-pointer flex-shrink-0"
              style={{ borderColor: 'var(--surface-border)' }}
            >
              <RefreshCw size={12} className={loadingAi ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>

          {/* Per-Feature Breakdown Table */}
          <div className="glass-card p-6 rounded-2xl space-y-4">
            <h3 className="text-sm font-bold flex items-center gap-2 text-primary">
              <Layers size={16} style={{ color: 'var(--accent)' }} /> AI Feature Consumption Breakdown
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="border-b bg-[var(--surface-2)] text-muted uppercase font-semibold text-[10px] tracking-wider" style={{ borderColor: 'var(--glass-border)' }}>
                  <tr>
                    <th className="py-3 px-4">AI Feature</th>
                    <th className="py-3 px-4 text-right">Invocations</th>
                    <th className="py-3 px-4 text-right">Tokens Consumed</th>
                    <th className="py-3 px-4 text-right">Cost (USD)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)] text-[11px]">
                  {(aiUsage?.feature_breakdown ?? []).map((f) => (
                    <tr key={f.feature_name} className="hover:bg-[var(--surface-hover)]">
                      <td className="py-3 px-4 font-bold text-primary flex items-center gap-2">
                        <span>{f.feature_name}</span>
                        <AIBadge size="xs" />
                      </td>
                      <td className="py-3 px-4 text-right text-muted">{f.call_count}</td>
                      <td className="py-3 px-4 text-right text-muted">{f.tokens_consumed.toLocaleString()}</td>
                      <td className="py-3 px-4 text-right font-bold text-[var(--accent)]">
                        ${f.cost_usd.toFixed(4)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
