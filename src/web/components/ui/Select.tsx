'use client';

import { forwardRef, SelectHTMLAttributes } from 'react';
import clsx from 'clsx';
import { ChevronDown } from 'lucide-react';

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { value: string; label: string }[];
  placeholder?: string;
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, placeholder, className, id, ...props }, ref) => {
    const selectId = id || label?.toLowerCase().replace(/\s+/g, '-');
    return (
      <div className="w-full">
        {label && (
          <label htmlFor={selectId} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
            {label}
          </label>
        )}
        <div className="relative">
          <select
            ref={ref}
            id={selectId}
            className={clsx(
              'w-full appearance-none rounded-xl border bg-white text-gray-900 text-sm transition-all duration-200 pl-3.5 pr-10 py-2.5',
              'focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 focus:shadow-sm focus:shadow-brand-500/10',
              'hover:border-gray-400 dark:hover:border-gray-600',
              'dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100 dark:focus:ring-brand-400/40 dark:focus:border-brand-400',
              error ? 'border-red-300 dark:border-red-600' : 'border-gray-300',
              className,
            )}
            {...props}
          >
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
        {error && <p className="mt-1 text-xs text-red-500 dark:text-red-400">{error}</p>}
      </div>
    );
  },
);

Select.displayName = 'Select';
export default Select;
