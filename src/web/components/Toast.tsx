'use client';

import { useEffect, useState } from 'react';

interface ToastProps {
  message: string;
  type?: 'success' | 'error' | 'info';
  duration?: number;
  onClose?: () => void;
}

export default function Toast({ message, type = 'info', duration = 3500, onClose }: ToastProps) {
  const [visible, setVisible] = useState(false);
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true));
    const timer = setTimeout(() => {
      setExiting(true);
      setTimeout(() => {
        setVisible(false);
        onClose?.();
      }, 300);
    }, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  if (!visible && !exiting) {
    // Trigger initial render
    return (
      <div className="fixed bottom-5 right-5 z-50">
        <div className={`${baseStyles(type)} translate-x-full opacity-0`}>
          {getIcon(type)}
          <span>{message}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-5 right-5 z-50">
      <div
        className={`${baseStyles(type)} transition-all duration-300 ${
          exiting ? 'translate-x-full opacity-0' : 'translate-x-0 opacity-100'
        }`}
      >
        {getIcon(type)}
        <span>{message}</span>
      </div>
    </div>
  );
}

function baseStyles(type: 'success' | 'error' | 'info') {
  const colors = {
    success: 'bg-emerald-600 dark:bg-emerald-500 shadow-emerald-500/25',
    error: 'bg-red-600 dark:bg-red-500 shadow-red-500/25',
    info: 'bg-brand-600 dark:bg-brand-500 shadow-brand-500/25',
  }[type];

  return `${colors} text-white px-5 py-3.5 rounded-xl shadow-lg flex items-center gap-3 text-sm font-medium backdrop-blur-sm`;
}

function getIcon(type: 'success' | 'error' | 'info') {
  const icons = {
    success: (
      <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center shrink-0">
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>
    ),
    error: (
      <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center shrink-0">
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>
    ),
    info: (
      <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center shrink-0">
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
    ),
  };
  return icons[type];
}
