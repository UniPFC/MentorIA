'use client';

import { ReactNode } from 'react';
import clsx from 'clsx';

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export default function Card({ children, className, hover, onClick }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        'bg-white rounded-2xl border border-gray-200/80 shadow-sm dark:bg-gray-900 dark:border-gray-800/80',
        hover && 'hover:shadow-lg hover:shadow-gray-200/50 hover:border-gray-300 hover:-translate-y-0.5 dark:hover:shadow-gray-900/50 dark:hover:border-gray-700 cursor-pointer transition-all duration-300',
        !hover && 'transition-all duration-300',
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={clsx('px-5 py-4 border-b border-gray-100 dark:border-gray-800', className)}>
      {children}
    </div>
  );
}

export function CardBody({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx('px-5 py-4', className)}>{children}</div>;
}
