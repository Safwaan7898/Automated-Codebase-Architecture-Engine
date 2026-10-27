import axios from 'axios'
import type {
  AnalysisResult,
  AnalyzeRequest,
  HealthResponse,
  IngestResponse,
  RefactorSuggestion,
  DiagnosticFinding,
  RecentAnalysisItem,
  AIMetricExplanation,
  AISmellFixSuggestion,
  AISecurityEnrichment,
  AITopologySummary,
  AIDashboardSummary,
  AIReportNarrative,
  AIChatResponse,
  AINLSearchFilter,
  AIRefactorProposal,
  AIUsageStatistics,
  WorkspaceProject,
  AnalysisComparison,
} from '../types'
import type {
  LoginPayload,
  RegisterPayload,
  TokenResponse,
  UserMeResponse,
  User,
  AuditLogEntry,
  ChangePasswordPayload,
  UpdateProfilePayload,
  UserPreferencesPayload,
  DemoUser,
} from '../types/auth'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
  withCredentials: true, // send httpOnly cookies on every request
})

// ── Global 401/403 handling ──────────────────────────────────────────────────
apiClient.interceptors.response.use(
  (res) => res,
  async (err) => {
    const status = err?.response?.status
    const url = err?.config?.url ?? ''
    const isAuthEndpoint =
      url.includes('/auth/login') ||
      url.includes('/auth/register') ||
      url.includes('/auth/refresh') ||
      url.includes('/auth/status')

    // If token expired on a protected endpoint, try silent refresh first (never on auth endpoints)
    if (status === 401 && !err.config?._retry && !isAuthEndpoint) {
      err.config._retry = true
      try {
        await apiClient.post('/auth/refresh')
        return apiClient(err.config)
      } catch {
        // Refresh failed → only redirect if not already on the login page
        if (!window.location.pathname.includes('/login')) {
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(err)
  }
)

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: RegisterPayload): Promise<User> =>
    apiClient.post<User>('/auth/register', data).then((r) => r.data),

  login: (data: LoginPayload): Promise<TokenResponse> =>
    apiClient.post<TokenResponse>('/auth/login', data).then((r) => r.data),

  refresh: (): Promise<TokenResponse> =>
    apiClient.post<TokenResponse>('/auth/refresh').then((r) => r.data),

  logout: (): Promise<{ message: string }> =>
    apiClient.post('/auth/logout').then((r) => r.data),

  me: (): Promise<UserMeResponse> =>
    apiClient.get<UserMeResponse>('/auth/me').then((r) => r.data),

  demoUsers: (): Promise<DemoUser[]> =>
    apiClient.get<DemoUser[]>('/auth/demo-users').then((r) => r.data),

  registerAdmin: (data: Record<string, unknown>): Promise<User> =>
    apiClient.post<User>('/auth/register-admin', data).then((r) => r.data),

  checkStatus: (identifier: string): Promise<{
    found: boolean
    status?: string
    full_name?: string
    employee_id?: string
    role?: string
    department?: string
    message: string
  }> =>
    apiClient.get(`/auth/status/${encodeURIComponent(identifier)}`).then((r) => r.data),
}

// ── Settings ─────────────────────────────────────────────────────────────────
export const settingsApi = {
  getProfile: (): Promise<User> =>
    apiClient.get<User>('/api/settings/profile').then((r) => r.data),

  updateProfile: (data: UpdateProfilePayload): Promise<User> =>
    apiClient.put<User>('/api/settings/profile', data).then((r) => r.data),

  changePassword: (data: ChangePasswordPayload): Promise<{ message: string }> =>
    apiClient.post('/api/settings/change-password', data).then((r) => r.data),

  getPreferences: (): Promise<{ theme_preference: string; notification_preferences: Record<string, unknown> }> =>
    apiClient.get('/api/settings/preferences').then((r) => r.data),

  updatePreferences: (data: UserPreferencesPayload): Promise<User> =>
    apiClient.put<User>('/api/settings/preferences', data).then((r) => r.data),
}

// ── Admin ─────────────────────────────────────────────────────────────────────
export const adminApi = {
  listUsers: (params?: { role?: string; status?: string }): Promise<User[]> =>
    apiClient.get<User[]>('/api/admin/users', { params }).then((r) => r.data),

  approveUser: (userId: string, role: string): Promise<User> =>
    apiClient.post<User>(`/api/admin/users/${userId}/approve`, { role }).then((r) => r.data),

  changeRole: (userId: string, role: string): Promise<User> =>
    apiClient.post<User>(`/api/admin/users/${userId}/role`, { role }).then((r) => r.data),

  unlockUser: (userId: string): Promise<User> =>
    apiClient.post<User>(`/api/admin/users/${userId}/unlock`).then((r) => r.data),

  getAuditLogs: (params?: { user_email?: string; action?: string; limit?: number }): Promise<AuditLogEntry[]> =>
    apiClient.get<AuditLogEntry[]>('/api/admin/audit-logs', { params }).then((r) => r.data),
}

// ── Analytics ─────────────────────────────────────────────────────────────────
export const analyticsApi = {
  getTeamAnalytics: (): Promise<Record<string, unknown>> =>
    apiClient.get('/api/analytics/team').then((r) => r.data),
}

// ── Core API (preserved from original) ───────────────────────────────────────
export const api = {
  /** GET /health */
  health: (): Promise<HealthResponse> =>
    apiClient.get<HealthResponse>('/health').then((r) => r.data),

  /** POST /analyze */
  analyze: (req: AnalyzeRequest): Promise<AnalysisResult> =>
    apiClient.post<AnalysisResult>('/analyze', req).then((r) => r.data),

  /** GET /graph/:repo_id */
  getGraph: (repoId: string): Promise<AnalysisResult> =>
    apiClient.get<AnalysisResult>(`/graph/${repoId}`).then((r) => r.data),

  /** GET /graphs */
  listGraphs: (): Promise<{ repo_ids: string[]; items?: RecentAnalysisItem[] }> =>
    apiClient.get<{ repo_ids: string[]; items?: RecentAnalysisItem[] }>('/graphs').then((r) => r.data),

  /** GET /ingest/config */
  getIngestConfig: (): Promise<{
    max_upload_size_mb: number
    max_upload_size_bytes: number
    allowed_extensions: string[]
    supported_languages: string[]
    allow_local_ingestion?: boolean
  }> =>
    apiClient.get('/ingest/config').then((r) => r.data),

  /** POST /ingest (Git URL, Archive URL, Snippet, Local Path) */
  startIngestion: (payload: Record<string, unknown>, signal?: AbortSignal): Promise<IngestResponse> =>
    apiClient.post<IngestResponse>('/ingest', payload, { signal }).then((r) => r.data),

  /** POST /ingest/archive (Upload ZIP or tar archive) */
  uploadArchive: (
    file: File,
    onProgress?: (pct: number) => void,
    signal?: AbortSignal,
    includeTests = false
  ): Promise<IngestResponse> => {
    const formData = new FormData()
    formData.append('archive', file)
    formData.append('include_tests', String(includeTests))
    return apiClient
      .post<IngestResponse>('/ingest/archive', formData, {
        headers: { 'Content-Type': undefined },
        timeout: 120_000,
        signal,
        onUploadProgress: (e) => {
          if (onProgress && e.total) {
            const pct = Math.round((e.loaded * 100) / e.total)
            onProgress(pct)
          }
        },
      })
      .then((r) => r.data)
  },

  /** POST /ingest/folder (Upload multi-file folder hierarchy) */
  uploadFolder: (
    files: File[],
    paths: string[],
    folderName = 'uploaded_repo',
    onProgress?: (pct: number) => void,
    signal?: AbortSignal,
    includeTests = false
  ): Promise<IngestResponse> => {
    const formData = new FormData()
    files.forEach((f) => formData.append('files', f))
    paths.forEach((p) => formData.append('paths', p))
    formData.append('folder_name', folderName)
    formData.append('include_tests', String(includeTests))
    return apiClient
      .post<IngestResponse>('/ingest/folder', formData, {
        headers: { 'Content-Type': undefined },
        timeout: 120_000,
        signal,
        onUploadProgress: (e) => {
          if (onProgress && e.total) {
            const pct = Math.round((e.loaded * 100) / e.total)
            onProgress(pct)
          }
        },
      })
      .then((r) => r.data)
  },

  /** GET /jobs/:job_id */
  getJobStatus: (jobId: string): Promise<Record<string, unknown>> =>
    apiClient.get<Record<string, unknown>>(`/jobs/${jobId}`).then((r) => r.data),

  /** POST /api/diagnostics/analyze-graph */
  getDiagnostics: (graphData: Record<string, unknown>): Promise<{
    findings: DiagnosticFinding[]
    risk_scores: Record<string, { total_risk: number; severity_component: number; centrality_component: number; complexity_component: number }>
  }> =>
    apiClient.post('/api/diagnostics/analyze-graph', graphData).then((r) => r.data),

  /** GET /api/refactor/{analysisId} */
  getRefactorPlan: (analysisId: string): Promise<{ suggestions: any[]; summary: any }> =>
    apiClient.get(`/api/refactor/${analysisId}`).then((r) => r.data),

  /** POST /api/refactor/suggest */
  getRefactorSuggestions: (
    graphData: Record<string, unknown>,
    repoPath = '.',
    enableLlm = false
  ): Promise<{ suggestions: RefactorSuggestion[] }> =>
    apiClient
      .post('/api/refactor/suggest', {
        graph: graphData,
        repo_path: repoPath,
        enable_llm: enableLlm,
      })
      .then((r) => r.data),

  /** POST /api/refactor/ai-proposal */
  requestAIRefactorProposal: (payload: {
    analysis_id: string
    target_node: string
    goal?: string
    file_path?: string
    existing_diff?: string
  }): Promise<{
    strategy: string
    target_node: string
    unified_diff: string
    syntax_valid: boolean
    validation_status: string
    validation_errors: string[]
    rationale: string
    llm_assisted: boolean
    is_fallback: boolean
  }> =>
    apiClient.post('/api/refactor/ai-proposal', payload).then((r) => r.data),

  /** POST /api/refactor/approve */
  approveRefactor: (suggestionId: string, reviewNotes?: string): Promise<Record<string, unknown>> =>
    apiClient
      .post('/api/refactor/approve', {
        suggestion_id: suggestionId,
        review_notes: reviewNotes,
      })
      .then((r) => r.data),

  /** POST /api/reports/generate */
  generateReport: async (payload: {
    repo_path?: string
    repo_name?: string
    format?: 'pdf' | 'html' | 'json'
    graph?: Record<string, unknown>
    query_osv?: boolean
  }): Promise<{ blob: Blob; filename: string; reportId: string | null }> => {
    const res = await apiClient.post('/api/reports/generate', payload, {
      responseType: 'blob',
    })
    const contentDisposition = res.headers['content-disposition'] || ''
    const match = contentDisposition.match(/filename="?([^"]+)"?/)
    const filename = match ? match[1] : `report.${payload.format || 'pdf'}`
    const reportId = (res.headers['x-report-id'] as string) || null
    return { blob: res.data, filename, reportId }
  },

  /** GET /api/reports/history */
  getReportHistory: (): Promise<{ total_reports: number; reports: Array<{
    report_id: string
    repo_name: string
    health_score: number
    grade: string
    components: number
    dependencies: number
    critical_vulnerabilities: number
    cycles: number
    generated_at: string
  }> }> =>
    apiClient.get('/api/reports/history').then((r) => r.data),

  /** GET /api/reports/:id/download */
  downloadExistingReport: async (
    reportId: string,
    format: 'pdf' | 'html' | 'json' = 'pdf'
  ): Promise<{ blob: Blob; filename: string }> => {
    const res = await apiClient.get(`/api/reports/${reportId}/download`, {
      params: { format },
      responseType: 'blob',
    })
    const contentDisposition = res.headers['content-disposition'] || ''
    const match = contentDisposition.match(/filename="?([^"]+)"?/)
    const filename = match ? match[1] : `report-${reportId}.${format}`
    return { blob: res.data, filename }
  },

  /** POST /api/reports/export-security */
  exportSecurityReport: async (payload: {
    repo_path?: string
    graph?: Record<string, unknown>
  }): Promise<{ blob: Blob; filename: string; reportId: string | null }> => {
    const res = await apiClient.post('/api/reports/export-security', {
      ...payload,
      format: 'json',
    }, { responseType: 'blob' })
    const contentDisposition = res.headers['content-disposition'] || ''
    const match = contentDisposition.match(/filename="?([^"]+)"?/)
    const filename = match ? match[1] : 'security-report.json'
    const reportId = (res.headers['x-report-id'] as string) || null
    return { blob: res.data, filename, reportId }
  },

  /** GET /api/diagnostics/cve */
  getCveDetails: (): Promise<Record<string, unknown>> =>
    apiClient.get('/api/diagnostics/cve').then((r) => r.data),

  /** GET /api/diagnostics/rules */
  getDiagnosticRules: (): Promise<Record<string, unknown>> =>
    apiClient.get('/api/diagnostics/rules').then((r) => r.data),
}

