import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  ArrowUp,
  AlertTriangle,
  BadgeCheck,
  ChevronRight,
  FileDown,
  FileSearch,
  FileText,
  GraduationCap,
  Library,
  Loader2,
  PenLine,
  Telescope,
  UploadCloud,
  Wrench,
  type LucideIcon,
} from 'lucide-react'
import { API_BASE_URL, streamChat, downloadDocument, uploadFiles } from '../api/client'
import type { Citation } from '../api/types'

// Resolve relative workspace image/file URLs (e.g. "/projects/<id>/files/<n>")
// against the API origin so figures the Analyst produced render in the transcript.
const MD_COMPONENTS = {
  img: ({ src = '', alt = '' }: { src?: string; alt?: string }) => (
    <img
      src={src.startsWith('/') ? `${API_BASE_URL}${src}` : src}
      alt={alt}
      className="my-3 rounded-md border border-stone-200 dark:border-stone-800 max-w-full"
    />
  ),
}

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

export type Message = UserMessage | AssistantMessage

// ---------------------------------------------------------------------------
// Agent activity / icons
// ---------------------------------------------------------------------------

const TOOL_ACTIVITY: Record<string, string> = {
  research: 'Researching sources',
  search_literature: 'Researching the literature',
  scopus_search: 'Searching Scopus',
  fetch_pdf_text: 'Reading a paper',
  verify_doi: 'Verifying a DOI',
  draft_section: 'Drafting',
}

const TOOL_LABELS: Record<string, string> = {
  research: 'Researched & curated sources',
  search_literature: 'Searched literature (OpenAlex)',
  scopus_search: 'Searched Scopus',
  fetch_pdf_text: 'Read PDF',
  verify_doi: 'Verified DOI',
  draft_section: 'Drafted section',
}

