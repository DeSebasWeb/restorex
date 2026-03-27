import { useState, useCallback, useRef, useEffect } from 'react'
import { Loader2, WifiOff, RefreshCw, AlertTriangle, Settings as SettingsIcon } from 'lucide-react'
import { Sidebar } from './components/Sidebar'
import { TopBar } from './components/TopBar'
import { SetupWizard } from './components/SetupWizard'
import { ChangePasswordModal } from './components/ChangePasswordModal'
import { ToastContainer, toast } from './components/Toast'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { DatabasesPage } from './pages/DatabasesPage'
import { HistoryPage } from './pages/HistoryPage'
import { ReportsPage } from './pages/ReportsPage'
import { LogsPage } from './pages/LogsPage'
import { NotificationsPage } from './pages/NotificationsPage'
import { SettingsPage } from './pages/SettingsPage'
import { UsersPage } from './pages/UsersPage'
import { useAuth } from './hooks/useAuth'
import { useBackupStatus } from './hooks/useBackupStatus'
import { useTheme } from './hooks/useTheme'
import { api } from './services/api'

const tabTitles: Record<string, string> = {
  dashboard: 'Dashboard',
  databases: 'Databases',
  history: 'History',
  reports: 'Reports',
  logs: 'Logs',
  users: 'Users',
  notifications: 'Notifications',
  settings: 'Settings',
}

export default function App() {
  const { user, loading: authLoading, isAuthenticated, login, logout, changePassword } = useAuth()
  const [activeTab, setActiveTab] = useState('dashboard')
  const [scanning, setScanning] = useState(false)
  const [showWizard, setShowWizard] = useState(false)
  const [wizardSkipped, setWizardSkipped] = useState(false)
  const { status, history, loading, error, refresh } = useBackupStatus(!isAuthenticated)
  const { theme, toggleTheme } = useTheme()

  const configured = status?.configured ?? true
  const databases = status?.databases ?? []
  const backupRunning = status?.backup_running ?? false

  // Show wizard automatically if not configured
  useEffect(() => {
    if (status && !status.configured && !wizardSkipped) {
      setShowWizard(true)
    }
  }, [status, wizardSkipped])

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

  // ── Auth gates ─────────────────────────────────────────────────

  // Loading auth state
  if (authLoading) {
    return (
      <div className="fixed inset-0 flex items-center justify-center" style={{ background: '#0f1219' }}>
        <div className="flex flex-col items-center gap-4">
          <Loader2 size={32} className="animate-spin text-emerald-500" />
          <p className="text-sm text-[#8b95a5]">Loading...</p>
        </div>
      </div>
    )
  }

  // Not authenticated → Login page
  if (!isAuthenticated) {
    return <LoginPage onLogin={login} />
  }

  // Force password change
  if (user?.force_password_change) {
    return (
      <div className="min-h-screen theme-bg-primary">
        <ChangePasswordModal forced onChangePassword={changePassword} />
      </div>
    )
  }

  // ── Authenticated dashboard ────────────────────────────────────

  return (
    <div className="flex min-h-screen theme-bg-primary theme-text-secondary transition-colors duration-300">
      {/* Setup Wizard */}
      {showWizard && (
        <SetupWizard
          onComplete={() => { setShowWizard(false); setWizardSkipped(false); refresh() }}
          onSkip={() => { setShowWizard(false); setWizardSkipped(true) }}
        />
      )}

      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        user={user}
        onLogout={logout}
      />

      <main className="ml-64 flex-1 min-h-screen">
        {/* Not configured banner */}
        {!configured && !showWizard && (
          <div className="mx-6 mt-4 p-4 rounded-xl border border-amber-500/30 bg-amber-500/5 flex items-center gap-4">
            <AlertTriangle size={20} className="text-amber-500 shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-[var(--text-primary)]">Setup required</p>
              <p className="text-xs text-[var(--text-faint)]">Configure your server connection to start backing up your databases.</p>
            </div>
            <button
              onClick={() => setShowWizard(true)}
              className="px-4 py-2 rounded-lg text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-500 transition-colors flex items-center gap-2 shrink-0"
            >
              <SettingsIcon size={13} /> Run Setup
            </button>
          </div>
        )}

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
        {activeTab === 'users' && (
          <UsersPage />
        )}
        {activeTab === 'notifications' && (
          <NotificationsPage />
        )}
        {activeTab === 'settings' && (
          <SettingsPage />
        )}
      </main>

      <ToastContainer />
    </div>
  )
}
