import { useState, useEffect } from 'react'
import { Bell, Send, TestTube, CheckCircle, XCircle, Loader2, Eye, EyeOff, Mail, Hash } from 'lucide-react'
import { api } from '../services/api'
import { toast } from '../components/Toast'
import type { NotificationChannel } from '../types'

interface ChannelDef {
  id: string
  label: string
  icon: React.ReactNode
  color: string
  fields: { key: string; label: string; type: string; placeholder: string; help?: string }[]
}

const CHANNELS: ChannelDef[] = [
  {
    id: 'slack',
    label: 'Slack',
    icon: <Hash size={18} />,
    color: 'text-[#4A154B]',
    fields: [
      { key: 'webhook_url', label: 'Webhook URL', type: 'password', placeholder: 'https://hooks.slack.com/services/...', help: 'Create an incoming webhook in your Slack workspace settings' },
    ],
  },
  {
    id: 'email',
    label: 'Email',
    icon: <Mail size={18} />,
    color: 'text-blue-400',
    fields: [
      { key: 'smtp_host', label: 'SMTP Host', type: 'text', placeholder: 'smtp.gmail.com' },
      { key: 'smtp_port', label: 'SMTP Port', type: 'text', placeholder: '587' },
      { key: 'smtp_user', label: 'Username', type: 'text', placeholder: 'you@example.com' },
      { key: 'smtp_password', label: 'Password', type: 'password', placeholder: 'App password' },
      { key: 'from_email', label: 'From Email', type: 'text', placeholder: 'restorex@example.com' },
      { key: 'to_emails', label: 'To Emails', type: 'text', placeholder: 'admin@example.com, team@example.com', help: 'Comma-separated list of recipients' },
    ],
  },
  {
    id: 'telegram',
    label: 'Telegram',
    icon: <Send size={18} />,
    color: 'text-[#0088cc]',
    fields: [
      { key: 'bot_token', label: 'Bot Token', type: 'password', placeholder: '123456:ABC-DEF...', help: 'Get it from @BotFather on Telegram' },
      { key: 'chat_id', label: 'Chat ID', type: 'text', placeholder: '-1001234567890', help: 'Use @userinfobot to get your chat ID' },
    ],
  },
]

