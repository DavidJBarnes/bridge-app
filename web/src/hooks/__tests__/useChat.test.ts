import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useChat } from '../useChat'
import * as api from '../../services/api'

vi.mock('../../services/api')
const mockStreamChat = vi.mocked(api.streamChat)

beforeEach(() => {
  vi.resetAllMocks()
})

describe('useChat', () => {
  it('initializes with empty state', () => {
    const { result } = renderHook(() => useChat('http://localhost:8000', 'key'))
    expect(result.current.messages).toEqual([])
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('sends a message and receives response', async () => {
    mockStreamChat.mockImplementation(async (_url, _key, _msgs, onToken) => {
      onToken('Hello')
      onToken(' World')
      return 'Hello World'
    })

    const { result } = renderHook(() => useChat('http://localhost:8000', 'key'))

    await act(async () => {
      await result.current.sendMessage('Hi')
    })

    expect(result.current.messages).toHaveLength(2)
    expect(result.current.messages[0].role).toBe('user')
    expect(result.current.messages[0].content).toBe('Hi')
    expect(result.current.messages[1].role).toBe('assistant')
    expect(result.current.messages[1].content).toBe('Hello World')
  })

  it('handles API errors', async () => {
    mockStreamChat.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useChat('http://localhost:8000', 'key'))

    await act(async () => {
      await result.current.sendMessage('Hi')
    })

    expect(result.current.error).toBe('Network error')
    // User message should remain, assistant message should be removed
    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0].role).toBe('user')
  })

  it('clears messages', async () => {
    mockStreamChat.mockResolvedValue('response')

    const { result } = renderHook(() => useChat('http://localhost:8000', 'key'))

    await act(async () => {
      await result.current.sendMessage('Hi')
    })

    act(() => {
      result.current.clearMessages()
    })

    expect(result.current.messages).toEqual([])
  })

  it('ignores empty messages', async () => {
    const { result } = renderHook(() => useChat('http://localhost:8000', 'key'))

    await act(async () => {
      await result.current.sendMessage('')
    })

    expect(result.current.messages).toEqual([])
    expect(mockStreamChat).not.toHaveBeenCalled()
  })

  it('ignores whitespace-only messages', async () => {
    const { result } = renderHook(() => useChat('http://localhost:8000', 'key'))

    await act(async () => {
      await result.current.sendMessage('   ')
    })

    expect(result.current.messages).toEqual([])
  })
})
