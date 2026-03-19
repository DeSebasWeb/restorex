import { useState, useEffect } from 'react'
import { Loader2, CheckCircle, Database } from 'lucide-react'
import { api } from '../services/api'
import type { BackupProgress } from '../types'

export function BackupProgressBar() {
  const [progress, setProgress] = useState<BackupProgress | null>(null)

  useEffect(() => {
    const poll = setInterval(async () => {
      try {
        const data = await api.getBackupStatus()
        setProgress(data.progress)
      } catch {
        // silent
      }
    }, 2000)

    // Initial fetch
    api.getBackupStatus().then(d => setProgress(d.progress)).catch(() => {})

    return () => clearInterval(poll)
  }, [])

  if (!progress || !progress.running) return null

  const pct = progress.total > 0 ? Math.round((progress.processed / progress.total) * 100) : 0

  return (
    <div className="theme-bg-card border theme-border rounded-2xl p-5 animate-fade-up">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Loader2 size={16} className="text-blue-500 animate-spin" />
          <h3 className="text-sm font-semibold theme-text">Backup in Progress</h3>
        </div>
        <span className="text-xs theme-text-muted">
          {progress.processed} / {progress.total} databases
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-2 rounded-full bg-blue-500/10 overflow-hidden mb-3">
        <div
          className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Current DB info */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database size={14} className="text-blue-400" />
          <span className="text-sm font-medium theme-text-secondary">
            {progress.current_db || 'Starting...'}
          </span>
          <span className="text-xs theme-text-muted">
            {progress.current_step}
          </span>
        </div>
        <span className="text-sm font-bold text-blue-400">{pct}%</span>
      </div>

      {/* Last completed */}
      {progress.last_completed_db && (
        <div className="flex items-center gap-1.5 mt-2 text-xs theme-text-faint">
          <CheckCircle size={11} className={progress.last_completed_status === 'success' ? 'text-emerald-400' : 'text-amber-400'} />
          Last: {progress.last_completed_db}
          <span className={progress.last_completed_status === 'success' ? 'text-emerald-400' : 'text-amber-400'}>
            ({progress.last_completed_status})
          </span>
        </div>
      )}
    </div>
  )
}
