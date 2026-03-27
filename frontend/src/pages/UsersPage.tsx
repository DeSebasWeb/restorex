import { useState, useEffect, useCallback } from 'react'
import { Plus, Pencil, Trash2, RotateCcw, KeyRound, Loader2, X, Eye, EyeOff, UserCheck, UserX, Shield } from 'lucide-react'
import { api } from '../services/api'
import { toast } from '../components/Toast'
import type { ManagedUser, Role } from '../types'

// ── Role badge colors ────────────────────────────────────────────

const ROLE_COLORS: Record<string, string> = {
  admin: 'bg-emerald-500/15 text-emerald-400',
  operator: 'bg-blue-500/15 text-blue-400',
  viewer: 'bg-gray-500/15 text-gray-400',
}

function StatusBadge({ user }: { user: ManagedUser }) {
  if (user.deleted_at) return <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-red-500/15 text-red-400">Deleted</span>
  if (!user.is_active) return <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-500/15 text-amber-400">Inactive</span>
  return <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-500/15 text-emerald-400">Active</span>
}

// ── Main Component ───────────────────────────────────────────────

export function UsersPage() {
  const [users, setUsers] = useState<ManagedUser[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(true)
  const [showDeleted, setShowDeleted] = useState(false)

  // Modal states
  const [modalMode, setModalMode] = useState<'create' | 'edit' | null>(null)
  const [editingUser, setEditingUser] = useState<ManagedUser | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<ManagedUser | null>(null)
  const [resetPassUser, setResetPassUser] = useState<ManagedUser | null>(null)

  // Form states
  const [form, setForm] = useState({ username: '', email: '', password: '', role_id: 0 })
  const [showPassword, setShowPassword] = useState(false)
  const [saving, setSaving] = useState(false)
  const [resetPass, setResetPass] = useState('')
  const [showResetPass, setShowResetPass] = useState(false)

  const fetchUsers = useCallback(async () => {
    try {
      const [usersRes, rolesRes] = await Promise.all([
        api.getUsers(showDeleted),
        api.getRoles(),
      ])
      setUsers(usersRes.users)
      setRoles(rolesRes.roles)
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to load users', 'error')
    } finally {
      setLoading(false)
    }
  }, [showDeleted])

  useEffect(() => { fetchUsers() }, [fetchUsers])

  // ── Handlers ─────────────────────────────────────────────────

  const openCreate = () => {
    setForm({ username: '', email: '', password: '', role_id: roles[0]?.id || 1 })
    setModalMode('create')
    setShowPassword(false)
  }

  const openEdit = (user: ManagedUser) => {
    setEditingUser(user)
    setForm({ username: user.username, email: user.email || '', password: '', role_id: user.role_id })
    setModalMode('edit')
  }

  const closeModal = () => { setModalMode(null); setEditingUser(null) }

  const handleSave = async () => {
    setSaving(true)
    try {
      if (modalMode === 'create') {
        await api.createUser({ username: form.username, email: form.email || undefined, password: form.password, role_id: form.role_id })
        toast('User created', 'success')
      } else if (modalMode === 'edit' && editingUser) {
        await api.updateUser(editingUser.id, { username: form.username, email: form.email || undefined, role_id: form.role_id })
        toast('User updated', 'success')
      }
      closeModal()
      fetchUsers()
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to save', 'error')
    } finally { setSaving(false) }
  }

  const handleDelete = async () => {
    if (!confirmDelete) return
    try {
      await api.deleteUser(confirmDelete.id)
      toast(`User '${confirmDelete.username}' deleted`, 'success')
      setConfirmDelete(null)
      fetchUsers()
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to delete', 'error')
    }
  }

  const handleRestore = async (user: ManagedUser) => {
    try {
      await api.restoreUser(user.id)
      toast(`User '${user.username}' restored`, 'success')
      fetchUsers()
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to restore', 'error')
    }
  }

  const handleResetPassword = async () => {
    if (!resetPassUser) return
    try {
      await api.resetUserPassword(resetPassUser.id, resetPass)
      toast(`Password reset for '${resetPassUser.username}'`, 'success')
      setResetPassUser(null)
      setResetPass('')
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to reset password', 'error')
    }
  }

  const handleToggleActive = async (user: ManagedUser) => {
    try {
      await api.updateUser(user.id, { is_active: !user.is_active })
      toast(`User '${user.username}' ${user.is_active ? 'deactivated' : 'activated'}`, 'success')
      fetchUsers()
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to update', 'error')
    }
  }

  // ── Render ───────────────────────────────────────────────────

  return (
    <div className="p-6 space-y-6 stagger-children">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold theme-text">User Management</h2>
          <p className="text-xs theme-text-faint mt-0.5">{users.length} user{users.length !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs theme-text-muted cursor-pointer">
            <input type="checkbox" checked={showDeleted} onChange={e => setShowDeleted(e.target.checked)}
              className="rounded border-[var(--border)] bg-[var(--bg-input)] accent-emerald-500" />
            Show deleted
          </label>
          <button onClick={openCreate}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-500 transition-colors">
            <Plus size={14} /> New User
          </button>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 size={24} className="animate-spin text-blue-500" />
        </div>
      ) : (
        <div className="rounded-xl border theme-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="theme-bg-table-header">
                <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider theme-text-faint">User</th>
                <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider theme-text-faint">Email</th>
                <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider theme-text-faint">Role</th>
                <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider theme-text-faint">Status</th>
                <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider theme-text-faint">Created</th>
                <th className="px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-wider theme-text-faint">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {users.map(user => (
                <tr key={user.id} className={`theme-hover transition-colors ${user.deleted_at ? 'opacity-50' : ''}`}>
                  <td className="px-4 py-3">
                    <span className={`font-semibold theme-text ${user.deleted_at ? 'line-through' : ''}`}>{user.username}</span>
                    {user.force_password_change && (
                      <span className="ml-2 px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/15 text-amber-400">PW CHANGE</span>
                    )}
                  </td>
                  <td className="px-4 py-3 theme-text-muted text-xs">{user.email || '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${ROLE_COLORS[user.role_name] || ROLE_COLORS.viewer}`}>
                      {user.role_name}
                    </span>
                  </td>
                  <td className="px-4 py-3"><StatusBadge user={user} /></td>
                  <td className="px-4 py-3 theme-text-faint text-xs">
                    {user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      {user.deleted_at ? (
                        <button onClick={() => handleRestore(user)} title="Restore user"
                          className="p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-500/10 transition-colors">
                          <RotateCcw size={14} />
                        </button>
                      ) : (
                        <>
                          <button onClick={() => openEdit(user)} title="Edit user"
                            className="p-1.5 rounded-lg theme-text-faint hover:theme-text hover:bg-[var(--bg-hover)] transition-colors">
                            <Pencil size={14} />
                          </button>
                          <button onClick={() => handleToggleActive(user)} title={user.is_active ? 'Deactivate' : 'Activate'}
                            className={`p-1.5 rounded-lg transition-colors ${user.is_active ? 'text-amber-400 hover:bg-amber-500/10' : 'text-emerald-400 hover:bg-emerald-500/10'}`}>
                            {user.is_active ? <UserX size={14} /> : <UserCheck size={14} />}
                          </button>
                          <button onClick={() => { setResetPassUser(user); setResetPass(''); setShowResetPass(false) }} title="Reset password"
                            className="p-1.5 rounded-lg text-blue-400 hover:bg-blue-500/10 transition-colors">
                            <KeyRound size={14} />
                          </button>
                          <button onClick={() => setConfirmDelete(user)} title="Delete user"
                            className="p-1.5 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors">
                            <Trash2 size={14} />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center theme-text-faint text-sm">No users found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Create / Edit Modal ─────────────────────────────────── */}
      {modalMode && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={closeModal} />
          <div className="relative w-full max-w-md mx-4 rounded-2xl border border-[var(--border)] bg-[var(--bg-primary)] shadow-2xl p-6 animate-fade-up">
            <button onClick={closeModal} className="absolute top-4 right-4 theme-text-faint hover:theme-text"><X size={18} /></button>

            <h3 className="text-base font-bold theme-text mb-4">
              {modalMode === 'create' ? 'Create New User' : `Edit ${editingUser?.username}`}
            </h3>

            <div className="space-y-3">
              <div>
                <label className="text-[10px] font-semibold theme-text-faint uppercase tracking-wider">Username</label>
                <input type="text" value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                  className="w-full mt-1 px-3 py-2.5 rounded-xl text-sm border theme-border bg-[var(--bg-input)] theme-text focus:outline-none focus:border-emerald-500/50" />
              </div>
              <div>
                <label className="text-[10px] font-semibold theme-text-faint uppercase tracking-wider">Email</label>
                <input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  placeholder="Optional"
                  className="w-full mt-1 px-3 py-2.5 rounded-xl text-sm border theme-border bg-[var(--bg-input)] theme-text placeholder:theme-text-faint focus:outline-none focus:border-emerald-500/50" />
              </div>
              {modalMode === 'create' && (
                <div>
                  <label className="text-[10px] font-semibold theme-text-faint uppercase tracking-wider">Password</label>
                  <div className="relative mt-1">
                    <input type={showPassword ? 'text' : 'password'} value={form.password}
                      onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                      placeholder="Min. 8 characters"
                      className="w-full px-3 py-2.5 pr-10 rounded-xl text-sm border theme-border bg-[var(--bg-input)] theme-text placeholder:theme-text-faint focus:outline-none focus:border-emerald-500/50" />
                    <button type="button" onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 theme-text-faint hover:theme-text">
                      {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                </div>
              )}
              <div>
                <label className="text-[10px] font-semibold theme-text-faint uppercase tracking-wider">Role</label>
                <select value={form.role_id} onChange={e => setForm(f => ({ ...f, role_id: Number(e.target.value) }))}
                  className="w-full mt-1 px-3 py-2.5 rounded-xl text-sm border theme-border bg-[var(--bg-input)] theme-text focus:outline-none focus:border-emerald-500/50">
                  {roles.map(r => <option key={r.id} value={r.id}>{r.name} — {r.description}</option>)}
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-5">
              <button onClick={closeModal} className="px-4 py-2 rounded-xl text-xs theme-text-muted hover:theme-text transition-colors">Cancel</button>
              <button onClick={handleSave} disabled={saving || !form.username || (modalMode === 'create' && form.password.length < 8)}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-40 transition-colors flex items-center gap-2">
                {saving ? <Loader2 size={13} className="animate-spin" /> : <Shield size={13} />}
                {modalMode === 'create' ? 'Create' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Delete Confirmation ──────────────────────────────────── */}
      {confirmDelete && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setConfirmDelete(null)} />
          <div className="relative w-full max-w-sm mx-4 rounded-2xl border border-red-500/30 bg-[var(--bg-primary)] shadow-2xl p-6 animate-fade-up">
            <h3 className="text-base font-bold theme-text mb-2">Delete User</h3>
            <p className="text-sm theme-text-muted mb-4">
              Are you sure you want to delete <strong className="theme-text">{confirmDelete.username}</strong>?
              The user will be deactivated and hidden, but the record is preserved.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmDelete(null)} className="px-4 py-2 rounded-xl text-xs theme-text-muted hover:theme-text">Cancel</button>
              <button onClick={handleDelete} className="px-5 py-2 rounded-xl text-xs font-bold bg-red-600 text-white hover:bg-red-500 transition-colors flex items-center gap-2">
                <Trash2 size={13} /> Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Reset Password Modal ─────────────────────────────────── */}
      {resetPassUser && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setResetPassUser(null)} />
          <div className="relative w-full max-w-sm mx-4 rounded-2xl border border-[var(--border)] bg-[var(--bg-primary)] shadow-2xl p-6 animate-fade-up">
            <h3 className="text-base font-bold theme-text mb-2">Reset Password</h3>
            <p className="text-xs theme-text-muted mb-4">Set a new password for <strong className="theme-text">{resetPassUser.username}</strong>. They will be forced to change it on next login.</p>
            <div className="relative">
              <input type={showResetPass ? 'text' : 'password'} value={resetPass} onChange={e => setResetPass(e.target.value)}
                placeholder="New password (min. 8 chars)"
                className="w-full px-3 py-2.5 pr-10 rounded-xl text-sm border theme-border bg-[var(--bg-input)] theme-text placeholder:theme-text-faint focus:outline-none focus:border-emerald-500/50" />
              <button type="button" onClick={() => setShowResetPass(!showResetPass)}
                className="absolute right-3 top-1/2 -translate-y-1/2 theme-text-faint hover:theme-text">
                {showResetPass ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setResetPassUser(null)} className="px-4 py-2 rounded-xl text-xs theme-text-muted hover:theme-text">Cancel</button>
              <button onClick={handleResetPassword} disabled={resetPass.length < 8}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-40 transition-colors flex items-center gap-2">
                <KeyRound size={13} /> Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
