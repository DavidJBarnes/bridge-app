/**
 * Bridge Chat — Main application component.
 * Manages global state, theme, settings, and renders the chat interface.
 */

import { useCallback, useEffect, useState } from 'react'
import { Chat } from './components/Chat'
import { Settings } from './components/Settings'
import { ProjectSelector } from './components/ProjectSelector'
import { ProjectPanel } from './components/ProjectPanel'
import { useChat } from './hooks/useChat'
import type { AppConfig, ModelInfo, Project, Theme } from './types'
import {
  fetchModels,
  fetchProjects,
  fetchProjectFiles,
  createProject,
  updateProject,
  deleteProject,
  uploadFile,
  deleteFile,
} from './services/api'

const STORAGE_KEY = 'bridge-config'
const THEME_KEY = 'bridge-theme'

/** Load config from localStorage with defaults. */
function loadConfig(): AppConfig {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) return JSON.parse(stored)
  } catch { /* use defaults */ }
  return { apiUrl: 'http://localhost:8000', apiKey: '', model: '', activeProjectId: null }
}

/** Load theme preference from localStorage. */
function loadTheme(): Theme {
  return (localStorage.getItem(THEME_KEY) as Theme) || 'dark'
}

/** Root application component. */
function App() {
  const [config, setConfig] = useState<AppConfig>(loadConfig)
  const [theme, setTheme] = useState<Theme>(loadTheme)
  const [showSettings, setShowSettings] = useState(false)
  const [models, setModels] = useState<ModelInfo[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [managingProjectId, setManagingProjectId] = useState<number | null | 'new'>(null)

  const { messages, isLoading, error, sendMessage, clearMessages, stopGeneration } = useChat(
    config.apiUrl,
    config.apiKey,
    config.activeProjectId,
  )

  // Apply theme class to document
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem(THEME_KEY, theme)
  }, [theme])

  // Fetch models when config changes
  useEffect(() => {
    if (config.apiKey) {
      fetchModels(config.apiUrl, config.apiKey)
        .then(setModels)
        .catch(() => setModels([]))
    }
  }, [config.apiUrl, config.apiKey])

  // Fetch projects when config changes
  useEffect(() => {
    if (config.apiKey) {
      fetchProjects(config.apiUrl, config.apiKey)
        .then(setProjects)
        .catch(() => setProjects([]))
    }
  }, [config.apiUrl, config.apiKey])

  const handleSaveConfig = useCallback((newConfig: AppConfig) => {
    setConfig(newConfig)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newConfig))
  }, [])

  const handleSelectProject = useCallback((projectId: number | null) => {
    const newConfig = { ...config, activeProjectId: projectId }
    setConfig(newConfig)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newConfig))
  }, [config])

  const handleProjectSaved = useCallback((project: Project) => {
    setProjects((prev) => {
      const idx = prev.findIndex((p) => p.id === project.id)
      if (idx >= 0) {
        const updated = [...prev]
        updated[idx] = project
        return updated
      }
      return [...prev, project]
    })
    handleSelectProject(project.id)
    setManagingProjectId(null)
  }, [handleSelectProject])

  const handleProjectDeleted = useCallback((projectId: number) => {
    setProjects((prev) => prev.filter((p) => p.id !== projectId))
    if (config.activeProjectId === projectId) {
      handleSelectProject(null)
    }
    setManagingProjectId(null)
  }, [config.activeProjectId, handleSelectProject])

  const handleFetchFiles = useCallback(
    (projectId: number) => fetchProjectFiles(config.apiUrl, config.apiKey, projectId),
    [config.apiUrl, config.apiKey],
  )

  const handleUploadFile = useCallback(
    async (projectId: number, file: File, filePath: string) => {
      await uploadFile(config.apiUrl, config.apiKey, projectId, file, filePath)
      // Refresh project list to update counts
      const updated = await fetchProjects(config.apiUrl, config.apiKey)
      setProjects(updated)
    },
    [config.apiUrl, config.apiKey],
  )

  const handleDeleteFile = useCallback(
    async (projectId: number, fileId: number) => {
      await deleteFile(config.apiUrl, config.apiKey, projectId, fileId)
      const updated = await fetchProjects(config.apiUrl, config.apiKey)
      setProjects(updated)
    },
    [config.apiUrl, config.apiKey],
  )

  const handleCreateProject = useCallback(
    (data: { name: string; description?: string; conventions?: string; system_prompt?: string }) =>
      createProject(config.apiUrl, config.apiKey, data),
    [config.apiUrl, config.apiKey],
  )

  const handleUpdateProject = useCallback(
    (projectId: number, data: { name?: string; description?: string; conventions?: string; system_prompt?: string }) =>
      updateProject(config.apiUrl, config.apiKey, projectId, data),
    [config.apiUrl, config.apiKey],
  )

  const handleDeleteProject = useCallback(
    (projectId: number) => deleteProject(config.apiUrl, config.apiKey, projectId),
    [config.apiUrl, config.apiKey],
  )

  const needsSetup = !config.apiKey
  const managingProject = typeof managingProjectId === 'number'
    ? projects.find((p) => p.id === managingProjectId) ?? null
    : null

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header
        className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: '1px solid var(--border-color)' }}
      >
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold">Bridge Chat</h1>
          {!needsSetup && (
            <ProjectSelector
              projects={projects}
              activeProjectId={config.activeProjectId}
              onSelect={handleSelectProject}
              onCreateNew={() => setManagingProjectId('new')}
              onManage={(id) => setManagingProjectId(id)}
            />
          )}
        </div>
        <button
          onClick={() => setShowSettings(true)}
          className="px-3 py-1 rounded text-sm"
          style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
          aria-label="Open settings"
        >
          Settings
        </button>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        {needsSetup ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center p-8">
              <h2 className="text-xl font-bold mb-4">Welcome to Bridge Chat</h2>
              <p className="mb-4" style={{ color: 'var(--text-secondary)' }}>
                Configure your API key to get started.
              </p>
              <button
                onClick={() => setShowSettings(true)}
                className="px-4 py-2 rounded text-white"
                style={{ backgroundColor: 'var(--accent)' }}
              >
                Open Settings
              </button>
            </div>
          </div>
        ) : (
          <Chat
            messages={messages}
            isLoading={isLoading}
            error={error}
            onSend={sendMessage}
            onStop={stopGeneration}
            onClear={clearMessages}
          />
        )}
      </main>

      {/* Settings modal */}
      {showSettings && (
        <Settings
          config={config}
          onSave={handleSaveConfig}
          onClose={() => setShowSettings(false)}
          theme={theme}
          onThemeChange={setTheme}
          models={models}
        />
      )}

      {/* Project management modal */}
      {managingProjectId !== null && (
        <ProjectPanel
          apiUrl={config.apiUrl}
          apiKey={config.apiKey}
          project={managingProject}
          onClose={() => setManagingProjectId(null)}
          onSaved={handleProjectSaved}
          onDeleted={handleProjectDeleted}
          fetchFiles={handleFetchFiles}
          onUploadFile={handleUploadFile}
          onDeleteFile={handleDeleteFile}
          onCreateProject={handleCreateProject}
          onUpdateProject={handleUpdateProject}
          onDeleteProject={handleDeleteProject}
        />
      )}
    </div>
  )
}

export default App
