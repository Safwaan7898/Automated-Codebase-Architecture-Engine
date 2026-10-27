import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import type { AnalysisResult, GraphNode, RecentAnalysisItem } from '../types'
import { generateSampleDataset } from '../utils/sampleData'
import { api } from '../api/client'

interface AnalysisContextType {
  result: AnalysisResult | null
  setResult: (res: AnalysisResult | null) => void
  selectedNode: GraphNode | null
  setSelectedNode: (node: GraphNode | null) => void
  activeDataset: 'live' | 'flask' | 'spring' | 'vulnerable' | 'custom'
  isLiveAnalysis: boolean
  loadSample: (type: 'flask' | 'spring' | 'vulnerable') => void
  loadRepoGraph: (repoId: string) => Promise<void>
  analyzeLiveCodebase: (path: string, language?: string, includeTests?: boolean) => Promise<AnalysisResult>
  pollIngestJob: (jobId: string, onProgress?: (msg: string, pct: number) => void) => Promise<AnalysisResult | null>
  repoList: string[]
  recentAnalyses: RecentAnalysisItem[]
  refreshRepoList: () => Promise<void>
  loading: boolean
  error: string | null
  setError: (err: string | null) => void
  notFoundId: string | null
  setNotFoundId: (id: string | null) => void
  lastIngestError: { error: string; metadata?: any } | null
  setLastIngestError: (info: { error: string; metadata?: any } | null) => void
  clearAnalysis: () => void
}

const AnalysisContext = createContext<AnalysisContextType | undefined>(undefined)

/** Infer clean architectural layers for real AST parsed nodes */
function inferLayer(nodeId: string, filePath?: string): 'Presentation' | 'Service' | 'Domain' | 'Data / Infrastructure' {
  const target = `${nodeId} ${filePath || ''}`.toLowerCase()
  if (/api|route|view|controller|endpoint|blueprint|web|cli|docs|app\.py|main\.py/.test(target)) {
    return 'Presentation'
  }
  if (/service|task|handler|manager|job|processor|workflow|engine|analyzer|runner/.test(target)) {
    return 'Service'
  }
  if (/repo|store|storage|db|database|sql|cache|network|http|source|client|util|helper/.test(target)) {
    return 'Data / Infrastructure'
  }
  return 'Domain'
}

