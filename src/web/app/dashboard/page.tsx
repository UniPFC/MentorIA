'use client';

import { useState, useEffect } from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import Sidebar from '@/components/Sidebar';
import DashboardContent from '@/components/DashboardContent';
import { authService } from '@/lib/auth';

export default function DashboardPage() {
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
        <div className="flex-1 flex flex-col md:ml-64 ml-0">
          <DashboardContent />
        </div>
      </div>
    </ProtectedRoute>
  );
}
