import { useState, useCallback } from 'react'
import { api } from '../api/client'
import type { AnalysisResult, Language } from '../types'

export interface UseAnalysisReturn {
  result: AnalysisResult | null
  loading: boolean
  error: string | null
  analyze: (path: string, language: Language) => Promise<void>
  reset: () => void
}

export function useAnalysis(): UseAnalysisReturn {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const analyze = useCallback(async (path: string, language: Language) => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await api.analyze({ path, language })
      setResult(data)
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } }; message: string }
        setError(axiosErr.response?.data?.detail ?? axiosErr.message)
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('An unexpected error occurred.')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return { result, loading, error, analyze, reset }
}
