'use client';

import { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export default function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4 text-center animate-fade-in">
      {icon && (
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-gray-100 to-gray-50 dark:from-gray-800 dark:to-gray-800/50 flex items-center justify-center mb-5 text-gray-400 dark:text-gray-500 shadow-sm">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1.5">{title}</h3>
      {description && <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm leading-relaxed">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
