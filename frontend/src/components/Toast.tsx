import { useEffect, useState } from 'react'

export type ToastType = 'success' | 'error' | 'info'

interface ToastMessage {
  id: number
  message: string
  type: ToastType
}

let addToastFn: ((message: string, type: ToastType) => void) | null = null
let toastCounter = 0

export function toast(message: string, type: ToastType = 'info') {
  addToastFn?.(message, type)
}

const typeClasses = {
  success: 'bg-emerald-600/90 text-emerald-50 border border-emerald-500/30 shadow-emerald-500/10',
  error:   'bg-red-600/90 text-red-50 border border-red-500/30 shadow-red-500/10',
  info:    'bg-blue-600/90 text-blue-50 border border-blue-500/30 shadow-blue-500/10',
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  useEffect(() => {
    addToastFn = (message: string, type: ToastType) => {
      const id = ++toastCounter
      setToasts(prev => [...prev, { id, message, type }])
      setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
    }
    return () => { addToastFn = null }
  }, [])

  return (
    <div className="fixed bottom-6 right-6 z-[1000] flex flex-col gap-2">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`px-5 py-3 rounded-xl text-sm font-medium shadow-2xl animate-slide-in max-w-sm backdrop-blur-sm ${typeClasses[t.type]}`}
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}
