import { useState, useEffect } from 'react'
import { Search, Download, Zap, Wifi, WifiOff, Sun, Moon } from 'lucide-react'
import type { Theme } from '../hooks/useTheme'
interface TopBarProps {
  title: string
  backupRunning: boolean
  onScan: () => void
  onBackup: (force: boolean) => void
  scanning: boolean
  theme: Theme
  onToggleTheme: () => void
}

function LiveClock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return (
    <span className="text-xs theme-text-muted font-mono tabular-nums">
      {now.toLocaleDateString('es-CO', { weekday: 'short', day: '2-digit', month: 'short' })}
      {' '}
      {now.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
    </span>
  )
}

export function TopBar({ title, backupRunning, onScan, onBackup, scanning, theme, onToggleTheme }: TopBarProps) {
  const [connected, setConnected] = useState(true)

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch('/api/health')
        setConnected(res.ok)
      } catch {
        setConnected(false)
      }
    }
    check()
    const id = setInterval(check, 30000)
    return () => clearInterval(id)
  }, [])

  return (
    <header className="h-16 px-7 flex items-center justify-between theme-border border-b theme-bg-secondary/80 backdrop-blur-md sticky top-0 z-40 transition-colors duration-300">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold theme-text">{title}</h1>

        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wide
          ${connected
            ? 'bg-emerald-500/10 text-emerald-500'
            : 'bg-red-500/10 text-red-400'
          }`}
        >
          {connected ? <Wifi size={11} /> : <WifiOff size={11} />}
          {connected ? 'Connected' : 'Offline'}
        </div>

        {backupRunning && (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 animate-pulse-glow">
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-[11px] font-semibold text-blue-400">Backup in progress...</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        <LiveClock />

        <div className="w-px h-6 theme-border border-l" />

        {/* Theme toggle */}
        <button
          onClick={onToggleTheme}
          className="w-9 h-9 rounded-xl flex items-center justify-center theme-text-muted hover:theme-text theme-border border
                     hover:bg-amber-500/10 hover:text-amber-500 hover:border-amber-500/20
                     transition-all duration-200"
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        <div className="w-px h-6 theme-border border-l" />

        <button
          onClick={onScan}
          disabled={scanning}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold
                     theme-border border theme-text-muted hover:theme-text
                     disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
        >
          <Search size={14} className={scanning ? 'animate-spin-slow' : ''} />
          {scanning ? 'Scanning...' : 'Scan DBs'}
        </button>

        <button
          onClick={() => onBackup(false)}
          disabled={backupRunning}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold
                     bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-500/20
                     hover:shadow-blue-500/30 hover:brightness-110
                     disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none transition-all duration-200"
        >
          <Download size={14} />
          {backupRunning ? 'Running...' : 'Smart Backup'}
        </button>

        <button
          onClick={() => onBackup(true)}
          disabled={backupRunning}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold
                     bg-amber-500/10 text-amber-500 border border-amber-500/20
                     hover:bg-amber-500/20 hover:border-amber-500/30
                     disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
        >
          <Zap size={14} />
          Force All
        </button>
      </div>
    </header>
  )
}