// ── AI Capabilities API ──────────────────────────────────────────────────────
export const aiApi = {
  /** POST /api/analysis/explain-metric */
  explainMetric: (
    metricName: string,
    value: number,
    analysisId?: string,
    repoContext?: Record<string, unknown>
  ): Promise<AIMetricExplanation> =>
    apiClient
      .post<AIMetricExplanation>('/api/analysis/explain-metric', {
        metric_name: metricName,
        value,
        analysis_id: analysisId,
        repo_context: repoContext ?? {},
      })
      .then((r) => r.data),

  /** POST /api/diagnostics/explain-smell */
  explainSmell: (
    smell: Record<string, unknown>,
    repoContext?: Record<string, unknown>
  ): Promise<AISmellFixSuggestion> =>
    apiClient
      .post<AISmellFixSuggestion>('/api/diagnostics/explain-smell', {
        smell,
        repo_context: repoContext ?? {},
      })
      .then((r) => r.data),

  /** POST /api/diagnostics/enrich-security */
  enrichSecurity: (
    finding: Record<string, unknown>,
    codeSnippet?: string
  ): Promise<AISecurityEnrichment> =>
    apiClient
      .post<AISecurityEnrichment>('/api/diagnostics/enrich-security', {
        finding,
        code_snippet: codeSnippet,
      })
      .then((r) => r.data),

  /** POST /api/analysis/topology-summary */
  summarizeTopology: (
    communityId: number,
    nodeIds: string[]
  ): Promise<AITopologySummary> =>
    apiClient
      .post<AITopologySummary>('/api/analysis/topology-summary', {
        community_id: communityId,
        node_ids: nodeIds,
      })
      .then((r) => r.data),

  /** POST /api/analysis/dashboard-summary */
  getDashboardSummary: (
    healthScore: number,
    grade: string,
    smellsCount: number = 0,
    cyclesCount: number = 0,
    topHotspots: string[] = []
  ): Promise<AIDashboardSummary> =>
    apiClient
      .post<AIDashboardSummary>('/api/analysis/dashboard-summary', {
        health_score: healthScore,
        grade,
        smells_count: smellsCount,
        cycles_count: cyclesCount,
        top_hotspots: topHotspots,
      })
      .then((r) => r.data),

  /** POST /api/reports/narrative */
  generateReportNarrative: (
    reportData: Record<string, unknown>,
    analysisId?: string
  ): Promise<AIReportNarrative> =>
    apiClient
      .post<AIReportNarrative>('/api/reports/narrative', {
        report_data: reportData,
        analysis_id: analysisId,
      })
      .then((r) => r.data),

  /** POST /api/analysis/chat */
  askArchLensChat: (
    query: string,
    analysisId?: string
  ): Promise<AIChatResponse> =>
    apiClient
      .post<AIChatResponse>('/api/analysis/chat', {
        query,
        analysis_id: analysisId,
      })
      .then((r) => r.data),

  /** POST /api/analysis/nl-search */
  nlSearch: (
    query: string,
    analysisId?: string
  ): Promise<AINLSearchFilter> =>
    apiClient
      .post<AINLSearchFilter>('/api/analysis/nl-search', {
        query,
        analysis_id: analysisId,
      })
      .then((r) => r.data),

  /** GET /api/admin/ai/usage */
  getAiUsage: (): Promise<AIUsageStatistics> =>
    apiClient.get<AIUsageStatistics>('/api/admin/ai/usage').then((r) => r.data),

  /** GET /api/admin/ai/status */
  getAiStatus: (): Promise<Record<string, unknown>> =>
    apiClient.get<Record<string, unknown>>('/api/admin/ai/status').then((r) => r.data),

  /** POST /api/refactor/ai-proposal */
  requestRefactorProposal: (
    smell: Record<string, unknown>,
    analysisId?: string,
    repoPath: string = '.',
    runTests: boolean = false
  ): Promise<AIRefactorProposal> =>
    apiClient
      .post<AIRefactorProposal>('/api/refactor/ai-proposal', {
        smell,
        analysis_id: analysisId,
        repo_path: repoPath,
        run_tests: runTests,
      })
      .then((r) => r.data),

  /** GET /api/refactor/export-patch/:proposalId */
  exportPatch: (proposalId: string): Promise<{ proposal_id: string; patch: string }> =>
    apiClient.get(`/api/refactor/export-patch/${encodeURIComponent(proposalId)}`).then((r) => r.data),
}

