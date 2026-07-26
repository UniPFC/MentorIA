'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import api from '@/lib/api';
import { Button } from '@/components/ui';

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const router = useRouter();
  
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Verificando seu email...');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('Token de verificação não encontrado na URL.');
      return;
    }

    const verifyToken = async () => {
      try {
        await api.post('/auth/verify-email', { token });
        setStatus('success');
        setMessage('Email verificado com sucesso!');
      } catch (error: any) {
        setStatus('error');
        setMessage(error.response?.data?.detail || 'Ocorreu um erro ao verificar seu email. O token pode estar inválido ou expirado.');
      }
    };

    verifyToken();
  }, [token]);

  return (
    <div className="text-center animate-fade-in">
      <div className="mb-6 flex justify-center">
        {status === 'loading' && (
          <div className="w-16 h-16 rounded-full bg-brand-50 dark:bg-brand-500/10 flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
          </div>
        )}
        {status === 'success' && (
          <div className="w-16 h-16 rounded-full bg-emerald-50 dark:bg-emerald-500/10 flex items-center justify-center">
            <CheckCircle className="w-8 h-8 text-emerald-500" />
          </div>
        )}
        {status === 'error' && (
          <div className="w-16 h-16 rounded-full bg-red-50 dark:bg-red-500/10 flex items-center justify-center">
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>
        )}
      </div>
      
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
        {status === 'loading' ? 'Verificando...' : status === 'success' ? 'Email Verificado!' : 'Falha na Verificação'}
      </h1>
      
      <p className="text-gray-500 dark:text-gray-400 mb-8">
        {message}
      </p>

      <div className="space-y-3">
        <Link href="/dashboard" className="block w-full">
          <Button className="w-full" variant={status === 'success' ? 'primary' : 'secondary'}>
            Ir para o Dashboard
          </Button>
        </Link>
        <Link href="/login" className="block w-full text-sm font-medium text-brand-600 dark:text-brand-400 hover:text-brand-500 mt-4">
          Fazer Login
        </Link>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-xl p-8 border border-gray-100 dark:border-gray-800">
        <Suspense fallback={
          <div className="flex justify-center p-8">
             <div className="w-8 h-8 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
          </div>
        }>
          <VerifyEmailContent />
        </Suspense>
      </div>
    </div>
  );
}
