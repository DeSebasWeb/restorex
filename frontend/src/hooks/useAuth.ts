import { useState, useEffect, useCallback } from 'react'
import type { AuthUser } from '../types'
import { api, setAccessToken, onAuthExpired } from '../services/api'

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  // On mount: try silent refresh (user may have valid refresh cookie)
  useEffect(() => {
    let cancelled = false

    async function tryRestore() {
      try {
        const refreshResult = await api.refresh()
        if (!refreshResult || cancelled) {
          setLoading(false)
          return
        }
        setAccessToken(refreshResult.access_token)
        const { user: me } = await api.getMe()
        if (!cancelled) setUser(me)
      } catch {
        // Not logged in — that's fine
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    tryRestore()
    return () => { cancelled = true }
  }, [])

  // Register auth expiry callback
  useEffect(() => {
    onAuthExpired(() => {
      setUser(null)
      setAccessToken(null)
    })
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const data = await api.login(username, password)
    setAccessToken(data.access_token)
    setUser(data.user)
    return data
  }, [])

  const logout = useCallback(async () => {
    try { await api.logout() } catch { /* ignore */ }
    setAccessToken(null)
    setUser(null)
  }, [])

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    const data = await api.changePassword(currentPassword, newPassword)
    setAccessToken(data.access_token)
    setUser(data.user)
  }, [])

  return {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    logout,
    changePassword,
  }
}
