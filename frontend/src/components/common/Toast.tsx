import { create } from 'zustand'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertCircle, CheckCircle, Info, Loader2, X } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'info' | 'loading'

export interface Toast {
  id: string
  type: ToastType
  message: string
  duration?: number
}

interface ToastState {
  toasts: Toast[]
  addToast: (type: ToastType, message: string, duration?: number) => string
  removeToast: (id: string) => void
  success: (message: string, duration?: number) => string
  error: (message: string, duration?: number) => string
  info: (message: string, duration?: number) => string
  loading: (message: string) => string
}

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],
  addToast: (type, message, duration = 5000) => {
    const id = Math.random().toString(36).slice(2)
    const toast: Toast = { id, type, message, duration }
    set(state => ({ toasts: [...state.toasts, toast] }))
    if (duration > 0) {
      setTimeout(() => get().removeToast(id), duration)
    }
    return id
  },
  removeToast: (id) => set(state => ({ toasts: state.toasts.filter(t => t.id !== id) })),
  success: (message, duration) => get().addToast('success', message, duration),
  error: (message, duration) => get().addToast('error', message, duration),
  info: (message, duration) => get().addToast('info', message, duration),
  loading: (message) => get().addToast('loading', message, 0),
}))

const icons = {
  success: CheckCircle,
  error: AlertCircle,
  info: Info,
  loading: Loader2,
}

const colors = {
  success: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400',
  error: 'bg-red-500/15 border-red-500/30 text-red-400',
  info: 'bg-cyan-500/15 border-cyan-500/30 text-cyan-400',
  loading: 'bg-blue-500/15 border-blue-500/30 text-blue-400',
}

const iconColors = {
  success: 'text-emerald-400',
  error: 'text-red-400',
  info: 'text-cyan-400',
  loading: 'text-blue-400',
}

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore()

  return (
    <AnimatePresence>
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map(toast => {
          const IconComponent = icons[toast.type]
          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, x: 100, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 100, scale: 0.95 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl border shadow-lg min-w-[280px] max-w-md pointer-events-auto ${colors[toast.type]}`}
            >
              <IconComponent className={`h-5 w-5 flex-shrink-0 ${iconColors[toast.type]}`} />
              <span className="text-sm text-slate-200 flex-1">{toast.message}</span>
              <button
                onClick={() => removeToast(toast.id)}
                className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-white/5 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          )
        })}
      </div>
    </AnimatePresence>
  )
}