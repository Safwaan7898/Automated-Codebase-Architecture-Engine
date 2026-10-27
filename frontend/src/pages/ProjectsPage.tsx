import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  GitCompare,
  Trash2,
  RefreshCw,
  GitBranch,
  FolderGit2,
} from 'lucide-react'
import type { WorkspaceProject } from '../types'
import { projectApi } from '../api/client'
import { ProjectHistoryTrend } from '../components/projects/ProjectHistoryTrend'
import { CompareModal } from '../components/projects/CompareModal'

export function ProjectsPage() {
  const [projects, setProjects] = useState<WorkspaceProject[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState<string>('')
  const [sortBy, setSortBy] = useState<string>('last_analyzed')
  const [expandedProjectId, setExpandedProjectId] = useState<string | null>(null)
  const [compareProject, setCompareProject] = useState<WorkspaceProject | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const loadProjects = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await projectApi.getProjects(search, sortBy)
      setProjects(data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load projects')
    } finally {
      setLoading(false)
    }
  }, [search, sortBy])

  useEffect(() => {
    loadProjects()
  }, [loadProjects])

  const handleDelete = async (project: WorkspaceProject) => {
    const confirm = window.confirm(
      `Are you sure you want to delete project "${project.name}" and all its ${project.analysis_count} recorded analyses? This cannot be undone.`
    )
    if (!confirm) return

    setDeletingId(project.project_id)
    try {
      await projectApi.deleteProject(project.project_id)
      setProjects((prev) => prev.filter((p) => p.project_id !== project.project_id))
    } catch (err: any) {
      alert(err?.response?.data?.detail || err.message || 'Failed to delete project')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
              Multi-Project Workspace
            </h1>
            <span className="badge badge-accent text-[10px] font-bold uppercase tracking-wider">Phase 8</span>
          </div>
          <p className="text-xs sm:text-sm mt-1 text-muted">
            Group analyses by repository URL and branch, inspect long-term health trends, and compare architecture runs.
          </p>
        </div>

        <button
          onClick={loadProjects}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-surface-2 dark:bg-white/5 border border-[var(--border)] dark:border-white/10 hover:border-accent text-[var(--text-primary)] transition-colors self-start sm:self-auto"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Controls: Search and Sort */}
      <div className="glass-card p-4 rounded-2xl flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            placeholder="Search projects or repositories..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl border border-[var(--border)] dark:border-white/10 bg-surface-2 dark:bg-white/5 text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-accent"
          />
        </div>

        <div className="flex items-center gap-2 text-xs">
          <SlidersHorizontal size={14} className="text-muted shrink-0" />
          <span className="text-muted shrink-0">Sort by:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-2.5 py-1.5 rounded-xl border border-[var(--border)] dark:border-white/10 bg-surface-2 dark:bg-white/5 text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-accent font-medium text-xs"
          >
            <option value="last_analyzed">Last Analyzed</option>
            <option value="risk">Portfolio Risk (Highest First)</option>
            <option value="score">Health Score</option>
            <option value="name">Project Name</option>
            <option value="smells">Smell Count</option>
          </select>
        </div>
      </div>

      {/* Loading & Error States */}
      {loading && projects.length === 0 && (
        <div className="glass-card p-12 rounded-2xl flex flex-col items-center justify-center text-muted animate-pulse">
          <RefreshCw size={24} className="animate-spin text-accent mb-2" />
          <span className="text-xs">Loading multi-project workspace...</span>
        </div>
      )}

      {error && (
        <div className="glass-card p-6 rounded-2xl text-red-400 text-xs text-center border-red-500/20">
          {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && projects.length === 0 && !error && (
        <div className="glass-card p-12 rounded-2xl flex flex-col items-center justify-center text-center text-muted">
          <FolderGit2 size={44} className="opacity-30 mb-3" />
          <h3 className="text-sm font-bold text-[var(--text-primary)]">No Projects Found</h3>
          <p className="text-xs text-muted max-w-md mt-1 mb-4">
            Ingest codebases via GitHub URL or folder upload on the Ingestion page to automatically populate this workspace.
          </p>
        </div>
      )}

      {/* Projects List */}
      <div className="space-y-4">
        {projects.map((proj) => {
          const isExpanded = expandedProjectId === proj.project_id

          return (
            <motion.div
              key={proj.project_id}
              layout
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card rounded-2xl overflow-hidden border border-[var(--border)] dark:border-white/10"
            >
              {/* Card Main Bar */}
              <div className="p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-base font-bold tracking-tight text-[var(--text-primary)] truncate">
                      {proj.name}
                    </h2>
                    <span className="badge badge-accent text-[10px] uppercase font-mono flex items-center gap-1">
                      <GitBranch size={10} /> {proj.branch}
                    </span>
                    <span className="text-[11px] text-muted font-mono">
                      {proj.analysis_count} {proj.analysis_count === 1 ? 'run' : 'runs'}
                    </span>
                  </div>
                  <div className="text-xs text-muted font-mono truncate">{proj.repo_url}</div>

                  {/* Language Badges */}
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    {Object.entries(proj.languages).map(([lang, count]) => (
                      <span
                        key={lang}
                        className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-surface-2 dark:bg-white/5 border border-[var(--border)] dark:border-white/5 text-muted"
                      >
                        {lang}: {count}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Score, Risk & Debt Metrics */}
                <div className="flex flex-wrap items-center gap-4 lg:gap-6 shrink-0">
                  <div className="text-center">
                    <div className="text-[10px] text-muted uppercase font-bold">Health Score</div>
                    <div className="text-xl font-bold font-mono text-emerald-700 dark:text-emerald-400 mt-0.5">
                      {proj.score} <span className="text-xs text-muted font-normal">({proj.grade})</span>
                    </div>
                  </div>

                  {(() => {
                    const riskVal =
                      proj.risk_score ??
                      Math.round((100 - proj.score) + proj.smells * 2 + proj.cycles * 5)
                    return (
                      <div className="text-center">
                        <div className="text-[10px] text-muted uppercase font-bold">Portfolio Risk</div>
                        <div
                          className={`text-xl font-bold font-mono mt-0.5 ${
                            riskVal > 60
                              ? 'text-red-700 dark:text-red-400'
                              : riskVal > 30
                              ? 'text-amber-700 dark:text-amber-400'
                              : 'text-emerald-700 dark:text-emerald-400'
                          }`}
                        >
                          {riskVal}
                          <span className="text-[10px] ml-1 font-normal uppercase">
                            {riskVal > 60 ? 'High' : riskVal > 30 ? 'Med' : 'Low'}
                          </span>
                        </div>
                      </div>
                    )
                  })()}

                  <div className="text-center">
                    <div className="text-[10px] text-muted uppercase font-bold">Cycles</div>
                    <div
                      className={`text-xl font-bold font-mono mt-0.5 ${
                        proj.cycles > 0 ? 'text-red-700 dark:text-red-400' : 'text-emerald-700 dark:text-emerald-400'
                      }`}
                    >
                      {proj.cycles}
                    </div>
                  </div>

                  <div className="text-center">
                    <div className="text-[10px] text-muted uppercase font-bold">Smells</div>
                    <div
                      className={`text-xl font-bold font-mono mt-0.5 ${
                        proj.smells > 0 ? 'text-amber-700 dark:text-amber-400' : 'text-emerald-700 dark:text-emerald-400'
                      }`}
                    >
                      {proj.smells}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setCompareProject(proj)}
                      className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-surface-2 dark:bg-white/5 border border-[var(--border)] dark:border-white/10 hover:border-accent text-[var(--text-primary)] flex items-center gap-1.5 transition-colors"
                      title="Compare analysis runs"
                    >
                      <GitCompare size={13} className="text-accent" />
                      <span>Compare</span>
                    </button>

                    <button
                      onClick={() => setExpandedProjectId(isExpanded ? null : proj.project_id)}
                      className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-surface-2 dark:bg-white/5 border border-[var(--border)] dark:border-white/10 hover:border-accent text-[var(--text-primary)] flex items-center gap-1.5 transition-colors"
                    >
                      <span>Trends</span>
                      {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                    </button>

                    <button
                      onClick={() => handleDelete(proj)}
                      disabled={deletingId === proj.project_id}
                      className="p-2 rounded-xl text-muted hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      title="Delete project"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>

              {/* Expandable History Drawer */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="border-t border-[var(--border)] dark:border-white/10 p-5 bg-surface/50"
                  >
                    <ProjectHistoryTrend history={proj.history} />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </div>

      {/* Compare Modal */}
      {compareProject && (
        <CompareModal
          project={compareProject}
          onClose={() => setCompareProject(null)}
        />
      )}
    </div>
  )
}
