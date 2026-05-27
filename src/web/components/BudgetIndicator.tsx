'use client';

import { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import { createPortal } from 'react-dom';
import { Zap } from 'lucide-react';
import BudgetProgressBar from './BudgetProgressBar';
import api from '@/lib/api';

interface BudgetIndicatorProps {
  className?: string;
  popoverPosition?: 'right' | 'bottom';
}

export interface BudgetIndicatorRef {
  refreshUserData: () => Promise<void>;
}

const BudgetIndicator = forwardRef<BudgetIndicatorRef, BudgetIndicatorProps>(({ className = '', popoverPosition = 'right' }, ref) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isTooltipOpen, setIsTooltipOpen] = useState(false);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUserData();
  }, []);

  const loadUserData = async () => {
    try {
      const res = await api.get('/auth/me');
      setUser(res.data);
    } catch (error) {
      console.error('Error loading user data:', error);
    } finally {
      setLoading(false);
    }
  };

  useImperativeHandle(ref, () => ({
    refreshUserData: loadUserData
  }));

  const isUnlimited = user?.level === 'LEVEL_05';
  const percentage = isUnlimited
    ? 100
    : user?.max_token_budget && user?.max_token_budget > 0
    ? (user.token_budget / user.max_token_budget) * 100
    : 0;

  const getLevelLabel = (level: string) => {
    const labels: Record<string, string> = {
      'LEVEL_01': 'Gratuito',
      'LEVEL_02': 'Lite',
      'LEVEL_03': 'Plus',
      'LEVEL_04': 'Max',
      'LEVEL_05': 'Admin',
    };
    return labels[level] || level;
  };

  const getLevelColor = (level: string) => {
    const colors: Record<string, string> = {
      'LEVEL_01': 'text-gray-500',
      'LEVEL_02': 'text-brand-500',
      'LEVEL_03': 'text-brand-600',
      'LEVEL_04': 'text-brand-700',
      'LEVEL_05': 'text-purple-600',
    };
    return colors[level] || 'text-gray-500';
  };

  if (loading) {
    return (
      <div className={`animate-pulse ${className}`}>
        <div className="w-6 h-6 bg-gray-200 dark:bg-gray-700 rounded-lg" />
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Trigger with custom tooltip */}
      <div
        className="flex items-center gap-1.5 cursor-pointer group relative"
        onClick={() => setIsModalOpen(true)}
        onMouseEnter={(e) => {
          if (popoverPosition === 'right') {
            const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
            setTooltipPos({ x: rect.right + 8, y: rect.top + rect.height / 2 });
          }
          setIsTooltipOpen(true);
        }}
        onMouseLeave={() => setIsTooltipOpen(false)}
      >
        <div className="relative">
          <Zap className={`w-4 h-4 ${percentage < 20 ? 'text-red-500' : 'text-brand-500'} group-hover:scale-110 transition-transform duration-200`} />
          {percentage < 20 && (
            <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
          )}
        </div>
        <div className="w-10 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              percentage < 20 ? 'bg-red-500' : 'bg-gradient-to-r from-brand-500 to-brand-600'
            }`}
            style={{ width: `${percentage}%` }}
          />
        </div>

        {/* Custom tooltip - inline for bottom, portal for right (sidebar) */}
        {isTooltipOpen && popoverPosition === 'bottom' && (
          <div className="absolute left-0 top-full mt-2 px-2 py-1 bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-xs font-medium rounded-lg shadow-lg whitespace-nowrap animate-fade-in z-10">
            {percentage.toFixed(0)}% de créditos restantes
            <div className="absolute -top-1 left-3 border-4 border-transparent border-b-gray-900 dark:border-b-white" />
          </div>
        )}
      </div>

      {/* Modal with portal */}
      {isModalOpen && typeof window !== 'undefined' && createPortal(
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[9999] flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-white dark:bg-gray-900 border border-gray-200/80 dark:border-gray-800/80 rounded-2xl shadow-xl shadow-gray-200/50 dark:shadow-gray-900/50 w-full max-w-sm overflow-hidden animate-scale-in">
            {/* Header */}
            <div className="bg-gradient-to-r from-brand-600 to-brand-700 px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-white" />
                <span className="text-xs font-bold text-white">Créditos</span>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-white/70 hover:text-white transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              {/* Plan info */}
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wide">Plano</span>
                <span className={`text-sm font-bold ${getLevelColor(user?.level || 'LEVEL_01')}`}>
                  {getLevelLabel(user?.level || 'LEVEL_01')}
                </span>
              </div>

              {/* Progress bar */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wide">Disponível</span>
                  <span className={`text-sm font-bold ${isUnlimited ? 'text-purple-600 dark:text-purple-400' : percentage < 20 ? 'text-red-600 dark:text-red-400' : 'text-brand-600 dark:text-brand-400'}`}>
                    {percentage.toFixed(0)}%
                  </span>
                </div>
                <BudgetProgressBar
                  current={isUnlimited ? 10000 : (user?.token_budget || 0)}
                  max={isUnlimited ? 10000 : (user?.max_token_budget || 10000)}
                  showLabel={false}
                  isAdmin={isUnlimited}
                />
              </div>

              {/* Warning if low */}
              {percentage < 20 && !isUnlimited && (
                <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-lg">
                  <Zap className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-red-600 dark:text-red-400">
                    Créditos baixos. Recarregue!
                  </p>
                </div>
              )}

              {/* Refill button */}
              <button
                onClick={() => {
                  setIsModalOpen(false);
                  window.location.href = '/dashboard/profile';
                }}
                className="w-full py-2 px-4 rounded-lg bg-gradient-to-r from-brand-500 to-brand-600 text-white text-sm font-semibold hover:from-brand-600 hover:to-brand-700 transition-all duration-200 active:scale-95"
              >
                Gerenciar Plano
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Sidebar tooltip via portal - escapes overflow-y-auto */}
      {isTooltipOpen && popoverPosition === 'right' && typeof window !== 'undefined' && createPortal(
        <div
          className="fixed px-2 py-1 bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-xs font-medium rounded-lg shadow-lg whitespace-nowrap animate-fade-in z-[9998] pointer-events-none"
          style={{ left: tooltipPos.x, top: tooltipPos.y, transform: 'translateY(-50%)' }}
        >
          {percentage.toFixed(0)}% de créditos restantes
          <div className="absolute top-1/2 -left-1 -translate-y-1/2 border-4 border-transparent border-r-gray-900 dark:border-r-white" />
        </div>,
        document.body
      )}
    </div>
  );
});

BudgetIndicator.displayName = 'BudgetIndicator';

export default BudgetIndicator;
