/**
 * Bridge Chat — Main application component.
 * Manages global state, theme, settings, and renders the chat interface.
 */

import { useCallback, useEffect, useState } from 'react'
import { Chat } from './components/Chat'
import { Settings } from './components/Settings'
import { useChat } from './hooks/useChat'
import type { AppConfig, ModelInfo, Theme } from './types'
import { fetchModels } from './services/api'

const STORAGE_KEY = 'bridge-config'
const THEME_KEY = 'bridge-theme'

/** Load config from localStorage with defaults. */
function loadConfig(): AppConfig {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) return JSON.parse(stored)
  } catch { /* use defaults */ }
  return { apiUrl: 'http://localhost:8000', apiKey: '', model: '' }
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

  const { messages, isLoading, error, sendMessage, clearMessages, stopGeneration } = useChat(
    config.apiUrl,
    config.apiKey
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

  const handleSaveConfig = useCallback((newConfig: AppConfig) => {
    setConfig(newConfig)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newConfig))
  }, [])

  const needsSetup = !config.apiKey

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header
        className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: '1px solid var(--border-color)' }}
      >
        <h1 className="text-lg font-bold">Bridge Chat</h1>
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
    </div>
  )
}

export default App
