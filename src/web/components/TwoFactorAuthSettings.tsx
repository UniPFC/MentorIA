'use client';

import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Shield, ShieldAlert, ShieldCheck, X } from 'lucide-react';
import { Button, Input } from '@/components/ui';
import Toast from '@/components/Toast';
import { authService, User } from '@/lib/auth';

interface TwoFactorAuthSettingsProps {
  user: User;
  onUserUpdate: (updatedUser: User) => void;
}

export default function TwoFactorAuthSettings({ user, onUserUpdate }: TwoFactorAuthSettingsProps) {
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  // Setup state
  const [showSetup, setShowSetup] = useState(false);
  const [qrCode, setQrCode] = useState('');
  const [secret, setSecret] = useState('');
  const [code, setCode] = useState('');

  // Disable state
  const [showDisable, setShowDisable] = useState(false);
  const [disableCode, setDisableCode] = useState('');

  const handleSetupClick = async () => {
    setLoading(true);
    try {
      const res = await authService.setup2FA();
      setSecret(res.secret);
      setQrCode(res.qr_code_base64);
      setShowSetup(true);
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || 'Erro ao preparar 2FA', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleEnableSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length !== 6) {
      setToast({ message: 'O código deve ter 6 dígitos', type: 'error' });
      return;
    }

    setLoading(true);
    try {
      await authService.enable2FA(secret, code);
      setToast({ message: '2FA ativado com sucesso!', type: 'success' });
      const updatedUser = { ...user, two_factor_enabled: true };
      authService.setUser(updatedUser);
      onUserUpdate(updatedUser);
      setShowSetup(false);
      setCode('');
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || 'Código inválido', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleDisableSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (disableCode.length !== 6) {
      setToast({ message: 'O código deve ter 6 dígitos', type: 'error' });
      return;
    }

    setLoading(true);
    try {
      await authService.disable2FA(disableCode);
      setToast({ message: '2FA desativado com sucesso.', type: 'success' });
      const updatedUser = { ...user, two_factor_enabled: false };
      authService.setUser(updatedUser);
      onUserUpdate(updatedUser);
      setShowDisable(false);
      setDisableCode('');
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || 'Código inválido', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card overflow-hidden animate-slide-up" style={{ animationDelay: '0.22s', animationFillMode: 'both' }}>
      <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-800 flex items-center gap-3">
        <Shield className="w-5 h-5 text-brand-500" />
        <h2 className="text-base font-bold text-gray-900 dark:text-white">Autenticação em Duas Etapas (2FA)</h2>
      </div>
      
      <div className="p-6">
        {user?.two_factor_enabled ? (
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800/50">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-emerald-100 dark:bg-emerald-800/50 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-emerald-800 dark:text-emerald-300">2FA Ativado</h3>
                <p className="text-sm text-emerald-600 dark:text-emerald-400 mt-1">
                  Sua conta possui uma camada extra de segurança no login.
                </p>
              </div>
            </div>
            <Button 
              variant="secondary" 
              onClick={() => setShowDisable(true)}
              className="shrink-0 text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/30 border-red-200 dark:border-red-900/30"
            >
              Desativar 2FA
            </Button>
          </div>
        ) : (
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-800/50 flex items-center justify-center text-amber-600 dark:text-amber-400 shrink-0">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-amber-800 dark:text-amber-300">2FA Desativado</h3>
                <p className="text-sm text-amber-600 dark:text-amber-400 mt-1">
                  Proteja sua conta exigindo um código no momento do login.
                </p>
              </div>
            </div>
            <Button 
              onClick={handleSetupClick} 
              loading={loading}
              className="shrink-0 bg-amber-500 hover:bg-amber-600 text-white border-transparent"
            >
              Ativar 2FA
            </Button>
          </div>
        )}
      </div>

      {/* Setup Modal */}
      {mounted && showSetup && createPortal(
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white dark:bg-gray-900 rounded-2xl max-w-md w-full shadow-2xl overflow-hidden flex flex-col animate-scale-in">
            <div className="p-4 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center">
              <h3 className="font-bold text-gray-900 dark:text-white">Configurar 2FA</h3>
              <button onClick={() => setShowSetup(false)} className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
                1. Escaneie este QR Code no aplicativo Google Authenticator ou Authy.
              </p>
              
              <div className="flex justify-center bg-white p-4 rounded-xl border border-gray-200 w-fit mx-auto">
                {qrCode && <img src={qrCode} alt="QR Code 2FA" className="w-48 h-48" />}
              </div>
              
              <p className="text-sm text-gray-600 dark:text-gray-400 text-center mt-4">
                2. Insira o código de 6 dígitos gerado pelo aplicativo para confirmar.
              </p>

              <form onSubmit={handleEnableSubmit} className="mt-4 flex flex-col gap-4">
                <Input
                  label="Código de Verificação"
                  placeholder="000000"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  required
                />
                <Button type="submit" loading={loading} className="w-full">
                  Verificar e Ativar
                </Button>
              </form>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Disable Modal */}
      {mounted && showDisable && createPortal(
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white dark:bg-gray-900 rounded-2xl max-w-md w-full shadow-2xl overflow-hidden flex flex-col animate-scale-in">
            <div className="p-4 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center">
              <h3 className="font-bold text-gray-900 dark:text-white">Desativar 2FA</h3>
              <button onClick={() => setShowDisable(false)} className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Para desativar a autenticação em duas etapas, insira o código atual do seu aplicativo.
              </p>

              <form onSubmit={handleDisableSubmit} className="mt-4 flex flex-col gap-4">
                <Input
                  label="Código 2FA"
                  placeholder="000000"
                  value={disableCode}
                  onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  required
                />
                <Button type="submit" variant="danger" loading={loading} className="w-full">
                  Desativar 2FA
                </Button>
              </form>
            </div>
          </div>
        </div>,
        document.body
      )}

      {mounted && toast && createPortal(
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />,
        document.body
      )}
    </div>
  );
}