/** Enriches raw backend AST result into full-featured topology graph */
function enrichAnalysisResult(data: any): AnalysisResult {
  if (!data || !data.graph) return data
  const rawNodes = data.graph?.nodes ?? []
  const rawEdges = data.graph?.edges ?? []

  // Calculate in-degree & out-degree
  const inDegreeMap = new Map<string, number>()
  const outDegreeMap = new Map<string, number>()
  rawEdges.forEach((e: any) => {
    const s = typeof e.source === 'string' ? e.source : e.source?.id
    const t = typeof e.target === 'string' ? e.target : e.target?.id
    if (s) outDegreeMap.set(s, (outDegreeMap.get(s) || 0) + 1)
    if (t) inDegreeMap.set(t, (inDegreeMap.get(t) || 0) + 1)
  })

  // Community clusters based on namespace packages
  const pkgMap = new Map<string, number>()
  let communityCounter = 0

  const enrichedNodes = rawNodes.map((n: any) => {
    const pkg = (n.id || '').split('.')[0] || 'default'
    if (!pkgMap.has(pkg)) {
      pkgMap.set(pkg, communityCounter++)
    }
    const community = n.community ?? pkgMap.get(pkg) ?? 0
    const in_degree = n.in_degree ?? (inDegreeMap.get(n.id) || 0)
    const out_degree = n.out_degree ?? (outDegreeMap.get(n.id) || 0)
    const totalNodes = Math.max(1, rawNodes.length)
    const centrality = n.centrality ?? Math.min(1, (in_degree + out_degree) / Math.max(5, totalNodes * 0.1))
    const layer = n.layer || inferLayer(n.id, n.file_path)

    // Check if node matches any detected smells
    const matchingSmells = (data.smells || []).filter((s: any) =>
      s.file && (n.file_path?.includes(s.file) || s.file.includes(n.label || n.id))
    )
    const is_vulnerable = n.is_vulnerable || matchingSmells.length > 0 || (n.risk_score ?? 0) >= 60
    const risk_score = n.risk_score ?? (is_vulnerable ? Math.min(95, 60 + matchingSmells.length * 15) : 15)

    return {
      ...n,
      label: n.label || n.id.split('.').pop() || n.id,
      layer,
      community,
      in_degree,
      out_degree,
      centrality,
      risk_score,
      is_vulnerable,
      language: n.language || 'unknown',
      loc: n.loc ?? 0,
    }
  })

  // Clean edges
  const enrichedEdges = rawEdges.map((e: any) => ({
    source: typeof e.source === 'string' ? e.source : e.source?.id,
    target: typeof e.target === 'string' ? e.target : e.target?.id,
    edge_type: e.edge_type || 'import',
    confidence: e.confidence || 'resolved',
    is_cycle: Boolean(e.is_cycle),
    weight: e.weight ?? 1.0,
  }))

  // Map backend suggestions to frontend refactor_suggestions
  const rawSuggestions = (data.refactor_suggestions && data.refactor_suggestions.length > 0)
    ? data.refactor_suggestions
    : (data.suggestions || [])

  const refactor_suggestions = rawSuggestions.map((s: any, idx: number) => ({
    id: s.id || `refactor-${idx + 1}`,
    type: s.type || 'break_cycle',
    title: s.title || `Refactor ${s.affected_nodes?.[0] || s.affected_files?.[0] || 'Module'}`,
    rationale: s.rationale || s.description || 'Improve modularity and decrease architectural coupling.',
    affected_nodes: s.affected_nodes || s.affected_files || [],
    effort: (s.effort === 'high' || s.effort === 'L') ? 'L' : (s.effort === 'medium' || s.effort === 'M') ? 'M' : 'S',
    priority_score: s.priority_score ?? 80,
    impact_before: s.impact_before || s.metrics?.before,
    impact_after: s.impact_after || s.metrics?.after,
    diff_preview: s.diff_preview || s.diff,
  }))

  const findings = (data.smells || []).map((s: any, idx: number) => ({
    id: `smell-${idx + 1}`,
    rule_id: s.type || 'ARCH-001',
    title: s.description || `${s.type} architectural smell detected`,
    severity: s.severity || 'medium',
    category: 'Architecture',
    file_path: s.file || '',
    line_number: s.line || 1,
    remediation: s.suggestion || 'Refactor module to adhere to clean architecture layering.',
  }))

  return {
    ...data,
    refactor_suggestions,
    findings: data.findings?.length ? data.findings : findings,
    graph: {
      nodes: enrichedNodes,
      edges: enrichedEdges,
    },
  }
}

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const location = useLocation()
  const [result, setResultState] = useState<AnalysisResult | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [activeDataset, setActiveDataset] = useState<'live' | 'flask' | 'spring' | 'vulnerable' | 'custom'>('live')
  const [isLiveAnalysis, setIsLiveAnalysis] = useState(false)
  const [repoList, setRepoList] = useState<string[]>([])
  const [recentAnalyses, setRecentAnalyses] = useState<RecentAnalysisItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notFoundId, setNotFoundId] = useState<string | null>(null)
  const [lastIngestError, setLastIngestError] = useState<{ error: string; metadata?: any } | null>(null)

  const syncAnalysisId = useCallback((id: string) => {
    if (!id || typeof window === 'undefined') return
    try {
      const url = new URL(window.location.href)
      if (url.searchParams.get('analysis') !== id) {
        url.searchParams.set('analysis', id)
        window.history.replaceState({}, '', url.toString())
      }
    } catch {
      // ignore
    }
  }, [])

  const setResult = useCallback((res: AnalysisResult | null) => {
    if (res) {
      setResultState(enrichAnalysisResult(res))
      setNotFoundId(null)
      setLastIngestError(null)
      if (res.repo_id) {
        syncAnalysisId(res.repo_id)
      }
    } else {
      setResultState(null)
    }
  }, [syncAnalysisId])

  const clearAnalysis = useCallback(() => {
    setResultState(null)
    setSelectedNode(null)
    setNotFoundId(null)
    setLastIngestError(null)
    setError(null)
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href)
      url.searchParams.delete('analysis')
      window.history.replaceState({}, '', url.toString())
    }
  }, [])

  const loadSample = useCallback((type: 'flask' | 'spring' | 'vulnerable') => {
    const data = generateSampleDataset(type)
    setResult(data)
    setSelectedNode(null)
    setActiveDataset(type)
    setIsLiveAnalysis(false)
    setError(null)
    setNotFoundId(null)
  }, [setResult])

  const refreshRepoList = useCallback(async () => {
    try {
      const res = await api.listGraphs()
      if (res?.repo_ids) {
        setRepoList(res.repo_ids)
      }
      if (res?.items) {
        setRecentAnalyses(res.items)
      }
    } catch {
      // Backend offline or empty
    }
  }, [])

  const analyzeLiveCodebase = useCallback(
    async (path: string, language = 'auto', includeTests = false): Promise<AnalysisResult> => {
      setLoading(true)
      setError(null)
      setNotFoundId(null)
      try {
        // POST /analyze triggers real-time AST parsing on backend
        const rawData = await api.analyze({ path, language: language as 'auto' | 'python' | 'java', include_tests: includeTests })
        const enriched = enrichAnalysisResult(rawData)
        setResultState(enriched)
        setSelectedNode(null)
        setActiveDataset('live')
        setIsLiveAnalysis(true)
        if (rawData?.repo_id) {
          syncAnalysisId(rawData.repo_id)
        }
        await refreshRepoList()
        return enriched
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Live analysis failed. Please verify the workspace path.'
        setError(msg)
        throw err
      } finally {
        setLoading(false)
      }
    },
    [refreshRepoList, syncAnalysisId]
  )

  const pollIngestJob = useCallback(
    async (
      jobId: string,
      onProgress?: (msg: string, pct: number) => void
    ): Promise<AnalysisResult | null> => {
      const maxAttempts = 60
      let attempts = 0

      while (attempts < maxAttempts) {
        attempts++
        try {
          const jobData = (await api.getJobStatus(jobId)) as {
            status?: string
            result?: AnalysisResult
            error?: string
            metadata?: { total_files?: number; processed_files?: number; language_breakdown?: Record<string, number>; primary_language?: string; file_count?: number }
          }

          if ((jobData.status === 'completed' || jobData.status === 'complete') && jobData.result) {
            const enriched = enrichAnalysisResult(jobData.result)
            setResultState(enriched)
            setSelectedNode(null)
            setActiveDataset('live')
            setIsLiveAnalysis(true)
            setNotFoundId(null)
            setLastIngestError(null)
            syncAnalysisId(jobId)
            if (onProgress) onProgress('Analysis complete!', 100)
            return enriched
          }

          if (jobData.status === 'failed') {
            const failMsg = jobData.error || 'Ingestion job reported a failure.'
            setLastIngestError({ error: failMsg, metadata: jobData.metadata })
            throw new Error(failMsg)
          }

          if ((jobData.status === 'completed' || jobData.status === 'complete') && !jobData.result) {
            const noFilesMsg = jobData.error || 'No Python or Java files found in the ingested repository.'
            setLastIngestError({ error: noFilesMsg, metadata: jobData.metadata })
            throw new Error(noFilesMsg)
          }

          // Compute approximate progress
          const pct = Math.min(95, 20 + attempts * 5)
          if (onProgress) onProgress(`Processing files... (job status: ${jobData.status})`, pct)

          // Wait 1 second before next poll
          await new Promise((r) => setTimeout(r, 1000))
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : ''
          if (msg && !msg.includes('Network Error') && !msg.includes('status code')) {
            throw err
          }
          if (attempts >= maxAttempts) throw err
          await new Promise((r) => setTimeout(r, 1000))
        }
      }

      throw new Error('Ingestion job timed out after 60 seconds.')
    },
    [syncAnalysisId]
  )

  const loadRepoGraph = useCallback(
    async (repoId: string) => {
      setLoading(true)
      setError(null)
      setNotFoundId(null)
      try {
        const rawData = await api.getGraph(repoId)
        const enriched = enrichAnalysisResult(rawData)
        setResultState(enriched)
        setSelectedNode(null)
        setActiveDataset('custom')
        setIsLiveAnalysis(true)
        syncAnalysisId(repoId)
      } catch (err: unknown) {
        setNotFoundId(repoId)
        setResultState(null)
        const msg = err instanceof Error ? err.message : `Failed to fetch graph '${repoId}' from backend`
        setError(msg)
      } finally {
        setLoading(false)
      }
    },
    [syncAnalysisId]
  )

  const urlAnalysisId = useMemo(() => {
    return new URLSearchParams(location.search).get('analysis')
  }, [location.search])

  // Sync state with ?analysis=<id> from URL:
  // ONLY load if ?analysis=<id> is in URL.
  // Never auto-fetch res.repo_ids[0] or restore stale sessionStorage.
  useEffect(() => {
    let isMounted = true

    if (urlAnalysisId) {
      if (urlAnalysisId !== result?.repo_id) {
        api.getGraph(urlAnalysisId)
          .then((rawData) => {
            if (isMounted && rawData?.graph?.nodes?.length > 0) {
              const enriched = enrichAnalysisResult(rawData)
              setResultState(enriched)
              setActiveDataset('live')
              setIsLiveAnalysis(true)
              setNotFoundId(null)
            } else if (isMounted) {
              setNotFoundId(urlAnalysisId)
              setResultState(null)
            }
          })
          .catch(() => {
            if (isMounted) {
              setNotFoundId(urlAnalysisId)
              setResultState(null)
              setError(`Analysis '${urlAnalysisId}' not found.`)
            }
          })
      }
    } else {
      // Clean start or clean navigation: if not live/sample in memory, clear notFoundId
      if (isMounted && notFoundId) {
        setNotFoundId(null)
      }
    }

    return () => {
      isMounted = false
    }
  }, [urlAnalysisId, result?.repo_id, notFoundId])

  useEffect(() => {
    refreshRepoList()
  }, [refreshRepoList])

  return (
    <AnalysisContext.Provider
      value={{
        result,
        setResult,
        selectedNode,
        setSelectedNode,
        activeDataset,
        isLiveAnalysis,
        loadSample,
        loadRepoGraph,
        analyzeLiveCodebase,
        pollIngestJob,
        repoList,
        recentAnalyses,
        refreshRepoList,
        loading,
        error,
        setError,
        notFoundId,
        setNotFoundId,
        lastIngestError,
        setLastIngestError,
        clearAnalysis,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  )
}

export function useAnalysisContext() {
  const ctx = useContext(AnalysisContext)
  if (!ctx) throw new Error('useAnalysisContext must be used within an AnalysisProvider')
  return ctx
}
