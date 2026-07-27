'use client';

import { useState, useEffect, ReactNode } from 'react';
import Link from 'next/link';
import { AlertCircle, ShieldAlert, X } from 'lucide-react';
import ProtectedRoute from '@/components/ProtectedRoute';
import Sidebar from '@/components/Sidebar';
import { authService } from '@/lib/auth';
import api from '@/lib/api';

interface DashboardLayoutProps {
  children: ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [user, setUser] = useState<any>(null);
  const [show2FAReminder, setShow2FAReminder] = useState(false);

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

  useEffect(() => {
    if (user && user.two_factor_enabled === false) {
      if (!user.last_2fa_reminder_at) {
        setShow2FAReminder(true);
      } else {
        const lastReminder = new Date(user.last_2fa_reminder_at);
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        if (lastReminder < thirtyDaysAgo) {
          setShow2FAReminder(true);
        }
      }
    } else {
      setShow2FAReminder(false);
    }
  }, [user]);

  const handleDismiss2FA = async () => {
    setShow2FAReminder(false);
    try {
      await authService.dismiss2FAReminder();
      if (user) {
        const updated = { ...user, last_2fa_reminder_at: new Date().toISOString() };
        authService.setUser(updated);
        setUser(updated);
      }
    } catch (e) {
      console.error(e);
    }
  };

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
          
          {/* Email Verification Banner */}
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

          {/* 2FA Reminder Banner */}
          {show2FAReminder && user?.email_verified !== false && (
            <div className="bg-blue-50 dark:bg-blue-900/20 border-b border-blue-100 dark:border-blue-900/40 p-3 px-6 flex items-center justify-between text-sm flex-shrink-0 z-10 animate-fade-in">
              <div className="flex items-center gap-3 text-blue-800 dark:text-blue-300">
                <ShieldAlert className="w-5 h-5 flex-shrink-0 text-blue-500" />
                <p>
                  <span className="font-semibold">Proteja sua conta.</span> A autenticação em duas etapas (2FA) não está ativa. Recomendamos ativá-la para maior segurança.
                </p>
              </div>
              <div className="flex items-center gap-4 ml-4 shrink-0">
                <Link href="/dashboard/profile" className="text-blue-700 dark:text-blue-400 hover:text-blue-900 dark:hover:text-blue-200 font-semibold underline underline-offset-2">
                  Ativar 2FA
                </Link>
                <button 
                  onClick={handleDismiss2FA} 
                  className="p-1 text-blue-400 hover:text-blue-600 dark:hover:text-blue-200 rounded-full hover:bg-blue-100 dark:hover:bg-blue-800/50 transition-colors"
                  title="Lembrar mais tarde"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
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
