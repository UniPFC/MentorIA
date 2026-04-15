'use client';

import { useState } from 'react';
import clsx from 'clsx';

interface Tab {
  id: string;
  label: string;
  icon?: React.ReactNode;
  count?: number;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export default function Tabs({ tabs, activeTab, onChange, className }: TabsProps) {
  return (
    <div className={clsx('flex border-b border-gray-200 dark:border-gray-800', className)}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={clsx(
            'flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition-all duration-200 -mb-px',
            activeTab === tab.id
              ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300',
          )}
        >
          {tab.icon}
          {tab.label}
          {tab.count !== undefined && (
            <span
              className={clsx(
                'px-1.5 py-0.5 rounded-lg text-xs font-semibold',
                activeTab === tab.id
                  ? 'bg-brand-50 text-brand-600 dark:bg-brand-500/10 dark:text-brand-400'
                  : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
              )}
            >
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
