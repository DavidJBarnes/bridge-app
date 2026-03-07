/**
 * API client for the Bridge Model API.
 * Handles completions, chat, streaming, model listing, and project management.
 */

import type { ChatMessage, ModelInfo, Project, ProjectFile } from '../types'

/** Build authorization headers for API requests. */
function authHeaders(apiKey: string): Record<string, string> {
  return {
    'Authorization': `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
  }
}

/** Build auth headers without content-type (for multipart). */
function authOnly(apiKey: string): Record<string, string> {
  return { 'Authorization': `Bearer ${apiKey}` }
}

/**
 * Send a streaming chat request and call onToken for each token.
 * @param apiUrl - Base URL of the Bridge API.
 * @param apiKey - API key for authentication.
 * @param messages - Conversation message history.
 * @param onToken - Callback invoked with each generated token.
 * @param signal - Optional AbortSignal to cancel the request.
 * @param projectId - Optional project ID for context injection.
 * @returns The complete response text.
 */
export async function streamChat(
  apiUrl: string,
  apiKey: string,
  messages: ChatMessage[],
  onToken: (token: string) => void,
  signal?: AbortSignal,
  projectId?: number | null,
): Promise<string> {
  const body: Record<string, unknown> = {
    messages: messages.map((m) => ({ role: m.role, content: m.content })),
    stream: true,
  }
  if (projectId) {
    body.project_id = projectId
    body.include_conventions = true
  }

  const response = await fetch(`${apiUrl}/v1/chat`, {
    method: 'POST',
    headers: authHeaders(apiKey),
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`API error ${response.status}: ${error}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let fullText = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value, { stream: true })
    const lines = chunk.split('\n')

    for (const line of lines) {
      const trimmed = line.trim()
      if (trimmed.startsWith('data: ') && trimmed !== 'data: [DONE]') {
        try {
          const data = JSON.parse(trimmed.slice(6))
          if (data.token) {
            fullText += data.token
            onToken(data.token)
          }
        } catch {
          // Skip malformed SSE lines
        }
      }
    }
  }

  return fullText
}

/**
 * Fetch available models from the API.
 * @param apiUrl - Base URL of the Bridge API.
 * @param apiKey - API key for authentication.
 * @returns List of available models.
 */
export async function fetchModels(
  apiUrl: string,
  apiKey: string,
): Promise<ModelInfo[]> {
  const response = await fetch(`${apiUrl}/v1/models`, {
    headers: authHeaders(apiKey),
  })

  if (!response.ok) {
    throw new Error(`API error ${response.status}`)
  }

  const data = await response.json()
  return data.models
}

// --- Project API ---

export async function fetchProjects(
  apiUrl: string,
  apiKey: string,
): Promise<Project[]> {
  const response = await fetch(`${apiUrl}/v1/projects`, {
    headers: authHeaders(apiKey),
  })
  if (!response.ok) throw new Error(`API error ${response.status}`)
  const data = await response.json()
  return data.projects
}

export async function createProject(
  apiUrl: string,
  apiKey: string,
  project: { name: string; description?: string; conventions?: string; system_prompt?: string },
): Promise<Project> {
  const response = await fetch(`${apiUrl}/v1/projects`, {
    method: 'POST',
    headers: authHeaders(apiKey),
    body: JSON.stringify(project),
  })
  if (!response.ok) throw new Error(`API error ${response.status}`)
  return response.json()
}

export async function updateProject(
  apiUrl: string,
  apiKey: string,
  projectId: number,
  updates: { name?: string; description?: string; conventions?: string; system_prompt?: string },
): Promise<Project> {
  const response = await fetch(`${apiUrl}/v1/projects/${projectId}`, {
    method: 'PUT',
    headers: authHeaders(apiKey),
    body: JSON.stringify(updates),
  })
  if (!response.ok) throw new Error(`API error ${response.status}`)
  return response.json()
}

export async function deleteProject(
  apiUrl: string,
  apiKey: string,
  projectId: number,
): Promise<void> {
  const response = await fetch(`${apiUrl}/v1/projects/${projectId}`, {
    method: 'DELETE',
    headers: authHeaders(apiKey),
  })
  if (!response.ok) throw new Error(`API error ${response.status}`)
}

export async function fetchProjectFiles(
  apiUrl: string,
  apiKey: string,
  projectId: number,
): Promise<ProjectFile[]> {
  const response = await fetch(`${apiUrl}/v1/projects/${projectId}/files`, {
    headers: authHeaders(apiKey),
  })
  if (!response.ok) throw new Error(`API error ${response.status}`)
  const data = await response.json()
  return data.files
}

export async function uploadFile(
  apiUrl: string,
  apiKey: string,
  projectId: number,
  file: File,
  filePath: string,
): Promise<{ file_id: number; chunk_count: number; total_tokens: number }> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('file_path', filePath)

  const response = await fetch(`${apiUrl}/v1/projects/${projectId}/files`, {
    method: 'POST',
    headers: authOnly(apiKey),
    body: formData,
  })
  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Upload failed: ${error}`)
  }
  return response.json()
}

export async function deleteFile(
  apiUrl: string,
  apiKey: string,
  projectId: number,
  fileId: number,
): Promise<void> {
  const response = await fetch(`${apiUrl}/v1/projects/${projectId}/files/${fileId}`, {
    method: 'DELETE',
    headers: authHeaders(apiKey),
  })
  if (!response.ok) throw new Error(`API error ${response.status}`)
}
