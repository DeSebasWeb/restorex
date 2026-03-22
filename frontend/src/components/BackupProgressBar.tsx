import { useState, useEffect } from 'react'
import { Loader2, CheckCircle, Database, Download } from 'lucide-react'
import { api } from '../services/api'
import type { BackupProgress } from '../types'

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`
}

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
    }, 1500)

    // Initial fetch
    api.getBackupStatus().then(d => setProgress(d.progress)).catch(() => {})

    return () => clearInterval(poll)
  }, [])

  if (!progress || !progress.running) return null

  const pct = progress.total > 0 ? Math.round((progress.processed / progress.total) * 100) : 0
  const isDownloading = progress.download_total > 0
  const downloadPct = isDownloading
    ? Math.round((progress.download_bytes / progress.download_total) * 100)
    : 0

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

      {/* Overall progress bar */}
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

      {/* Download progress bar (only when downloading) */}
      {isDownloading && (
        <div className="mt-3 pt-3 border-t theme-border">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5">
              <Download size={12} className="text-cyan-400" />
              <span className="text-xs theme-text-muted">Downloading</span>
            </div>
            <span className="text-xs font-mono theme-text-muted">
              {formatBytes(progress.download_bytes)} / {formatBytes(progress.download_total)}
              <span className="ml-2 text-cyan-400 font-semibold">{downloadPct}%</span>
            </span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-cyan-500/10 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-600 to-cyan-400 rounded-full transition-all duration-300"
              style={{ width: `${downloadPct}%` }}
            />
          </div>
        </div>
      )}

      {/* Last completed */}
      {progress.last_completed_db && (
        <div className="flex items-center gap-1.5 mt-2 text-xs theme-text-faint">
          <CheckCircle size={11} className={
            progress.last_completed_status === 'success' ? 'text-emerald-400' :
            progress.last_completed_status === 'partial' ? 'text-amber-400' :
            'text-red-400'
          } />
          Last: {progress.last_completed_db}
          <span className={
            progress.last_completed_status === 'success' ? 'text-emerald-400' :
            progress.last_completed_status === 'partial' ? 'text-amber-400' :
            'text-red-400'
          }>
            ({progress.last_completed_status})
          </span>
        </div>
      )}
    </div>
  )
}
