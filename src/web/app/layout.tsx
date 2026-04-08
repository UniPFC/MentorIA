import type { Metadata } from 'next';
import { ThemeProvider } from '@/lib/theme';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'Portal RAG',
  description: 'Sistema de Questões e Chat Inteligente',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
