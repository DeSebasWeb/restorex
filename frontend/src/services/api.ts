import type { StatusResponse, BackupRun, Report, AppSettings, ConnectionTestResult, BackupProgress } from '../types'

const BASE = '/api'
const REQUEST_TIMEOUT = 30000 // 30 seconds

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT)

  try {
    const res = await fetch(`${BASE}${url}`, {
      ...options,
      signal: controller.signal,
    })

    // Try to parse JSON, but handle non-JSON responses (e.g., nginx 502 HTML page)
    const contentType = res.headers.get('content-type') || ''
    if (!contentType.includes('application/json')) {
      const text = await res.text()
      throw new Error(
        res.ok ? `Unexpected response format from server` : `Server error (${res.status}): ${text.slice(0, 200)}`
      )
    }

    const data = await res.json()
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
    return data as T
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error('Request timed out — server may be busy or unreachable')
    }
    throw err
  } finally {
    clearTimeout(timeout)
  }
}

export const api = {
  getStatus: () => request<StatusResponse>('/status'),

  getHistory: () => request<{ history: BackupRun[] }>('/history'),

  runBackup: (force: boolean) =>
    request<{ message: string }>('/backup/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force }),
    }),

  getBackupStatus: () => request<{ running: boolean; progress: BackupProgress | null }>('/backup/status'),

  scan: () => request<{ message: string; count: number }>('/scan', { method: 'POST' }),

  getReport: () => request<Report>('/report'),

  getLogs: () => request<{ logs: string[] }>('/logs'),

  // Settings
  getSettings: () => request<{ settings: AppSettings; configured: boolean }>('/settings'),

  saveSettings: (settings: Partial<AppSettings>) =>
    request<{ message: string; configured: boolean }>('/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    }),

  testConnection: (settings?: Partial<AppSettings>) =>
    request<ConnectionTestResult>('/settings/test-connection', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings || {}),
    }),
}
