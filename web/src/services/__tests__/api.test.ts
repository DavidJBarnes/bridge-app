import { describe, it, expect, vi, beforeEach } from 'vitest'
import { sendChat, streamChat, fetchModels } from '../api'

const mockFetch = vi.fn()
global.fetch = mockFetch

beforeEach(() => {
  mockFetch.mockReset()
})

describe('sendChat', () => {
  it('sends chat request and returns response', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ message: { content: 'Hello back' } }),
    })

    const result = await sendChat('http://localhost:8000', 'key', [
      { id: '1', role: 'user', content: 'Hello', timestamp: 0 },
    ])

    expect(result).toBe('Hello back')
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/v1/chat',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('throws on API error', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
      text: () => Promise.resolve('Unauthorized'),
    })

    await expect(
      sendChat('http://localhost:8000', 'bad-key', [
        { id: '1', role: 'user', content: 'Hello', timestamp: 0 },
      ])
    ).rejects.toThrow('API error 401')
  })
})

describe('streamChat', () => {
  it('streams tokens and returns full text', async () => {
    const encoder = new TextEncoder()
    const chunks = [
      'data: {"token":"Hello"}\n\n',
      'data: {"token":" World"}\n\n',
      'data: [DONE]\n\n',
    ]

    let chunkIndex = 0
    const mockReader = {
      read: vi.fn().mockImplementation(() => {
        if (chunkIndex < chunks.length) {
          const value = encoder.encode(chunks[chunkIndex++])
          return Promise.resolve({ done: false, value })
        }
        return Promise.resolve({ done: true, value: undefined })
      }),
    }

    mockFetch.mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    const tokens: string[] = []
    const result = await streamChat(
      'http://localhost:8000',
      'key',
      [{ id: '1', role: 'user', content: 'test', timestamp: 0 }],
      (token) => tokens.push(token)
    )

    expect(tokens).toEqual(['Hello', ' World'])
    expect(result).toBe('Hello World')
  })

  it('throws when no response body', async () => {
    mockFetch.mockResolvedValue({ ok: true, body: null })

    await expect(
      streamChat('http://localhost:8000', 'key', [], vi.fn())
    ).rejects.toThrow('No response body')
  })

  it('throws on API error', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Server error'),
    })

    await expect(
      streamChat('http://localhost:8000', 'key', [], vi.fn())
    ).rejects.toThrow('API error 500')
  })

  it('skips malformed SSE lines', async () => {
    const encoder = new TextEncoder()
    const chunks = ['data: {invalid json}\n\ndata: {"token":"ok"}\n\n']

    let chunkIndex = 0
    const mockReader = {
      read: vi.fn().mockImplementation(() => {
        if (chunkIndex < chunks.length) {
          const value = encoder.encode(chunks[chunkIndex++])
          return Promise.resolve({ done: false, value })
        }
        return Promise.resolve({ done: true, value: undefined })
      }),
    }

    mockFetch.mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    const tokens: string[] = []
    await streamChat('http://localhost:8000', 'key', [], (t) => tokens.push(t))
    expect(tokens).toEqual(['ok'])
  })
})

describe('fetchModels', () => {
  it('returns model list', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ models: [{ id: 'model1', provider: 'ollama' }] }),
    })

    const models = await fetchModels('http://localhost:8000', 'key')
    expect(models).toEqual([{ id: 'model1', provider: 'ollama' }])
  })

  it('throws on API error', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 403 })

    await expect(fetchModels('http://localhost:8000', 'bad')).rejects.toThrow('API error 403')
  })
})
