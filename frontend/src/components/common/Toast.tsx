import { create } from 'zustand'
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
  success: 'bg-green-900/30 border-green-800 text-green-300',
  error: 'bg-red-900/30 border-red-800 text-red-300',
  info: 'bg-blue-900/30 border-blue-800 text-blue-300',
  loading: 'bg-violet-900/30 border-violet-800 text-violet-300',
}

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore()

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map(toast => (
        <div
          key={toast.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg min-w-[280px] max-w-md pointer-events-auto animate-slide-in ${
            colors[toast.type]
          }`}
        >
          <icons[toast.type] className="h-5 w-5 flex-shrink-0" />
          <span className="text-sm flex-1">{toast.message}</span>
          <button
            onClick={() => removeToast(toast.id)}
            className="text-current opacity-50 hover:opacity-100"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  )
}