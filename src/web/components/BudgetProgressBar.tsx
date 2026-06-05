'use client';

import { useEffect, useState } from 'react';
import { Zap } from 'lucide-react';

interface BudgetProgressBarProps {
  current: number;
  max: number;
  showLabel?: boolean;
  className?: string;
  isAdmin?: boolean;
}

export default function BudgetProgressBar({
  current,
  max,
  showLabel = true,
  className = '',
  isAdmin = false
}: BudgetProgressBarProps) {
  const percentage = max > 0 ? Math.min((current / max) * 100, 100) : 0;

  // Determine color based on percentage or Admin status
  let colorClass = 'from-brand-500 to-brand-600';
  let textColorClass = percentage < 20 ? 'text-red-600 dark:text-red-400' : 'text-brand-600 dark:text-brand-400';
  let shadowClass = 'shadow-brand-500/20';
  let shimmerColorClass = 'via-brand-300/50';

  if (isAdmin) {
    colorClass = 'from-purple-500 to-purple-600';
    textColorClass = 'text-purple-600 dark:text-purple-400';
    shadowClass = 'shadow-purple-500/20';
    shimmerColorClass = 'via-purple-300/50';
  } else if (percentage < 20) {
    colorClass = 'from-red-500 to-red-600';
    textColorClass = 'text-red-600 dark:text-red-400';
    shadowClass = 'shadow-red-500/20';
    shimmerColorClass = 'via-red-300/50';
  } else if (percentage < 40) {
    colorClass = 'from-orange-500 to-orange-600';
    textColorClass = 'text-orange-600 dark:text-orange-400';
    shadowClass = 'shadow-orange-500/20';
    shimmerColorClass = 'via-orange-300/50';
  } else if (percentage < 60) {
    colorClass = 'from-yellow-500 to-yellow-600';
    textColorClass = 'text-yellow-600 dark:text-yellow-400';
    shadowClass = 'shadow-yellow-500/20';
    shimmerColorClass = 'via-yellow-300/50';
  }

  return (
    <div className={`relative ${className}`}>
      {showLabel && (
        <div className="absolute top-0 right-0 -mt-6">
          <span className={`text-xs font-bold ${textColorClass}`}>
            {percentage.toFixed(0)}%
          </span>
        </div>
      )}
      {/* Background bar */}
      <div className="h-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        {/* Progress bar with animated gradient */}
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out shadow-lg ${shadowClass} bg-gradient-to-r ${colorClass} animate-gradient bg-[length:300%_300%] relative overflow-hidden`}
          style={{ width: `${percentage}%` }}
        >
          {/* Shimmer effect with dynamic color - more visible */}
          <div className={`absolute inset-0 bg-gradient-to-r from-transparent ${shimmerColorClass} to-transparent animate-shimmer-slide`} />
        </div>
      </div>
    </div>
  );
}
