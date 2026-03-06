import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Message } from '../Message'
import type { ChatMessage } from '../../types'

describe('Message', () => {
  it('renders user message', () => {
    const msg: ChatMessage = {
      id: '1',
      role: 'user',
      content: 'Hello there',
      timestamp: Date.now(),
    }
    render(<Message message={msg} />)
    expect(screen.getByText('Hello there')).toBeInTheDocument()
  })

  it('renders assistant message', () => {
    const msg: ChatMessage = {
      id: '2',
      role: 'assistant',
      content: 'Here is some code',
      timestamp: Date.now(),
    }
    render(<Message message={msg} />)
    expect(screen.getByText('Here is some code')).toBeInTheDocument()
  })

  it('renders code blocks with language label', () => {
    const msg: ChatMessage = {
      id: '3',
      role: 'assistant',
      content: 'Try this:\n```typescript\nconst x = 1\n```\nDone.',
      timestamp: Date.now(),
    }
    render(<Message message={msg} />)
    expect(screen.getByText('typescript')).toBeInTheDocument()
  })

  it('renders code block content', () => {
    const msg: ChatMessage = {
      id: '3b',
      role: 'assistant',
      content: '```text\nhello world\n```',
      timestamp: Date.now(),
    }
    const { container } = render(<Message message={msg} />)
    expect(container.querySelector('code')).toHaveTextContent('hello world')
  })

  it('shows loading indicator for empty assistant message', () => {
    const msg: ChatMessage = {
      id: '4',
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    }
    render(<Message message={msg} />)
    expect(screen.getByLabelText('Loading')).toBeInTheDocument()
  })

  it('handles multiple code blocks', () => {
    const msg: ChatMessage = {
      id: '5',
      role: 'assistant',
      content: '```java\nint x = 1;\n```\nand\n```python\nx = 1\n```',
      timestamp: Date.now(),
    }
    render(<Message message={msg} />)
    expect(screen.getByText('java')).toBeInTheDocument()
    expect(screen.getByText('python')).toBeInTheDocument()
  })

  it('handles message with no code blocks', () => {
    const msg: ChatMessage = {
      id: '6',
      role: 'assistant',
      content: 'Just plain text response',
      timestamp: Date.now(),
    }
    render(<Message message={msg} />)
    expect(screen.getByText('Just plain text response')).toBeInTheDocument()
  })
})
