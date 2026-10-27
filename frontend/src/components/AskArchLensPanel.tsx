import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Sparkles, X, ChevronRight, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react'
import { AIBadge } from './ui/AILabel'
import { aiApi } from '../api/client'
import type { AIChatResponse } from '../types'

interface AskArchLensPanelProps {
  analysisId?: string
  onSelectNode?: (nodeId: string) => void
  isOpen: boolean
  onClose: () => void
}

interface MessageItem {
  id: string
  sender: 'user' | 'assistant'
  text: string
  citations?: AIChatResponse['citations']
  verified?: boolean
  isAiGenerated?: boolean
  timestamp: string
}

export function AskArchLensPanel({
  analysisId,
  onSelectNode,
  isOpen,
  onClose,
}: AskArchLensPanelProps) {
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: 'init-msg',
      sender: 'assistant',
      text: 'Ask me anything about this repository architecture. Queries are answered strictly using deterministic graph facts and must cite validated node IDs.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isAiGenerated: false,
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const query = input.trim()
    if (!query || isLoading) return

    const userMsg: MessageItem = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsLoading(true)

    try {
      const res = await aiApi.askArchLensChat(query, analysisId)
      const assistantMsg: MessageItem = {
        id: `ai-${Date.now()}`,
        sender: 'assistant',
        text: res.answer,
        citations: res.citations,
        verified: res.verified,
        isAiGenerated: res.is_ai_generated,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch {
      const fallbackMsg: MessageItem = {
        id: `err-${Date.now()}`,
        sender: 'assistant',
        text: 'AI unavailable — could not complete graph chat request. You can still inspect components directly via the graph and metrics views.',
        isAiGenerated: false,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
      setMessages((prev) => [...prev, fallbackMsg])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: 380, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 380, opacity: 0 }}
          transition={{ type: 'spring', damping: 25, stiffness: 220 }}
          className="fixed top-16 right-0 bottom-0 w-96 z-40 flex flex-col bg-[var(--surface)] border-l border-[var(--border)] shadow-2xl backdrop-blur-xl"
          data-testid="ask-archlens-panel"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-[var(--border)]">
            <div className="flex items-center gap-2">
              <Sparkles size={16} style={{ color: 'var(--accent)' }} />
              <h3 className="font-bold text-sm tracking-tight" style={{ color: 'var(--text-primary)' }}>
                Ask ArchLens
              </h3>
              <AIBadge size="xs" />
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-muted hover:text-white hover:bg-white/5 transition-colors"
              aria-label="Close Ask ArchLens"
            >
              <X size={16} />
            </button>
          </div>

          {/* Subheader info notice */}
          <div className="px-4 py-2 bg-black/20 text-[10px] font-mono text-muted border-b border-white/5">
            Deterministic retrieval engine: answers citing non-existent components are automatically rejected.
          </div>

          {/* Message List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-xs">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl p-3.5 space-y-2 ${
                    m.sender === 'user'
                      ? 'bg-[var(--accent)] text-black font-semibold'
                      : 'bg-[var(--surface-2)] text-[var(--text-primary)] border border-white/10'
                  }`}
                >
                  <p className="leading-relaxed whitespace-pre-wrap">{m.text}</p>

                  {/* Assistant footer with verified citation badge */}
                  {m.sender === 'assistant' && (
                    <div className="pt-2 border-t border-white/10 flex flex-col gap-1.5">
                      <div className="flex items-center justify-between text-[9px] text-muted">
                        <span className="flex items-center gap-1">
                          {m.verified ? (
                            <>
                              <CheckCircle2 size={10} style={{ color: 'var(--accent)' }} />
                              <span style={{ color: 'var(--accent)' }}>Citations Verified</span>
                            </>
                          ) : (
                            <>
                              <AlertCircle size={10} className="text-muted" />
                              <span>Standard Response</span>
                            </>
                          )}
                        </span>
                        {m.isAiGenerated ? (
                          <span className="text-[9px] px-1 py-0.2 rounded font-bold uppercase tracking-wider bg-[rgba(198,244,50,0.1)] text-[var(--accent)]">
                            AI-generated
                          </span>
                        ) : (
                          <span className="text-[9px] text-muted">System</span>
                        )}
                      </div>

                      {/* Clickable Citations */}
                      {m.citations && m.citations.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-1">
                          {m.citations.map((c, idx) => (
                            <button
                              key={idx}
                              onClick={() => onSelectNode?.(c.node_id)}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-mono border border-[var(--accent)]/30 hover:border-[var(--accent)] text-[var(--accent)] bg-[var(--accent)]/5 transition-colors cursor-pointer"
                              title={`Inspect cited node ${c.node_id}`}
                            >
                              <span>{c.node_id.split(/[./\\]/).pop()}</span>
                              <ChevronRight size={8} />
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
                <span className="text-[9px] text-muted mt-1 px-1">{m.timestamp}</span>
              </div>
            ))}

            {isLoading && (
              <div className="flex items-center gap-2 p-3 text-xs text-muted font-mono">
                <Loader2 size={14} className="animate-spin" style={{ color: 'var(--accent)' }} />
                <span>Querying deterministic graph facts…</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Form */}
          <form
            onSubmit={handleSend}
            className="p-3 border-t border-[var(--border)] bg-[var(--surface-2)] flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about dependencies, cycles, hotspots…"
              className="flex-1 px-3 py-2 text-xs font-mono rounded-xl bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)] placeholder-[var(--placeholder)] focus:outline-none focus:border-[var(--accent)]"
              disabled={isLoading}
              data-testid="ask-archlens-input"
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="p-2.5 rounded-xl font-bold transition-all disabled:opacity-40 cursor-pointer"
              style={{ background: 'var(--accent)', color: '#0B0D0C' }}
              aria-label="Send message"
              data-testid="ask-archlens-send-button"
            >
              <Send size={14} />
            </button>
          </form>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
