import { useState, useEffect } from 'react'
import { FileBarChart, Printer, RefreshCw, Server, Database, Shield, HardDrive, TrendingUp, AlertTriangle } from 'lucide-react'
import { ProgressRing } from '../components/ProgressRing'
import { fmtSize } from '../utils/format'
import { api } from '../services/api'
import type { Report } from '../types'

export function ReportsPage() {
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(false)

  const loadReport = async () => {
    setLoading(true)
    try {
      const data = await api.getReport()
      setReport(data)
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadReport() }, [])

  const handlePrint = () => window.print()

  if (!report) {
    return (
      <div className="p-7">
        <div className="theme-bg-card border theme-border rounded-2xl p-12 flex flex-col items-center">
          <FileBarChart size={40} className="theme-text-faint mb-3" />
          <p className="text-sm theme-text-muted">Loading report...</p>
          <button
            onClick={loadReport}
            disabled={loading}
            className="mt-4 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 transition-all disabled:opacity-50"
          >
            <RefreshCw size={14} className={`inline mr-2 ${loading ? 'animate-spin' : ''}`} />
            Generate Report
          </button>
        </div>
      </div>
    )
  }

  const protectedDBs = report.databases.filter(d => d.last_backup).length
  const unprotected = report.databases.filter(d => !d.last_backup)
  const coveragePercent = report.total_databases > 0
    ? Math.round((protectedDBs / report.total_databases) * 100)
    : 0

  return (
    <div className="p-7 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold theme-text">Executive Report</h2>
          <p className="text-xs theme-text-muted mt-0.5">
            Generated {new Date(report.generated_at).toLocaleString('es-CO')}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadReport}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold
                       border theme-border theme-text-tertiary hover:theme-text theme-border-hover
                       disabled:opacity-40 transition-all"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button
            onClick={handlePrint}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold
                       bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/20
                       hover:brightness-110 transition-all"
          >
            <Printer size={14} />
            Print Report
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 stagger-children">
        <div className="theme-bg-card border theme-border rounded-2xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-blue-500/15 flex items-center justify-center">
              <Server size={18} className="text-blue-400" />
            </div>
            <span className="text-[11px] theme-text-muted font-semibold uppercase tracking-wider">Server</span>
          </div>
          <p className="text-lg font-bold theme-text">{report.server}</p>
          <p className="text-xs theme-text-muted mt-1">{report.total_databases} databases monitored</p>
        </div>

        <div className="theme-bg-card border theme-border rounded-2xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/15 flex items-center justify-center">
              <TrendingUp size={18} className="text-emerald-400" />
            </div>
            <span className="text-[11px] theme-text-muted font-semibold uppercase tracking-wider">Success Rate</span>
          </div>
          <p className="text-lg font-bold theme-text">{report.success_rate}%</p>
          <p className="text-xs theme-text-muted mt-1">{report.total_backups_created} backups created</p>
        </div>

        <div className="theme-bg-card border theme-border rounded-2xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/15 flex items-center justify-center">
              <HardDrive size={18} className="text-purple-400" />
            </div>
            <span className="text-[11px] theme-text-muted font-semibold uppercase tracking-wider">Storage</span>
          </div>
          <p className="text-lg font-bold theme-text">{report.local_storage_used}</p>
          <p className="text-xs theme-text-muted mt-1">{report.retention_days}-day retention policy</p>
        </div>

        <div className="theme-bg-card border theme-border rounded-2xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/15 flex items-center justify-center">
              <Shield size={18} className="text-amber-400" />
            </div>
            <span className="text-[11px] theme-text-muted font-semibold uppercase tracking-wider">Runs</span>
          </div>
          <p className="text-lg font-bold theme-text">{report.total_backup_runs}</p>
          <p className="text-xs theme-text-muted mt-1">{report.total_failures} total failures</p>
        </div>
      </div>

      {/* Coverage + Unprotected */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Coverage ring */}
        <div className="theme-bg-card border theme-border rounded-2xl p-8 flex flex-col items-center justify-center">
          <ProgressRing percentage={coveragePercent} size={140} label="Database Coverage" />
          <div className="mt-4 text-center">
            <p className="text-sm theme-text-secondary">
              <span className="font-bold text-emerald-400">{protectedDBs}</span> of{' '}
              <span className="font-bold theme-text">{report.total_databases}</span> databases protected
            </p>
          </div>
        </div>

        {/* Unprotected databases alert */}
        <div className="xl:col-span-2 theme-bg-card border theme-border rounded-2xl overflow-hidden">
          <div className="px-5 py-4 border-b theme-border flex items-center gap-2">
            <AlertTriangle size={16} className="text-amber-400" />
            <h3 className="text-sm font-semibold theme-text">Databases Without Backup</h3>
            <span className="ml-auto text-[11px] theme-text-faint">{unprotected.length} databases</span>
          </div>
          {unprotected.length === 0 ? (
            <div className="p-8 text-center">
              <Shield size={32} className="mx-auto mb-2 text-emerald-400 opacity-50" />
              <p className="text-sm text-emerald-400 font-medium">All databases are protected!</p>
            </div>
          ) : (
            <div className="divide-y divide-[var(--border)] max-h-[300px] overflow-y-auto">
              {unprotected.map(db => (
                <div key={db.name} className="px-5 py-3 flex items-center justify-between theme-hover">
                  <div className="flex items-center gap-3">
                    <Database size={16} className="text-amber-500/50" />
                    <div>
                      <span className="text-sm font-medium theme-text-secondary">{db.name}</span>
                      <span className="text-xs theme-text-faint ml-2">{db.size}</span>
                    </div>
                  </div>
                  <div className="text-xs theme-text-muted">
                    {db.tables} tables &middot; {db.live_rows.toLocaleString('es-CO')} rows
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Full database list */}
      <div className="theme-bg-card border theme-border rounded-2xl overflow-hidden">
        <div className="px-5 py-4 border-b theme-border">
          <h3 className="text-sm font-semibold theme-text">Complete Database Inventory</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="theme-bg-table-header">
                <th className="px-4 py-3 text-left text-[10px] uppercase tracking-wider font-semibold theme-text-muted">#</th>
                <th className="px-4 py-3 text-left text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Database</th>
                <th className="px-4 py-3 text-left text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Size</th>
                <th className="px-4 py-3 text-left text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Tables</th>
                <th className="px-4 py-3 text-left text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Rows</th>
                <th className="px-4 py-3 text-left text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Last Backup</th>
                <th className="px-4 py-3 text-left text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Backup Size</th>
                <th className="px-4 py-3 text-left text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {report.databases.map((db, i) => (
                <tr key={db.name} className="theme-hover">
                  <td className="px-4 py-2.5 theme-text-faint font-mono text-xs">{i + 1}</td>
                  <td className="px-4 py-2.5 font-semibold theme-text-secondary">{db.name}</td>
                  <td className="px-4 py-2.5 theme-text-tertiary font-mono text-xs">{db.size}</td>
                  <td className="px-4 py-2.5 theme-text-tertiary">{db.tables}</td>
                  <td className="px-4 py-2.5 theme-text-tertiary font-mono text-xs">{db.live_rows.toLocaleString('es-CO')}</td>
                  <td className="px-4 py-2.5 text-xs">
                    {db.last_backup ? (
                      <span className="theme-text-tertiary">{db.last_backup.timestamp}</span>
                    ) : (
                      <span className="text-amber-500">Never</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 theme-text-muted font-mono text-xs">
                    {db.last_backup ? fmtSize(db.last_backup.backup_size + db.last_backup.sql_size) : '--'}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold
                      ${db.last_backup ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
                      {db.last_backup ? 'Protected' : 'At Risk'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
