/**
 * Settings panel for API configuration and theme selection.
 */

import { useCallback, useState } from 'react'
import type { AppConfig, ModelInfo, Theme } from '../types'

/** @param config - Current app configuration. */
/** @param onSave - Callback when settings are saved. */
/** @param onClose - Callback to close the settings panel. */
/** @param theme - Current theme. */
/** @param onThemeChange - Callback when theme changes. */
/** @param models - Available models from the API. */
interface SettingsProps {
  config: AppConfig
  onSave: (config: AppConfig) => void
  onClose: () => void
  theme: Theme
  onThemeChange: (theme: Theme) => void
  models: ModelInfo[]
}

/** Settings panel component for configuring the Bridge Chat app. */
export function Settings({ config, onSave, onClose, theme, onThemeChange, models }: SettingsProps) {
  const [apiUrl, setApiUrl] = useState(config.apiUrl)
  const [apiKey, setApiKey] = useState(config.apiKey)
  const [model, setModel] = useState(config.model)

  const handleSave = useCallback(() => {
    onSave({ apiUrl: apiUrl.replace(/\/+$/, ''), apiKey, model })
    onClose()
  }, [apiUrl, apiKey, model, onSave, onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-lg p-6 shadow-xl"
        style={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-bold mb-4">Settings</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
              API URL
            </label>
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="w-full rounded-md px-3 py-2 text-sm"
              style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
              placeholder="http://localhost:8000"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
              API Key
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full rounded-md px-3 py-2 text-sm"
              style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
              placeholder="bridge-xxx"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
              Model
            </label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full rounded-md px-3 py-2 text-sm"
              style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
            >
              <option value="">Default</option>
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id} ({m.provider})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
              Theme
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => onThemeChange('light')}
                className={`px-3 py-1 rounded text-sm ${theme === 'light' ? 'font-bold' : ''}`}
                style={{
                  backgroundColor: theme === 'light' ? 'var(--accent)' : 'var(--bg-secondary)',
                  color: theme === 'light' ? '#ffffff' : 'var(--text-primary)',
                }}
              >
                Light
              </button>
              <button
                onClick={() => onThemeChange('dark')}
                className={`px-3 py-1 rounded text-sm ${theme === 'dark' ? 'font-bold' : ''}`}
                style={{
                  backgroundColor: theme === 'dark' ? 'var(--accent)' : 'var(--bg-secondary)',
                  color: theme === 'dark' ? '#ffffff' : 'var(--text-primary)',
                }}
              >
                Dark
              </button>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded text-sm"
            style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 rounded text-sm text-white"
            style={{ backgroundColor: 'var(--accent)' }}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  )
}
