import { Database, LayoutDashboard, Clock, FileText, BarChart3, Bell, Shield, Settings } from 'lucide-react'

interface SidebarProps {
  activeTab: string
  onTabChange: (tab: string) => void
}

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'databases', label: 'Databases', icon: Database },
  { id: 'history', label: 'History', icon: Clock },
  { id: 'reports', label: 'Reports', icon: BarChart3 },
  { id: 'logs', label: 'Logs', icon: FileText },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'settings', label: 'Settings', icon: Settings },
]

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  return (
    <nav className="w-64 theme-bg-secondary flex flex-col fixed top-0 left-0 bottom-0 z-50 theme-border border-r transition-colors duration-300">
      {/* Logo */}
      <div className="px-6 py-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Shield size={20} className="text-white" />
          </div>
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
        {navItems.map(({ id, label, icon: Icon }) => {
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

      {/* Footer */}
      <div className="px-4 pb-5">
        <div className="rounded-xl bg-gradient-to-br from-blue-500/[0.08] to-indigo-500/[0.04] border border-blue-500/10 p-4">
          <div className="flex items-center gap-2 mb-1.5">
            <Shield size={14} className="text-blue-400" />
            <span className="text-[11px] font-semibold text-emerald-400">Secure System</span>
          </div>
          <p className="text-[10px] theme-text-muted leading-relaxed">
            Encrypted SSH transfers, validated operations, hexagonal architecture.
          </p>
        </div>
        <p className="text-center text-[10px] theme-text-faint mt-3">Restorex v1.0.0</p>
      </div>
    </nav>
  )
}
