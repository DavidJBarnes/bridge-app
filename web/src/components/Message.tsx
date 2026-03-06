/**
 * Chat message component that renders user and assistant messages.
 * Parses markdown-style code blocks for syntax highlighting.
 */

import type { ChatMessage } from '../types'
import { CodeBlock } from './CodeBlock'

/** @param message - The chat message to render. */
interface MessageProps {
  message: ChatMessage
}

/** Parse message content into text and code block segments. */
function parseContent(content: string): Array<{ type: 'text' | 'code'; content: string; language?: string }> {
  const segments: Array<{ type: 'text' | 'code'; content: string; language?: string }> = []
  const codeBlockRegex = /```(\w*)\n?([\s\S]*?)```/g
  let lastIndex = 0
  let match

  while ((match = codeBlockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', content: content.slice(lastIndex, match.index) })
    }
    segments.push({ type: 'code', language: match[1] || 'text', content: match[2].trimEnd() })
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < content.length) {
    segments.push({ type: 'text', content: content.slice(lastIndex) })
  }

  return segments
}

/** Renders a single chat message with code block detection. */
export function Message({ message }: MessageProps) {
  const isUser = message.role === 'user'
  const segments = parseContent(message.content)

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser ? 'text-white' : ''
        }`}
        style={{
          backgroundColor: isUser ? 'var(--accent)' : 'var(--bg-secondary)',
          color: isUser ? '#ffffff' : 'var(--text-primary)',
        }}
      >
        {segments.map((segment, i) =>
          segment.type === 'code' ? (
            <CodeBlock key={i} language={segment.language || 'text'} code={segment.content} />
          ) : (
            <span key={i} className="whitespace-pre-wrap">
              {segment.content}
            </span>
          )
        )}
        {!message.content && message.role === 'assistant' && (
          <span className="animate-pulse" aria-label="Loading">...</span>
        )}
      </div>
    </div>
  )
}
