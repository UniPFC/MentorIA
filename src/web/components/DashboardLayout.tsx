'use client';

import { useState, useEffect, ReactNode } from 'react';
import Link from 'next/link';
import { AlertCircle } from 'lucide-react';
import ProtectedRoute from '@/components/ProtectedRoute';
import Sidebar from '@/components/Sidebar';
import { authService } from '@/lib/auth';
import api from '@/lib/api';

interface DashboardLayoutProps {
  children: ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const fetchUser = async () => {
      // Carrega do cache local primeiro para uma renderização rápida
      const cached = authService.getUser();
      if (cached) setUser(cached);

      // Busca dados atualizados da API em background
      try {
        const res = await api.get('/auth/me');
        authService.setUser(res.data);
        setUser(res.data);
      } catch (err) {
        console.error('Failed to update user profile in layout', err);
      }
    };

    fetchUser();
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
          {user && user.email_verified === false && (
            <div className="bg-amber-100 dark:bg-amber-900/30 border-b border-amber-200 dark:border-amber-800/50 p-3 px-6 flex items-center justify-between text-sm flex-shrink-0 z-10">
              <div className="flex items-center gap-2 text-amber-800 dark:text-amber-200">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <p>
                  <span className="font-semibold">Seu email não está verificado.</span> Para usar recursos como Chat e Upload de Planilhas, você precisa verificar sua conta.
                </p>
              </div>
              <Link href="/dashboard/profile" className="text-amber-700 dark:text-amber-300 hover:text-amber-900 dark:hover:text-amber-100 font-semibold underline underline-offset-2 ml-4 flex-shrink-0">
                Verificar Agora
              </Link>
            </div>
          )}
          <div className="flex-1 flex flex-col overflow-hidden relative">
            {children}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
