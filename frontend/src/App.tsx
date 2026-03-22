import { useState, useCallback, useRef, useEffect } from 'react'
import { Loader2, WifiOff, RefreshCw } from 'lucide-react'
import { Sidebar } from './components/Sidebar'
import { TopBar } from './components/TopBar'
import { ToastContainer, toast } from './components/Toast'
import { DashboardPage } from './pages/DashboardPage'
import { DatabasesPage } from './pages/DatabasesPage'
import { HistoryPage } from './pages/HistoryPage'
import { ReportsPage } from './pages/ReportsPage'
import { LogsPage } from './pages/LogsPage'
import { SettingsPage } from './pages/SettingsPage'
import { useBackupStatus } from './hooks/useBackupStatus'
import { useTheme } from './hooks/useTheme'
import { api } from './services/api'

const tabTitles: Record<string, string> = {
  dashboard: 'Dashboard',
  databases: 'Databases',
  history: 'History',
  reports: 'Reports',
  logs: 'Logs',
  settings: 'Settings',
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [scanning, setScanning] = useState(false)
  const { status, history, loading, error, refresh } = useBackupStatus()
  const { theme, toggleTheme } = useTheme()

  const databases = status?.databases ?? []
  const backupRunning = status?.backup_running ?? false

  const handleScan = useCallback(async () => {
    setScanning(true)
    try {
      const data = await api.scan()
      toast(`Scanned ${data.count} databases`, 'success')
      await refresh()
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Scan failed', 'error')
    } finally {
      setScanning(false)
    }
  }, [refresh])

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const handleBackup = useCallback(async (force: boolean) => {
    const mode = force ? 'FORCED (all databases)' : 'smart (only changed)'
    try {
      await api.runBackup(force)
      toast(`Starting ${mode} backup...`, 'info')

      if (pollRef.current) clearInterval(pollRef.current)

      pollRef.current = setInterval(async () => {
        try {
          const { running } = await api.getBackupStatus()
          if (!running) {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            toast('Backup completed!', 'success')
            await refresh()
          }
        } catch {
          if (pollRef.current) clearInterval(pollRef.current)
          pollRef.current = null
        }
      }, 3000)
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Backup failed', 'error')
    }
  }, [refresh])

  return (
    <div className="flex min-h-screen theme-bg-primary theme-text-secondary transition-colors duration-300">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="ml-64 flex-1 min-h-screen">
        <TopBar
          title={tabTitles[activeTab]}
          backupRunning={backupRunning}
          onScan={handleScan}
          onBackup={handleBackup}
          scanning={scanning}
          theme={theme}
          onToggleTheme={toggleTheme}
        />

        {loading && !status && (
          <div className="flex items-center justify-center h-64 gap-3">
            <Loader2 size={24} className="animate-spin text-blue-500" />
            <span className="text-sm theme-text-muted">Connecting to server...</span>
          </div>
        )}

        {error && !status && !loading && (
          <div className="flex flex-col items-center justify-center h-64 gap-4">
            <WifiOff size={36} className="text-red-400 opacity-60" />
            <p className="text-sm theme-text-secondary">{error}</p>
            <button
              onClick={refresh}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold bg-blue-600 text-white hover:brightness-110 transition-all"
            >
              <RefreshCw size={14} /> Retry
            </button>
          </div>
        )}

        {status && activeTab === 'dashboard' && (
          <DashboardPage databases={databases} history={history} backupRunning={backupRunning} />
        )}
        {status && activeTab === 'databases' && (
          <DatabasesPage databases={databases} />
        )}
        {status && activeTab === 'history' && (
          <HistoryPage history={history} />
        )}
        {activeTab === 'reports' && (
          <ReportsPage />
        )}
        {activeTab === 'logs' && (
          <LogsPage />
        )}
        {activeTab === 'settings' && (
          <SettingsPage />
        )}
      </main>

      <ToastContainer />
    </div>
  )
}
