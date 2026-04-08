'use client';

import { useState, FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Mail, Lock, Eye, EyeOff } from 'lucide-react';
import { Button, Input } from './ui';
import Toast from './Toast';
import ThemeToggle from './ThemeToggle';
import { authService } from '@/lib/auth';

export default function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const router = useRouter();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!email || !password) return;
    if (password.length < 8) {
      setToast({ message: 'Senha deve ter no mínimo 8 caracteres', type: 'error' });
      return;
    }

    setLoading(true);
    try {
      await authService.login(email, password, rememberMe);
      setToast({ message: 'Login realizado com sucesso!', type: 'success' });
      router.push('/dashboard');
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || 'Erro ao fazer login', type: 'error' });
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-[420px] mx-auto px-4">
      {/* Header */}
      <div className="text-center mb-10 animate-fade-in">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 mb-5 lg:hidden shadow-lg shadow-brand-500/25">
          <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Bem-vindo de volta</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Entre na sua conta para continuar</p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="animate-slide-up-stagger-1">
          <Input
            label="E-mail"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="seu@email.com"
            required
            autoComplete="email"
            icon={<Mail className="w-[18px] h-[18px]" />}
          />
        </div>

        <div className="animate-slide-up-stagger-2">
          <Input
            label="Senha"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Mínimo 8 caracteres"
            required
            autoComplete="current-password"
            icon={<Lock className="w-[18px] h-[18px]" />}
            rightIcon={
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-[18px] h-[18px]" /> : <Eye className="w-[18px] h-[18px]" />}
              </button>
            }
          />
        </div>

        <div className="flex items-center justify-between text-sm animate-slide-up-stagger-3">
          <label className="flex items-center gap-2.5 cursor-pointer select-none group">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="w-4 h-4 rounded-md border-gray-300 text-brand-600 focus:ring-brand-500 focus:ring-offset-0 dark:border-gray-600 dark:bg-gray-800 transition-colors"
            />
            <span className="text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-200 transition-colors">Lembrar-me</span>
          </label>
          <Link href="/forgot-password" className="text-brand-600 dark:text-brand-400 font-medium hover:text-brand-700 dark:hover:text-brand-300 transition-colors text-sm">
            Esqueci minha senha
          </Link>
        </div>

        <div className="animate-slide-up-stagger-4 pt-1">
          <Button type="submit" loading={loading} className="w-full !py-3 !rounded-xl !text-sm !font-bold">
            {loading ? 'Entrando...' : 'Entrar'}
          </Button>
        </div>
      </form>

      <p className="text-center mt-8 text-sm text-gray-500 dark:text-gray-400 animate-slide-up-stagger-5">
        Não tem uma conta?{' '}
        <Link href="/register" className="text-brand-600 dark:text-brand-400 font-semibold hover:text-brand-700 dark:hover:text-brand-300 transition-colors">
          Cadastre-se gratuitamente
        </Link>
      </p>

      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
