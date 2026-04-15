'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { MessageSquare, FolderOpen, Upload, ChevronRight, Plus, Sparkles } from 'lucide-react';
import api from '@/lib/api';

export default function DashboardContent() {
  const [stats, setStats] = useState({ totalChats: 0, totalChatTypes: 0, totalJobs: 0 });
  const [chats, setChats] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [chatsRes, typesRes, jobsRes] = await Promise.allSettled([
        api.get('/chats/', { params: { limit: 5 } }),
        api.get('/chat-types/', { params: { limit: 1 } }),
        api.get('/upload/jobs/', { params: { limit: 1 } }),
      ]);

      const chatList = chatsRes.status === 'fulfilled' ? chatsRes.value.data : [];
      const typesData = typesRes.status === 'fulfilled' ? typesRes.value.data : { total: 0 };
      const jobsList = jobsRes.status === 'fulfilled' ? jobsRes.value.data : [];

      setChats(Array.isArray(chatList) ? chatList.slice(0, 5) : []);
      setStats({
        totalChats: Array.isArray(chatList) ? chatList.length : 0,
        totalChatTypes: typesData?.total ?? 0,
        totalJobs: Array.isArray(jobsList) ? jobsList.length : 0,
      });
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });

  if (loading) {
    return (
      <div className="flex-1 flex flex-col min-h-0">
        <div className="flex-1 overflow-auto p-6 space-y-6 animate-pulse">
          <div className="h-44 rounded-2xl bg-gray-200 dark:bg-gray-800" />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card p-5 space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-xl bg-gray-200 dark:bg-gray-700" />
                  <div className="h-4 w-20 bg-gray-200 dark:bg-gray-700 rounded" />
                </div>
                <div className="h-8 w-12 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
            ))}
          </div>
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
              <div className="h-5 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
            </div>
            {[1, 2, 3].map((i) => (
              <div key={i} className="px-6 py-4 border-b border-gray-100 dark:border-gray-800">
                <div className="h-4 w-48 bg-gray-200 dark:bg-gray-700 rounded mb-2" />
                <div className="h-3 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const statCards = [
    { label: 'Meus Chats', value: stats.totalChats, icon: MessageSquare, color: 'text-brand-600 bg-brand-50 dark:text-brand-400 dark:bg-brand-500/10', shadow: 'shadow-brand-500/5' },
    { label: 'Tipos de Chat', value: stats.totalChatTypes, icon: FolderOpen, color: 'text-violet-600 bg-violet-50 dark:text-violet-400 dark:bg-violet-500/10', shadow: 'shadow-violet-500/5' },
    { label: 'Uploads', value: stats.totalJobs, icon: Upload, color: 'text-amber-600 bg-amber-50 dark:text-amber-400 dark:bg-amber-500/10', shadow: 'shadow-amber-500/5' },
  ];

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Welcome Banner */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-brand-600 via-brand-700 to-brand-800 p-8 text-white animate-fade-in">
          <div className="absolute -top-16 -right-16 w-64 h-64 rounded-full bg-white/5 animate-pulse-soft" />
          <div className="absolute -bottom-20 -left-20 w-48 h-48 rounded-full bg-white/5 animate-pulse-soft" style={{ animationDelay: '1s' }} />
          <div className="absolute top-8 right-32 w-3 h-3 rounded-full bg-white/20 animate-float" />
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-5 h-5 text-white/70" />
              <span className="text-xs font-semibold text-white/60 uppercase tracking-wider">Painel</span>
            </div>
            <h1 className="text-2xl font-extrabold mb-2 tracking-tight">Bem-vindo ao MentorIA</h1>
            <p className="text-white/60 max-w-lg text-sm leading-relaxed">
              Gerencie seus chats inteligentes, envie documentos e obtenha respostas contextualizadas com IA.
            </p>
            <div className="flex flex-wrap gap-3 mt-6">
              <Link href="/dashboard/upload" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/15 hover:bg-white/25 backdrop-blur-sm text-sm font-semibold transition-all duration-200 active:scale-[0.98]">
                <Upload className="w-4 h-4" />
                Upload de Dados
              </Link>
              <Link href="/dashboard/chats" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white text-brand-700 text-sm font-semibold hover:bg-white/90 transition-all duration-200 shadow-lg shadow-black/10 active:scale-[0.98]">
                <Plus className="w-4 h-4" />
                Novo Chat
              </Link>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 animate-slide-up" style={{ animationDelay: '0.1s', animationFillMode: 'both' }}>
          {statCards.map((stat, i) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.label}
                className={`card p-5 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300 ${stat.shadow}`}
                style={{ animationDelay: `${i * 0.05}s` }}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${stat.color}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{stat.label}</p>
                </div>
                <p className="text-3xl font-extrabold text-gray-900 dark:text-white">{stat.value}</p>
              </div>
            );
          })}
        </div>

        {/* Recent Chats */}
        <div className="card overflow-hidden animate-slide-up" style={{ animationDelay: '0.2s', animationFillMode: 'both' }}>
          <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
            <h2 className="text-base font-bold text-gray-900 dark:text-white">Chats Recentes</h2>
            <Link href="/dashboard/chats" className="text-sm text-brand-600 dark:text-brand-400 font-semibold hover:text-brand-700 dark:hover:text-brand-300 transition-colors">
              Ver todos
            </Link>
          </div>
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {chats.length === 0 ? (
              <div className="p-10 text-center">
                <div className="w-12 h-12 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mx-auto mb-3">
                  <MessageSquare className="w-6 h-6 text-gray-400" />
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Nenhum chat criado ainda.{' '}
                  <Link href="/dashboard/chats" className="text-brand-600 dark:text-brand-400 font-semibold hover:text-brand-700 dark:hover:text-brand-300 transition-colors">
                    Crie seu primeiro chat
                  </Link>
                </p>
              </div>
            ) : (
              chats.map((chat: any) => (
                <Link key={chat.id} href={`/dashboard/chat/${chat.id}`} className="block px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-all duration-200 group">
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <h3 className="text-sm font-semibold text-gray-900 dark:text-white group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">{chat.title}</h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        {formatDate(chat.created_at)}
                      </p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-gray-400 shrink-0 ml-4 group-hover:text-brand-500 group-hover:translate-x-0.5 transition-all duration-200" />
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
