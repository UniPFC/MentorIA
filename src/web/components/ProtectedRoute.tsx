'use client';

import { ReactNode, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authService } from '@/lib/auth';

interface ProtectedRouteProps {
  children: ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const router = useRouter();

  useEffect(() => {
    // Com HttpOnly cookies, não temos mais acesso ao token no Javascript.
    // Pulamos a verificação síncrona do token e vamos direto para a validação no backend.

    // Mantém isAuthenticated como null (tela de loading/branca) até a resposta do servidor
    authService.verifyToken().then((isValid) => {
      if (!isValid) {
        setIsAuthenticated(false);
        router.push('/login');
        return;
      }

      setIsAuthenticated(true);
    });
  }, [router]);

  if (isAuthenticated === null) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent dark:border-indigo-400 dark:border-t-transparent"></div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Autenticando...</p>
        </div>
      </div>
    );
  }
  if (!isAuthenticated) return null;

  return <>{children}</>;
}
