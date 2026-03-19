interface StatusDotProps {
  status: 'green' | 'yellow' | 'red' | 'gray'
  label?: string
  pulse?: boolean
}

const dotClasses = {
  green:  'bg-emerald-500',
  yellow: 'bg-amber-500',
  red:    'bg-red-500',
  gray:   'bg-gray-600',
}

const glowClasses = {
  green:  'bg-emerald-500/40',
  yellow: 'bg-amber-500/40',
  red:    'bg-red-500/40',
  gray:   'bg-gray-600/40',
}

const labelClasses = {
  green:  'text-emerald-400 bg-emerald-500/10',
  yellow: 'text-amber-400 bg-amber-500/10',
  red:    'text-red-400 bg-red-500/10',
  gray:   'text-gray-500 bg-gray-500/10',
}

export function StatusDot({ status, label, pulse = false }: StatusDotProps) {
  if (label) {
    return (
      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold ${labelClasses[status]}`}>
        <span className="relative flex h-2 w-2">
          {(pulse || status === 'green') && (
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${glowClasses[status]}`} />
          )}
          <span className={`relative inline-flex rounded-full h-2 w-2 ${dotClasses[status]}`} />
        </span>
        {label}
      </span>
    )
  }

  return (
    <span className="relative flex h-2.5 w-2.5">
      {(pulse || status === 'green') && (
        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-50 ${glowClasses[status]}`} />
      )}
      <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${dotClasses[status]}`} />
    </span>
  )
}
