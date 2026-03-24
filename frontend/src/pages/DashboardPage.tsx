import { Database, CheckCircle, AlertTriangle, XCircle, TrendingUp, HardDrive } from 'lucide-react'
import { StatCard } from '../components/StatCard'
import { StatusDot } from '../components/StatusDot'
import { ProgressRing } from '../components/ProgressRing'
import { BackupProgressBar } from '../components/BackupProgressBar'
import { fmtNum, fmtSize, timeAgo, formatTimestamp } from '../utils/format'
import type { DatabaseStatus, BackupRun } from '../types'

interface Props {
  databases: DatabaseStatus[]
  history: BackupRun[]
  backupRunning: boolean
}

export function DashboardPage({ databases, history, backupRunning }: Props) {
  const backedUp = databases.filter(d => d.last_backup !== null && !d.needs_backup).length
  const pending = databases.filter(d => d.last_backup === null || d.needs_backup).length
  const totalRows = databases.reduce((acc, d) => acc + d.live_rows, 0)
  const recentRuns = history.slice(0, 8)
  const lastRun = history[0] ?? null
  const recentFailed = lastRun?.failed ?? 0
  const coveragePercent = databases.length > 0 ? Math.round((backedUp / databases.length) * 100) : 0

  return (
    <div className="p-7 space-y-6">
      {/* ── Stats Grid ──────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4 stagger-children">
        <StatCard icon={<Database size={22} />} value={databases.length} label="Databases" color="blue" />
        <StatCard icon={<CheckCircle size={22} />} value={backedUp} label="Backed Up" color="green" subtitle={`${coveragePercent}% coverage`} />
        <StatCard icon={<AlertTriangle size={22} />} value={pending} label="Pending" color="yellow" />
        <StatCard icon={<XCircle size={22} />} value={recentFailed} label="Last Failures" color="red" />
        <StatCard icon={<TrendingUp size={22} />} value={fmtNum(totalRows)} label="Total Rows" color="purple" />
      </div>

      {/* ── Live Progress ─────────────────────────────────────── */}
      {backupRunning && <BackupProgressBar />}

      {/* ── Coverage + Activity ──────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Coverage Ring */}
        <div className="theme-bg-card border theme-border rounded-2xl p-6 flex flex-col items-center justify-center">
          <ProgressRing percentage={coveragePercent} label="Backup Coverage" />
          <p className="text-xs theme-text-faint mt-3 text-center">
            {backedUp} of {databases.length} databases protected
          </p>
        </div>

        {/* Recent Activity */}
        <div className="xl:col-span-2 theme-bg-card border theme-border rounded-2xl overflow-hidden">
          <div className="px-5 py-4 border-b theme-border flex items-center justify-between">
            <h2 className="text-sm font-semibold theme-text">Recent Backup Runs</h2>
            {lastRun && (
              <span className="text-[10px] theme-text-faint">Last: {timeAgo(lastRun.started_at)}</span>
            )}
          </div>

          <div className="divide-y divide-[var(--border)]">
            {recentRuns.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 theme-text-faint">
                <HardDrive size={32} className="mb-2 opacity-30" />
                <p className="text-sm">No backup runs yet</p>
                <p className="text-xs mt-1">Click "Smart Backup" to start</p>
              </div>
            ) : (
              recentRuns.map((run, i) => {
                const start = new Date(run.started_at)
                const end = run.finished_at ? new Date(run.finished_at) : null
                const dur = end ? `${Math.round((end.getTime() - start.getTime()) / 1000)}s` : '--'
                const total = run.backed_up + run.skipped + run.failed
                const successRate = total > 0 ? Math.round(((run.backed_up + run.skipped) / total) * 100) : 0

                return (
                  <div key={i} className="px-5 py-3.5 flex items-center justify-between theme-hover transition-colors">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold
                        ${run.failed > 0 ? 'bg-red-500/10 text-red-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                        {successRate}%
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[13px] font-medium theme-text-secondary">
                          {start.toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short' })}
                        </span>
                        <span className="text-[11px] theme-text-faint">
                          {start.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })} &middot; {dur}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-5 text-[12px]">
                      <span className="flex items-center gap-1 text-emerald-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        {run.backed_up}
                      </span>
                      <span className="flex items-center gap-1 theme-text-muted">
                        <span className="w-1.5 h-1.5 rounded-full bg-gray-600" />
                        {run.skipped}
                      </span>
                      {run.failed > 0 && (
                        <span className="flex items-center gap-1 text-red-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                          {run.failed}
                        </span>
                      )}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>

      {/* ── Database Overview Table ──────────────────────────── */}
      <div className="theme-bg-card border theme-border rounded-2xl overflow-hidden">
        <div className="px-5 py-4 border-b theme-border flex items-center justify-between">
          <h2 className="text-sm font-semibold theme-text">Database Overview</h2>
          <div className="flex items-center gap-2">
            {backupRunning && (
              <StatusDot status="green" label="Running" pulse />
            )}
            <span className="text-[11px] theme-text-faint">{databases.length} databases</span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="text-left theme-bg-table-header">
                {['', 'Database', 'Size', 'Tables', 'Rows', 'Changes (I/U/D)', 'Last Backup', 'Status'].map(h => (
                  <th key={h} className="px-4 py-3 text-[10px] uppercase tracking-wider font-semibold theme-text-muted">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {databases.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-12">
                    <div className="flex flex-col items-center theme-text-faint">
                      <Database size={36} className="mb-2 opacity-20" />
                      <p className="text-sm font-medium">No databases loaded</p>
                      <p className="text-xs mt-1">Click "Scan DBs" to discover databases on the server</p>
                    </div>
                  </td>
                </tr>
              ) : (
                databases.map(db => {
                  return (
                    <tr key={db.name} className="theme-hover transition-colors">
                      <td className="px-4 py-3 w-8">
                        <StatusDot status={db.last_backup && !db.needs_backup ? 'green' : db.needs_backup ? 'yellow' : 'gray'} />
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-semibold theme-text-secondary">{db.name}</span>
                      </td>
                      <td className="px-4 py-3 theme-text-tertiary font-mono text-xs">{db.size}</td>
                      <td className="px-4 py-3 theme-text-tertiary">{db.tables}</td>
                      <td className="px-4 py-3 theme-text-tertiary font-mono text-xs">{fmtNum(db.live_rows)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5 text-xs font-mono">
                          <span className="text-emerald-400">{fmtNum(db.inserts)}</span>
                          <span className="theme-text-faint">/</span>
                          <span className="text-blue-400">{fmtNum(db.updates)}</span>
                          <span className="theme-text-faint">/</span>
                          <span className="text-red-400">{fmtNum(db.deletes)}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {db.last_backup ? (
                          <div className="flex flex-col">
                            <span className="text-xs theme-text-tertiary">{formatTimestamp(db.last_backup.timestamp)}</span>
                            <span className="text-[10px] theme-text-faint">
                              {fmtSize(db.last_backup.backup_size + db.last_backup.sql_size)}
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-amber-500/80 font-medium">Never</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {db.last_backup && !db.needs_backup ? (
                          <StatusDot status="green" label="Protected" />
                        ) : db.needs_backup ? (
                          <StatusDot status="yellow" label="Needs Backup" />
                        ) : (
                          <StatusDot status="gray" label="No Data" />
                        )}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
