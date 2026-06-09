'use client';

import { useState, useEffect } from 'react';
import { Shield, Database, HardDrive, RefreshCw, Trash2, AlertCircle, CheckCircle, Mail, Lock, Eye, EyeOff } from 'lucide-react';
import { authService } from '@/lib/auth';
import Toast from '@/components/Toast';
import ThemeToggle from '@/components/ThemeToggle';
import { Button, Input } from '@/components/ui';

interface BackupFile {
  name: string;
  size: number;
  created: string;
}

interface BackupListResponse {
  date_folders: string[];
  current_backups: Record<string, BackupFile[]>;
}

interface BackupResponse {
  success: boolean;
  message: string;
  files?: string[];
}

export default function AdminPage({ params }: { params: { slug: string } }) {
  const [slugVerified, setSlugVerified] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [backups, setBackups] = useState<BackupListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [isRestoring, setIsRestoring] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  
  // Login form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loginLoading, setLoginLoading] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const adminSlug = params.slug;

  useEffect(() => {
    // Verify admin slug
    verifySlug();
  }, [adminSlug]);

  const verifySlug = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/admin/${adminSlug}/verify`);
      setSlugVerified(true);
      if (response.ok) {
        // Check if user is already logged in
        const user = authService.getUser();
        if (user) {
          setIsLoggedIn(true);
          loadBackups();
        }
      } else {
        setError("You're not authorized to access this page");
      }
    } catch (e) {
      setSlugVerified(true);
      setError('Failed to verify admin slug');
    }
  };

  const loadBackups = async () => {
    try {
      const token = authService.getToken();
      const response = await fetch(`${API_BASE}/api/v1/admin/${adminSlug}/backups`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setBackups(data);
      } else if (response.status === 401) {
        setIsLoggedIn(false);
      }
    } catch (e) {
      setError('Failed to load backups');
    }
  };

  const handleLogin = async (e: any) => {
    e.preventDefault();
    if (!email || !password) return;
    if (password.length < 8) {
      setError('Senha deve ter no mínimo 8 caracteres');
      return;
    }

    setLoginLoading(true);
    setError(null);
    try {
      await authService.login(email, password, false);
      setIsLoggedIn(true);
      setSuccess('Login realizado com sucesso!');
      loadBackups();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao fazer login');
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    authService.logout();
    setIsLoggedIn(false);
    setBackups(null);
    setSuccess(null);
  };

  const triggerBackup = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const token = authService.getToken();
      const response = await fetch(`${API_BASE}/api/v1/admin/${adminSlug}/backup`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      const data: BackupResponse = await response.json();

      if (response.ok) {
        setSuccess(data.message);
        loadBackups();
      } else {
        setError(data.message || 'Backup failed');
      }
    } catch (e) {
      setError('Failed to trigger backup');
    } finally {
      setLoading(false);
    }
  };

  const restoreBackup = async () => {
    if (!selectedDate) {
      setError('Please select a backup date');
      return;
    }

    setIsRestoring(true);
    setError(null);
    setSuccess(null);

    try {
      const token = authService.getToken();
      const response = await fetch(`${API_BASE}/api/v1/admin/${adminSlug}/restore`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ date_str: selectedDate }),
      });

      const data: BackupResponse = await response.json();

      if (response.ok) {
        setSuccess(data.message);
      } else {
        setError(data.message || 'Restore failed');
      }
    } catch (e) {
      setError('Failed to restore backup');
    } finally {
      setIsRestoring(false);
    }
  };

  const deleteBackup = async (dateStr: string) => {
    if (!confirm(`Are you sure you want to delete backup from ${dateStr}?`)) {
      return;
    }

    try {
      const token = authService.getToken();
      const response = await fetch(`${API_BASE}/api/v1/admin/${adminSlug}/backups/${dateStr}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      const data: BackupResponse = await response.json();

      if (response.ok) {
        setSuccess(data.message);
        loadBackups();
      } else {
        setError(data.message || 'Delete failed');
      }
    } catch (e) {
      setError('Failed to delete backup');
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateStr: string) => {
    if (dateStr.length === 8 && /^\d+$/.test(dateStr)) {
      const day = dateStr.substring(0, 2);
      const month = dateStr.substring(2, 4);
      const year = dateStr.substring(4, 8);
      return `${day}/${month}/${year}`;
    }
    return dateStr;
  };

  if (!slugVerified) {
    return (
      <div className="min-h-screen flex bg-gray-50 dark:bg-gray-950 items-center justify-center">
        <div className="text-center">
          <Shield className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <p className="text-gray-500">Verificando acesso...</p>
        </div>
      </div>
    );
  }

  if (!isLoggedIn) {
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
              <span className="text-lg font-bold tracking-tight">MentorIA Admin</span>
            </div>

            <div>
              <h2 className="text-4xl font-extrabold leading-tight mb-4">
                Painel de
                <br /><span className="text-white/90">Administração</span>
              </h2>
              <p className="text-base text-white/50 max-w-sm leading-relaxed">
                Gerencie backups e restore do sistema de forma segura.
              </p>

              <div className="mt-10 space-y-4">
                {[
                  { text: 'Criar backups manuais do sistema', delay: '' },
                  { text: 'Listar e gerenciar backups existentes', delay: 'animation-delay: 0.1s' },
                  { text: 'Restaurar backups quando necessário', delay: 'animation-delay: 0.2s' },
                ].map((item) => (
                  <div key={item.text} className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center shrink-0 backdrop-blur-sm">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                    </div>
                    <span className="text-sm text-white/60">{item.text}</span>
                  </div>
                ))}
              </div>
            </div>

            <p className="text-xs text-white/20 font-medium">&copy; 2026 MentorIA. Todos os direitos reservados.</p>
          </div>
        </div>

        {/* Right form panel */}
        <div className="flex-1 flex items-center justify-center relative">
          <div className="w-full max-w-[420px] mx-auto px-4">
            <div className="text-center mb-10 animate-fade-in">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 mb-5 lg:hidden shadow-lg shadow-brand-500/25">
                <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Acesso Administrativo</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Faça login para acessar o painel</p>
            </div>

            <form onSubmit={handleLogin} className="space-y-5">
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

              <div className="animate-slide-up-stagger-3 pt-1">
                <Button type="submit" loading={loginLoading} className="w-full !py-3 !rounded-xl !text-sm !font-bold">
                  {loginLoading ? 'Entrando...' : 'Entrar'}
                </Button>
              </div>
            </form>

            <div className="absolute top-4 right-4">
              <ThemeToggle />
            </div>

            {error && (
              <div className="mt-4 bg-red-500/10 border border-red-500 text-red-500 px-4 py-3 rounded-lg flex items-center gap-2">
                <AlertCircle className="w-5 h-5" />
                {error}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Header */}
      <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900 dark:text-white">MentorIA Admin</h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">Gerenciamento de Backups</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <ThemeToggle />
              <Button onClick={handleLogout} variant="secondary" className="!text-sm">
                Sair
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {error && (
          <div className="bg-red-500/10 border border-red-500 text-red-500 px-4 py-3 rounded mb-6 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-500/10 border border-green-500 text-green-500 px-4 py-3 rounded mb-6 flex items-center gap-2">
            <CheckCircle className="w-5 h-5" />
            {success}
          </div>
        )}

        {/* Action cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <button
            onClick={triggerBackup}
            disabled={loading}
            className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 p-6 rounded-xl shadow-sm hover:shadow-md transition-all flex flex-col items-center gap-3 group"
          >
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center group-hover:bg-blue-500/20 transition-colors">
              <Database className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <span className="font-semibold text-gray-900 dark:text-white">Criar Backup</span>
            {loading && <RefreshCw className="w-5 h-5 text-blue-600 dark:text-blue-400 animate-spin" />}
          </button>

          <button
            onClick={restoreBackup}
            disabled={isRestoring || !selectedDate}
            className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 p-6 rounded-xl shadow-sm hover:shadow-md transition-all flex flex-col items-center gap-3 group disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="w-12 h-12 rounded-xl bg-green-500/10 flex items-center justify-center group-hover:bg-green-500/20 transition-colors">
              <HardDrive className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <span className="font-semibold text-gray-900 dark:text-white">Restaurar Backup</span>
            {isRestoring && <RefreshCw className="w-5 h-5 text-green-600 dark:text-green-400 animate-spin" />}
          </button>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 p-6 rounded-xl shadow-sm flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gray-500/10 flex items-center justify-center">
              <RefreshCw className="w-6 h-6 text-gray-600 dark:text-gray-400" />
            </div>
            <span className="font-semibold text-gray-900 dark:text-white">Backups: {backups?.date_folders.length || 0}</span>
          </div>
        </div>

        {/* Backups list */}
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm overflow-hidden">
          <div className="p-6 border-b border-gray-200 dark:border-gray-800">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Backups Disponíveis</h2>
          </div>

          {backups && backups.date_folders.length > 0 ? (
            <div className="divide-y divide-gray-200 dark:divide-gray-800">
              {backups.date_folders.map((dateFolder) => (
                <div
                  key={dateFolder}
                  className={`p-6 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-all cursor-pointer ${
                    selectedDate === dateFolder ? 'bg-blue-50 dark:bg-blue-900/10 border-l-4 border-blue-500' : ''
                  }`}
                  onClick={() => setSelectedDate(dateFolder)}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <Database className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                      <span className="text-lg font-semibold text-gray-900 dark:text-white">{formatDate(dateFolder)}</span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteBackup(dateFolder);
                      }}
                      className="text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 transition-colors p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/10"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>

                  {backups.current_backups[dateFolder] && (
                    <div className="ml-8 space-y-2">
                      {backups.current_backups[dateFolder].map((file) => (
                        <div key={file.name} className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
                          <span className="font-mono text-xs">{file.name}</span>
                          <span>{formatFileSize(file.size)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="p-12 text-center text-gray-500 dark:text-gray-400">
              <Database className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>Nenhum backup disponível</p>
            </div>
          )}
        </div>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
