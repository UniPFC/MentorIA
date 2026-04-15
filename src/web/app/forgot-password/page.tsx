'use client';

import { useState, FormEvent } from 'react';
import Link from 'next/link';
import { Mail, ArrowLeft, CheckCircle } from 'lucide-react';
import { Button, Input } from '@/components/ui';
import Toast from '@/components/Toast';
import ThemeToggle from '@/components/ThemeToggle';
import api from '@/lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setLoading(true);
    try {
      await api.post('/auth/forgot-password', { email });
      setSent(true);
    } catch (err: any) {
      setToast({
        message: err.response?.data?.detail || 'Erro ao enviar e-mail de recuperação',
        type: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-gray-50 dark:bg-gray-950">
      {/* Left brand panel */}
      <div className="hidden lg:flex lg:w-[45%] relative overflow-hidden bg-gradient-to-br from-brand-600 via-brand-700 to-brand-900">
        <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
        <div className="absolute -top-24 -left-24 w-96 h-96 rounded-full bg-white/5 animate-pulse-soft" />
        <div className="absolute -bottom-32 -right-32 w-[500px] h-[500px] rounded-full bg-white/5 animate-pulse-soft" style={{ animationDelay: '1s' }} />

        <div className="relative z-10 flex flex-col justify-between p-12 text-white w-full">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <span className="text-lg font-bold">MentorIA</span>
          </div>

          <div>
            <h2 className="text-3xl font-bold leading-tight mb-3">
              Recupere sua
              <br />conta com segurança
            </h2>
            <p className="text-base text-white/60 max-w-sm leading-relaxed">
              Enviaremos um link seguro para o seu e-mail para redefinir sua senha.
            </p>
          </div>

          <p className="text-xs text-white/30">&copy; 2026 MentorIA. Todos os direitos reservados.</p>
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center relative">
        <div className="absolute top-4 right-4">
          <ThemeToggle />
        </div>

        <div className="w-full max-w-[440px] mx-auto px-4">
          {sent ? (
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-emerald-50 dark:bg-emerald-500/10 mb-6">
                <CheckCircle className="w-8 h-8 text-emerald-600 dark:text-emerald-400" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Verifique seu e-mail</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">
                Enviamos um link de recuperação para <strong className="text-gray-700 dark:text-gray-300">{email}</strong>.
                Verifique sua caixa de entrada e spam.
              </p>
              <Link href="/login">
                <Button variant="secondary" className="w-full">
                  <ArrowLeft className="w-4 h-4" />
                  Voltar ao login
                </Button>
              </Link>
            </div>
          ) : (
            <>
              <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 mb-4 lg:hidden shadow-lg shadow-brand-500/25">
                  <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                </div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Esqueceu sua senha?</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Insira seu e-mail e enviaremos instruções para redefinir sua senha
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
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

                <Button type="submit" loading={loading} className="w-full !py-3 !rounded-xl !text-sm !font-semibold">
                  {loading ? 'Enviando...' : 'Enviar link de recuperação'}
                </Button>
              </form>

              <p className="text-center mt-6 text-sm text-gray-500 dark:text-gray-400">
                Lembrou a senha?{' '}
                <Link href="/login" className="text-brand-600 dark:text-brand-400 font-medium hover:underline">
                  Voltar ao login
                </Link>
              </p>
            </>
          )}
        </div>

        {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      </div>
    </div>
  );
}
