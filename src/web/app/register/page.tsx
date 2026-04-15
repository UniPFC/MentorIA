'use client';

import { useState, FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { User, Mail, Lock, Eye, EyeOff } from 'lucide-react';
import { Button, Input } from '@/components/ui';
import Toast from '@/components/Toast';
import ThemeToggle from '@/components/ThemeToggle';
import { authService } from '@/lib/auth';

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const router = useRouter();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const getRegisterErrorMessage = (err: any): string => {
    const apiError = err?.response?.data;
    const fieldErrors = apiError?.errors;

    if (Array.isArray(fieldErrors) && fieldErrors.length > 0) {
      return fieldErrors[0]?.message || 'Erro de validação no cadastro';
    }

    return apiError?.detail || 'Erro ao fazer cadastro';
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!formData.email || !formData.password || !formData.confirmPassword) {
      setToast({ message: 'Preencha todos os campos', type: 'error' });
      return;
    }
    if (formData.username.trim().length > 0 && formData.username.trim().length < 3) {
      setToast({ message: 'Nome de usuário deve ter no mínimo 3 caracteres', type: 'error' });
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setToast({ message: 'As senhas não coincidem', type: 'error' });
      return;
    }
    if (formData.password.length < 8) {
      setToast({ message: 'Senha deve ter no mínimo 8 caracteres', type: 'error' });
      return;
    }

    setLoading(true);
    try {
      await authService.register(formData.email, formData.password, formData.username.trim());
      setToast({ message: 'Cadastro realizado com sucesso!', type: 'success' });
      setTimeout(() => router.push('/dashboard'), 1500);
    } catch (err: any) {
      setToast({ message: getRegisterErrorMessage(err), type: 'error' });
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
        <div className="absolute top-[30%] right-[20%] w-48 h-48 rounded-full bg-white/5 animate-float" />
        <div className="absolute bottom-[30%] left-[15%] w-24 h-24 rounded-full bg-white/[0.03] animate-float" style={{ animationDelay: '3s' }} />

        <div className="relative z-10 flex flex-col justify-between p-12 text-white w-full">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-white/15 backdrop-blur-sm flex items-center justify-center shadow-lg shadow-black/10">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <span className="text-lg font-bold tracking-tight">MentorIA</span>
          </div>

          <div>
            <h2 className="text-4xl font-extrabold leading-tight mb-4">
              Comece sua
              <br /><span className="text-white/90">jornada agora</span>
            </h2>
            <p className="text-base text-white/50 max-w-sm leading-relaxed">
              Crie sua conta gratuita e tenha acesso ao chat inteligente com tecnologia RAG.
            </p>

            <div className="mt-10 space-y-4">
              {['Cadastro rápido e gratuito', 'Envie seus materiais de estudo', 'Obtenha respostas inteligentes e contextuais'].map((item) => (
                <div key={item} className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center shrink-0 backdrop-blur-sm">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  </div>
                  <span className="text-sm text-white/60">{item}</span>
                </div>
              ))}
            </div>
          </div>

          <p className="text-xs text-white/20 font-medium">&copy; 2026 MentorIA. Todos os direitos reservados.</p>
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center relative">
        <div className="absolute top-4 right-4">
          <ThemeToggle />
        </div>

        <div className="w-full max-w-[420px] mx-auto px-4">
          {/* Header */}
          <div className="text-center mb-10 animate-fade-in">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 mb-5 lg:hidden shadow-lg shadow-brand-500/25">
              <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Crie sua conta</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Preencha seus dados para começar</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="animate-slide-up-stagger-1">
              <Input
                label="Nome de usuário"
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                placeholder="seu_usuario"
                autoComplete="username"
                icon={<User className="w-[18px] h-[18px]" />}
              />
            </div>

            <div className="animate-slide-up-stagger-2">
              <Input
                label="E-mail"
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="seu@email.com"
                required
                autoComplete="email"
                icon={<Mail className="w-[18px] h-[18px]" />}
              />
            </div>

            <div className="animate-slide-up-stagger-3">
              <Input
                label="Senha"
                type={showPassword ? 'text' : 'password'}
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Mínimo 8 caracteres"
                required
                autoComplete="new-password"
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

            <div className="animate-slide-up-stagger-4">
              <Input
                label="Confirmar Senha"
                type="password"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="Digite a senha novamente"
                required
                autoComplete="new-password"
                icon={<Lock className="w-[18px] h-[18px]" />}
              />
            </div>

            <div className="animate-slide-up-stagger-5 pt-1">
              <Button type="submit" loading={loading} className="w-full !py-3 !rounded-xl !text-sm !font-bold">
                {loading ? 'Cadastrando...' : 'Criar conta'}
              </Button>
            </div>
          </form>

          <p className="text-center mt-8 text-sm text-gray-500 dark:text-gray-400">
            Já tem uma conta?{' '}
            <Link href="/login" className="text-brand-600 dark:text-brand-400 font-semibold hover:text-brand-700 dark:hover:text-brand-300 transition-colors">
              Faça login
            </Link>
          </p>

          {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
        </div>
      </div>
    </div>
  );
}
