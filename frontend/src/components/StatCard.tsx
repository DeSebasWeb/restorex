import type { ReactNode } from 'react'

interface StatCardProps {
  icon: ReactNode
  value: number | string
  label: string
  color: 'blue' | 'green' | 'yellow' | 'red' | 'purple'
  subtitle?: string
}

const themes = {
  blue: {
    icon: 'bg-blue-500/15 text-blue-500 shadow-blue-500/10',
    glow: 'from-blue-500/[0.03]',
  },
  green: {
    icon: 'bg-emerald-500/15 text-emerald-500 shadow-emerald-500/10',
    glow: 'from-emerald-500/[0.03]',
  },
  yellow: {
    icon: 'bg-amber-500/15 text-amber-500 shadow-amber-500/10',
    glow: 'from-amber-500/[0.03]',
  },
  red: {
    icon: 'bg-red-500/15 text-red-500 shadow-red-500/10',
    glow: 'from-red-500/[0.03]',
  },
  purple: {
    icon: 'bg-purple-500/15 text-purple-500 shadow-purple-500/10',
    glow: 'from-purple-500/[0.03]',
  },
}

export function StatCard({ icon, value, label, color, subtitle }: StatCardProps) {
  const t = themes[color]
  return (
    <div className="relative overflow-hidden theme-bg-card theme-border border rounded-2xl p-5
                    theme-border-hover transition-all duration-300 group">
      <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl ${t.glow} to-transparent rounded-full -translate-y-1/2 translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />

      <div className="relative flex items-center gap-4">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center shadow-lg ${t.icon}`}>
          {icon}
        </div>
        <div className="flex flex-col">
          <span className="text-[28px] font-extrabold leading-none theme-text tracking-tight">{value}</span>
          <span className="text-[11px] theme-text-muted mt-1 font-semibold uppercase tracking-wider">{label}</span>
          {subtitle && (
            <span className="text-[10px] theme-text-faint mt-0.5">{subtitle}</span>
          )}
        </div>
      </div>
    </div>
  )
}
