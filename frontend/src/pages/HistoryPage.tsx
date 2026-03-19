import { useState } from 'react'
import { ChevronDown, ChevronUp, CheckCircle, XCircle, SkipForward, Clock } from 'lucide-react'
import { fmtSize } from '../utils/format'
import type { BackupRun } from '../types'

interface Props {
  history: BackupRun[]
}

function RunCard({ run, index }: { run: BackupRun; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const start = new Date(run.started_at)
  const end = run.finished_at ? new Date(run.finished_at) : null
  const dur = end ? Math.round((end.getTime() - start.getTime()) / 1000) : null
  const total = run.backed_up + run.skipped + run.failed
  const successRate = total > 0 ? Math.round(((run.backed_up + run.skipped) / total) * 100) : 0
  const hasFailed = run.failed > 0

  return (
    <div className={`theme-bg-card border rounded-2xl overflow-hidden transition-all duration-200
      ${hasFailed ? 'border-red-500/15' : 'theme-border'}
      ${expanded ? 'ring-1 ring-blue-500/10' : ''}`}>

      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center justify-between theme-hover transition-colors"
      >
        <div className="flex items-center gap-4">
          {/* Timeline dot */}
          <div className="flex flex-col items-center">
            <div className={`w-3 h-3 rounded-full ${hasFailed ? 'bg-red-500' : 'bg-emerald-500'} shadow-lg
              ${hasFailed ? 'shadow-red-500/30' : 'shadow-emerald-500/30'}`} />
            {index > 0 && <div className="w-px h-4 bg-white/[0.06] -mt-px" />}
          </div>

          <div className="flex flex-col items-start gap-0.5">
            <span className="text-sm font-semibold theme-text">
              {start.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
            </span>
            <span className="text-[11px] theme-text-muted flex items-center gap-1.5">
              <Clock size={10} />
              {start.toLocaleTimeString('es-CO')}
              {dur !== null && <>&middot; {dur < 60 ? `${dur}s` : `${Math.floor(dur / 60)}m ${dur % 60}s`}</>}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-5">
          {/* Stats pills */}
          <div className="flex items-center gap-3 text-xs">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold">
              <CheckCircle size={12} />
              {run.backed_up}
            </span>
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-gray-500/10 theme-text-tertiary font-semibold">
              <SkipForward size={12} />
              {run.skipped}
            </span>
            {hasFailed && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-red-500/10 text-red-400 font-semibold">
                <XCircle size={12} />
                {run.failed}
              </span>
            )}
          </div>

          {/* Success rate */}
          <div className={`text-sm font-bold ${hasFailed ? 'text-red-400' : 'text-emerald-400'}`}>
            {successRate}%
          </div>

          {expanded ? <ChevronUp size={16} className="theme-text-muted" /> : <ChevronDown size={16} className="theme-text-muted" />}
        </div>
      </button>

      {/* Expanded details */}
      {expanded && run.results.length > 0 && (
        <div className="border-t theme-border">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="theme-bg-table-header">
                  <th className="px-4 py-2.5 text-left text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Database</th>
                  <th className="px-4 py-2.5 text-left text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Status</th>
                  <th className="px-4 py-2.5 text-left text-[10px] uppercase tracking-wider font-semibold theme-text-muted">.backup</th>
                  <th className="px-4 py-2.5 text-left text-[10px] uppercase tracking-wider font-semibold theme-text-muted">.sql</th>
                  <th className="px-4 py-2.5 text-left text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Duration</th>
                  <th className="px-4 py-2.5 text-left text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Detail</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {run.results.map((r, j) => (
                  <tr key={j} className="hover:bg-white/[0.01]">
                    <td className="px-4 py-2.5 font-medium theme-text-secondary">{r.db_name}</td>
                    <td className="px-4 py-2.5">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold
                        ${r.status === 'success' ? 'bg-emerald-500/10 text-emerald-400' :
                          r.status === 'skipped' ? 'bg-gray-500/10 theme-text-tertiary' :
                          'bg-red-500/10 text-red-400'}`}>
                        {r.status === 'success' ? <CheckCircle size={10} /> :
                         r.status === 'skipped' ? <SkipForward size={10} /> :
                         <XCircle size={10} />}
                        {r.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 theme-text-muted font-mono">{fmtSize(r.backup_size ?? 0)}</td>
                    <td className="px-4 py-2.5 theme-text-muted font-mono">{fmtSize(r.sql_size ?? 0)}</td>
                    <td className="px-4 py-2.5 theme-text-muted font-mono">
                      {r.duration_seconds ? `${r.duration_seconds}s` : '--'}
                    </td>
                    <td className="px-4 py-2.5 theme-text-faint max-w-[200px] truncate">
                      {r.error || r.reason || '--'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

export function HistoryPage({ history }: Props) {
  const totalBackups = history.reduce((acc, r) => acc + r.backed_up, 0)
  const totalFailed = history.reduce((acc, r) => acc + r.failed, 0)

  return (
    <div className="p-7 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold theme-text">Backup History</h2>
          <p className="text-xs theme-text-muted mt-0.5">
            {history.length} runs &middot; {totalBackups} backups created &middot; {totalFailed} failures
          </p>
        </div>
      </div>

      {history.length === 0 ? (
        <div className="theme-bg-card border theme-border rounded-2xl p-12 flex flex-col items-center theme-text-faint">
          <Clock size={40} className="mb-3 opacity-20" />
          <p className="text-sm font-medium">No backup history</p>
          <p className="text-xs mt-1">Run your first backup to see the timeline</p>
        </div>
      ) : (
        <div className="space-y-3">
          {history.map((run, i) => (
            <RunCard key={i} run={run} index={i} />
          ))}
        </div>
      )}
    </div>
  )
}
