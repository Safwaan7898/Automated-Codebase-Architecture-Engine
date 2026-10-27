/**
 * AIExplainPanel – collapsible AI-generated explanation panel.
 *
 * Accepts an async `fetch` callback.  Shows a spinner while loading,
 * renders the AI content with AIBlock, and shows AIFallback on error/disabled.
 * Invariant: finding counts, scores, grades and graph structure are NEVER
 * altered by this panel — it annotates only.
 */
import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, ChevronDown, Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import { AIBlock, AIFallback, AIBadge } from './ui/AILabel'

interface AIExplainPanelProps {
  /** Label shown on the trigger button. */
  label?: string
  /** Async function that fetches AI content. Must NOT throw — return null on error. */
  fetch: () => Promise<AIPanelContent | null>
  /** If false, the panel is disabled (AI toggle off). */
  enabled?: boolean
  /** Optional CSS class on the wrapper div. */
  className?: string
}

export interface AIPanelContent {
  /** Main explanation text. */
  explanation: string
  /** Optional: fix or action text. */
  fix?: string
  /** Optional: false-positive likelihood (percentage number or label string). Only used in security context. */
  fp_likelihood?: number | string
  fp_reason?: string
  /** Optional extra fields. */
  [key: string]: unknown
}

export function AIExplainPanel({
  label = 'Explain with AI',
  fetch,
  enabled = true,
  className = '',
}: AIExplainPanelProps) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [content, setContent] = useState<AIPanelContent | null>(null)
  const [error, setError] = useState(false)

  const handleToggle = useCallback(async () => {
    if (!enabled) return
    if (open) {
      setOpen(false)
      return
    }
    setOpen(true)
    if (content !== null) return // cached
    setLoading(true)
    setError(false)
    try {
      const result = await fetch()
      setContent(result)
      if (!result) setError(true)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [open, content, fetch, enabled])

  const handleRetry = useCallback(async () => {
    setContent(null)
    setError(false)
    setLoading(true)
    try {
      const result = await fetch()
      setContent(result)
      if (!result) setError(true)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [fetch])

  if (!enabled) {
    return (
      <div className={`${className}`}>
        <button
          disabled
          className="flex items-center gap-1.5 text-[11px] text-muted cursor-not-allowed opacity-50"
          aria-label="AI explain disabled"
        >
          <Sparkles size={12} />
          {label} <span className="text-[10px]">(AI off)</span>
        </button>
      </div>
    )
  }

  return (
    <div className={className}>
      <button
        onClick={handleToggle}
        className="flex items-center gap-1.5 text-[11px] font-semibold transition-opacity hover:opacity-80"
        style={{ color: 'var(--accent)' }}
        aria-expanded={open}
        aria-label={label}
      >
        <Sparkles size={12} />
        {label}
        <ChevronDown
          size={12}
          style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            key="ai-panel"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden"
          >
            <div className="mt-2">
              {loading && (
                <div className="flex items-center gap-2 text-xs text-muted py-3">
                  <Loader2 size={14} className="animate-spin" style={{ color: 'var(--accent)' }} />
                  Generating AI explanation…
                </div>
              )}

              {!loading && error && (
                <div className="flex items-center gap-2">
                  <AIFallback message="AI unavailable — deterministic data unchanged" />
                  <button
                    onClick={handleRetry}
                    className="text-[11px] text-muted hover:text-white flex items-center gap-1"
                    aria-label="Retry AI explanation"
                  >
                    <RefreshCw size={11} /> Retry
                  </button>
                </div>
              )}

              {!loading && !error && content && (
                <AIBlock>
                  <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                    {content.explanation}
                  </p>

                  {content.fix && (
                    <div className="mt-3 pt-3" style={{ borderTop: '1px solid rgba(198,244,50,0.15)' }}>
                      <p className="text-[10px] font-bold uppercase mb-1" style={{ color: 'var(--accent)' }}>
                        Suggested Fix
                      </p>
                      <p className="text-xs leading-relaxed text-muted">{content.fix}</p>
                    </div>
                  )}

                  {content.fp_likelihood !== undefined && (
                    <div className="mt-3 flex items-start gap-2">
                      <AlertCircle
                        size={13}
                        style={{ color: 'var(--warning)', marginTop: 1 }}
                      />
                      <div>
                        <span className="text-[10px] font-bold" style={{ color: 'var(--text-muted)' }}>
                          False-positive likelihood:{' '}
                          <span style={{ color: 'var(--warning)' }}>
                            {content.fp_likelihood}
                            {typeof content.fp_likelihood === 'number' ? '%' : ''}
                          </span>
                        </span>
                        {content.fp_reason && (
                          <p className="text-[11px] text-muted mt-0.5">{content.fp_reason}</p>
                        )}
                      </div>
                    </div>
                  )}
                </AIBlock>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/**
 * AIChatMessage – renders a single Q&A pair from the Ask ArchLens panel.
 * Shows the "AI-generated" badge on every answer.
 */
export function AIChatMessage({
  question,
  answer,
  loading,
}: {
  question: string
  answer: string | null
  loading?: boolean
}) {
  return (
    <div className="space-y-2">
      <div
        className="rounded-xl px-3 py-2 text-xs max-w-[85%] ml-auto"
        style={{ background: 'var(--surface-2)', color: 'var(--text-primary)' }}
      >
        {question}
      </div>
      {loading ? (
        <div className="flex items-center gap-2 text-xs text-muted">
          <Loader2 size={12} className="animate-spin" style={{ color: 'var(--accent)' }} />
          Thinking…
        </div>
      ) : answer ? (
        <AIBlock className="max-w-[95%]">
          <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {answer}
          </p>
        </AIBlock>
      ) : (
        <AIFallback message="AI unavailable — try again or rephrase your query" />
      )}
    </div>
  )
}

/** Re-export badge for convenience */
export { AIBadge }
