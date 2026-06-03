import type {
  ChatRequest,
  ChatResponse,
  Conversation,
  PapersResponse,
  DocumentsResponse,
  HarvestRequest,
  HarvestResponse,
  HealthResponse,
} from './types'

// ---------------------------------------------------------------------------
// Config — read once from env at module load time
// ---------------------------------------------------------------------------

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY as string | undefined

function headers(extra?: Record<string, string>): HeadersInit {
  const h: Record<string, string> = { 'Content-Type': 'application/json' }
  if (API_KEY) h['x-api-key'] = API_KEY
  return { ...h, ...extra }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health', { headers: headers() })
}

export function postChat(body: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>('/chat', {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
  })
}

export function getConversation(id: string): Promise<Conversation> {
  return request<Conversation>(`/conversations/${id}`, { headers: headers() })
}

export function searchPapers(query: string): Promise<PapersResponse> {
  const params = new URLSearchParams({ query })
  return request<PapersResponse>(`/papers?${params}`, { headers: headers() })
}

export function getDocuments(): Promise<DocumentsResponse> {
  return request<DocumentsResponse>('/documents', { headers: headers() })
}

export function postHarvest(body: HarvestRequest): Promise<HarvestResponse> {
  return request<HarvestResponse>('/harvest', {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
  })
}
