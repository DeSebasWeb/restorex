import { useState, useEffect } from 'react'
import { Save, TestTube, CheckCircle, XCircle, Loader2, Server, Database, FolderOpen, Clock, Eye, EyeOff } from 'lucide-react'
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

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null)
  const [configured, setConfigured] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    setLoading(true)
    try {
      const data = await api.getSettings()
      setSettings(data.settings)
      setConfigured(data.configured)
    } catch (err) {
      toast('Failed to load settings', 'error')
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

  if (loading || !settings) {
    return (
      <div className="p-7 flex items-center justify-center h-64">
        <Loader2 size={24} className="animate-spin text-blue-500" />
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
          <Field label="Local Backup Directory" name="BACKUP_LOCAL_DIR" value={settings.BACKUP_LOCAL_DIR} onChange={handleChange} placeholder="/backups/databases" help="Inside Docker, mapped to D:\Backups\PostgreSQL" />
          <Field label="Remote Temp Directory" name="BACKUP_REMOTE_TMP_DIR" value={settings.BACKUP_REMOTE_TMP_DIR} onChange={handleChange} placeholder="/tmp/pg_backups" help="Temporary directory on the remote server" />
          <Field label="Retention (days)" name="RETENTION_DAYS" value={settings.RETENTION_DAYS} onChange={handleChange} placeholder="7" help="Backups older than this are auto-deleted" />
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
