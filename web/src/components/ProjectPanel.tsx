/**
 * Modal panel for managing a project's settings, conventions, and files.
 * Supports creating new projects and editing existing ones.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { Project, ProjectFile } from '../types'

interface ProjectPanelProps {
  apiUrl: string
  apiKey: string
  project: Project | null
  onClose: () => void
  onSaved: (project: Project) => void
  onDeleted: (projectId: number) => void
  fetchFiles: (projectId: number) => Promise<ProjectFile[]>
  onUploadFile: (projectId: number, file: File, filePath: string) => Promise<void>
  onDeleteFile: (projectId: number, fileId: number) => Promise<void>
  onCreateProject: (data: { name: string; description?: string; conventions?: string; system_prompt?: string }) => Promise<Project>
  onUpdateProject: (projectId: number, data: { name?: string; description?: string; conventions?: string; system_prompt?: string }) => Promise<Project>
  onDeleteProject: (projectId: number) => Promise<void>
}

export function ProjectPanel({
  project,
  onClose,
  onSaved,
  onDeleted,
  fetchFiles,
  onUploadFile,
  onDeleteFile,
  onCreateProject,
  onUpdateProject,
  onDeleteProject,
}: ProjectPanelProps) {
  const [name, setName] = useState(project?.name ?? '')
  const [description, setDescription] = useState(project?.description ?? '')
  const [conventions, setConventions] = useState(project?.conventions ?? '')
  const [systemPrompt, setSystemPrompt] = useState(project?.system_prompt ?? '')
  const [files, setFiles] = useState<ProjectFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<'settings' | 'files'>('settings')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const isNew = !project

  useEffect(() => {
    if (project) {
      fetchFiles(project.id).then(setFiles).catch(() => setFiles([]))
    }
  }, [project, fetchFiles])

  const handleSave = useCallback(async () => {
    setError(null)
    try {
      if (isNew) {
        const created = await onCreateProject({
          name,
          description: description || undefined,
          conventions: conventions || undefined,
          system_prompt: systemPrompt || undefined,
        })
        onSaved(created)
      } else {
        const updated = await onUpdateProject(project.id, {
          name,
          description,
          conventions,
          system_prompt: systemPrompt,
        })
        onSaved(updated)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    }
  }, [isNew, name, description, conventions, systemPrompt, project, onCreateProject, onUpdateProject, onSaved])

  const handleDelete = useCallback(async () => {
    if (!project || !confirm(`Delete project "${project.name}"? This cannot be undone.`)) return
    try {
      await onDeleteProject(project.id)
      onDeleted(project.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete')
    }
  }, [project, onDeleteProject, onDeleted])

  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!project || !e.target.files?.length) return
    setUploading(true)
    setError(null)
    try {
      for (const file of Array.from(e.target.files)) {
        await onUploadFile(project.id, file, file.name)
      }
      const updated = await fetchFiles(project.id)
      setFiles(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }, [project, onUploadFile, fetchFiles])

  const handleDeleteFile = useCallback(async (fileId: number) => {
    if (!project) return
    try {
      await onDeleteFile(project.id, fileId)
      setFiles((prev) => prev.filter((f) => f.id !== fileId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    }
  }, [project, onDeleteFile])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="w-full max-w-lg max-h-[80vh] flex flex-col rounded-lg shadow-xl"
        style={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4" style={{ borderBottom: '1px solid var(--border-color)' }}>
          <h2 className="text-lg font-bold">{isNew ? 'New Project' : project.name}</h2>
          <button onClick={onClose} className="text-lg px-2" style={{ color: 'var(--text-secondary)' }}>
            ✕
          </button>
        </div>

        {/* Tabs (only for existing projects) */}
        {!isNew && (
          <div className="flex" style={{ borderBottom: '1px solid var(--border-color)' }}>
            {(['settings', 'files'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className="flex-1 px-4 py-2 text-sm font-medium capitalize"
                style={{
                  borderBottom: tab === t ? '2px solid var(--accent)' : '2px solid transparent',
                  color: tab === t ? 'var(--accent)' : 'var(--text-secondary)',
                }}
              >
                {t} {t === 'files' ? `(${files.length})` : ''}
              </button>
            ))}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {error && <div className="text-red-500 text-sm">{error}</div>}

          {(isNew || tab === 'settings') && (
            <>
              <div>
                <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-md px-3 py-2 text-sm"
                  style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
                  placeholder="My Spring App"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>Description</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full rounded-md px-3 py-2 text-sm"
                  style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
                  placeholder="Optional description"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
                  System Prompt
                </label>
                <textarea
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  className="w-full rounded-md px-3 py-2 text-sm resize-none"
                  style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
                  rows={3}
                  placeholder="You are a Spring Boot expert..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
                  Conventions
                </label>
                <textarea
                  value={conventions}
                  onChange={(e) => setConventions(e.target.value)}
                  className="w-full rounded-md px-3 py-2 text-sm resize-none"
                  style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
                  rows={4}
                  placeholder="# Coding Standards&#10;- Use constructor injection&#10;- JavaDoc on public methods"
                />
              </div>
            </>
          )}

          {!isNew && tab === 'files' && (
            <>
              <div>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileUpload}
                  className="hidden"
                  accept=".java,.ts,.tsx,.js,.jsx,.py,.go,.rs,.kt,.cs,.rb,.swift,.c,.cpp,.h,.hpp,.sql,.yaml,.yml,.json,.xml,.toml,.md,.txt"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  className="px-4 py-2 rounded text-sm text-white disabled:opacity-50"
                  style={{ backgroundColor: 'var(--accent)' }}
                >
                  {uploading ? 'Uploading...' : 'Upload Files'}
                </button>
              </div>

              {files.length === 0 ? (
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  No files yet. Upload source files to enable context injection.
                </p>
              ) : (
                <div className="space-y-1">
                  {files.map((f) => (
                    <div
                      key={f.id}
                      className="flex items-center justify-between px-3 py-2 rounded text-sm"
                      style={{ backgroundColor: 'var(--bg-secondary)' }}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="truncate font-mono text-xs">{f.file_path}</div>
                        <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                          {f.chunk_count} chunks, {f.total_tokens} tokens
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteFile(f.id)}
                        className="ml-2 px-2 py-0.5 rounded text-xs text-red-500 hover:bg-red-500/10"
                      >
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4" style={{ borderTop: '1px solid var(--border-color)' }}>
          <div>
            {!isNew && (
              <button onClick={handleDelete} className="px-3 py-1.5 rounded text-sm text-red-500 hover:bg-red-500/10">
                Delete Project
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded text-sm"
              style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
            >
              Cancel
            </button>
            {(isNew || tab === 'settings') && (
              <button
                onClick={handleSave}
                disabled={!name.trim()}
                className="px-4 py-1.5 rounded text-sm text-white disabled:opacity-50"
                style={{ backgroundColor: 'var(--accent)' }}
              >
                {isNew ? 'Create' : 'Save'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
