import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Chat } from '../Chat'
import type { ChatMessage } from '../../types'

const mockOnSend = vi.fn()
const mockOnStop = vi.fn()
const mockOnClear = vi.fn()

const defaultProps = {
  messages: [] as ChatMessage[],
  isLoading: false,
  error: null,
  onSend: mockOnSend,
  onStop: mockOnStop,
  onClear: mockOnClear,
}

describe('Chat', () => {
  beforeEach(() => {
    mockOnSend.mockClear()
    mockOnStop.mockClear()
    mockOnClear.mockClear()
  })
  it('renders empty state', () => {
    render(<Chat {...defaultProps} />)
    expect(screen.getByText('Bridge Chat')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Ask a coding question...')).toBeInTheDocument()
  })

  it('renders messages', () => {
    const messages: ChatMessage[] = [
      { id: '1', role: 'user', content: 'Hello', timestamp: Date.now() },
      { id: '2', role: 'assistant', content: 'Hi there', timestamp: Date.now() },
    ]
    render(<Chat {...defaultProps} messages={messages} />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
    expect(screen.getByText('Hi there')).toBeInTheDocument()
  })

  it('calls onSend when sending a message', () => {
    render(<Chat {...defaultProps} />)
    const input = screen.getByPlaceholderText('Ask a coding question...')
    fireEvent.change(input, { target: { value: 'Write hello world' } })
    fireEvent.click(screen.getByText('Send'))
    expect(mockOnSend).toHaveBeenCalledWith('Write hello world')
  })

  it('sends on Enter key', () => {
    render(<Chat {...defaultProps} />)
    const input = screen.getByPlaceholderText('Ask a coding question...')
    fireEvent.change(input, { target: { value: 'test' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(mockOnSend).toHaveBeenCalledWith('test')
  })

  it('does not send on Shift+Enter', () => {
    render(<Chat {...defaultProps} />)
    const input = screen.getByPlaceholderText('Ask a coding question...')
    fireEvent.change(input, { target: { value: 'test' } })
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true })
    expect(mockOnSend).not.toHaveBeenCalled()
  })

  it('disables input during loading', () => {
    render(<Chat {...defaultProps} isLoading={true} />)
    expect(screen.getByPlaceholderText('Ask a coding question...')).toBeDisabled()
  })

  it('shows stop button during loading', () => {
    render(<Chat {...defaultProps} isLoading={true} />)
    expect(screen.getByText('Stop')).toBeInTheDocument()
  })

  it('calls onStop when stop is clicked', () => {
    render(<Chat {...defaultProps} isLoading={true} />)
    fireEvent.click(screen.getByText('Stop'))
    expect(mockOnStop).toHaveBeenCalled()
  })

  it('shows clear button when there are messages', () => {
    const messages: ChatMessage[] = [
      { id: '1', role: 'user', content: 'Hello', timestamp: Date.now() },
    ]
    render(<Chat {...defaultProps} messages={messages} />)
    expect(screen.getByText('Clear')).toBeInTheDocument()
  })

  it('calls onClear when clear is clicked', () => {
    const messages: ChatMessage[] = [
      { id: '1', role: 'user', content: 'Hello', timestamp: Date.now() },
    ]
    render(<Chat {...defaultProps} messages={messages} />)
    fireEvent.click(screen.getByText('Clear'))
    expect(mockOnClear).toHaveBeenCalled()
  })

  it('displays error message', () => {
    render(<Chat {...defaultProps} error="Something went wrong" />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('does not send empty message', () => {
    render(<Chat {...defaultProps} />)
    fireEvent.click(screen.getByText('Send'))
    expect(mockOnSend).not.toHaveBeenCalled()
  })
})
