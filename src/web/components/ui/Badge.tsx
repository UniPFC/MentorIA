'use client';

import clsx from 'clsx';

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  dot?: boolean;
}

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-gray-100 text-gray-600 ring-gray-500/10 dark:bg-gray-800 dark:text-gray-300 dark:ring-gray-400/10',
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-500/10 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-400/10',
  warning: 'bg-amber-50 text-amber-700 ring-amber-500/10 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-400/10',
  danger: 'bg-red-50 text-red-700 ring-red-500/10 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-400/10',
  info: 'bg-brand-50 text-brand-700 ring-brand-500/10 dark:bg-brand-500/10 dark:text-brand-400 dark:ring-brand-400/10',
};

const dotClasses: Record<BadgeVariant, string> = {
  default: 'bg-gray-400',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-red-500',
  info: 'bg-brand-500',
};

export default function Badge({ children, variant = 'default', dot }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg text-xs font-medium ring-1 ring-inset',
        variantClasses[variant],
      )}
    >
      {dot && <span className={clsx('w-1.5 h-1.5 rounded-full', dotClasses[variant])} />}
      {children}
    </span>
  );
}
