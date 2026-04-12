import type { StatusResponse, BackupRun, Report, AppSettings, ConnectionTestResult, BackupProgress, NotificationChannel, NotificationTestResult, LoginResponse, AuthUser, ManagedUser, CreateUserRequest, UpdateUserRequest, Role } from '../types'

const BASE = '/api'
const REQUEST_TIMEOUT = 30000

// ── Token management (in memory only — never localStorage) ──────

let _accessToken: string | null = null
let _authExpiredCallback: (() => void) | null = null
let _refreshPromise: Promise<string | null> | null = null

export function setAccessToken(token: string | null) { _accessToken = token }
export function getAccessToken() { return _accessToken }
export function onAuthExpired(cb: () => void) { _authExpiredCallback = cb }

// ── Core request function with auto-refresh ─────────────────────

async function request<T>(url: string, options?: RequestInit, _isRetry = false): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT)

  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string> || {}),
  }
  if (_accessToken) {
    headers['Authorization'] = `Bearer ${_accessToken}`
  }

  try {
    const res = await fetch(`${BASE}${url}`, {
      ...options,
      headers,
      credentials: 'include', // Send httpOnly cookies
      signal: controller.signal,
    })

    // Handle 401 with auto-refresh (only once)
    if (res.status === 401 && !url.startsWith('/auth/')) {
      const body = await res.json().catch(() => ({}))
      if (!_isRetry) {
        // First 401 — try refreshing regardless of error code
        const newToken = await _silentRefresh()
        if (newToken) {
          return request<T>(url, options, true)
        }
      }
      // Refresh failed or already retried — truly expired
      _accessToken = null
      _authExpiredCallback?.()
      throw new Error(body.error || 'Authentication required')
    }

    const contentType = res.headers.get('content-type') || ''
    if (!contentType.includes('application/json')) {
      const text = await res.text()
      throw new Error(
        res.ok ? 'Unexpected response format from server' : `Server error (${res.status}): ${text.slice(0, 200)}`
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

// ── Silent refresh (mutex to prevent concurrent refreshes) ──────

async function _silentRefresh(): Promise<string | null> {
  if (_refreshPromise) return _refreshPromise

  _refreshPromise = (async () => {
    try {
      const res = await fetch(`${BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      })
      if (!res.ok) return null
      const data = await res.json()
      _accessToken = data.access_token
      return _accessToken
    } catch {
      return null
    } finally {
      _refreshPromise = null
    }
  })()

  return _refreshPromise
}

// ── Public API ──────────────────────────────────────────────────

export const api = {
  // Auth
  login: (username: string, password: string) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }),

  refresh: async (): Promise<{ access_token: string } | null> => {
    const token = await _silentRefresh()
    return token ? { access_token: token } : null
  },

  logout: () =>
    request<{ message: string }>('/auth/logout', { method: 'POST' }),

  changePassword: (current_password: string, new_password: string) =>
    request<{ message: string; access_token: string; user: AuthUser }>('/auth/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password, new_password }),
    }),

  getMe: () => request<{ user: AuthUser }>('/auth/me'),

  // Status
  getStatus: () => request<StatusResponse>('/status'),

  getHistory: () => request<{ history: BackupRun[] }>('/history'),

  runBackup: (force: boolean) =>
    request<{ message: string }>('/backup/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force }),
    }),

  getBackupStatus: () => request<{ running: boolean; progress: BackupProgress | null }>('/backup/status'),

  cancelBackup: () => request<{ message: string }>('/backup/cancel', { method: 'POST' }),

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

  // Notifications (global — admin only)
  getNotifications: () => request<{ channels: NotificationChannel[] }>('/notifications'),

  saveNotification: (channel: string, data: Partial<NotificationChannel>) =>
    request<{ message: string }>(`/notifications/${channel}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  testNotification: (channel: string) =>
    request<NotificationTestResult>(`/notifications/${channel}/test`, {
      method: 'POST',
    }),

  // Notifications (per-user)
  getUserNotifications: () => request<{ channels: NotificationChannel[] }>('/users/me/notifications'),

  saveUserNotification: (channel: string, data: Partial<NotificationChannel>) =>
    request<{ message: string }>(`/users/me/notifications/${channel}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  testUserNotification: (channel: string) =>
    request<NotificationTestResult>(`/users/me/notifications/${channel}/test`, {
      method: 'POST',
    }),

  // Storage / Browse
  getDrives: () => request<{ drives: { letter: string; path: string }[] }>('/storage/drives'),

  browsePath: (drive: string, path: string) =>
    request<{ drive: string; path: string; display: string; folders: string[] }>(
      `/storage/browse?drive=${encodeURIComponent(drive)}&path=${encodeURIComponent(path)}`
    ),

  createFolder: (drive: string, path: string) =>
    request<{ message: string; display: string }>('/storage/create-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ drive, path }),
    }),

  // User Management
  getUsers: (includeDeleted = false) =>
    request<{ users: ManagedUser[] }>(`/users?include_deleted=${includeDeleted}`),

  getRoles: () => request<{ roles: Role[] }>('/users/roles'),

  createUser: (data: CreateUserRequest) =>
    request<{ user: ManagedUser; message: string }>('/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  updateUser: (id: number, data: UpdateUserRequest) =>
    request<{ user: ManagedUser; message: string }>(`/users/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  deleteUser: (id: number) =>
    request<{ message: string }>(`/users/${id}`, { method: 'DELETE' }),

  restoreUser: (id: number) =>
    request<{ user: ManagedUser; message: string }>(`/users/${id}/restore`, { method: 'POST' }),

  resetUserPassword: (id: number, new_password: string) =>
    request<{ message: string }>(`/users/${id}/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password }),
    }),
}
