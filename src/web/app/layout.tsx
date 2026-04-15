import type { Metadata } from 'next';
import { ThemeProvider } from '@/lib/theme';
import '@/styles/globals.css';

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
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
