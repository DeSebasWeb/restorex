import { useState, useCallback } from 'react'
import { Server, Database, FolderOpen, CheckCircle, ArrowRight, ArrowLeft, X, Loader2, Shield, Zap, Eye, EyeOff, HardDrive, ChevronRight, FolderPlus, AlertTriangle } from 'lucide-react'
import { api } from '../services/api'
import type { ConnectionTestResult } from '../types'

interface SetupWizardProps {
  onComplete: () => void
  onSkip: () => void
}

const STEPS = [
  { id: 'welcome', icon: Shield, title: 'Welcome to Restorex' },
  { id: 'ssh', icon: Server, title: 'SSH Connection' },
  { id: 'postgres', icon: Database, title: 'PostgreSQL' },
  { id: 'backup', icon: FolderOpen, title: 'Backup Directory' },
  { id: 'test', icon: Zap, title: 'Test & Finish' },
]

export function SetupWizard({ onComplete, onSkip }: SetupWizardProps) {
  const [step, setStep] = useState(0)
  const [settings, setSettings] = useState({
    SSH_HOST: '',
    SSH_PORT: '22',
    SSH_USER: 'root',
    SSH_PASSWORD: '',
    PG_HOST: 'localhost',
    PG_PORT: '5432',
    PG_USER: 'postgres',
    PG_PASSWORD: '',
    BACKUP_LOCAL_DIR: 'D:/Backups/PostgreSQL',
  })
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null)
  const [saving, setSaving] = useState(false)
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({})

  // Folder browser state
  const [browserOpen, setBrowserOpen] = useState(false)
  const [drives, setDrives] = useState<{ letter: string; path: string }[]>([])
  const [currentDrive, setCurrentDrive] = useState('')
  const [currentPath, setCurrentPath] = useState('')
  const [folders, setFolders] = useState<string[]>([])
  const [browsing, setBrowsing] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')

  const update = (key: string, value: string) => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }

  const togglePassword = (key: string) => {
    setShowPasswords(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const result = await api.testConnection(settings)
      setTestResult(result)
    } catch (err) {
      setTestResult({ success: false, ssh: false, postgres: false, error: err instanceof Error ? err.message : 'Connection failed' })
    }
    setTesting(false)
  }

  const handleFinish = async () => {
    setSaving(true)
    try {
      await api.saveSettings(settings)
      onComplete()
    } catch {
      // Settings were already saved during test, just complete
      onComplete()
    }
    setSaving(false)
  }

  // Folder browser handlers
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

  const openBrowser = () => {
    setBrowserOpen(true)
    loadDrives()
    const v = (settings.BACKUP_LOCAL_DIR || '').replace(/\\/g, '/')
    if (v.length >= 2 && v[1] === ':') {
      browse(v[0].toUpperCase(), v.substring(3))
    }
  }

  const confirmFolder = () => {
    const display = currentPath ? `${currentDrive}:/${currentPath}` : `${currentDrive}:/`
    update('BACKUP_LOCAL_DIR', display)
    setBrowserOpen(false)
  }

  const createFolder = async () => {
    if (!newFolderName.trim()) return
    try {
      const folderPath = currentPath ? `${currentPath}/${newFolderName}` : newFolderName
      await api.createFolder(currentDrive, folderPath)
      setNewFolderName('')
      browse(currentDrive, currentPath)
    } catch { /* ignore */ }
  }

  const canProceed = () => {
    if (step === 1) return !!settings.SSH_HOST && !!settings.SSH_PASSWORD
    if (step === 2) return !!settings.PG_USER && !!settings.PG_PASSWORD
    if (step === 3) return !!settings.BACKUP_LOCAL_DIR
    if (step === 4) return testResult?.success === true
    return true
  }

  const renderInput = (label: string, key: string, opts: { type?: string; placeholder?: string; help?: string } = {}) => {
    const isPassword = opts.type === 'password'
    const show = showPasswords[key]
    return (
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">{label}</label>
        <div className="relative">
          <input
            type={isPassword && !show ? 'password' : 'text'}
            value={(settings as Record<string, string>)[key] || ''}
            onChange={e => update(key, e.target.value)}
            placeholder={opts.placeholder}
            className="w-full px-4 py-3 rounded-xl text-sm border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] placeholder:text-[var(--text-faint)] focus:outline-none focus:border-emerald-500/50 transition-colors"
          />
          {isPassword && (
            <button type="button" onClick={() => togglePassword(key)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-faint)] hover:text-[var(--text-secondary)]">
              {show ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          )}
        </div>
        {opts.help && <p className="text-[10px] text-[var(--text-faint)]">{opts.help}</p>}
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-md" />

      {/* Wizard card */}
      <div className="relative w-full max-w-xl mx-4 bg-[var(--bg-primary)] rounded-2xl border border-[var(--border)] shadow-2xl overflow-hidden">

        {/* Skip button */}
        <button
          onClick={onSkip}
          className="absolute top-4 right-4 z-10 w-8 h-8 rounded-lg flex items-center justify-center text-[var(--text-faint)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-all"
          title="Skip setup (you can configure later in Settings)"
        >
          <X size={18} />
        </button>

        {/* Progress bar */}
        <div className="h-1 bg-[var(--bg-secondary)]">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all duration-500"
            style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
          />
        </div>

        {/* Step indicators */}
        <div className="px-8 pt-6 pb-2 flex items-center justify-between">
          {STEPS.map((s, i) => {
            const Icon = s.icon
            const done = i < step
            const active = i === step
            return (
              <div key={s.id} className="flex flex-col items-center gap-1.5">
                <div className={`w-9 h-9 rounded-full flex items-center justify-center transition-all ${
                  done ? 'bg-emerald-500 text-white' :
                  active ? 'bg-emerald-500/15 text-emerald-500 ring-2 ring-emerald-500/30' :
                  'bg-[var(--bg-secondary)] text-[var(--text-faint)]'
                }`}>
                  {done ? <CheckCircle size={16} /> : <Icon size={16} />}
                </div>
                <span className={`text-[9px] font-semibold uppercase tracking-wider ${active ? 'text-emerald-500' : 'text-[var(--text-faint)]'}`}>
                  {s.title}
                </span>
              </div>
            )
          })}
        </div>

        {/* Content */}
        <div className="px-8 py-6 min-h-[320px]">

          {/* Step 0: Welcome */}
          {step === 0 && (
            <div className="text-center py-8">
              <img src="/logo.png" alt="Restorex" className="w-20 h-20 mx-auto mb-6 rounded-2xl shadow-lg shadow-emerald-500/20" />
              <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-3">Welcome to Restorex</h2>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed max-w-sm mx-auto mb-6">
                Let's set up your backup system in under 2 minutes. You'll need your server's SSH credentials and PostgreSQL access.
              </p>
              <div className="flex flex-col gap-2 text-xs text-[var(--text-faint)] max-w-xs mx-auto">
                <div className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-500 shrink-0" /> SSH access to your database server</div>
                <div className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-500 shrink-0" /> PostgreSQL username & password</div>
                <div className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-500 shrink-0" /> A folder to store your backups</div>
              </div>
            </div>
          )}

          {/* Step 1: SSH */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-bold text-[var(--text-primary)] mb-1">SSH Connection</h2>
                <p className="text-xs text-[var(--text-faint)]">Connect to the server where your databases live</p>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  {renderInput('Host / IP', 'SSH_HOST', { placeholder: '192.168.1.100', help: 'Your server IP (via VPN if needed)' })}
                </div>
                {renderInput('Port', 'SSH_PORT', { placeholder: '22' })}
              </div>
              <div className="grid grid-cols-2 gap-3">
                {renderInput('Username', 'SSH_USER', { placeholder: 'root' })}
                {renderInput('Password', 'SSH_PASSWORD', { type: 'password', placeholder: '••••••••' })}
              </div>
            </div>
          )}

          {/* Step 2: PostgreSQL */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-bold text-[var(--text-primary)] mb-1">PostgreSQL Credentials</h2>
                <p className="text-xs text-[var(--text-faint)]">Database credentials as seen from your server (usually localhost)</p>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  {renderInput('Host', 'PG_HOST', { placeholder: 'localhost', help: 'Usually localhost (DB runs on the same server)' })}
                </div>
                {renderInput('Port', 'PG_PORT', { placeholder: '5432' })}
              </div>
              <div className="grid grid-cols-2 gap-3">
                {renderInput('Username', 'PG_USER', { placeholder: 'postgres' })}
                {renderInput('Password', 'PG_PASSWORD', { type: 'password', placeholder: '••••••••' })}
              </div>
            </div>
          )}

          {/* Step 3: Backup Directory */}
          {step === 3 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-bold text-[var(--text-primary)] mb-1">Backup Directory</h2>
                <p className="text-xs text-[var(--text-faint)]">Where to save your backup files on this computer</p>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">Folder Path</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={settings.BACKUP_LOCAL_DIR}
                    onChange={e => update('BACKUP_LOCAL_DIR', e.target.value)}
                    placeholder="D:/Backups/PostgreSQL"
                    className="flex-1 px-4 py-3 rounded-xl text-sm border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-emerald-500/50"
                  />
                  <button
                    onClick={openBrowser}
                    className="px-4 py-3 rounded-xl text-sm border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] transition-colors flex items-center gap-2"
                  >
                    <HardDrive size={14} /> Browse
                  </button>
                </div>
                <p className="text-[10px] text-[var(--text-faint)]">Click Browse to select a folder on any connected drive</p>
              </div>

              {/* Inline folder browser */}
              {browserOpen && (
                <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] overflow-hidden">
                  {/* Breadcrumb */}
                  <div className="px-4 py-2 border-b border-[var(--border)] text-xs text-[var(--text-tertiary)] flex items-center gap-1.5">
                    {currentDrive ? (
                      <>
                        <span className="text-emerald-500 font-semibold cursor-pointer" onClick={() => { setCurrentDrive(''); setCurrentPath(''); setFolders([]) }}>Drives</span>
                        <ChevronRight size={11} />
                        <span className="font-semibold cursor-pointer" onClick={() => browse(currentDrive, '')}>{currentDrive}:</span>
                        {currentPath.split('/').filter(Boolean).map((part, i, arr) => (
                          <span key={i} className="flex items-center gap-1">
                            <ChevronRight size={11} />
                            <span className={i === arr.length - 1 ? 'font-bold text-[var(--text-primary)]' : 'cursor-pointer hover:underline'}
                              onClick={() => { if (i < arr.length - 1) browse(currentDrive, arr.slice(0, i + 1).join('/')) }}
                            >{part}</span>
                          </span>
                        ))}
                      </>
                    ) : <span className="font-semibold">Select a drive</span>}
                  </div>

                  {/* Content */}
                  <div className="p-3 max-h-[180px] overflow-y-auto">
                    {browsing ? (
                      <div className="flex items-center justify-center py-6"><Loader2 size={18} className="animate-spin text-emerald-500" /></div>
                    ) : !currentDrive ? (
                      <div className="grid grid-cols-2 gap-2">
                        {drives.map(d => (
                          <button key={d.letter} onClick={() => browse(d.letter, '')}
                            className="flex items-center gap-3 p-3 rounded-lg border border-[var(--border)] hover:border-emerald-500/40 hover:bg-emerald-500/5 transition-all">
                            <HardDrive size={18} className="text-emerald-500" />
                            <span className="font-semibold text-sm text-[var(--text-primary)]">{d.letter}: Drive</span>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="space-y-0.5">
                        {currentPath && (
                          <button onClick={() => { const parts = currentPath.split('/').filter(Boolean); parts.pop(); browse(currentDrive, parts.join('/')) }}
                            className="flex items-center gap-2 w-full p-2 rounded-lg hover:bg-[var(--bg-hover)] text-sm text-[var(--text-secondary)]">
                            <ArrowLeft size={13} /> ..
                          </button>
                        )}
                        {folders.length === 0 && <p className="text-xs text-[var(--text-faint)] text-center py-4">Empty — create a folder below</p>}
                        {folders.map(f => (
                          <button key={f} onClick={() => browse(currentDrive, currentPath ? `${currentPath}/${f}` : f)}
                            className="flex items-center gap-2 w-full p-2 rounded-lg hover:bg-[var(--bg-hover)] text-sm text-[var(--text-primary)]">
                            <FolderOpen size={14} className="text-amber-500" /> {f}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Footer */}
                  {currentDrive && (
                    <div className="px-3 py-2.5 border-t border-[var(--border)] flex items-center gap-2">
                      <input type="text" value={newFolderName} onChange={e => setNewFolderName(e.target.value)}
                        placeholder="New folder..." onKeyDown={e => { if (e.key === 'Enter') createFolder() }}
                        className="flex-1 px-3 py-1.5 rounded-lg text-xs border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)]" />
                      <button onClick={createFolder} disabled={!newFolderName.trim()}
                        className="px-2.5 py-1.5 rounded-lg text-xs border border-[var(--border)] hover:bg-[var(--bg-hover)] disabled:opacity-40 flex items-center gap-1">
                        <FolderPlus size={11} /> Create
                      </button>
                      <button onClick={confirmFolder}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-500">
                        Select
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Step 4: Test & Finish */}
          {step === 4 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-bold text-[var(--text-primary)] mb-1">Test Connection</h2>
                <p className="text-xs text-[var(--text-faint)]">Let's verify everything works before we start</p>
              </div>

              {/* Summary */}
              <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4 space-y-2 text-xs">
                <div className="flex justify-between"><span className="text-[var(--text-faint)]">SSH</span><span className="text-[var(--text-primary)] font-mono">{settings.SSH_USER}@{settings.SSH_HOST}:{settings.SSH_PORT}</span></div>
                <div className="flex justify-between"><span className="text-[var(--text-faint)]">PostgreSQL</span><span className="text-[var(--text-primary)] font-mono">{settings.PG_USER}@{settings.PG_HOST}:{settings.PG_PORT}</span></div>
                <div className="flex justify-between"><span className="text-[var(--text-faint)]">Backup Dir</span><span className="text-[var(--text-primary)] font-mono">{settings.BACKUP_LOCAL_DIR}</span></div>
              </div>

              {/* Test button */}
              <button
                onClick={handleTest}
                disabled={testing}
                className="w-full py-3 rounded-xl text-sm font-bold bg-gradient-to-r from-emerald-500 to-cyan-500 text-white hover:from-emerald-400 hover:to-cyan-400 disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20"
              >
                {testing ? <><Loader2 size={16} className="animate-spin" /> Testing...</> : <><Zap size={16} /> Test Connection</>}
              </button>

              {/* Result */}
              {testResult && (
                <div className={`rounded-xl border p-4 ${testResult.success ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
                  <div className="flex items-center gap-2 mb-2">
                    {testResult.success ? <CheckCircle size={18} className="text-emerald-500" /> : <AlertTriangle size={18} className="text-red-500" />}
                    <span className={`font-bold text-sm ${testResult.success ? 'text-emerald-500' : 'text-red-500'}`}>
                      {testResult.success ? 'Connection Successful!' : 'Connection Failed'}
                    </span>
                  </div>
                  <div className="space-y-1 text-xs">
                    <div className="flex items-center gap-2">
                      {testResult.ssh ? <CheckCircle size={12} className="text-emerald-500" /> : <X size={12} className="text-red-500" />}
                      <span className="text-[var(--text-secondary)]">SSH {testResult.ssh ? 'Connected' : 'Failed'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {testResult.postgres ? <CheckCircle size={12} className="text-emerald-500" /> : <X size={12} className="text-red-500" />}
                      <span className="text-[var(--text-secondary)]">PostgreSQL {testResult.postgres ? 'Connected' : 'Failed'}</span>
                    </div>
                    {testResult.pg_version && <p className="text-[10px] text-[var(--text-faint)] mt-1 font-mono">{testResult.pg_version}</p>}
                    {testResult.error && <p className="text-[10px] text-red-400 mt-1">{testResult.error}</p>}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Navigation buttons */}
        <div className="px-8 py-4 border-t border-[var(--border)] bg-[var(--bg-secondary)] flex items-center justify-between">
          <div>
            {step > 0 && (
              <button
                onClick={() => setStep(step - 1)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] transition-colors"
              >
                <ArrowLeft size={14} /> Back
              </button>
            )}
          </div>

          {step < 4 ? (
            <button
              onClick={() => setStep(step + 1)}
              disabled={!canProceed()}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-40 transition-all"
            >
              {step === 0 ? "Let's Go" : 'Next'} <ArrowRight size={14} />
            </button>
          ) : (
            <button
              onClick={handleFinish}
              disabled={!testResult?.success || saving}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold bg-gradient-to-r from-emerald-500 to-cyan-500 text-white hover:from-emerald-400 hover:to-cyan-400 disabled:opacity-40 transition-all shadow-lg shadow-emerald-500/20"
            >
              {saving ? <><Loader2 size={14} className="animate-spin" /> Saving...</> : <><CheckCircle size={14} /> Start Using Restorex</>}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
