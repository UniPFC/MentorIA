'use client';

import { ReactNode } from 'react';
import clsx from 'clsx';

interface PageTransitionProps {
  children: ReactNode;
  className?: string;
}

export default function PageTransition({ children, className }: PageTransitionProps) {
  return (
    <div className={clsx('animate-slide-up', className)}>
      {children}
    </div>
  );
}
