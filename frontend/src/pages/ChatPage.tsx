import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { streamChat, downloadPdf } from '../api/client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ToolCall {
  name: string
  input: unknown
}

interface UserMessage {
  role: 'user'
  content: string
}

interface AssistantMessage {
  role: 'assistant'
  content: string
  tools: ToolCall[]
  status: 'streaming' | 'done' | 'error'
}

type Message = UserMessage | AssistantMessage

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const TOOL_LABELS: Record<string, string> = {
  search_literature: 'Searching literature (OpenAlex)',
  scopus_search: 'Searching Scopus',
  fetch_pdf_text: 'Reading PDF',
  verify_doi: 'Verifying DOI',
  draft_section: 'Drafting section (Claude Sonnet)',
}

function ToolCallCard({ call }: { call: ToolCall }) {
  const [open, setOpen] = useState(false)
  const label = TOOL_LABELS[call.name] ?? call.name
  return (
    <div className="mt-2 border border-mentis-100 rounded-lg bg-mentis-50/60">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-mentis-800"
      >
        <svg
          className={`transition-transform ${open ? 'rotate-90' : ''}`}
          width="11" height="11" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
        <span className="font-mono">🔧 {label}</span>
      </button>
      {open && (
        <pre className="px-3 pb-2 text-[11px] text-gray-500 whitespace-pre-wrap break-words">
          {JSON.stringify(call.input, null, 2)}
        </pre>
      )}
    </div>
  )
}

function AssistantBubble({ msg }: { msg: AssistantMessage }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 shadow-sm max-w-2xl w-full">
      {msg.tools.map((t, i) => (
        <ToolCallCard key={`${t.name}-${i}`} call={t} />
      ))}
      {msg.content && (
        <div className="assistant-prose mt-2">
          <ReactMarkdown>{msg.content}</ReactMarkdown>
        </div>
      )}
      {msg.status === 'streaming' && (
        <span className="inline-block w-2 h-4 ml-0.5 align-text-bottom bg-mentis-500 animate-pulse" />
      )}
      {msg.status === 'error' && (
        <p className="text-xs text-red-500 mt-1">stream error — see message above</p>
      )}
      {msg.status === 'done' && msg.content && (
        <div className="mt-3 pt-2 border-t border-gray-100">
          <button
            onClick={() =>
              downloadPdf(msg.content).catch((e) =>
                alert('PDF export failed: ' + (e instanceof Error ? e.message : 'error')),
              )
            }
            className="inline-flex items-center gap-1.5 text-xs text-mentis-700 hover:text-mentis-900"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Download PDF
          </button>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [conversationId, setConversationId] = useState<string | undefined>()
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Mutate the last (assistant) message in place.
  const patchLast = (fn: (m: AssistantMessage) => AssistantMessage) => {
    setMessages((prev) => {
      const next = [...prev]
      for (let i = next.length - 1; i >= 0; i--) {
        if (next[i].role === 'assistant') {
          next[i] = fn(next[i] as AssistantMessage)
          break
        }
      }
      return next
    })
  }

  const handleSend = async () => {
    const q = input.trim()
    if (!q || busy) return
    setInput('')
    textareaRef.current?.focus()

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: q },
      { role: 'assistant', content: '', tools: [], status: 'streaming' },
    ])
    setBusy(true)

    try {
      await streamChat(
        { message: q, conversation_id: conversationId },
        {
          onConversation: (id) => setConversationId(id),
          onToken: (text) => patchLast((m) => ({ ...m, content: m.content + text })),
          onToolCall: (call) => patchLast((m) => ({ ...m, tools: [...m.tools, call] })),
          onFinished: (text) =>
            patchLast((m) => ({ ...m, content: text || m.content, status: 'done' })),
          onError: (message) =>
            patchLast((m) => ({
              ...m,
              content: m.content + `\n\n> **Error:** ${message}`,
              status: 'error',
            })),
        },
      )
    } catch (err) {
      patchLast((m) => ({
        ...m,
        content: m.content + `\n\n> **Error:** ${err instanceof Error ? err.message : 'request failed'}`,
        status: 'error',
      }))
    } finally {
      setBusy(false)
      patchLast((m) => (m.status === 'streaming' ? { ...m, status: 'done' } : m))
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
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-400 -mt-10">
            <div className="w-14 h-14 bg-mentis-50 rounded-full flex items-center justify-center mb-4">
              <svg className="text-mentis-600" width="28" height="28" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-xl font-light text-gray-600 mb-1">Research &amp; draft a whitepaper</p>
            <p className="text-sm text-gray-400 max-w-sm">
              e.g. <span className="italic">"Draft an introduction on CO₂ absorption in biobased solvents"</span> —
              watch the agents search, verify, and write underneath.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'user' ? (
              <div className="bg-mentis-600 text-white rounded-xl px-4 py-2.5 max-w-lg">
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              </div>
            ) : (
              <AssistantBubble msg={msg} />
            )}
          </div>
        ))}

        <div ref={bottomRef} />
      </div>

      <div className="shrink-0 border-t border-gray-200 bg-white px-6 py-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex gap-2 items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask Mentis to research or draft… (Enter to send, Shift+Enter for newline)"
              rows={2}
              className="flex-1 resize-none border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-mentis-500 focus:border-transparent leading-relaxed"
            />
            <button
              onClick={handleSend}
              disabled={busy || !input.trim()}
              aria-label="Send"
              className="shrink-0 w-10 h-10 flex items-center justify-center bg-mentis-600 text-white rounded-xl hover:bg-mentis-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
