'use client';

import { useState, useEffect, FormEvent } from 'react';
import { User, Mail, Lock, Eye, EyeOff, Save, Shield } from 'lucide-react';
import DashboardLayout from '@/components/DashboardLayout';
import { Button, Input } from '@/components/ui';
import Toast from '@/components/Toast';
import api from '@/lib/api';
import { authService } from '@/lib/auth';

export default function ProfilePage() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Profile form
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [profileLoading, setProfileLoading] = useState(false);

  // Password form
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);

  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const res = await api.get('/auth/me');
      setUser(res.data);
      setUsername(res.data.username || '');
      setEmail(res.data.email || '');
    } catch {
      setToast({ message: 'Erro ao carregar perfil', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleProfileUpdate = async (e: FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !email.trim()) {
      setToast({ message: 'Preencha todos os campos', type: 'error' });
      return;
    }

    setProfileLoading(true);
    try {
      const res = await api.put('/auth/me', { username: username.trim(), email: email.trim() });
      setUser(res.data);
      authService.setUser(res.data);
      setToast({ message: 'Perfil atualizado com sucesso!', type: 'success' });
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Erro ao atualizar perfil';
      setToast({ message: msg, type: 'error' });
    } finally {
      setProfileLoading(false);
    }
  };

  const handlePasswordChange = async (e: FormEvent) => {
    e.preventDefault();
    if (!currentPassword || !newPassword || !confirmPassword) {
      setToast({ message: 'Preencha todos os campos de senha', type: 'error' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setToast({ message: 'As senhas não coincidem', type: 'error' });
      return;
    }
    if (newPassword.length < 8) {
      setToast({ message: 'Nova senha deve ter no mínimo 8 caracteres', type: 'error' });
      return;
    }

    setPasswordLoading(true);
    try {
      await api.put('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setToast({ message: 'Senha alterada com sucesso!', type: 'success' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      let msg = 'Erro ao alterar senha';
      if (typeof detail === 'string') {
        msg = detail;
      } else if (Array.isArray(detail)) {
        msg = detail[0]?.msg || msg;
      }
      setToast({ message: msg, type: 'error' });
    } finally {
      setPasswordLoading(false);
    }
  };

  const userInitials = user
    ? (user.username || user.email || 'U').substring(0, 2).toUpperCase()
    : 'U';

  const profileSkeleton = (
    <div className="flex-1 overflow-auto p-6 space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
      <div className="card p-6 space-y-4">
        <div className="h-20 w-20 rounded-full bg-gray-200 dark:bg-gray-700 mx-auto" />
        <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded" />
        <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded" />
      </div>
    </div>
  );

  return (
    <DashboardLayout>
      {loading ? profileSkeleton : (
        <div className="flex-1 overflow-auto p-6 space-y-6">
          <div className="animate-fade-in">
            <h1 className="text-2xl font-extrabold text-gray-900 dark:text-white tracking-tight">Meu Perfil</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Gerencie suas informações pessoais e segurança</p>
          </div>

          {/* Profile Info */}
          <div className="card overflow-hidden animate-slide-up" style={{ animationDelay: '0.1s', animationFillMode: 'both' }}>
            <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-800 flex items-center gap-3">
              <User className="w-5 h-5 text-brand-500" />
              <h2 className="text-base font-bold text-gray-900 dark:text-white">Informações Pessoais</h2>
            </div>
            <form onSubmit={handleProfileUpdate} className="p-6 space-y-5">
              {/* Avatar */}
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white flex items-center justify-center text-xl font-extrabold shadow-lg shadow-brand-500/20">
                  {userInitials}
                </div>
                <div>
                  <p className="text-sm font-bold text-gray-900 dark:text-white">{user?.username}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{user?.email}</p>
                </div>
              </div>

              <Input
                label="Nome de Usuário"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Seu nome de usuário"
                icon={<User className="w-[18px] h-[18px]" />}
              />

              <Input
                label="E-mail"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com"
                icon={<Mail className="w-[18px] h-[18px]" />}
              />

              <div className="flex justify-end">
                <Button type="submit" loading={profileLoading} className="!w-auto !px-6 !py-2.5 !rounded-xl !text-sm !font-semibold">
                  <Save className="w-4 h-4 mr-2" />
                  Salvar Alterações
                </Button>
              </div>
            </form>
          </div>

          {/* Change Password */}
          <div className="card overflow-hidden animate-slide-up" style={{ animationDelay: '0.2s', animationFillMode: 'both' }}>
            <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-800 flex items-center gap-3">
              <Shield className="w-5 h-5 text-brand-500" />
              <h2 className="text-base font-bold text-gray-900 dark:text-white">Alterar Senha</h2>
            </div>
            <form onSubmit={handlePasswordChange} className="p-6 space-y-5">
              <Input
                label="Senha Atual"
                type={showCurrentPassword ? 'text' : 'password'}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Digite sua senha atual"
                icon={<Lock className="w-[18px] h-[18px]" />}
                rightIcon={
                  <button type="button" onClick={() => setShowCurrentPassword(!showCurrentPassword)} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors" tabIndex={-1}>
                    {showCurrentPassword ? <EyeOff className="w-[18px] h-[18px]" /> : <Eye className="w-[18px] h-[18px]" />}
                  </button>
                }
              />

              <Input
                label="Nova Senha"
                type={showNewPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Mínimo 8 caracteres"
                icon={<Lock className="w-[18px] h-[18px]" />}
                rightIcon={
                  <button type="button" onClick={() => setShowNewPassword(!showNewPassword)} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors" tabIndex={-1}>
                    {showNewPassword ? <EyeOff className="w-[18px] h-[18px]" /> : <Eye className="w-[18px] h-[18px]" />}
                  </button>
                }
              />

              <Input
                label="Confirmar Nova Senha"
                type={showNewPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repita a nova senha"
                icon={<Lock className="w-[18px] h-[18px]" />}
              />

              <div className="flex justify-end">
                <Button type="submit" loading={passwordLoading} className="!w-auto !px-6 !py-2.5 !rounded-xl !text-sm !font-semibold">
                  <Shield className="w-4 h-4 mr-2" />
                  Alterar Senha
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </DashboardLayout>
  );
}