// ── Multi-Project Workspace API (Phase 8) ───────────────────────────────────
export const projectApi = {
  /** GET /api/projects */
  getProjects: (search?: string, sortBy: string = 'last_analyzed'): Promise<WorkspaceProject[]> =>
    apiClient
      .get<WorkspaceProject[]>('/api/projects', {
        params: { search: search || undefined, sort_by: sortBy },
      })
      .then((r) => r.data),

  /** GET /api/projects/:projectId */
  getProject: (projectId: string): Promise<WorkspaceProject> =>
    apiClient.get<WorkspaceProject>(`/api/projects/${encodeURIComponent(projectId)}`).then((r) => r.data),

  /** DELETE /api/projects/:projectId */
  deleteProject: (projectId: string): Promise<{ success: boolean; deleted_analyses: number; message: string }> =>
    apiClient.delete(`/api/projects/${encodeURIComponent(projectId)}`).then((r) => r.data),

  /** POST /api/projects/compare */
  compareAnalyses: (baseId: string, targetId: string, enableAi: boolean = false): Promise<AnalysisComparison> =>
    apiClient
      .post<AnalysisComparison>('/api/projects/compare', {
        base_id: baseId,
        target_id: targetId,
        enable_ai: enableAi,
      })
      .then((r) => r.data),
}


export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}
