// Shared TypeScript types for ArchLens Agencia frontend

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'clean'

export interface DiagnosticFinding {
  id: string
  rule_id: string
  title: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  category: string
  cwe?: string
  owasp?: string
  file_path: string
  line_number?: number
  code_snippet?: string
  remediation?: string
}

export interface ImpactMetrics {
  coupling: number
  complexity: number
  god_classes: number
  cycles: number
}

export interface RefactorSuggestion {
  id: string
  type: 'break_cycle' | 'split_god_class' | 'extract_module' | 'move_method' | 'isolate_vulnerable_service'
  title: string
  rationale: string
  affected_nodes: string[]
  effort: 'S' | 'M' | 'L'
  priority_score?: number
  impact_before?: ImpactMetrics
  impact_after?: ImpactMetrics
  action_details?: Record<string, unknown>
  diff_preview?: string
}

export interface GraphNode {
  id: string
  label: string
  type: 'module' | 'class' | 'function' | 'package' | 'interface' | 'unknown' | string
  file_path?: string
  loc?: number
  cyclomatic_complexity?: number
  max_complexity?: number
  mean_complexity?: number
  community?: number
  layer?: 'Presentation' | 'Service' | 'Domain' | 'Data / Infrastructure' | 'External' | string
  risk_score?: number // 0-100
  in_degree?: number
  out_degree?: number
  centrality?: number
  pagerank?: number
  is_vulnerable?: boolean
  language?: string
  findings?: DiagnosticFinding[]
  metadata?: Record<string, unknown>
  metrics?: Record<string, unknown>
  // Simulation coordinate props
  x?: number
  y?: number
  z?: number
  vx?: number
  vy?: number
  vz?: number
}

export interface GraphEdge {
  source: string | GraphNode
  target: string | GraphNode
  edge_type: 'import' | 'inherit' | 'implement' | 'call' | string
  confidence?: 'resolved' | 'parsed' | 'ai_inferred' | string
  weight?: number
  is_cycle?: boolean
}

export interface DependencyGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export type SmellType =
  | 'god_module'
  | 'circular_import'
  | 'dead_code'
  | 'deep_inheritance'
  | 'large_class'
  | 'feature_envy'
  | 'long_parameter_list'
  | 'duplicate_code'
  | 'missing_type_hints'

export interface Smell {
  type: SmellType
  file: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  line?: number
  suggestion?: string
}

export interface Suggestion {
  title: string
  description: string
  affected_files: string[]
  effort: 'low' | 'medium' | 'high'
  impact: 'low' | 'medium' | 'high'
}

export interface HealthScoreResult {
  status: 'ok' | 'insufficient_data' | string
  score: number | null
  grade: string | null
  sub_scores?: Record<string, number>
  summary?: string | null
}

export interface AnalysisResult {
  repo_id: string
  path: string
  language: string
  node_count: number
  edge_count: number
  smells: Smell[]
  suggestions: Suggestion[]
  refactor_suggestions?: RefactorSuggestion[]
  findings?: DiagnosticFinding[]
  graph: DependencyGraph
  health?: HealthScoreResult
  source_fingerprint?: string
  commit_sha?: string
  parser_version?: string
  settings_hash?: string
  cycles?: any[]
  truncated?: boolean
  truncated_counts?: Record<string, number>
  random_seed?: number
  ambiguous_imports?: number
  files_excluded?: number
  include_tests?: boolean
  unsupported_files?: Record<string, number>
  languages?: string[]
}

export interface HealthResponse {
  status: string
  version: string
  environment: string
}

export type Language = 'auto' | 'python' | 'java'

export interface AnalyzeRequest {
  path: string
  language: Language
  include_tests?: boolean
}

export interface IngestionEvent {
  stage: string
  progress: number
  message: string
  timestamp?: string
}

export interface IngestResponse {
  job_id: string
  status: string
  message: string
  repo_id?: string
}

export type IngestionTab = 'git' | 'archive' | 'folder' | 'snippet'

export interface ReportHistoryItem {
  report_id: string
  repo_name: string
  health_score: number
  grade: string
  components: number
  dependencies: number
  critical_vulnerabilities: number
  cycles: number
  generated_at: string
}

export interface ReportHistoryResponse {
  total_reports: number
  reports: ReportHistoryItem[]
}

