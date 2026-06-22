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
    const token = authService.getToken();
    if (!token) {
      router.push('/login');
      return;
    }

    setIsAuthenticated(true);

    authService.verifyToken().then((isValid) => {
      if (!isValid) {
        setIsAuthenticated(false);
        router.push('/login');
        return;
      }

      setIsAuthenticated(true);
    });
  }, [router]);

  if (isAuthenticated === null) return null;
  if (!isAuthenticated) return null;

  return <>{children}</>;
}
