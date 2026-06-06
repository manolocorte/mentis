// ---- Health ----

export interface HealthResponse {
  status: string
  region?: string
  supervisor_model?: string
  draft_model?: string
  scopus?: boolean
}

// ---- Streaming chat (SSE) ----

export interface ToolCallEvent {
  name: string
  input: unknown
}

export interface Citation {
  n: number
  title?: string | null
  authors?: string
  year?: string
  doi?: string
  verified: boolean
  supported?: boolean | null
  unsupported?: boolean
}

export interface Project {
  id: string
  name: string
  brief: string
  sources: string[]
  created_at: number
  updated_at: number
}

export interface SourceProvider {
  key: string
  label: string
  free: boolean
  available: boolean
}

export interface Conversation {
  id: string
  project_id: string
  title: string
  created_at: number
}

export interface StoredMessage {
  role: 'user' | 'assistant'
  content: string
  created_at: number
}

export interface Job {
  id: string
  project_id: string
  conversation_id: string
  prompt: string
  status: 'running' | 'done' | 'error'
  result?: string
  error?: string
  created_at: number
  finished_at?: number
}

export interface ProjectFile {
  name: string
  size: number
  modified: number
  kind: 'image' | 'file'
}

export interface LibrarySource {
  doi: string
  title: string
  authors: string
  year: string
  venue: string
  verified: number
}

export interface StreamCallbacks {
  onConversation?: (info: { conversationId: string; projectId?: string; title?: string }) => void
  onToken?: (text: string) => void
  onToolCall?: (call: ToolCallEvent) => void
  onStatus?: (label: string) => void
  onCitations?: (items: Citation[]) => void
  onFinished?: (text: string) => void
  onError?: (message: string) => void
}
