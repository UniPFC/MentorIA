'use client';

import LoginForm from '@/components/LoginForm';

export default function LoginPage() {
  return (
    <div className="min-h-screen flex bg-gray-50 dark:bg-gray-950">
      {/* Left brand panel */}
      <div className="hidden lg:flex lg:w-[45%] relative overflow-hidden bg-gradient-to-br from-brand-600 via-brand-700 to-brand-900">
        {/* Pattern grid */}
        <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
        {/* Decorative elements */}
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
              Aprenda de forma
              <br /><span className="text-white/90">inteligente com IA</span>
            </h2>
            <p className="text-base text-white/50 max-w-sm leading-relaxed">
              Faça upload dos seus materiais e obtenha respostas contextualizadas com tecnologia RAG.
            </p>

            <div className="mt-10 space-y-4">
              {[
                { text: 'Upload de documentos PDF, TXT, CSV e mais', delay: '' },
                { text: 'Respostas baseadas nos seus próprios materiais', delay: 'animation-delay: 0.1s' },
                { text: 'Chat inteligente com múltiplos contextos', delay: 'animation-delay: 0.2s' },
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
        <LoginForm />
      </div>
    </div>
  );
}
