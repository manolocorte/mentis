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
  unsupported?: boolean
}

export interface StreamCallbacks {
  onConversation?: (id: string) => void
  onToken?: (text: string) => void
  onToolCall?: (call: ToolCallEvent) => void
  onStatus?: (label: string) => void
  onCitations?: (items: Citation[]) => void
  onFinished?: (text: string) => void
  onError?: (message: string) => void
}
