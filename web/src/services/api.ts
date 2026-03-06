/**
 * API client for the Bridge Model API.
 * Handles completions, chat, streaming, and model listing.
 */

import type { ChatMessage, ModelInfo } from '../types'

/** Build authorization headers for API requests. */
function authHeaders(apiKey: string): Record<string, string> {
  return {
    'Authorization': `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
  }
}

/**
 * Send a chat request and return the full response.
 * @param apiUrl - Base URL of the Bridge API.
 * @param apiKey - API key for authentication.
 * @param messages - Conversation message history.
 * @returns The assistant's response text.
 */
export async function sendChat(
  apiUrl: string,
  apiKey: string,
  messages: ChatMessage[]
): Promise<string> {
  const response = await fetch(`${apiUrl}/v1/chat`, {
    method: 'POST',
    headers: authHeaders(apiKey),
    body: JSON.stringify({
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      stream: false,
    }),
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`API error ${response.status}: ${error}`)
  }

  const data = await response.json()
  return data.message.content
}

/**
 * Send a streaming chat request and call onToken for each token.
 * @param apiUrl - Base URL of the Bridge API.
 * @param apiKey - API key for authentication.
 * @param messages - Conversation message history.
 * @param onToken - Callback invoked with each generated token.
 * @param signal - Optional AbortSignal to cancel the request.
 * @returns The complete response text.
 */
export async function streamChat(
  apiUrl: string,
  apiKey: string,
  messages: ChatMessage[],
  onToken: (token: string) => void,
  signal?: AbortSignal
): Promise<string> {
  const response = await fetch(`${apiUrl}/v1/chat`, {
    method: 'POST',
    headers: authHeaders(apiKey),
    body: JSON.stringify({
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      stream: true,
    }),
    signal,
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`API error ${response.status}: ${error}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let fullText = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value, { stream: true })
    const lines = chunk.split('\n')

    for (const line of lines) {
      const trimmed = line.trim()
      if (trimmed.startsWith('data: ') && trimmed !== 'data: [DONE]') {
        try {
          const data = JSON.parse(trimmed.slice(6))
          if (data.token) {
            fullText += data.token
            onToken(data.token)
          }
        } catch {
          // Skip malformed SSE lines
        }
      }
    }
  }

  return fullText
}

/**
 * Fetch available models from the API.
 * @param apiUrl - Base URL of the Bridge API.
 * @param apiKey - API key for authentication.
 * @returns List of available models.
 */
export async function fetchModels(
  apiUrl: string,
  apiKey: string
): Promise<ModelInfo[]> {
  const response = await fetch(`${apiUrl}/v1/models`, {
    headers: authHeaders(apiKey),
  })

  if (!response.ok) {
    throw new Error(`API error ${response.status}`)
  }

  const data = await response.json()
  return data.models
}
