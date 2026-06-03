import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { postChat } from '../api/client'
import type { ChatResponse, Citation, TraceStep } from '../api/types'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface UserMessage {
  role: 'user'
  content: string
}

interface AssistantMessage {
  role: 'assistant'
  content: string
  citations: Citation[]
  trace: TraceStep[]
  intent: string
  confidence: number
}

type Message = UserMessage | AssistantMessage

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function TracePanel({ trace }: { trace: TraceStep[] }) {
  const [open, setOpen] = useState(false)
  if (!trace.length) return null
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs text-mentis-700 hover:text-mentis-900 transition-colors"
      >
        <svg
          className={`transition-transform ${open ? 'rotate-90' : ''}`}
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
        Agent trace ({trace.length} step{trace.length !== 1 ? 's' : ''})
      </button>
      {open && (
        <ol className="mt-2 space-y-1 pl-3 border-l-2 border-mentis-200">
          {trace.map((step, i) => (
            <li key={i} className="text-xs text-gray-600">
              <span className="font-medium text-mentis-700">{step.agent}:</span>{' '}
              {step.summary}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

function CitationsList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null
  return (
    <div className="mt-3">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
        Citations
      </p>
      <ul className="space-y-1.5">
        {citations.map((c) => (
          <li key={c.chunk_id} className="bg-gray-50 border border-gray-100 rounded-lg px-3 py-2">
            {c.title && (
              <p className="text-xs font-medium text-gray-700 mb-0.5">
                {c.doi ? (
                  <a
                    href={`https://doi.org/${c.doi}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-mentis-700 hover:underline"
                  >
                    {c.title}
                  </a>
                ) : (
                  c.title
                )}
              </p>
            )}
            <p className="text-xs text-gray-500 italic leading-snug">{c.snippet}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}

function AssistantBubble({ msg }: { msg: AssistantMessage }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 shadow-sm max-w-2xl">
      <div className="assistant-prose">
        <ReactMarkdown>{msg.content}</ReactMarkdown>
      </div>
      <div className="flex items-center gap-2 mt-2 text-xs text-gray-400">
        <span className="bg-gray-100 px-2 py-0.5 rounded">{msg.intent}</span>
        <span>{Math.round(msg.confidence * 100)}% confidence</span>
      </div>
      <TracePanel trace={msg.trace} />
      <CitationsList citations={msg.citations} />
    </div>
  )
}

function Spinner() {
  return (
    <svg
      className="animate-spin text-mentis-600"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="12" y1="2" x2="12" y2="6" />
      <line x1="12" y1="18" x2="12" y2="22" />
      <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
      <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
      <line x1="2" y1="12" x2="6" y2="12" />
      <line x1="18" y1="12" x2="22" y2="12" />
      <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
      <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | undefined>()
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async () => {
    const q = input.trim()
    if (!q || loading) return
    setInput('')
    textareaRef.current?.focus()

    const userMsg: UserMessage = { role: 'user', content: q }
    setMessages((prev) => [...prev, userMsg])
    setLoading(true)

    try {
      const res: ChatResponse = await postChat({
        query: q,
        conversation_id: conversationId,
      })
      setConversationId(res.conversation_id)
      const assistantMsg: AssistantMessage = {
        role: 'assistant',
        content: res.answer,
        citations: res.citations ?? [],
        trace: res.trace ?? [],
        intent: res.intent ?? 'unknown',
        confidence: res.confidence ?? 0,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      const errorMsg: AssistantMessage = {
        role: 'assistant',
        content: `Sorry, an error occurred: ${err instanceof Error ? err.message : 'Unknown error'}`,
        citations: [],
        trace: [],
        intent: 'error',
        confidence: 0,
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-400 -mt-10">
            <div className="w-14 h-14 bg-mentis-50 rounded-full flex items-center justify-center mb-4">
              <svg
                className="text-mentis-600"
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-xl font-light text-gray-600 mb-1">Ask a research question</p>
            <p className="text-sm text-gray-400 max-w-xs">
              Search your ingested papers, explore citations, or start a new research thread.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'user' ? (
              <div className="bg-mentis-600 text-white rounded-xl px-4 py-2.5 max-w-lg">
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              </div>
            ) : (
              <AssistantBubble msg={msg} />
            )}
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 shadow-sm">
              <Spinner />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="shrink-0 border-t border-gray-200 bg-white px-6 py-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex gap-2 items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a research question… (Enter to send, Shift+Enter for newline)"
              rows={2}
              className="flex-1 resize-none border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-mentis-500 focus:border-transparent leading-relaxed"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              aria-label="Send"
              className="shrink-0 w-10 h-10 flex items-center justify-center bg-mentis-600 text-white rounded-xl hover:bg-mentis-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
          {conversationId && (
            <p className="text-xs text-gray-400 mt-1.5 text-right">
              Conversation {conversationId.slice(0, 8)}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
