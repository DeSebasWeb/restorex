import { useState, useEffect, useCallback } from 'react'
import { Save, TestTube, CheckCircle, XCircle, Loader2, Server, Database, FolderOpen, Clock, Eye, EyeOff, HardDrive, ChevronRight, FolderPlus, ArrowLeft } from 'lucide-react'
import { api } from '../services/api'
import { toast } from '../components/Toast'
import type { AppSettings, ConnectionTestResult } from '../types'

interface FieldProps {
  label: string
  name: keyof AppSettings
  value: string | number
  onChange: (name: keyof AppSettings, value: string) => void
  type?: string
  placeholder?: string
  help?: string
  icon?: React.ReactNode
}

function Field({ label, name, value, onChange, type = 'text', placeholder, help, icon }: FieldProps) {
  const [showPassword, setShowPassword] = useState(false)
  const isPassword = type === 'password'

  return (
    <div className="space-y-1.5">
      <label className="flex items-center gap-1.5 text-xs font-semibold theme-text-tertiary uppercase tracking-wider">
        {icon}
        {label}
      </label>
      <div className="relative">
        <input
          type={isPassword && !showPassword ? 'password' : 'text'}
          value={value}
          onChange={e => onChange(name, e.target.value)}
          placeholder={placeholder}
          className="w-full px-4 py-2.5 rounded-xl theme-bg-primary border theme-border text-sm theme-text-secondary
                     placeholder:theme-text-faint focus:outline-none focus:border-blue-500/30 focus:ring-1 focus:ring-blue-500/20
                     transition-all font-mono"
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 theme-text-faint hover:theme-text-tertiary transition-colors"
          >
            {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        )}
      </div>
      {help && <p className="text-[10px] theme-text-faint">{help}</p>}
    </div>
  )
}

interface FolderBrowserProps {
  value: string
  onChange: (path: string) => void
}

