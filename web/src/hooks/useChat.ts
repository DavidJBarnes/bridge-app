/**
 * Custom hook for managing chat state and streaming API interaction.
 */

import { useCallback, useRef, useState } from 'react'
import type { ChatMessage } from '../types'
import { streamChat } from '../services/api'

/** Return type for the useChat hook. */
interface UseChatReturn {
  messages: ChatMessage[]
  isLoading: boolean
  error: string | null
  sendMessage: (content: string) => Promise<void>
  clearMessages: () => void
  stopGeneration: () => void
}

/**
 * Hook for managing chat conversations with streaming support.
 * @param apiUrl - Base URL of the Bridge API.
 * @param apiKey - API key for authentication.
 * @param projectId - Optional project ID for context injection.
 * @returns Chat state and control functions.
 */
export function useChat(apiUrl: string, apiKey: string, projectId?: number | null): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return

      setError(null)
      const userMessage: ChatMessage = {
        id: Math.random().toString(36).slice(2) + Date.now().toString(36),
        role: 'user',
        content: content.trim(),
        timestamp: Date.now(),
      }

      const assistantMessage: ChatMessage = {
        id: Math.random().toString(36).slice(2) + Date.now().toString(36),
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
      }

      setMessages((prev) => [...prev, userMessage, assistantMessage])
      setIsLoading(true)

      const abortController = new AbortController()
      abortRef.current = abortController

      try {
        const allMessages = [...messages, userMessage]
        const fullText = await streamChat(
          apiUrl,
          apiKey,
          allMessages,
          (token) => {

            setMessages((prev) => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              if (last.role === 'assistant') {
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content + token,
                }
              }
              return updated
            })
          },
          abortController.signal,
          projectId,
        )

        setMessages((prev) => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last.role === 'assistant') {
            updated[updated.length - 1] = { ...last, content: fullText.trimEnd() }
          }
          return updated
        })
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          return
        }
        const errorMsg = err instanceof Error ? err.message : 'Unknown error'
        setError(errorMsg)
        setMessages((prev) => prev.filter((m) => m.id !== assistantMessage.id))
      } finally {
        setIsLoading(false)
        abortRef.current = null
      }
    },
    [apiUrl, apiKey, messages, isLoading, projectId]
  )

  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
  }, [])

  const stopGeneration = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return { messages, isLoading, error, sendMessage, clearMessages, stopGeneration }
}
