/** A single message in a chat conversation. */
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
}

/** Configuration for the API connection. */
export interface AppConfig {
  apiUrl: string
  apiKey: string
  model: string
  activeProjectId: number | null
}

/** Model info returned from the API. */
export interface ModelInfo {
  id: string
  provider: string
}

/** Project for context memory. */
export interface Project {
  id: number
  name: string
  description: string | null
  conventions: string | null
  system_prompt: string | null
  file_count: number
  total_chunks: number
  created_at: string
  updated_at: string
}

/** A file within a project. */
export interface ProjectFile {
  id: number
  file_path: string
  file_type: string | null
  summary: string | null
  total_tokens: number
  chunk_count: number
  created_at: string
  updated_at: string
}

/** Theme options for the app. */
export type Theme = 'light' | 'dark'
