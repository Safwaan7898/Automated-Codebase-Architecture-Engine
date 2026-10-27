import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  TrendingUp,
  Activity,
  Users,
  Award,
  ArrowUpRight,
  ShieldCheck,
  Zap,
} from 'lucide-react'

export function AnalyticsPage() {
  const [timeframe, setTimeframe] = useState<'30d' | '90d' | '1y'>('30d')

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Engineering Leadership Analytics
            </h1>
            <span className="badge badge-accent text-[9px] uppercase font-bold">Manager View</span>
          </div>
          <p className="text-xs sm:text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            High-level architectural health velocity, refactoring ROI, and team technical debt trends.
          </p>
        </div>

        {/* Timeframe Switcher */}
        <div className="flex items-center gap-1 p-1 rounded-xl bg-[var(--surface-2)] border border-[var(--border)] dark:bg-black/20 dark:border-white/5">
          {(['30d', '90d', '1y'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTimeframe(t)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors duration-150 ${
                timeframe === t ? 'bg-accent text-obsidian font-bold shadow-sm' : 'text-muted hover:text-primary'
              }`}
            >
              {t.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted">Arch Health Trajectory</span>
            <TrendingUp size={16} className="text-[var(--accent-text)] dark:text-accent" />
          </div>
          <div className="text-2xl font-bold mt-2 font-mono text-primary">+14.2%</div>
          <p className="text-[11px] mt-1 text-[var(--accent-text)] dark:text-accent font-semibold flex items-center gap-0.5">
            <ArrowUpRight size={12} /> Up from 71 to 82 pts
          </p>
        </div>

        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted">Debt Paydown Velocity</span>
            <Zap size={16} className="text-[var(--accent-text)] dark:text-accent" />
          </div>
          <div className="text-2xl font-bold mt-2 font-mono text-primary">8 Patches</div>
          <p className="text-[11px] mt-1 text-muted">Merged this month across 3 squads</p>
        </div>

        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted">Cycles Eliminated</span>
            <ShieldCheck size={16} className="text-[var(--accent-text)] dark:text-accent" />
          </div>
          <div className="text-2xl font-bold mt-2 font-mono text-primary">5 Loops</div>
          <p className="text-[11px] mt-1 text-muted">Zero circular dependencies in core</p>
        </div>

        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted">Active Contributors</span>
            <Users size={16} className="text-[var(--accent-text)] dark:text-accent" />
          </div>
          <div className="text-2xl font-bold mt-2 font-mono text-primary">18 Devs</div>
          <p className="text-[11px] mt-1 text-muted">Participating in architecture reviews</p>
        </div>
      </div>

      {/* Trajectory & Compliance Radar */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Health Velocity Chart Simulator */}
        <div className="glass-card p-6 rounded-2xl space-y-4">
          <h3 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <Activity size={16} className="text-[var(--accent-text)] dark:text-accent" /> Architecture Health Score Over Time
          </h3>
          <p className="text-xs text-muted">
            Continuous score tracking across git commit history and automated CI pipeline checks.
          </p>

          <div className="h-44 flex items-end justify-between gap-2 pt-6 pb-2 px-2 border-b border-[var(--border)] dark:border-white/5">
            {[
              { label: 'W1', score: 62 },
              { label: 'W2', score: 65 },
              { label: 'W3', score: 64 },
              { label: 'W4', score: 70 },
              { label: 'W5', score: 73 },
              { label: 'W6', score: 71 },
              { label: 'W7', score: 79 },
              { label: 'W8', score: 85 },
            ].map((bar, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-2 h-full justify-end">
                <span className="text-[10px] font-mono text-muted">{bar.score}</span>
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: `${(bar.score / 100) * 120}px` }}
                  transition={{ duration: 0.5, delay: i * 0.05 }}
                  className="w-full rounded-t-lg bg-[var(--surface-hover)] dark:bg-transparent"
                  style={{
                    background: bar.score >= 80 ? 'var(--accent)' : undefined,
                  }}
                />
                <span className="text-[10px] font-mono text-muted">{bar.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Policy Compliance Scorecard */}
        <div className="glass-card p-6 rounded-2xl space-y-4">
          <h3 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <Award size={16} className="text-[var(--accent-text)] dark:text-accent" /> Architecture Governance Rules
          </h3>
          <p className="text-xs text-muted">
            Enterprise boundary rules automatically enforced on pull requests.
          </p>

          <div className="space-y-3">
            {[
              { rule: 'Zero Circular Dependencies between Microservices', status: 'Passed', val: '0 found', ok: true },
              { rule: 'Presentation layer cannot call Data layer directly', status: 'Passed', val: '100% compliant', ok: true },
              { rule: 'Maximum Class Size < 600 LOC', status: 'Warning', val: '2 God Classes exceed', ok: false },
              { rule: 'No critical OWASP Injection vulnerabilities', status: 'Warning', val: 'Action required', ok: false },
            ].map((p, idx) => (
              <div key={idx} className="p-3.5 rounded-xl border flex items-center justify-between gap-3 bg-[var(--surface-2)] border-[var(--border)] dark:bg-black/20 dark:border-white/5">
                <div>
                  <span className="text-xs font-semibold block text-primary">{p.rule}</span>
                  <span className="text-[11px] font-mono text-muted">{p.val}</span>
                </div>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                    p.ok ? 'badge-accent' : 'badge-danger'
                  }`}
                >
                  {p.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
