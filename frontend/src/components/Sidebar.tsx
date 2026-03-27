import { Database, LayoutDashboard, Clock, FileText, BarChart3, Bell, Settings, LogOut, User } from 'lucide-react'
import type { AuthUser } from '../types'

interface SidebarProps {
  activeTab: string
  onTabChange: (tab: string) => void
  user?: AuthUser | null
  onLogout?: () => void
}

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, minRole: 'viewer' },
  { id: 'databases', label: 'Databases', icon: Database, minRole: 'viewer' },
  { id: 'history', label: 'History', icon: Clock, minRole: 'viewer' },
  { id: 'reports', label: 'Reports', icon: BarChart3, minRole: 'viewer' },
  { id: 'logs', label: 'Logs', icon: FileText, minRole: 'viewer' },
  { id: 'notifications', label: 'Notifications', icon: Bell, minRole: 'admin' },
  { id: 'settings', label: 'Settings', icon: Settings, minRole: 'admin' },
]

const ROLE_LEVEL: Record<string, number> = { admin: 3, operator: 2, viewer: 1 }

export function Sidebar({ activeTab, onTabChange, user, onLogout }: SidebarProps) {
  const userLevel = ROLE_LEVEL[user?.role || ''] || 0

  const visibleItems = navItems.filter(item => userLevel >= (ROLE_LEVEL[item.minRole] || 0))

  return (
    <nav className="w-64 theme-bg-secondary flex flex-col fixed top-0 left-0 bottom-0 z-50 theme-border border-r transition-colors duration-300">
      {/* Logo */}
      <div className="px-6 py-6">
        <div className="flex items-center gap-3">
          <img src="/logo.png" alt="Restorex" className="w-10 h-10 rounded-xl shadow-lg shadow-emerald-500/20" />
          <div className="flex flex-col">
            <span className="text-[15px] font-bold theme-text tracking-tight">Restorex</span>
            <span className="text-[10px] theme-text-faint font-medium tracking-wider uppercase">Backup Engine</span>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-4 h-px bg-gradient-to-r from-transparent via-[var(--border)] to-transparent" />

      {/* Nav links */}
      <div className="flex-1 px-3 py-4 space-y-1">
        <p className="px-3 mb-2 text-[10px] font-semibold uppercase tracking-widest theme-text-faint">Main Menu</p>
        {visibleItems.map(({ id, label, icon: Icon }) => {
          const isActive = activeTab === id
          return (
            <button
              key={id}
              onClick={() => onTabChange(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all duration-200 relative group
                ${isActive
                  ? 'bg-gradient-to-r from-blue-500/15 to-indigo-500/10 text-blue-500'
                  : 'theme-text-muted theme-hover hover:theme-text-tertiary'
                }`}
            >
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
              )}
              <Icon size={18} className={isActive ? 'text-blue-500' : 'theme-text-faint group-hover:theme-text-muted'} />
              {label}
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-500 shadow-[0_0_6px_rgba(59,130,246,0.8)]" />
              )}
            </button>
          )
        })}
      </div>

      {/* User info + Logout */}
      {user && (
        <div className="px-4 pb-3">
          <div className="rounded-xl theme-bg-primary border theme-border p-3">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/20 flex items-center justify-center">
                <User size={14} className="text-emerald-500" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold theme-text truncate">{user.username}</p>
                <span className={`inline-block text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded mt-0.5 ${
                  user.role === 'admin' ? 'bg-emerald-500/15 text-emerald-400' :
                  user.role === 'operator' ? 'bg-blue-500/15 text-blue-400' :
                  'bg-gray-500/15 text-gray-400'
                }`}>
                  {user.role}
                </span>
              </div>
              <button
                onClick={() => onLogout?.()}
                title="Sign out"
                className="p-1.5 rounded-lg theme-text-faint hover:text-red-400 hover:bg-red-500/10 transition-all"
              >
                <LogOut size={14} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="px-4 pb-4">
        <p className="text-center text-[10px] theme-text-faint">Restorex v1.0.0</p>
      </div>
    </nav>
  )
}
