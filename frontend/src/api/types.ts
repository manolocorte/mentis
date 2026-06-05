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

export interface StreamCallbacks {
  onConversation?: (id: string) => void
  onToken?: (text: string) => void
  onToolCall?: (call: ToolCallEvent) => void
  onFinished?: (text: string) => void
  onError?: (message: string) => void
}
