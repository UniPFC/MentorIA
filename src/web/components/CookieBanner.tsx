'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

export default function CookieBanner() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Verificar se o usuário já aceitou os cookies
    const consent = localStorage.getItem('cookie_consent');
    if (!consent) {
      setIsVisible(true);
    }
  }, []);

  const acceptCookies = () => {
    localStorage.setItem('cookie_consent', 'true');
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 md:p-6 pointer-events-none">
      <div className="max-w-4xl mx-auto pointer-events-auto">
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-2xl rounded-2xl p-5 md:p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 animate-slide-up">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">🍪</span>
              <h3 className="text-base font-bold text-gray-900 dark:text-white">Nós usamos cookies</h3>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
              Utilizamos apenas cookies essenciais para manter sua sessão segura e permitir o funcionamento do sistema. Não usamos cookies de rastreamento ou marketing. 
              Ao continuar navegando, você concorda com a nossa{' '}
              <Link href="/legal/privacy.md" className="text-brand-600 dark:text-brand-400 font-medium hover:underline">
                Política de Privacidade
              </Link>{' '}
              e nossos{' '}
              <Link href="/legal/terms.md" className="text-brand-600 dark:text-brand-400 font-medium hover:underline">
                Termos de Uso
              </Link>.
            </p>
          </div>
          <div className="flex shrink-0 gap-3 w-full md:w-auto">
            <button
              onClick={acceptCookies}
              className="flex-1 md:flex-none px-6 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold rounded-xl transition-colors active:scale-95 shadow-md shadow-brand-500/20"
            >
              Aceitar e Continuar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
