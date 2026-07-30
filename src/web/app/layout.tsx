import type { Metadata } from 'next';
import { ThemeProvider } from '@/lib/theme';
import CookieBanner from '@/components/CookieBanner';
import '@/styles/globals.css';
import 'katex/dist/katex.min.css';

export const metadata: Metadata = {
  title: 'MentorIA',
  description: 'Chat Inteligente com Tecnologia RAG',
  icons: {
    icon: '/MentorIA-Logo-Full-Transparent.ico',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          {children}
          <CookieBanner />
        </ThemeProvider>
      </body>
    </html>
  );
}
