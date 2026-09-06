import { clsx } from 'clsx'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'critical' | 'high' | 'medium' | 'low' | 'success' | 'warning' | 'danger'
  className?: string
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  const variants = {
    default: 'bg-slate-700 text-slate-200',
    critical: 'bg-red-900/30 text-red-300 border border-red-800',
    high: 'bg-orange-900/30 text-orange-300 border border-orange-800',
    medium: 'bg-yellow-900/30 text-yellow-300 border border-yellow-800',
    low: 'bg-blue-900/30 text-blue-300 border border-blue-800',
    success: 'bg-green-900/30 text-green-300 border border-green-800',
    warning: 'bg-amber-900/30 text-amber-300 border border-amber-800',
    danger: 'bg-red-900/30 text-red-300 border border-red-800',
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  )
}