import type {
  Conversation,
  HealthResponse,
  LibrarySource,
  Job,
  Project,
  ProjectFile,
  SourceProvider,
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

export const API_BASE_URL = BASE_URL

// --- session token ---
const TOKEN_KEY = 'mentis-token'
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
function setToken(t: string): void {
  localStorage.setItem(TOKEN_KEY, t)
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}
function authToken(): string | undefined {
  return getToken() ?? API_KEY ?? undefined
}

let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: () => void): void {
  onUnauthorized = fn
}
function notifyUnauthorized(): void {
  clearToken()
  onUnauthorized?.()
}

function headers(extra?: Record<string, string>): HeadersInit {
  const h: Record<string, string> = { 'Content-Type': 'application/json' }
  const t = authToken()
  if (t) h['x-api-key'] = t
  return { ...h, ...extra }
}

async function jreq<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers: headers(init?.headers as Record<string, string>) })
  if (res.status === 401) notifyUnauthorized()
  if (!res.ok) throw new Error(`${res.status}: ${await res.text().catch(() => res.statusText)}`)
  return res.json() as Promise<T>
}

// --- auth ---
export function getAuthStatus(): Promise<{ auth_required: boolean }> {
  return jreq('/auth/status')
}

export async function login(username: string, password: string): Promise<{ token: string; username: string }> {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    throw new Error(res.status === 401 ? 'Invalid username or password' : `${res.status}: ${await res.text().catch(() => res.statusText)}`)
  }
  const data = await res.json()
  setToken(data.token)
  return data
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${BASE_URL}/auth/logout`, { method: 'POST', headers: headers() })
  } catch {
    // ignore network errors on logout — we clear the token regardless
  }
  clearToken()
}

export function getMe(): Promise<{ username: string | null; auth_required: boolean }> {
  return jreq('/auth/me')
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

export function getSourceProviders(): Promise<{ sources: SourceProvider[] }> {
  return jreq('/sources')
}

export async function compileProject(projectId: string, format: 'pdf' | 'docx'): Promise<void> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/compile`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ format }),
  })
  if (!res.ok) throw new Error(`${res.status}: ${await res.text().catch(() => res.statusText)}`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `whitepaper.${format}`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export function updateProjectSources(projectId: string, sources: string[]): Promise<Project> {
  return jreq(`/projects/${projectId}`, { method: 'PATCH', body: JSON.stringify({ sources }) })
}

// --- project files (workspace) ---

export function listFiles(projectId: string): Promise<{ files: ProjectFile[] }> {
  return jreq(`/projects/${projectId}/files`)
}

export async function uploadFiles(projectId: string, files: File[]): Promise<{ files: ProjectFile[] }> {
  const fd = new FormData()
  for (const f of files) fd.append('files', f)
  const h: Record<string, string> = {}
  const t = authToken()
  if (t) h['x-api-key'] = t
  const res = await fetch(`${BASE_URL}/projects/${projectId}/files`, { method: 'POST', headers: h, body: fd })
  if (res.status === 401) notifyUnauthorized()
  if (!res.ok) throw new Error(`${res.status}: ${await res.text().catch(() => res.statusText)}`)
  return res.json()
}

export function deleteFile(projectId: string, name: string): Promise<{ ok: boolean }> {
  return jreq(`/projects/${projectId}/files/${encodeURIComponent(name)}`, { method: 'DELETE' })
}

export function fileUrl(projectId: string, name: string): string {
  return `${BASE_URL}/projects/${projectId}/files/${encodeURIComponent(name)}`
}

// --- background jobs ---

export function submitJob(
  message: string,
  conversationId?: string,
): Promise<{ job_id: string; conversation_id: string; project_id: string; title?: string }> {
  return jreq('/jobs', { method: 'POST', body: JSON.stringify({ message, conversation_id: conversationId }) })
}

export function listJobs(projectId: string): Promise<{ jobs: Job[] }> {
  return jreq(`/projects/${projectId}/jobs`)
}

export function getJob(jobId: string): Promise<Job> {
  return jreq(`/jobs/${jobId}`)
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
  if (res.status === 401) notifyUnauthorized()
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

export async function downloadDocument(
  markdown: string,
  format: 'pdf' | 'docx',
  title?: string,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/export`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ markdown, format, title }),
  })
  if (!res.ok) throw new Error(`${res.status}: ${await res.text().catch(() => res.statusText)}`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `mentis-whitepaper.${format}`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