export interface GenerateReportPayload {
  repo_path?: string
  repo_name?: string
  format?: 'pdf' | 'html' | 'json'
  graph?: Record<string, unknown>
  query_osv?: boolean
}

export interface RecentAnalysisItem {
  id: string
  repo_name: string
  branch?: string
  commit_sha?: string | null
  created_at: string
  score?: number | null
  grade?: string | null
  include_tests?: boolean
}

// ── Phase 6 AI Types ─────────────────────────────────────────────────────────

export interface AIMetricExplanation {
  metric_name: string
  value: number
  explanation: string
  impact: string
  recommendation: string
  is_ai_generated: boolean
}

export interface AISmellFixSuggestion {
  smell_id: string
  why_it_matters: string
  fix_outline: string
  refactor_pattern: string
  is_ai_generated: boolean
}

export interface AISecurityEnrichment {
  finding_id: string
  explanation: string
  false_positive_likelihood: string
  false_positive_reason: string
  suggested_fix: string
  is_ai_generated: boolean
}

export interface AITopologySummary {
  community_id: number
  community_name: string
  description: string
  layer_explanation?: string
  verified_nodes: string[]
  is_ai_generated: boolean
}

export interface AIDashboardSummary {
  headline: string
  summary: string
  priority_actions: string[]
  is_ai_generated: boolean
}

export interface AIReportNarrative {
  executive_summary: string
  what_this_means: string
  why_it_matters: string
  what_to_do: string
  is_ai_generated: boolean
}

export interface AIChatCitation {
  node_id: string
  citation_type: string
  file_path?: string
  line_number?: number
}

export interface AIChatResponse {
  query: string
  answer: string
  citations: AIChatCitation[]
  verified: boolean
  is_ai_generated: boolean
}

export interface AINLSearchFilter {
  name_contains?: string | null
  depends_on?: string | null
  min_complexity?: number | null
  max_instability?: number | null
  smell_type?: string | null
  language?: string | null
  is_ai_generated: boolean
}

export interface AIRefactorValidationResult {
  applies_cleanly: boolean
  parses_without_syntax_errors: boolean
  target_smell_resolved: boolean
  new_cycles_introduced: number
  new_critical_findings: number
  instability_delta: number
  public_symbols_preserved: boolean
  tests_passed: boolean | null
  validation_status: string
  validation_errors: string[]
}

export interface AIRefactorProposal {
  proposal_id: string
  smell_id: string
  target_node: string
  strategy_name: string
  rationale: string
  unified_diff: string
  before_metrics?: Record<string, number>
  after_metrics?: Record<string, number>
  risk_level: string
  confidence: number
  validation: AIRefactorValidationResult
  is_ai_generated: boolean
}

export interface AIFeatureUsageSummary {
  feature_name: string
  call_count: number
  tokens_consumed: number
  cost_usd: number
}

export interface AIUsageStatistics {
  total_calls: number
  total_tokens: number
  total_cost_usd: number
  feature_breakdown: AIFeatureUsageSummary[]
  active_provider?: string
  active_model?: string
}

// ── Phase 8 Multi-Project Workspace Types ───────────────────────────────────

export interface ProjectHistoryItem {
  analysis_id: string
  created_at: string
  commit_sha: string
  status: string
  score: number
  cycles: number
  smells: number
  node_count: number
  edge_count: number
}

export interface WorkspaceProject {
  project_id: string
  name: string
  repo_url: string
  branch: string
  last_analyzed: string
  analysis_count: number
  latest_analysis_id: string
  score: number
  grade: string
  cycles: number
  smells: number
  risk_score?: number
  total_nodes: number
  total_edges: number
  languages: Record<string, number>
  history: ProjectHistoryItem[]
}

export interface AnalysisComparison {
  base_id: string
  target_id: string
  base_score: number
  target_score: number
  score_delta: number
  base_grade: string
  target_grade: string
  added_modules: string[]
  removed_modules: string[]
  modified_modules: Array<{
    id: string
    loc_before: number
    loc_after: number
    loc_delta: number
    complexity_before: number
    complexity_after: number
    complexity_delta: number
  }>
  added_edges: Array<{ source: string; target: string }>
  removed_edges: Array<{ source: string; target: string }>
  base_cycles: number
  target_cycles: number
  cycles_delta: number
  base_smells: number
  target_smells: number
  smells_delta: number
  summary: string
  is_ai_generated: boolean
}


