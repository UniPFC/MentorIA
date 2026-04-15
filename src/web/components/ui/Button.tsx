'use client';

import { ButtonHTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
}

const variants: Record<ButtonVariant, string> = {
  primary:
    'bg-gradient-to-r from-brand-600 to-brand-700 text-white hover:from-brand-700 hover:to-brand-800 active:from-brand-800 active:to-brand-900 focus:ring-brand-500/40 shadow-sm shadow-brand-500/25 hover:shadow-md hover:shadow-brand-500/30 dark:from-brand-500 dark:to-brand-600 dark:hover:from-brand-600 dark:hover:to-brand-700',
  secondary:
    'border border-gray-200 text-gray-700 bg-white hover:bg-gray-50 hover:border-gray-300 active:bg-gray-100 focus:ring-gray-500/20 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:border-gray-600',
  danger:
    'bg-gradient-to-r from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 active:from-red-700 active:to-red-800 focus:ring-red-500/40 shadow-sm shadow-red-500/20 dark:from-red-500 dark:to-red-600',
  ghost:
    'text-gray-600 hover:bg-gray-100 active:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-800',
};

const sizes: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs rounded-lg gap-1.5',
  md: 'px-4 py-2.5 text-sm rounded-xl gap-2',
  lg: 'px-6 py-3 text-base rounded-xl gap-2.5',
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, icon, children, className, disabled, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={clsx(
        'inline-flex items-center justify-center font-semibold transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {loading ? (
        <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : icon ? (
        icon
      ) : null}
      {children}
    </button>
  ),
);

Button.displayName = 'Button';
export default Button;
