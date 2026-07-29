'use client';

import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Loader2 } from 'lucide-react';
import { authService } from '@/lib/auth';

interface TermsBlockerModalProps {
  isOpen: boolean;
  onAccepted: () => void;
}

export default function TermsBlockerModal({ isOpen, onAccepted }: TermsBlockerModalProps) {
  const [termsContent, setTermsContent] = useState('');
  const [privacyContent, setPrivacyContent] = useState('');
  const [activeTab, setActiveTab] = useState<'terms' | 'privacy'>('terms');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [accepting, setAccepting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      setError('');
      Promise.all([
        fetch('/legal/terms.md').then((res) => {
          if (!res.ok) throw new Error('Falha ao carregar os Termos');
          return res.text();
        }),
        fetch('/legal/privacy.md').then((res) => {
          if (!res.ok) throw new Error('Falha ao carregar a Privacidade');
          return res.text();
        })
      ])
        .then(([termsText, privacyText]) => {
          setTermsContent(termsText);
          setPrivacyContent(privacyText);
        })
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [isOpen]);

  const handleAccept = async () => {
    try {
      setAccepting(true);
      await authService.acceptTerms();
      onAccepted();
    } catch (err) {
      console.error(err);
      setError('Falha ao aceitar os termos. Tente novamente.');
    } finally {
      setAccepting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto overflow-x-hidden bg-black/80 backdrop-blur-md p-4 sm:p-0">
      <div 
        className="relative w-full max-w-3xl max-h-[90vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl animate-scale-in flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100 dark:border-gray-800 shrink-0">
          <div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white">
              Atualização nos Termos e Privacidade
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Para continuar usando o MentorIA, você precisa ler e aceitar nossos novos termos e políticas de privacidade.
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-100 dark:border-gray-800 px-6 shrink-0 bg-white dark:bg-gray-900">
          <button
            onClick={() => setActiveTab('terms')}
            className={`py-3 px-4 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'terms' 
                ? 'border-brand-600 text-brand-600 dark:text-brand-400 dark:border-brand-400' 
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            Termos de Uso
          </button>
          <button
            onClick={() => setActiveTab('privacy')}
            className={`py-3 px-4 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'privacy' 
                ? 'border-brand-600 text-brand-600 dark:text-brand-400 dark:border-brand-400' 
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            Política de Privacidade
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8 bg-gray-50 dark:bg-gray-800/50">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-brand-600 dark:text-brand-400">
              <Loader2 className="w-8 h-8 animate-spin mb-4" />
              <p className="text-sm font-medium">Carregando documento...</p>
            </div>
          ) : error && !termsContent && !privacyContent ? (
            <div className="text-center py-10 text-red-500">
              <p>{error}</p>
            </div>
          ) : (
            <article className="prose prose-gray dark:prose-invert max-w-none prose-headings:font-bold prose-a:text-brand-600 hover:prose-a:text-brand-500 prose-p:leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {activeTab === 'terms' ? termsContent : privacyContent}
              </ReactMarkdown>
            </article>
          )}
        </div>
        
        {/* Footer */}
        <div className="px-6 py-5 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 rounded-b-2xl flex justify-between items-center shrink-0">
          {error && (termsContent || privacyContent) && (
            <span className="text-sm text-red-500 font-medium">{error}</span>
          )}
          <div className="flex-1 flex justify-end">
            <button
              onClick={handleAccept}
              disabled={loading || accepting || (!termsContent && !privacyContent && !error)}
              className="px-8 py-3 bg-brand-600 hover:bg-brand-700 text-white font-bold rounded-xl transition-colors shadow-sm disabled:opacity-50 flex items-center justify-center min-w-[160px]"
            >
              {accepting ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Li e Concordo'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
