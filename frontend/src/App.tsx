import { useState, useCallback, useRef, useEffect } from 'react'
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
  const { status, history, refresh } = useBackupStatus()
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

        {activeTab === 'dashboard' && (
          <DashboardPage databases={databases} history={history} backupRunning={backupRunning} />
        )}
        {activeTab === 'databases' && (
          <DatabasesPage databases={databases} />
        )}
        {activeTab === 'history' && (
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