const TOOL_ICON: Record<string, LucideIcon> = {
  research: Telescope,
  search_literature: Library,
  scopus_search: GraduationCap,
  fetch_pdf_text: FileText,
  verify_doi: BadgeCheck,
  draft_section: PenLine,
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ActivityLine({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 mb-2.5 text-stone-500 dark:text-stone-400">
      <Loader2 size={13} className="animate-spin text-mentis-600 dark:text-mentis-400" />
      <span className="font-mono text-[0.7rem] uppercase tracking-[0.12em]">{label}</span>
    </div>
  )
}

function ToolTimeline({ tools }: { tools: ToolCall[] }) {
  const [open, setOpen] = useState(false)
  if (!tools.length) return null
  return (
    <div className="mt-3">
      <button onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 font-mono text-[0.7rem] text-stone-400 hover:text-stone-600 dark:hover:text-stone-300">
        <ChevronRight size={12} className={`transition-transform ${open ? 'rotate-90' : ''}`} />
        {tools.length} step{tools.length !== 1 ? 's' : ''}
      </button>
      {open && (
        <ol className="mt-2 space-y-1.5 pl-3 border-l border-stone-200 dark:border-stone-700">
          {tools.map((t, i) => {
            const Icon = TOOL_ICON[t.name] ?? Wrench
            return (
              <li key={i} className="flex items-center gap-2 text-[0.78rem] text-stone-600 dark:text-stone-400">
                <Icon size={13} className="text-mentis-600 dark:text-mentis-400 shrink-0" />
                {TOOL_LABELS[t.name] ?? t.name}
              </li>
            )
          })}
        </ol>
      )}
    </div>
  )
}

function SourcesSummary({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null
  const backed = citations.filter((c) => c.supported === true).length
  const flagged = citations.filter((c) => c.supported === false)
  const unverifiable = citations.filter((c) => c.supported !== true && c.supported !== false)
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-3 font-mono text-[0.7rem]">
      <span className="inline-flex items-center gap-1 text-mentis-700 dark:text-mentis-400">
        <BadgeCheck size={13} /> {backed}/{citations.length} backed by source
      </span>
      {flagged.length > 0 && (
        <span className="inline-flex items-center gap-1 text-amber-600">
          <AlertTriangle size={12} /> {flagged.length} unsupported ({flagged.map((c) => `[${c.n}]`).join(' ')})
        </span>
      )}
      {unverifiable.length > 0 && (
        <span className="text-stone-400">{unverifiable.length} not auto-verified</span>
      )}
    </div>
  )
}

function AssistantBubble({ msg }: { msg: AssistantMessage }) {
  return (
    <div className="max-w-2xl w-full rounded-lg border border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900 px-5 py-4">
      {msg.status === 'streaming' && <ActivityLine label={msg.activity || 'Working'} />}
      {msg.content && (
        <div className="assistant-prose">
          <ReactMarkdown components={MD_COMPONENTS}>{msg.content}</ReactMarkdown>
        </div>
      )}
      <ToolTimeline tools={msg.tools} />
      {msg.status === 'done' && <SourcesSummary citations={msg.citations} />}
      {msg.status === 'done' && msg.content && (
        <div className="mt-3 pt-3 border-t border-stone-100 dark:border-stone-800 flex gap-5">
          {(['pdf', 'docx'] as const).map((fmt) => (
            <button key={fmt}
              onClick={() => downloadDocument(msg.content, fmt).catch((e) =>
                alert('Export failed: ' + (e instanceof Error ? e.message : 'error')))}
              className="inline-flex items-center gap-1.5 text-xs text-stone-500 hover:text-mentis-700 dark:hover:text-mentis-300">
              <FileDown size={14} />
              {fmt === 'pdf' ? 'PDF' : 'Word'}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ChatPage({
  conversationId,
  initialMessages,
  onTitle,
  projectId,
  onFilesChanged,
}: {
  conversationId: string
  initialMessages: Message[]
  onTitle?: (conversationId: string, title: string) => void
  projectId?: string
  onFilesChanged?: () => void
}) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [input, setInput] = useState('')
  const [working, setWorking] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState<string | null>(null)
  const convIdRef = useRef<string>(conversationId)
  const runningRef = useRef(false)
  const queueRef = useRef<string[]>([])
  const dragDepth = useRef(0)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleFiles = async (files: File[]) => {
    if (!projectId || !files.length) return
    setUploading(files.length === 1 ? files[0].name : `${files.length} files`)
    try {
      await uploadFiles(projectId, files)
      onFilesChanged?.()
    } catch (e) {
      alert('Upload failed: ' + (e instanceof Error ? e.message : 'error'))
    } finally {
      setUploading(null)
    }
  }

  const onDragEnter = (e: React.DragEvent) => {
    if (!e.dataTransfer.types.includes('Files') || !projectId) return
    e.preventDefault()
    dragDepth.current += 1
    setDragging(true)
  }
  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    dragDepth.current -= 1
    if (dragDepth.current <= 0) setDragging(false)
  }
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    dragDepth.current = 0
    setDragging(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length) handleFiles(files)
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
          onConversation: (info) => {
            convIdRef.current = info.conversationId
            if (info.title) onTitle?.(info.conversationId, info.title)
          },
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
      onFilesChanged?.() // a run may have produced figures/data in the workspace
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
    <div
      className="relative flex flex-col h-full"
      onDragEnter={onDragEnter}
      onDragOver={(e) => { if (dragging) e.preventDefault() }}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {dragging && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-mentis-50/90 dark:bg-stone-900/90 border-2 border-dashed border-mentis-400 dark:border-mentis-600 pointer-events-none">
          <UploadCloud size={34} className="text-mentis-600 dark:text-mentis-400 mb-3" />
          <p className="font-serif text-lg text-stone-700 dark:text-stone-200">Drop files to add to this project</p>
          <p className="text-sm text-stone-500 dark:text-stone-400 mt-1">Spreadsheets, CSVs, images — the Analyst can read them</p>
        </div>
      )}
      {uploading && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2 rounded-full bg-stone-900 text-stone-100 px-4 py-1.5 text-xs shadow-lg">
          <Loader2 size={13} className="animate-spin" /> Uploading {uploading}…
        </div>
      )}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="max-w-3xl mx-auto space-y-5">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center text-center pt-24">
              <div className="w-12 h-12 rounded-full bg-mentis-50 dark:bg-stone-800 flex items-center justify-center mb-5">
                <FileSearch size={22} className="text-mentis-600 dark:text-mentis-400" />
              </div>
              <p className="font-serif text-2xl text-stone-700 dark:text-stone-200 mb-2">Research &amp; draft a whitepaper</p>
              <p className="text-sm text-stone-500 dark:text-stone-400 max-w-md leading-relaxed">
                e.g. <span className="italic">“Draft an introduction on CO₂ absorption in biobased solvents.”</span>{' '}
                Watch the agents research and write beneath your message — you can keep typing while they work.
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'user' ? (
                <div className="max-w-lg rounded-lg bg-mentis-600 text-white px-4 py-2.5">
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                </div>
              ) : (
                <AssistantBubble msg={msg} />
              )}
            </div>
          ))}

          <div ref={bottomRef} />
        </div>
      </div>

      <div className="shrink-0 border-t border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900 px-6 py-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex gap-2 items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask Mentis to research or draft…  (Enter to send — you can keep sending while it works)"
              rows={2}
              className="flex-1 resize-none rounded-lg border border-stone-300 dark:border-stone-700 bg-stone-50 dark:bg-stone-800 text-stone-800 dark:text-stone-100 placeholder-stone-400 px-4 py-2.5 text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-mentis-500/40 focus:border-mentis-500"
            />
            <button onClick={handleSend} disabled={!input.trim()} aria-label="Send"
              className="shrink-0 w-10 h-10 flex items-center justify-center bg-mentis-600 text-white rounded-lg hover:bg-mentis-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
              <ArrowUp size={18} />
            </button>
          </div>
          <div className="mt-1.5 font-mono text-[0.65rem] uppercase tracking-wider text-stone-400">
            {working ? 'Working — you can still send' : ''}
            {queueRef.current.length > 0 ? `  ·  ${queueRef.current.length} queued` : ''}
          </div>
        </div>
      </div>
    </div>
  )
}