function ChannelCard({ def, data, onSave }: { def: ChannelDef; data: NotificationChannel | null; onSave: () => void }) {
  const [config, setConfig] = useState<NotificationChannel>({
    channel: def.id,
    enabled: false,
    on_success: true,
    on_failure: true,
    on_partial: true,
    settings: {},
  })
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({})

  useEffect(() => {
    if (data) setConfig(data)
  }, [data])

  const updateSetting = (key: string, value: string) => {
    setConfig(prev => ({ ...prev, settings: { ...prev.settings, [key]: value } }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.saveNotification(def.id, config)
      toast(`${def.label} configuration saved`, 'success')
      onSave()
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to save', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    // Save first, then test
    setTesting(true)
    try {
      await api.saveNotification(def.id, config)
      const result = await api.testNotification(def.id)
      if (result.success) {
        toast(`${def.label} test sent successfully!`, 'success')
      } else {
        toast(result.message || 'Test failed', 'error')
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Test failed', 'error')
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="theme-bg-card border theme-border rounded-2xl p-6 space-y-5">
      {/* Header with toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-xl bg-white/5 flex items-center justify-center ${def.color}`}>
            {def.icon}
          </div>
          <div>
            <h3 className="text-sm font-semibold theme-text">{def.label}</h3>
            <p className="text-[10px] theme-text-faint">
              {config.enabled ? 'Active — receiving notifications' : 'Disabled'}
            </p>
          </div>
        </div>

        <label className="relative cursor-pointer">
          <input
            type="checkbox"
            checked={config.enabled}
            onChange={e => setConfig(prev => ({ ...prev, enabled: e.target.checked }))}
            className="sr-only peer"
          />
          <div className="w-10 h-5 rounded-full bg-slate-600/40 peer-checked:bg-emerald-500/80 transition-colors" />
          <div className="absolute left-0.5 top-0.5 w-4 h-4 rounded-full bg-slate-300 peer-checked:bg-white peer-checked:translate-x-5 transition-all" />
        </label>
      </div>

      {/* Fields (only show when enabled) */}
      {config.enabled && (
        <>
          <div className="space-y-3">
            {def.fields.map(field => (
              <div key={field.key} className="space-y-1">
                <label className="text-[10px] font-semibold theme-text-tertiary uppercase tracking-wider">
                  {field.label}
                </label>
                <div className="relative">
                  <input
                    type={field.type === 'password' && !showPasswords[field.key] ? 'password' : 'text'}
                    value={config.settings[field.key] || ''}
                    onChange={e => updateSetting(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    className="w-full px-4 py-2.5 rounded-xl theme-bg-primary border theme-border text-sm theme-text-secondary
                               placeholder:theme-text-faint focus:outline-none focus:border-emerald-500/30 focus:ring-1 focus:ring-emerald-500/20
                               transition-all font-mono"
                  />
                  {field.type === 'password' && (
                    <button
                      type="button"
                      onClick={() => setShowPasswords(prev => ({ ...prev, [field.key]: !prev[field.key] }))}
                      className="absolute right-3 top-1/2 -translate-y-1/2 theme-text-faint hover:theme-text-tertiary transition-colors"
                    >
                      {showPasswords[field.key] ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  )}
                </div>
                {field.help && <p className="text-[10px] theme-text-faint">{field.help}</p>}
              </div>
            ))}
          </div>

          {/* Trigger preferences */}
          <div className="pt-3 border-t theme-border">
            <p className="text-[10px] font-semibold theme-text-tertiary uppercase tracking-wider mb-2">
              Notify when
            </p>
            <div className="flex flex-wrap gap-3">
              {[
                { key: 'on_success', label: 'Backup succeeds', color: 'text-emerald-400' },
                { key: 'on_failure', label: 'Backup fails', color: 'text-red-400' },
                { key: 'on_partial', label: 'Partial success', color: 'text-amber-400' },
              ].map(trigger => (
                <label key={trigger.key} className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={config[trigger.key as keyof typeof config] as boolean}
                    onChange={e => setConfig(prev => ({ ...prev, [trigger.key]: e.target.checked }))}
                    className="rounded border-gray-600 bg-transparent text-emerald-500 focus:ring-emerald-500/20 w-3.5 h-3.5"
                  />
                  <span className={`text-xs ${trigger.color} group-hover:brightness-125 transition-all`}>
                    {trigger.label}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 pt-2">
            <button
              onClick={handleTest}
              disabled={testing}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold
                         border theme-border theme-text-secondary hover:border-emerald-500/30 hover:text-emerald-400
                         disabled:opacity-40 transition-all"
            >
              {testing ? <Loader2 size={13} className="animate-spin" /> : <TestTube size={13} />}
              {testing ? 'Sending...' : 'Send Test'}
            </button>

            <button
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold
                         bg-emerald-500 text-white hover:bg-emerald-400
                         disabled:opacity-40 transition-all"
            >
              {saving ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle size={13} />}
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export function NotificationsPage() {
  const [channels, setChannels] = useState<NotificationChannel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadChannels = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getNotifications()
      setChannels(data.channels || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadChannels() }, [])

  if (loading) {
    return (
      <div className="p-7 flex items-center justify-center h-64">
        <Loader2 size={24} className="animate-spin text-emerald-500" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-7 flex flex-col items-center justify-center h-64 gap-4">
        <XCircle size={32} className="text-red-400" />
        <p className="text-sm theme-text-secondary">{error}</p>
        <button onClick={loadChannels} className="px-4 py-2 rounded-xl text-sm font-semibold bg-emerald-600 text-white">
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="p-7 space-y-6 max-w-4xl">
      <div>
        <h2 className="text-lg font-semibold theme-text flex items-center gap-2">
          <Bell size={20} className="text-emerald-400" />
          Notifications
        </h2>
        <p className="text-xs theme-text-muted mt-0.5">
          Get notified when backups complete or fail. Configure one or more channels below.
        </p>
      </div>

      <div className="space-y-4">
        {CHANNELS.map(def => (
          <ChannelCard
            key={def.id}
            def={def}
            data={channels.find(c => c.channel === def.id) || null}
            onSave={loadChannels}
          />
        ))}
      </div>
    </div>
  )
}
