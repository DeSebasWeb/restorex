import { useEffect, useState, useRef } from 'react'
import { RefreshCw, Download, Terminal } from 'lucide-react'
import { api } from '../services/api'

function colorizeLog(line: string) {
  if (line.includes('[ERROR]') || line.includes('ERROR'))
    return 'text-red-400'
  if (line.includes('[WARNING]') || line.includes('WARNING'))
    return 'text-amber-400'
  if (line.includes('[INFO]') && (line.includes('OK ') || line.includes('complete')))
    return 'text-emerald-400'
  if (line.includes('[INFO]'))
    return 'text-blue-300'
  if (line.includes('Connecting') || line.includes('connected'))
    return 'text-purple-400'
  return 'theme-text-muted'
}

export function LogsPage() {
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)

  const loadLogs = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getLogs()
      setLogs(data.logs || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load logs')
    } finally {
      setLoading(false)
    }
  }

  const downloadLogs = () => {
    const blob = new Blob([logs.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `restorex-logs-${new Date().toISOString().slice(0, 10)}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  useEffect(() => { loadLogs() }, [])

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  return (
    <div className="p-7 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold theme-text">Application Logs</h2>
          <p className="text-xs theme-text-muted mt-0.5">{logs.length} lines</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-xs theme-text-muted cursor-pointer">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={e => setAutoScroll(e.target.checked)}
              className="rounded border-gray-600 bg-transparent text-blue-500 focus:ring-blue-500/20 w-3.5 h-3.5"
            />
            Auto-scroll
          </label>

          <button
            onClick={downloadLogs}
            disabled={logs.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold
                       border theme-border theme-text-tertiary hover:theme-text theme-border-hover
                       disabled:opacity-30 transition-all"
          >
            <Download size={13} />
            Export
          </button>

          <button
            onClick={loadLogs}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold
                       bg-blue-600/80 text-white hover:bg-blue-600
                       disabled:opacity-40 transition-all"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Terminal */}
      <div className="theme-bg-primary border theme-border rounded-2xl overflow-hidden">
        {/* Terminal header */}
        <div className="px-4 py-2.5 theme-bg-secondary border-b theme-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500/80" />
              <div className="w-3 h-3 rounded-full bg-amber-500/80" />
              <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
            </div>
            <span className="text-[11px] theme-text-faint ml-2 flex items-center gap-1">
              <Terminal size={11} />
              restorex &mdash; logs
            </span>
          </div>
        </div>

        {/* Log content */}
        <div className="max-h-[600px] overflow-y-auto p-4 font-mono text-[12px] leading-[1.8]">
          {logs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 theme-text-faint">
              <Terminal size={32} className="mb-2 opacity-30" />
              <p className="text-sm">{error || 'No logs available'}</p>
              <p className="text-xs mt-1">{error ? 'Check backend connection' : 'Click "Refresh" to load'}</p>
            </div>
          ) : (
            <>
              {logs.map((line, i) => (
                <div key={i} className="flex theme-hover -mx-2 px-2 rounded">
                  <span className="w-10 shrink-0 text-right pr-3 theme-text-faint select-none">{i + 1}</span>
                  <span className={colorizeLog(line)}>{line}</span>
                </div>
              ))}
              <div ref={bottomRef} />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
