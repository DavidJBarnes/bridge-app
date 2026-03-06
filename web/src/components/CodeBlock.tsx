/**
 * Syntax-highlighted code block with copy-to-clipboard button.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import Prism from 'prismjs'
import 'prismjs/themes/prism-tomorrow.css'
import 'prismjs/components/prism-java'
import 'prismjs/components/prism-typescript'
import 'prismjs/components/prism-jsx'
import 'prismjs/components/prism-tsx'
import 'prismjs/components/prism-python'
import 'prismjs/components/prism-bash'
import 'prismjs/components/prism-json'
import 'prismjs/components/prism-yaml'
import 'prismjs/components/prism-sql'
import 'prismjs/components/prism-css'

/** @param language - Programming language for syntax highlighting. */
/** @param code - The source code to display. */
interface CodeBlockProps {
  language: string
  code: string
}

/** Renders a code block with syntax highlighting and a copy button. */
export function CodeBlock({ language, code }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)
  const codeRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (codeRef.current) {
      Prism.highlightElement(codeRef.current)
    }
  }, [code, language])

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback for non-secure contexts
      const textarea = document.createElement('textarea')
      textarea.value = code
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }, [code])

  const langClass = `language-${language || 'text'}`

  return (
    <div className="relative group my-3 rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--bg-code)' }}>
      <div className="flex items-center justify-between px-4 py-2 text-xs" style={{ color: 'var(--text-secondary)', borderBottom: '1px solid var(--border-color)' }}>
        <span>{language || 'text'}</span>
        <button
          onClick={handleCopy}
          className="px-2 py-1 rounded text-xs transition-colors hover:opacity-80"
          style={{ color: 'var(--text-secondary)' }}
          aria-label="Copy code"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-sm">
        <code ref={codeRef} className={langClass}>
          {code}
        </code>
      </pre>
    </div>
  )
}
