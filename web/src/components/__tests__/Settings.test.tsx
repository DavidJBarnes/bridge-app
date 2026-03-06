import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Settings } from '../Settings'

const mockOnSave = vi.fn()
const mockOnClose = vi.fn()
const mockOnThemeChange = vi.fn()

const defaultProps = {
  config: { apiUrl: 'http://localhost:8000', apiKey: 'bridge-test', model: '' },
  onSave: mockOnSave,
  onClose: mockOnClose,
  theme: 'dark' as const,
  onThemeChange: mockOnThemeChange,
  models: [{ id: 'test-model', provider: 'ollama' }],
}

describe('Settings', () => {
  it('renders settings form', () => {
    render(<Settings {...defaultProps} />)
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByDisplayValue('http://localhost:8000')).toBeInTheDocument()
  })

  it('shows model selector with options', () => {
    render(<Settings {...defaultProps} />)
    expect(screen.getByText('test-model (ollama)')).toBeInTheDocument()
  })

  it('saves config on save click', () => {
    render(<Settings {...defaultProps} />)
    fireEvent.click(screen.getByText('Save'))
    expect(mockOnSave).toHaveBeenCalledWith({
      apiUrl: 'http://localhost:8000',
      apiKey: 'bridge-test',
      model: '',
    })
    expect(mockOnClose).toHaveBeenCalled()
  })

  it('closes on cancel click', () => {
    render(<Settings {...defaultProps} />)
    fireEvent.click(screen.getByText('Cancel'))
    expect(mockOnClose).toHaveBeenCalled()
  })

  it('closes on backdrop click', () => {
    render(<Settings {...defaultProps} />)
    // Click the backdrop (outer div)
    const backdrop = screen.getByText('Settings').parentElement!.parentElement!
    fireEvent.click(backdrop)
    expect(mockOnClose).toHaveBeenCalled()
  })

  it('changes theme to light', () => {
    render(<Settings {...defaultProps} />)
    fireEvent.click(screen.getByText('Light'))
    expect(mockOnThemeChange).toHaveBeenCalledWith('light')
  })

  it('changes theme to dark', () => {
    render(<Settings {...defaultProps} />)
    fireEvent.click(screen.getByText('Dark'))
    expect(mockOnThemeChange).toHaveBeenCalledWith('dark')
  })

  it('allows editing API URL', () => {
    render(<Settings {...defaultProps} />)
    const input = screen.getByDisplayValue('http://localhost:8000')
    fireEvent.change(input, { target: { value: 'http://new-url.com/' } })
    fireEvent.click(screen.getByText('Save'))
    expect(mockOnSave).toHaveBeenCalledWith(
      expect.objectContaining({ apiUrl: 'http://new-url.com' })
    )
  })

  it('allows editing API key', () => {
    render(<Settings {...defaultProps} />)
    const input = screen.getByDisplayValue('bridge-test')
    fireEvent.change(input, { target: { value: 'bridge-new-key' } })
    fireEvent.click(screen.getByText('Save'))
    expect(mockOnSave).toHaveBeenCalledWith(
      expect.objectContaining({ apiKey: 'bridge-new-key' })
    )
  })
})
