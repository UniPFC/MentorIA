'use client';

import { InputHTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, icon, rightIcon, className, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');
    return (
      <div className="w-full">
        {label && (
          <label htmlFor={inputId} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
            {label}
          </label>
        )}
        <div className="relative group">
          {icon && (
            <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 transition-colors group-focus-within:text-brand-500 dark:group-focus-within:text-brand-400">
              {icon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            className={clsx(
              'w-full rounded-xl border bg-white text-gray-900 placeholder-gray-400 text-sm transition-all duration-200',
              'focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500 focus:shadow-sm focus:shadow-brand-500/10',
              'dark:bg-gray-800/80 dark:border-gray-700 dark:text-gray-100 dark:placeholder-gray-500 dark:focus:ring-brand-400/30 dark:focus:border-brand-400',
              error
                ? 'border-red-300 focus:ring-red-500/30 focus:border-red-500 dark:border-red-600'
                : 'border-gray-300 hover:border-gray-400 dark:hover:border-gray-600',
              icon ? 'pl-10' : 'pl-3.5',
              rightIcon ? 'pr-10' : 'pr-3.5',
              'py-2.5',
              className,
            )}
            {...props}
          />
          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500">
              {rightIcon}
            </div>
          )}
        </div>
        {error && <p className="mt-1.5 text-xs text-red-500 dark:text-red-400 flex items-center gap-1">{error}</p>}
      </div>
    );
  },
);

Input.displayName = 'Input';
export default Input;
