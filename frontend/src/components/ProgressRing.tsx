interface ProgressRingProps {
  percentage: number
  size?: number
  strokeWidth?: number
  label: string
}

export function ProgressRing({ percentage, size = 120, strokeWidth = 8, label }: ProgressRingProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (percentage / 100) * circumference

  const color = percentage >= 80
    ? 'text-emerald-500'
    : percentage >= 50
      ? 'text-amber-500'
      : 'text-red-500'

  const shadow = percentage >= 80
    ? 'drop-shadow-[0_0_8px_rgba(16,185,129,0.4)]'
    : percentage >= 50
      ? 'drop-shadow-[0_0_8px_rgba(245,158,11,0.4)]'
      : 'drop-shadow-[0_0_8px_rgba(239,68,68,0.4)]'

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className={`-rotate-90 ${shadow}`}>
          {/* Background ring */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-[var(--border)]"
          />
          {/* Progress ring */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={`${color} transition-all duration-1000 ease-out`}
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-2xl font-extrabold ${color}`}>{Math.round(percentage)}%</span>
        </div>
      </div>
      <span className="text-[11px] theme-text-muted font-semibold uppercase tracking-wider">{label}</span>
    </div>
  )
}
