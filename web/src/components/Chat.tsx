/**
 * Main chat interface component.
 * Handles message input, display, and auto-scrolling.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { ChatMessage } from '../types'
import { Message } from './Message'

/** @param messages - Array of chat messages to display. */
/** @param isLoading - Whether a response is being generated. */
/** @param error - Error message to display, if any. */
/** @param onSend - Callback when the user sends a message. */
/** @param onStop - Callback to stop generation. */
/** @param onClear - Callback to clear the chat history. */
interface ChatProps {
  messages: ChatMessage[]
  isLoading: boolean
  error: string | null
  onSend: (message: string) => void
  onStop: () => void
  onClear: () => void
}

/** Chat interface with message list and input area. */
export function Chat({ messages, isLoading, error, onSend, onStop, onClear }: ChatProps) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSubmit = useCallback(() => {
    if (input.trim() && !isLoading) {
      onSend(input)
      setInput('')
    }
  }, [input, isLoading, onSend])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSubmit()
      }
    },
    [handleSubmit]
  )

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center" style={{ color: 'var(--text-secondary)' }}>
              <h2 className="text-2xl font-bold mb-2">Bridge Chat</h2>
              <p>Ask me about Java/Spring Boot or React/TypeScript code</p>
            </div>
          </div>
        )}
        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
        {error && (
          <div className="text-red-500 text-sm text-center py-2">{error}</div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-4" style={{ borderTop: '1px solid var(--border-color)' }}>
        <div className="flex gap-2 mb-2">
          {isLoading && (
            <button
              onClick={onStop}
              className="px-3 py-1 rounded text-xs text-white bg-red-500 hover:bg-red-600"
            >
              Stop
            </button>
          )}
          {messages.length > 0 && (
            <button
              onClick={onClear}
              className="px-3 py-1 rounded text-xs"
              style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}
            >
              Clear
            </button>
          )}
        </div>
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a coding question..."
            className="flex-1 rounded-lg px-4 py-3 text-sm resize-none"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)',
            }}
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={handleSubmit}
            disabled={isLoading || !input.trim()}
            className="px-4 py-3 rounded-lg text-sm text-white transition-colors disabled:opacity-50"
            style={{ backgroundColor: 'var(--accent)' }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
