'use client';

import { useState, FormEvent, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { AlertTriangle, CheckCircle, AlertCircle } from 'lucide-react';
import api from '@/lib/api';
import { authService } from '@/lib/auth';
import { Button, Input } from '@/components/ui';

function DeleteAccountForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const router = useRouter();
  
  const [confirmWord, setConfirmWord] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!token) {
      setStatus('error');
      setMessage('Token de exclusão não encontrado.');
      return;
    }
    
    if (confirmWord !== 'DELETAR') {
      setStatus('error');
      setMessage('Você deve digitar DELETAR em maiúsculo para confirmar.');
      return;
    }

    setLoading(true);
    setStatus('idle');
    try {
      await api.delete('/auth/me', { data: { token } });
      localStorage.removeItem('user');
      setStatus('success');
      setMessage('Sua conta foi excluída permanentemente.');
    } catch (error: any) {
      setStatus('error');
      setMessage(error.response?.data?.detail || 'Erro ao excluir conta. O token pode estar inválido ou expirado.');
    } finally {
      setLoading(false);
    }
  };

  if (status === 'success') {
    return (
      <div className="text-center animate-fade-in">
        <div className="mb-6 flex justify-center">
          <div className="w-16 h-16 rounded-full bg-red-50 dark:bg-red-500/10 flex items-center justify-center">
            <CheckCircle className="w-8 h-8 text-red-500" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Conta Excluída</h1>
        <p className="text-gray-500 dark:text-gray-400 mb-8">{message}</p>
        <Link href="/login" className="block w-full">
          <Button className="w-full">Voltar para o Login</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8 text-center">
        <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-500/20 flex items-center justify-center mx-auto mb-4">
          <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Exclusão de Conta</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Esta ação é irreversível. Todos os seus dados serão apagados permanentemente.
        </p>
      </div>

      {status === 'error' && (
        <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
          <p className="text-sm font-medium text-red-700 dark:text-red-400">{message}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 mb-4 text-sm text-gray-600 dark:text-gray-400 text-center">
          Para confirmar a exclusão, digite a palavra <strong>DELETAR</strong> no campo abaixo.
        </div>

        <Input
          label="Confirmação"
          type="text"
          value={confirmWord}
          onChange={(e) => setConfirmWord(e.target.value)}
          required
          placeholder="Digite DELETAR"
          className="text-center uppercase"
        />

        <Button 
          type="submit" 
          className="w-full mt-6 bg-red-500 hover:bg-red-600 text-white border-none disabled:opacity-50 disabled:cursor-not-allowed" 
          loading={loading}
          disabled={confirmWord !== 'DELETAR'}
        >
          Excluir Definitivamente
        </Button>
      </form>
    </div>
  );
}

export default function DeleteAccountPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-xl p-8 border border-red-100 dark:border-red-900/30">
        <Suspense fallback={
          <div className="flex justify-center p-8">
             <div className="w-8 h-8 rounded-full border-2 border-red-500 border-t-transparent animate-spin" />
          </div>
        }>
          <DeleteAccountForm />
        </Suspense>
      </div>
    </div>
  );
}
