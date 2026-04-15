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

    // Render children immediately if token exists
    setIsAuthenticated(true);

    // Verify token validity in the background
    authService.verifyToken().then((isValid) => {
      if (!isValid) {
        setIsAuthenticated(false);
        router.push('/login');
      }
    });
  }, [router]);

  // Only block render if there's clearly no token
  if (isAuthenticated === null) return null;
  if (!isAuthenticated) return null;

  return <>{children}</>;
}
