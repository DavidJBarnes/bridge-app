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
}

/** Model info returned from the API. */
export interface ModelInfo {
  id: string
  provider: string
}

/** Theme options for the app. */
export type Theme = 'light' | 'dark'
