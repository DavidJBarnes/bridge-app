import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CodeBlock } from '../CodeBlock'

describe('CodeBlock', () => {
  it('renders code content', () => {
    const { container } = render(<CodeBlock language="text" code="hello world" />)
    expect(container.querySelector('code')).toHaveTextContent('hello world')
  })

  it('displays the language label', () => {
    render(<CodeBlock language="java" code="int x = 1;" />)
    expect(screen.getByText('java')).toBeInTheDocument()
  })

  it('defaults to text when no language specified', () => {
    render(<CodeBlock language="" code="plain text" />)
    expect(screen.getByText('text')).toBeInTheDocument()
  })

  it('has a copy button', () => {
    render(<CodeBlock language="python" code="print('hi')" />)
    expect(screen.getByRole('button', { name: /copy/i })).toBeInTheDocument()
  })

  it('copies code to clipboard on click', async () => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    })

    render(<CodeBlock language="python" code="print('hi')" />)
    const copyBtn = screen.getByRole('button', { name: /copy/i })
    fireEvent.click(copyBtn)

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("print('hi')")
  })

  it('shows "Copied!" after clicking copy', async () => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    })

    render(<CodeBlock language="text" code="test" />)
    fireEvent.click(screen.getByRole('button', { name: /copy/i }))

    expect(await screen.findByText('Copied!')).toBeInTheDocument()
  })

  it('falls back when clipboard API fails', () => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error('fail')) },
    })
    document.execCommand = vi.fn()

    render(<CodeBlock language="text" code="test" />)
    fireEvent.click(screen.getByRole('button', { name: /copy/i }))

    // Should not throw
  })

  it('applies language class to code element', () => {
    const { container } = render(<CodeBlock language="typescript" code="const x = 1" />)
    const codeEl = container.querySelector('code')
    expect(codeEl).toHaveClass('language-typescript')
  })
})
