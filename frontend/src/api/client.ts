import type {
  Conversation,
  HealthResponse,
  LibrarySource,
  Project,
  StoredMessage,
  StreamCallbacks,
} from './types'

// ---------------------------------------------------------------------------
// Config — read once from env at module load time
// ---------------------------------------------------------------------------

const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ??
  'http://localhost:8080'
const API_KEY = import.meta.env.VITE_API_KEY as string | undefined

function headers(extra?: Record<string, string>): HeadersInit {
  const h: Record<string, string> = { 'Content-Type': 'application/json' }
  if (API_KEY) h['x-api-key'] = API_KEY
  return { ...h, ...extra }
}

async function jreq<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers: headers(init?.headers as Record<string, string>) })
  if (!res.ok) throw new Error(`${res.status}: ${await res.text().catch(() => res.statusText)}`)
  return res.json() as Promise<T>
}

export function getHealth(): Promise<HealthResponse> {
  return jreq<HealthResponse>('/health')
}

// --- projects / conversations / library ---

export function listProjects(): Promise<{ projects: Project[] }> {
  return jreq('/projects')
}

export function createProject(name: string): Promise<Project> {
  return jreq('/projects', { method: 'POST', body: JSON.stringify({ name }) })
}

export function updateBrief(projectId: string, brief: string): Promise<Project> {
  return jreq(`/projects/${projectId}`, { method: 'PATCH', body: JSON.stringify({ brief }) })
}

export function renameProject(projectId: string, name: string): Promise<Project> {
  return jreq(`/projects/${projectId}`, { method: 'PATCH', body: JSON.stringify({ name }) })
}

export function deleteProject(projectId: string): Promise<{ ok: boolean }> {
  return jreq(`/projects/${projectId}`, { method: 'DELETE' })
}

export function renameConversation(conversationId: string, title: string): Promise<Conversation> {
  return jreq(`/conversations/${conversationId}`, { method: 'PATCH', body: JSON.stringify({ title }) })
}

export function deleteConversation(conversationId: string): Promise<{ ok: boolean }> {
  return jreq(`/conversations/${conversationId}`, { method: 'DELETE' })
}

export function listConversations(projectId: string): Promise<{ conversations: Conversation[] }> {
  return jreq(`/projects/${projectId}/conversations`)
}

export function createConversation(projectId: string, title?: string): Promise<Conversation> {
  return jreq(`/projects/${projectId}/conversations`, {
    method: 'POST',
    body: JSON.stringify({ title }),
  })
}

export function getConversationMessages(
  conversationId: string,
): Promise<{ id: string; title: string; messages: StoredMessage[] }> {
  return jreq(`/conversations/${conversationId}`)
}

export function getLibrary(projectId: string): Promise<{ sources: LibrarySource[] }> {
  return jreq(`/projects/${projectId}/library`)
}

// ---------------------------------------------------------------------------
// Streaming chat (SSE) — Claude Code-style transcript
// ---------------------------------------------------------------------------

function dispatchFrame(frame: string, cb: StreamCallbacks): void {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }
  if (!dataLines.length) return
  let data: any
  try {
    data = JSON.parse(dataLines.join('\n'))
  } catch {
    return
  }
  switch (event) {
    case 'conversation':
      cb.onConversation?.({
        conversationId: data.conversation_id,
        projectId: data.project_id,
        title: data.title,
      })
      break
    case 'token':
      cb.onToken?.(data.text ?? '')
      break
    case 'tool_call':
      cb.onToolCall?.({ name: data.name, input: data.input })
      break
    case 'status':
      cb.onStatus?.(data.label ?? '')
      break
    case 'citations':
      cb.onCitations?.(data.items ?? [])
      break
    case 'run_finished':
      cb.onFinished?.(data.text ?? '')
      break
    case 'error':
      cb.onError?.(data.message ?? 'unknown error')
      break
  }
}

export async function streamChat(
  body: { message: string; conversation_id?: string },
  cb: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${text}`)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const frames = buf.split('\n\n')
    buf = frames.pop() ?? ''
    for (const frame of frames) if (frame.trim()) dispatchFrame(frame, cb)
  }
  if (buf.trim()) dispatchFrame(buf, cb)
}

// ---------------------------------------------------------------------------
// PDF export
// ---------------------------------------------------------------------------

export async function downloadPdf(markdown: string, title?: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/export/pdf`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ markdown, title }),
  })
  if (!res.ok) throw new Error(`${res.status}: ${await res.text().catch(() => res.statusText)}`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'mentis-whitepaper.pdf'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
