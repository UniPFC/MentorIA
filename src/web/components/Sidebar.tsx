'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useState } from 'react';
import { LayoutDashboard, MessageSquare, Upload, FolderOpen, LogOut, Menu, X, BookOpen, UserCircle, Clock } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import { authService } from '@/lib/auth';

interface SidebarProps {
  userName: string;
  userEmail: string;
  userInitials: string;
}

export default function Sidebar({ userName, userEmail, userInitials }: SidebarProps) {
  const [isOpen, setIsOpen] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  const navItems = [
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/dashboard/chat-types', label: 'Tipos de Chat', icon: FolderOpen },
    { href: '/dashboard/chats', label: 'Meus Chats', icon: MessageSquare },
    { href: '/dashboard/upload', label: 'Upload de Dados', icon: Upload },
    { href: '/dashboard/jobs', label: 'Histórico de Uploads', icon: Clock },
    { href: '/dashboard/profile', label: 'Perfil', icon: UserCircle },
  ];

  const handleLogout = async () => {
    await authService.logout();
    router.push('/login');
  };

  return (
    <>
      {/* Mobile Menu Toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="md:hidden fixed left-4 top-4 z-50 p-2.5 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-lg shadow-gray-200/50 dark:shadow-gray-900/50 text-gray-700 dark:text-gray-300 active:scale-95 transition-all duration-200"
      >
        {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Sidebar */}
      <aside className={`fixed left-0 top-0 w-[270px] h-screen bg-white dark:bg-gray-900 border-r border-gray-200/80 dark:border-gray-800/80 overflow-y-auto transition-transform duration-300 ease-out z-40 flex flex-col ${
        isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
      }`}>
        {/* Brand Header */}
        <div className="relative overflow-hidden bg-gradient-to-br from-brand-600 via-brand-700 to-brand-800 dark:from-brand-700 dark:via-brand-800 dark:to-brand-900 p-5">
          <div className="absolute -top-8 -right-8 w-28 h-28 rounded-full bg-white/10 animate-pulse-soft" />
          <div className="absolute -bottom-4 -left-4 w-16 h-16 rounded-full bg-white/5" />
          <div className="absolute top-3 right-12 w-3 h-3 rounded-full bg-white/20" />
          <div className="relative flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center shadow-sm">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">MentorIA</h2>
              <p className="text-[11px] text-white/50 font-medium">Aprendizado Inteligente</p>
            </div>
          </div>
        </div>

        {/* User Info */}
        <div className="p-3">
          <Link
            href="/dashboard/profile"
            className="flex items-center gap-3 p-3 rounded-xl bg-gradient-to-r from-gray-50 to-gray-100/50 dark:from-gray-800/60 dark:to-gray-800/30 border border-gray-200/60 dark:border-gray-700/30 hover:border-brand-300 dark:hover:border-brand-500/30 transition-all duration-200 group"
            onClick={() => setIsOpen(false)}
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-sm shadow-brand-500/20 group-hover:shadow-md group-hover:shadow-brand-500/30 transition-shadow duration-200">
              {userInitials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">{userName}</p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400 truncate">{userEmail}</p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 pb-3 space-y-0.5">
          <p className="px-3 mb-2 text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-gray-500">Menu</p>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
            return (
              <Link
                key={item.label}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-gradient-to-r from-brand-600 to-brand-700 text-white shadow-md shadow-brand-600/25 dark:from-brand-500 dark:to-brand-600 dark:shadow-brand-500/20'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200'
                }`}
                onClick={() => setIsOpen(false)}
              >
                <Icon className={`w-[18px] h-[18px] ${isActive ? '' : 'opacity-70'}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Bottom Section */}
        <div className="p-3 border-t border-gray-100 dark:border-gray-800/80 space-y-1">
          <div className="flex items-center justify-between px-3 py-1.5">
            <span className="text-[11px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide">Tema</span>
            <ThemeToggle />
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium text-red-500 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10 transition-all duration-200 active:scale-[0.98]"
          >
            <LogOut className="w-[18px] h-[18px]" />
            <span>Sair</span>
          </button>
        </div>
      </aside>

      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/30 backdrop-blur-sm md:hidden z-30 animate-fade-in"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
}
