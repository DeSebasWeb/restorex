import { useState, useCallback } from 'react'
import { Eye, EyeOff, Loader2, Lock, Shield, AlertTriangle } from 'lucide-react'

interface ChangePasswordModalProps {
  forced?: boolean
  onChangePassword: (currentPassword: string, newPassword: string) => Promise<void>
  onClose?: () => void
}

export function ChangePasswordModal({ forced, onChangePassword, onClose }: ChangePasswordModalProps) {
  const [current, setCurrent] = useState('')
  const [newPass, setNewPass] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew, setShowNew] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const isValid = current && newPass.length >= 8 && newPass === confirm

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValid) return

    setError('')
    setLoading(true)
    try {
      await onChangePassword(current, newPass)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to change password')
    } finally {
      setLoading(false)
    }
  }, [current, newPass, isValid, onChangePassword])

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-md" />

      <div className="relative w-full max-w-md mx-4 animate-fade-up">
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-primary)] shadow-2xl p-8">

          {/* Header */}
          <div className="text-center mb-6">
            <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
              {forced ? <AlertTriangle size={24} className="text-amber-500" /> : <Lock size={24} className="text-emerald-500" />}
            </div>
            <h2 className="text-lg font-bold text-[var(--text-primary)]">
              {forced ? 'Password Change Required' : 'Change Password'}
            </h2>
            <p className="text-xs text-[var(--text-faint)] mt-1">
              {forced
                ? 'You must change your default password before continuing'
                : 'Enter your current password and choose a new one'
              }
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Current Password */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">Current Password</label>
              <div className="relative">
                <input
                  type={showCurrent ? 'text' : 'password'}
                  value={current}
                  onChange={e => setCurrent(e.target.value)}
                  placeholder="••••••••"
                  autoFocus
                  className="w-full px-4 py-3 pr-11 rounded-xl text-sm border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] placeholder:text-[var(--text-faint)] focus:outline-none focus:border-emerald-500/50 transition-colors"
                />
                <button type="button" onClick={() => setShowCurrent(!showCurrent)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-faint)] hover:text-[var(--text-secondary)]">
                  {showCurrent ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            {/* New Password */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">New Password</label>
              <div className="relative">
                <input
                  type={showNew ? 'text' : 'password'}
                  value={newPass}
                  onChange={e => setNewPass(e.target.value)}
                  placeholder="Min. 8 characters"
                  className="w-full px-4 py-3 pr-11 rounded-xl text-sm border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] placeholder:text-[var(--text-faint)] focus:outline-none focus:border-emerald-500/50 transition-colors"
                />
                <button type="button" onClick={() => setShowNew(!showNew)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-faint)] hover:text-[var(--text-secondary)]">
                  {showNew ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              {newPass && newPass.length < 8 && (
                <p className="text-[10px] text-red-400">Must be at least 8 characters</p>
              )}
            </div>

            {/* Confirm Password */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">Confirm Password</label>
              <input
                type="password"
                value={confirm}
                onChange={e => setConfirm(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-3 rounded-xl text-sm border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] placeholder:text-[var(--text-faint)] focus:outline-none focus:border-emerald-500/50 transition-colors"
              />
              {confirm && confirm !== newPass && (
                <p className="text-[10px] text-red-400">Passwords don't match</p>
              )}
            </div>

            {/* Error */}
            {error && (
              <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20">
                <p className="text-xs text-red-400">{error}</p>
              </div>
            )}

            {/* Buttons */}
            <div className="flex gap-3 pt-2">
              {!forced && onClose && (
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 py-3 rounded-xl text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] transition-colors"
                >
                  Cancel
                </button>
              )}
              <button
                type="submit"
                disabled={!isValid || loading}
                className="flex-1 py-3 rounded-xl text-sm font-bold bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-40 transition-all flex items-center justify-center gap-2"
              >
                {loading ? (
                  <><Loader2 size={14} className="animate-spin" /> Changing...</>
                ) : (
                  <><Shield size={14} /> Change Password</>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
