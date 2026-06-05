import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { streamChat, downloadPdf } from '../api/client'
import type { Citation } from '../api/types'

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
  citations: Citation[]
  activity?: string
  status: 'streaming' | 'done' | 'error'
}

type Message = UserMessage | AssistantMessage

// ---------------------------------------------------------------------------
// Activity labels (Claude Code-style "what it's doing now")
// ---------------------------------------------------------------------------

const TOOL_ACTIVITY: Record<string, string> = {
  search_literature: 'Researching the literature',
  scopus_search: 'Searching Scopus',
  fetch_pdf_text: 'Reading a paper',
  verify_doi: 'Verifying a DOI',
  draft_section: 'Drafting the section',
}

const TOOL_LABELS: Record<string, string> = {
  search_literature: 'Searched literature (OpenAlex)',
  scopus_search: 'Searched Scopus',
  fetch_pdf_text: 'Read PDF',
  verify_doi: 'Verified DOI',
  draft_section: 'Drafted section',
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ActivityLine({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-mentis-700 mb-2">
      <span className="flex gap-0.5">
        <span className="w-1.5 h-1.5 rounded-full bg-mentis-500 animate-bounce [animation-delay:-0.3s]" />
        <span className="w-1.5 h-1.5 rounded-full bg-mentis-500 animate-bounce [animation-delay:-0.15s]" />
        <span className="w-1.5 h-1.5 rounded-full bg-mentis-500 animate-bounce" />
      </span>
      <span className="italic">{label}…</span>
    </div>
  )
}

function ToolTimeline({ tools }: { tools: ToolCall[] }) {
  const [open, setOpen] = useState(false)
  if (!tools.length) return null
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700"
      >
        <svg className={`transition-transform ${open ? 'rotate-90' : ''}`} width="11" height="11"
          viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
          strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
        {tools.length} step{tools.length !== 1 ? 's' : ''}
      </button>
      {open && (
        <ol className="mt-1.5 space-y-1 pl-3 border-l-2 border-mentis-100">
          {tools.map((t, i) => (
            <li key={i} className="text-xs text-gray-600">
              <span className="font-mono text-mentis-700">🔧 {TOOL_LABELS[t.name] ?? t.name}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

function SourcesSummary({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null
  const verified = citations.filter((c) => c.verified).length
  const flagged = citations.filter((c) => !c.verified)
  return (
    <p className="text-xs text-gray-500 mt-2">
      <span className="text-mentis-700 font-medium">✓ {verified}/{citations.length} sources verified</span>
      {flagged.length > 0 && (
        <span className="text-amber-600"> · {flagged.length} unverified ({flagged.map((c) => `[${c.n}]`).join(' ')})</span>
      )}
    </p>
  )
}

function AssistantBubble({ msg }: { msg: AssistantMessage }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 shadow-sm max-w-2xl w-full">
      {msg.status === 'streaming' && <ActivityLine label={msg.activity || 'Working'} />}
      {msg.content && (
        <div className="assistant-prose">
          <ReactMarkdown>{msg.content}</ReactMarkdown>
        </div>
      )}
      <ToolTimeline tools={msg.tools} />
      {msg.status === 'done' && <SourcesSummary citations={msg.citations} />}
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
  const [working, setWorking] = useState(false)
  const [conversationId, setConversationId] = useState<string | undefined>()
  const convIdRef = useRef<string | undefined>(undefined)
  const runningRef = useRef(false)
  const queueRef = useRef<string[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Update the most recent assistant message in place.
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

  // Process the queue one run at a time (sequential — safe for the shared collector).
  const pump = async () => {
    if (runningRef.current) return
    const q = queueRef.current.shift()
    if (q === undefined) return
    runningRef.current = true
    setWorking(true)
    setMessages((prev) => [
      ...prev,
      { role: 'assistant', content: '', tools: [], citations: [], activity: 'Thinking', status: 'streaming' },
    ])
    try {
      await streamChat(
        { message: q, conversation_id: convIdRef.current },
        {
          onConversation: (id) => { convIdRef.current = id; setConversationId(id) },
          onToken: (t) => patchLast((m) => ({ ...m, content: m.content + t, activity: 'Writing' })),
          onToolCall: (c) =>
            patchLast((m) => ({ ...m, tools: [...m.tools, c], activity: TOOL_ACTIVITY[c.name] ?? 'Working' })),
          onStatus: (label) => patchLast((m) => ({ ...m, activity: label })),
          onCitations: (items) => patchLast((m) => ({ ...m, citations: items })),
          onFinished: (txt) =>
            patchLast((m) => ({ ...m, content: txt || m.content, status: 'done', activity: undefined })),
          onError: (msg) =>
            patchLast((m) => ({
              ...m,
              content: m.content + `\n\n> **Error:** ${msg}`,
              status: 'error',
              activity: undefined,
            })),
        },
      )
    } catch (e) {
      patchLast((m) => ({
        ...m,
        content: m.content + `\n\n> **Error:** ${e instanceof Error ? e.message : 'request failed'}`,
        status: 'error',
        activity: undefined,
      }))
    } finally {
      runningRef.current = false
      patchLast((m) => (m.status === 'streaming' ? { ...m, status: 'done', activity: undefined } : m))
      if (queueRef.current.length > 0) pump()
      else setWorking(false)
    }
  }

  const handleSend = () => {
    const q = input.trim()
    if (!q) return
    setInput('')
    textareaRef.current?.focus()
    setMessages((prev) => [...prev, { role: 'user', content: q }])
    queueRef.current.push(q)
    pump()
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
              watch it research and write underneath. You can keep typing while it works.
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
              placeholder="Ask Mentis to research or draft… (Enter to send — you can keep sending while it works)"
              rows={2}
              className="flex-1 resize-none border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-mentis-500 focus:border-transparent leading-relaxed"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim()}
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
          <div className="flex justify-between mt-1.5 text-xs text-gray-400">
            <span>{working ? 'Working — you can still send' : ''}{queueRef.current.length > 0 ? ` · ${queueRef.current.length} queued` : ''}</span>
            {conversationId && <span>Conversation {conversationId.slice(0, 8)}</span>}
          </div>
        </div>
      </div>
    </div>
  )
}
