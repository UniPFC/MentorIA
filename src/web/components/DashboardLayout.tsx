'use client';

import { useState, useEffect, ReactNode } from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import Sidebar from '@/components/Sidebar';
import { authService } from '@/lib/auth';

interface DashboardLayoutProps {
  children: ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const userData = authService.getUser();
    if (userData) setUser(userData);
  }, []);

  const userInitials = user
    ? (user.username || user.email || 'U').substring(0, 2).toUpperCase()
    : 'U';

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-950 overflow-hidden">
        <Sidebar
          userName={user?.username || user?.name || 'Usuário'}
          userEmail={user?.email || ''}
          userInitials={userInitials}
        />
        <div className="flex-1 flex flex-col md:ml-[270px] ml-0 min-h-0">
          {children}
        </div>
      </div>
    </ProtectedRoute>
  );
}
