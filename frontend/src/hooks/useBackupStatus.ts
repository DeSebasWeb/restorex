import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'
import type { StatusResponse, BackupRun } from '../types'

export function useBackupStatus() {
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [history, setHistory] = useState<BackupRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [statusData, historyData] = await Promise.all([
        api.getStatus(),
        api.getHistory(),
      ])
      setStatus(statusData)
      setHistory(historyData.history || [])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 15000)
    return () => clearInterval(interval)
  }, [refresh])

  return { status, history, loading, error, refresh }
}
