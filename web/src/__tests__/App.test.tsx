import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import App from '../App'

// Mock the API module
vi.mock('../services/api', () => ({
  fetchModels: vi.fn().mockResolvedValue([]),
  streamChat: vi.fn().mockResolvedValue(''),
}))

beforeEach(() => {
  localStorage.clear()
})

describe('App', () => {
  it('renders welcome screen when no API key', () => {
    render(<App />)
    expect(screen.getByText('Welcome to Bridge Chat')).toBeInTheDocument()
    expect(screen.getByText('Open Settings')).toBeInTheDocument()
  })

  it('shows settings button in header', () => {
    render(<App />)
    expect(screen.getByLabelText('Open settings')).toBeInTheDocument()
  })

  it('opens settings modal', () => {
    render(<App />)
    fireEvent.click(screen.getByLabelText('Open settings'))
    expect(screen.getByText('API URL')).toBeInTheDocument()
    expect(screen.getByText('API Key')).toBeInTheDocument()
  })

  it('shows chat interface when API key is configured', () => {
    localStorage.setItem(
      'bridge-config',
      JSON.stringify({ apiUrl: 'http://localhost:8000', apiKey: 'bridge-test', model: '' })
    )
    render(<App />)
    expect(screen.getByPlaceholderText('Ask a coding question...')).toBeInTheDocument()
  })

  it('saves config from settings', () => {
    render(<App />)
    fireEvent.click(screen.getByLabelText('Open settings'))

    // Fill in API key
    const keyInput = screen.getByPlaceholderText('bridge-xxx')
    fireEvent.change(keyInput, { target: { value: 'bridge-new-key' } })
    fireEvent.click(screen.getByText('Save'))

    const stored = JSON.parse(localStorage.getItem('bridge-config') || '{}')
    expect(stored.apiKey).toBe('bridge-new-key')
  })

  it('loads dark theme by default', () => {
    render(<App />)
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('persists theme preference', () => {
    render(<App />)
    fireEvent.click(screen.getByLabelText('Open settings'))
    fireEvent.click(screen.getByText('Light'))

    expect(localStorage.getItem('bridge-theme')).toBe('light')
  })
})
