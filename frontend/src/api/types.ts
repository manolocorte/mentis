// ---- Chat / Conversation ----

export interface Citation {
  chunk_id: string
  doi?: string
  title?: string
  snippet: string
}

export interface TraceStep {
  agent: string
  summary: string
}

export interface ChatRequest {
  query: string
  project?: string
  conversation_id?: string
}

export interface ChatResponse {
  conversation_id: string
  answer: string
  intent: string
  confidence: number
  citations: Citation[]
  trace: TraceStep[]
}

export interface ConversationMessage {
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface Conversation {
  id: string
  messages: ConversationMessage[]
}

// ---- Papers ----

export interface Paper {
  id: string
  title: string
  authors: string[]
  year?: number
  venue?: string
  doi?: string
  citation_count?: number
  source: string
}

export interface PapersResponse {
  papers: Paper[]
}

// ---- Documents ----

export interface Document {
  id: string
  title: string
  status: string
  chunk_count: number
  created_at: string
}

export interface DocumentsResponse {
  documents: Document[]
}

// ---- Harvest ----

export interface HarvestRequest {
  query: string
  max_results?: number
}

export interface HarvestResponse {
  enqueued: number
  message: string
}

// ---- Health ----

export interface HealthResponse {
  status: string
}
