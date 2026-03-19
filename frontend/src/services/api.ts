import type { StatusResponse, BackupRun, Report, AppSettings, ConnectionTestResult, BackupProgress } from '../types'

const BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, options)
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
  return data as T
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
