/**
 * Dropdown for selecting the active project context.
 * Shows project list with file/chunk counts and a "New Project" option.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { Project } from '../types'

interface ProjectSelectorProps {
  projects: Project[]
  activeProjectId: number | null
  onSelect: (projectId: number | null) => void
  onCreateNew: () => void
  onManage: (projectId: number) => void
}

export function ProjectSelector({ projects, activeProjectId, onSelect, onCreateNew, onManage }: ProjectSelectorProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const active = projects.find((p) => p.id === activeProjectId)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleSelect = useCallback((id: number | null) => {
    onSelect(id)
    setOpen(false)
  }, [onSelect])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 rounded text-sm"
        style={{
          backgroundColor: active ? 'var(--accent)' : 'var(--bg-secondary)',
          color: active ? '#ffffff' : 'var(--text-primary)',
          border: '1px solid var(--border-color)',
        }}
      >
        <span>{active ? active.name : 'No Project'}</span>
        <span style={{ fontSize: '0.6rem' }}>{open ? '\u25B2' : '\u25BC'}</span>
      </button>

      {open && (
        <div
          className="absolute top-full left-0 mt-1 w-64 rounded-lg shadow-lg z-50 overflow-hidden"
          style={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
        >
          <button
            onClick={() => handleSelect(null)}
            className="w-full text-left px-3 py-2 text-sm hover:opacity-80"
            style={{
              backgroundColor: !activeProjectId ? 'var(--bg-secondary)' : 'transparent',
              color: 'var(--text-secondary)',
            }}
          >
            No Project (no context)
          </button>

          {projects.map((p) => (
            <div
              key={p.id}
              className="flex items-center justify-between px-3 py-2 text-sm hover:opacity-80 cursor-pointer"
              style={{
                backgroundColor: p.id === activeProjectId ? 'var(--bg-secondary)' : 'transparent',
                color: 'var(--text-primary)',
              }}
              onClick={() => handleSelect(p.id)}
            >
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{p.name}</div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  {p.file_count} files, {p.total_chunks} chunks
                </div>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); onManage(p.id); setOpen(false) }}
                className="ml-2 px-2 py-0.5 rounded text-xs"
                style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}
              >
                Manage
              </button>
            </div>
          ))}

          <button
            onClick={() => { onCreateNew(); setOpen(false) }}
            className="w-full text-left px-3 py-2 text-sm font-medium"
            style={{ borderTop: '1px solid var(--border-color)', color: 'var(--accent)' }}
          >
            + New Project
          </button>
        </div>
      )}
    </div>
  )
}
