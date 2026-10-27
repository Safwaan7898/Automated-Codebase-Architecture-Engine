import { useState, type FormEvent } from 'react'
import type { Language } from '../types'

interface Props {
  onAnalyze: (path: string, language: Language) => void
  loading: boolean
}

const SAMPLE_PATHS = [
  { label: '🐍 Python Flask sample', path: '../samples/python-flask' },
  { label: '☕ Java Spring sample', path: '../samples/java-spring' },
]

export function AnalyzePanel({ onAnalyze, loading }: Props) {
  const [path, setPath] = useState('')
  const [language, setLanguage] = useState<Language>('auto')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!path.trim()) return
    onAnalyze(path.trim(), language)
  }

  return (
    <div className="p-5 space-y-5">
      {/* Header */}
      <div>
        <h2 className="text-lg font-bold text-white tracking-tight">Analyze Codebase</h2>
        <p className="text-xs text-slate-400 mt-0.5">Enter a local path or choose a sample</p>
      </div>

      {/* Quick samples */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-widest">Quick Start</p>
        {SAMPLE_PATHS.map((s) => (
          <button
            key={s.path}
            type="button"
            onClick={() => setPath(s.path)}
            className="w-full text-left px-3 py-2 rounded-lg bg-surface-700 hover:bg-surface-600
                       text-xs text-slate-300 transition-colors duration-150 border border-surface-600
                       hover:border-brand-500"
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="text-xs font-medium text-slate-400 mb-1 block" htmlFor="repo-path">
            Repository Path
          </label>
          <input
            id="repo-path"
            type="text"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/path/to/repo"
            className="w-full bg-surface-700 border border-surface-600 rounded-lg px-3 py-2
                       text-sm text-white placeholder-slate-500 focus:outline-none
                       focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition"
          />
        </div>

        <div>
          <label className="text-xs font-medium text-slate-400 mb-1 block" htmlFor="language">
            Language
          </label>
          <select
            id="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            className="w-full bg-surface-700 border border-surface-600 rounded-lg px-3 py-2
                       text-sm text-white focus:outline-none focus:border-brand-500
                       focus:ring-1 focus:ring-brand-500 transition"
          >
            <option value="auto">🔍 Auto-detect</option>
            <option value="python">🐍 Python</option>
            <option value="java">☕ Java</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={loading || !path.trim()}
          id="analyze-btn"
          className="w-full py-2.5 rounded-lg font-semibold text-sm transition-[transform,opacity,box-shadow] duration-150 will-change-transform
                     bg-gradient-brand text-white shadow-glow-brand
                     hover:opacity-90 hover:shadow-lg active:scale-95
                     disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              Analyzing…
            </span>
          ) : (
            '▶ Run Analysis'
          )}
        </button>
      </form>
    </div>
  )
}