function FolderBrowser({ value, onChange }: FolderBrowserProps) {
  const [open, setOpen] = useState(false)
  const [drives, setDrives] = useState<{ letter: string; path: string }[]>([])
  const [currentDrive, setCurrentDrive] = useState('')
  const [currentPath, setCurrentPath] = useState('')
  const [folders, setFolders] = useState<string[]>([])
  const [browsing, setBrowsing] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [creating, setCreating] = useState(false)

  const loadDrives = useCallback(async () => {
    try {
      const res = await api.getDrives()
      setDrives(res.drives)
    } catch { /* ignore */ }
  }, [])

  const browse = useCallback(async (drive: string, path: string) => {
    setBrowsing(true)
    try {
      const res = await api.browsePath(drive, path)
      setCurrentDrive(res.drive)
      setCurrentPath(res.path)
      setFolders(res.folders)
    } catch { /* ignore */ }
    setBrowsing(false)
  }, [])

  const handleOpen = () => {
    setOpen(true)
    loadDrives()
    // Parse current value to browse to it
    const v = (value || '').replace(/\\/g, '/')
    if (v.length >= 2 && v[1] === ':') {
      const drive = v[0].toUpperCase()
      const rest = v.substring(3)
      browse(drive, rest)
    }
  }

  const handleSelectDrive = (letter: string) => {
    browse(letter, '')
  }

  const handleSelectFolder = (folder: string) => {
    const newPath = currentPath ? `${currentPath}/${folder}` : folder
    browse(currentDrive, newPath)
  }

  const handleGoUp = () => {
    const parts = currentPath.split('/').filter(Boolean)
    parts.pop()
    browse(currentDrive, parts.join('/'))
  }

  const handleConfirm = () => {
    const display = currentPath ? `${currentDrive}:/${currentPath}` : `${currentDrive}:/`
    onChange(display)
    setOpen(false)
  }

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return
    setCreating(true)
    try {
      const folderPath = currentPath ? `${currentPath}/${newFolderName}` : newFolderName
      await api.createFolder(currentDrive, folderPath)
      setNewFolderName('')
      browse(currentDrive, currentPath) // Refresh
      toast(`Folder "${newFolderName}" created`, 'success')
    } catch {
      toast('Failed to create folder', 'error')
    }
    setCreating(false)
  }

  const displayPath = currentPath ? `${currentDrive}:/${currentPath}` : currentDrive ? `${currentDrive}:/` : ''

  return (
    <div className="space-y-1.5">
      <label className="flex items-center gap-1.5 text-xs font-semibold theme-text-tertiary uppercase tracking-wider">
        <FolderOpen size={12} />
        Backup Directory
      </label>
      <div className="flex gap-2">
        <input
          type="text"
          value={value || ''}
          onChange={e => onChange(e.target.value)}
          placeholder="D:/Backups/PostgreSQL"
          className="flex-1 px-3 py-2 rounded-lg text-sm border theme-input transition-colors"
        />
        <button
          type="button"
          onClick={handleOpen}
          className="px-3 py-2 rounded-lg text-sm border theme-border theme-text-secondary hover:theme-bg-hover transition-colors flex items-center gap-1.5"
        >
          <HardDrive size={14} />
          Browse
        </button>
      </div>
      <p className="text-[10px] theme-text-faint">Choose any folder on your connected drives</p>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6" onClick={() => setOpen(false)}>
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

          {/* Modal */}
          <div
            className="relative bg-[var(--bg-primary)] rounded-2xl border border-[var(--border)] shadow-2xl w-full max-w-xl flex flex-col overflow-hidden"
            style={{ maxHeight: '75vh' }}
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-[var(--border)] flex items-center justify-between bg-[var(--bg-secondary)]">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-emerald-500/15 flex items-center justify-center">
                  <HardDrive size={18} className="text-emerald-500" />
                </div>
                <div>
                  <h3 className="font-bold text-[var(--text-primary)] text-base">Select Backup Folder</h3>
                  <p className="text-[11px] text-[var(--text-faint)]">Choose where to store your database backups</p>
                </div>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--text-faint)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-all"
              >
                &times;
              </button>
            </div>

            {/* Breadcrumb */}
            <div className="px-6 py-2.5 border-b border-[var(--border)] text-xs text-[var(--text-tertiary)] flex items-center gap-1.5 flex-wrap bg-[var(--bg-primary)]">
              {currentDrive ? (
                <>
                  <span className="text-emerald-500 font-semibold cursor-pointer hover:underline" onClick={() => { setCurrentDrive(''); setCurrentPath(''); setFolders([]); }}>
                    <HardDrive size={11} className="inline mr-1" />Drives
                  </span>
                  <ChevronRight size={11} className="text-[var(--text-faint)]" />
                  <span className="font-semibold cursor-pointer hover:underline" onClick={() => browse(currentDrive, '')}>{currentDrive}:</span>
                  {currentPath.split('/').filter(Boolean).map((part, i, arr) => (
                    <span key={i} className="flex items-center gap-1.5">
                      <ChevronRight size={11} className="text-[var(--text-faint)]" />
                      <span
                        className={i === arr.length - 1 ? 'font-bold text-[var(--text-primary)]' : 'cursor-pointer hover:underline'}
                        onClick={() => { if (i < arr.length - 1) browse(currentDrive, arr.slice(0, i + 1).join('/')) }}
                      >{part}</span>
                    </span>
                  ))}
                </>
              ) : (
                <span className="font-semibold text-[var(--text-secondary)]">
                  <HardDrive size={11} className="inline mr-1" />Select a drive to browse
                </span>
              )}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 min-h-[280px]">
              {browsing ? (
                <div className="flex flex-col items-center justify-center h-48 gap-3">
                  <Loader2 size={28} className="animate-spin text-emerald-500" />
                  <span className="text-xs text-[var(--text-faint)]">Loading folders...</span>
                </div>
              ) : !currentDrive ? (
                /* Drive selection */
                <div className="grid grid-cols-2 gap-3">
                  {drives.map(d => (
                    <button
                      key={d.letter}
                      onClick={() => handleSelectDrive(d.letter)}
                      className="flex items-center gap-4 p-4 rounded-xl border border-[var(--border)] hover:border-emerald-500/50 hover:bg-emerald-500/5 transition-all group"
                    >
                      <div className="w-11 h-11 rounded-xl bg-emerald-500/10 group-hover:bg-emerald-500/20 flex items-center justify-center transition-colors">
                        <HardDrive size={22} className="text-emerald-500" />
                      </div>
                      <div className="text-left">
                        <div className="font-bold text-[var(--text-primary)] text-sm">{d.letter}: Drive</div>
                        <div className="text-xs text-[var(--text-faint)]">Local disk</div>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                /* Folder list */
                <div className="space-y-0.5">
                  {currentPath && (
                    <button onClick={handleGoUp} className="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg hover:bg-[var(--bg-hover)] transition-colors text-sm text-[var(--text-secondary)] group">
                      <ArrowLeft size={15} className="text-[var(--text-faint)] group-hover:text-emerald-500 transition-colors" />
                      <span className="font-medium">..</span>
                    </button>
                  )}
                  {folders.length === 0 && (
                    <div className="text-center py-12">
                      <FolderOpen size={32} className="mx-auto text-[var(--text-faint)] mb-3 opacity-40" />
                      <p className="text-sm text-[var(--text-faint)]">No subfolders here</p>
                      <p className="text-xs text-[var(--text-faint)] mt-1">Create one below or select this folder</p>
                    </div>
                  )}
                  {folders.map(f => (
                    <button
                      key={f}
                      onClick={() => handleSelectFolder(f)}
                      className="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg hover:bg-[var(--bg-hover)] transition-colors text-sm text-[var(--text-primary)] group"
                    >
                      <FolderOpen size={16} className="text-amber-500 shrink-0 group-hover:text-amber-400 transition-colors" />
                      <span className="truncate font-medium">{f}</span>
                      <ChevronRight size={13} className="ml-auto text-[var(--text-faint)] opacity-0 group-hover:opacity-100 transition-opacity" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Footer: Create folder + Confirm */}
            {currentDrive && (
              <div className="px-6 py-4 border-t border-[var(--border)] bg-[var(--bg-secondary)] space-y-3">
                {/* New folder row */}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newFolderName}
                    onChange={e => setNewFolderName(e.target.value)}
                    placeholder="New folder name..."
                    className="flex-1 px-3 py-2 rounded-lg text-xs border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] placeholder:text-[var(--text-faint)] focus:outline-none focus:border-emerald-500/50 transition-colors"
                    onKeyDown={e => { if (e.key === 'Enter') handleCreateFolder() }}
                  />
                  <button
                    onClick={handleCreateFolder}
                    disabled={creating || !newFolderName.trim()}
                    className="px-3 py-2 rounded-lg text-xs font-medium border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] transition-colors flex items-center gap-1.5 disabled:opacity-40"
                  >
                    <FolderPlus size={13} />
                    Create
                  </button>
                </div>
                {/* Selected path + confirm */}
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <FolderOpen size={14} className="text-emerald-500 shrink-0" />
                    <span className="text-xs text-[var(--text-secondary)] truncate font-mono">{displayPath || 'No folder selected'}</span>
                  </div>
                  <button
                    onClick={handleConfirm}
                    className="px-5 py-2.5 rounded-lg text-sm font-bold bg-emerald-600 text-white hover:bg-emerald-500 transition-colors shrink-0 shadow-md shadow-emerald-500/20"
                  >
                    Select This Folder
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null)
  const [configured, setConfigured] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const data = await api.getSettings()
      setSettings(data.settings)
      setConfigured(data.configured)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load settings'
      setLoadError(msg)
      toast(msg, 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (name: keyof AppSettings, value: string) => {
    if (!settings) return
    setSettings({ ...settings, [name]: value })
    setTestResult(null)
  }

  const handleSave = async () => {
    if (!settings) return
    setSaving(true)
    try {
      const data = await api.saveSettings(settings)
      setConfigured(data.configured)
      toast('Settings saved and applied!', 'success')
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to save', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    if (!settings) return
    setTesting(true)
    setTestResult(null)
    try {
      const result = await api.testConnection(settings)
      setTestResult(result)
      if (result.success) {
        toast('Connection successful!', 'success')
      } else {
        toast(result.error || 'Connection failed', 'error')
      }
    } catch (err) {
      setTestResult({ success: false, ssh: false, postgres: false, error: String(err) })
      toast('Connection test failed', 'error')
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return (
      <div className="p-7 flex items-center justify-center h-64">
        <Loader2 size={24} className="animate-spin text-blue-500" />
      </div>
    )
  }

  if (loadError || !settings) {
    return (
      <div className="p-7 flex flex-col items-center justify-center h-64 gap-4">
        <XCircle size={32} className="text-red-400" />
        <p className="text-sm theme-text-secondary">{loadError || 'Failed to load settings'}</p>
        <button
          onClick={loadSettings}
          className="px-4 py-2 rounded-xl text-sm font-semibold bg-blue-600 text-white hover:brightness-110 transition-all"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="p-7 space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold theme-text">Settings</h2>
          <p className="text-xs theme-text-muted mt-0.5">
            Configure your server connection and backup preferences
          </p>
        </div>
        <div className="flex items-center gap-2">
          {configured ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400">
              <CheckCircle size={12} /> Configured
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400">
              <XCircle size={12} /> Not configured
            </span>
          )}
        </div>
      </div>

      {/* SSH Section */}
      <div className="theme-bg-card border theme-border rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b theme-border">
          <Server size={16} className="text-blue-400" />
          <h3 className="text-sm font-semibold theme-text">SSH Connection</h3>
          <span className="text-[10px] theme-text-faint ml-auto">Connect to the remote server via SSH</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Host" name="SSH_HOST" value={settings.SSH_HOST} onChange={handleChange} placeholder="192.168.1.100" />
          <Field label="Port" name="SSH_PORT" value={settings.SSH_PORT} onChange={handleChange} placeholder="22" />
          <Field label="Username" name="SSH_USER" value={settings.SSH_USER} onChange={handleChange} placeholder="root" />
          <Field label="Password" name="SSH_PASSWORD" value={settings.SSH_PASSWORD} onChange={handleChange} type="password" placeholder="SSH password" />
          <Field label="SSH Key Path" name="SSH_KEY_PATH" value={settings.SSH_KEY_PATH} onChange={handleChange} placeholder="~/.ssh/id_rsa" help="Leave empty to use password auth" />
        </div>
      </div>

      {/* PostgreSQL Section */}
      <div className="theme-bg-card border theme-border rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b theme-border">
          <Database size={16} className="text-emerald-400" />
          <h3 className="text-sm font-semibold theme-text">PostgreSQL</h3>
          <span className="text-[10px] theme-text-faint ml-auto">Database server credentials</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Host" name="PG_HOST" value={settings.PG_HOST} onChange={handleChange} placeholder="localhost" help="As seen from the SSH server (usually localhost)" />
          <Field label="Port" name="PG_PORT" value={settings.PG_PORT} onChange={handleChange} placeholder="5432" />
          <Field label="Username" name="PG_USER" value={settings.PG_USER} onChange={handleChange} placeholder="postgres" />
          <Field label="Password" name="PG_PASSWORD" value={settings.PG_PASSWORD} onChange={handleChange} type="password" placeholder="PostgreSQL password" />
        </div>
      </div>

      {/* Backup Section */}
      <div className="theme-bg-card border theme-border rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b theme-border">
          <FolderOpen size={16} className="text-purple-400" />
          <h3 className="text-sm font-semibold theme-text">Backup Storage</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FolderBrowser value={settings.BACKUP_LOCAL_DIR as string} onChange={(path) => handleChange('BACKUP_LOCAL_DIR', path)} />
          <Field label="Remote Temp Directory" name="BACKUP_REMOTE_TMP_DIR" value={settings.BACKUP_REMOTE_TMP_DIR} onChange={handleChange} placeholder="/tmp/pg_backups" help="Temporary directory on the remote server" />
          <Field label="Retention (days)" name="RETENTION_DAYS" value={settings.RETENTION_DAYS} onChange={handleChange} placeholder="7" help="Backups older than this are auto-deleted" />
        </div>

        <div className="pt-3 border-t theme-border">
          <label className="flex items-center gap-3 cursor-pointer group">
            <div className="relative">
              <input
                type="checkbox"
                checked={!!settings.GENERATE_SQL}
                onChange={e => setSettings({ ...settings, GENERATE_SQL: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-9 h-5 rounded-full bg-slate-600/40 peer-checked:bg-blue-500/80 transition-colors" />
              <div className="absolute left-0.5 top-0.5 w-4 h-4 rounded-full bg-slate-300 peer-checked:bg-white peer-checked:translate-x-4 transition-all" />
            </div>
            <div>
              <span className="text-sm font-medium theme-text-secondary group-hover:theme-text transition-colors">
                Generate .sql.gz backup
              </span>
              <p className="text-[10px] theme-text-faint">
                Creates a compressed SQL dump in addition to the .backup file. Disable to speed up backups significantly.
              </p>
            </div>
          </label>
        </div>

        <div className="pt-3 border-t theme-border">
          <label className="text-xs font-semibold theme-text-tertiary uppercase tracking-wider">
            Parallel Workers
          </label>
          <div className="flex items-center gap-4 mt-2">
            <input
              type="range"
              min="1"
              max="10"
              value={Number(settings.PARALLEL_WORKERS) || 3}
              onChange={e => setSettings({ ...settings, PARALLEL_WORKERS: Number(e.target.value) })}
              className="flex-1 h-2 rounded-full appearance-none bg-slate-600/30 accent-blue-500"
            />
            <span className="text-sm font-bold text-blue-400 w-6 text-center">
              {Number(settings.PARALLEL_WORKERS) || 3}
            </span>
          </div>
          <p className="text-[10px] theme-text-faint mt-1">
            Number of databases to backup simultaneously. Higher values = faster but more server load.
          </p>
        </div>
      </div>

      {/* Scheduler Section */}
      <div className="theme-bg-card border theme-border rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b theme-border">
          <Clock size={16} className="text-amber-400" />
          <h3 className="text-sm font-semibold theme-text">Automatic Schedule</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Hour (0-23)" name="SCHEDULER_HOUR" value={settings.SCHEDULER_HOUR} onChange={handleChange} placeholder="23" help="Daily backup hour (24h format)" />
          <Field label="Minute (0-59)" name="SCHEDULER_MINUTE" value={settings.SCHEDULER_MINUTE} onChange={handleChange} placeholder="0" />
        </div>
      </div>

      {/* Test result */}
      {testResult && (
        <div className={`rounded-2xl p-5 border ${testResult.success ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-red-500/5 border-red-500/20'}`}>
          <div className="flex items-center gap-2 mb-2">
            {testResult.success
              ? <CheckCircle size={18} className="text-emerald-400" />
              : <XCircle size={18} className="text-red-400" />
            }
            <span className={`text-sm font-semibold ${testResult.success ? 'text-emerald-400' : 'text-red-400'}`}>
              {testResult.success ? 'Connection Successful!' : 'Connection Failed'}
            </span>
          </div>
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-2">
              <span className={testResult.ssh ? 'text-emerald-400' : 'text-red-400'}>
                {testResult.ssh ? '\u2713' : '\u2717'} SSH
              </span>
              <span className="theme-text-muted">{testResult.ssh ? 'Connected' : 'Failed'}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={testResult.postgres ? 'text-emerald-400' : 'text-red-400'}>
                {testResult.postgres ? '\u2713' : '\u2717'} PostgreSQL
              </span>
              <span className="theme-text-muted">{testResult.postgres ? 'Connected' : 'Failed'}</span>
            </div>
            {testResult.pg_version && (
              <p className="theme-text-muted mt-1 font-mono">{testResult.pg_version}</p>
            )}
            {testResult.error && (
              <p className="text-red-400 mt-1">{testResult.error}</p>
            )}
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-3 pt-2">
        <button
          onClick={handleTest}
          disabled={testing}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold
                     border theme-border theme-text-secondary theme-border-hover hover:theme-text theme-hover
                     disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          {testing ? <Loader2 size={16} className="animate-spin" /> : <TestTube size={16} />}
          {testing ? 'Testing...' : 'Test Connection'}
        </button>

        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold
                     bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/20
                     hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  )
}
