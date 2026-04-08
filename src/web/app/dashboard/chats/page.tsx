'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import ProtectedRoute from '@/components/ProtectedRoute';
import Sidebar from '@/components/Sidebar';
import { authService } from '@/lib/auth';
import api from '@/lib/api';

interface Chat {
  id: string;
  title: string;
  chat_type_id: string;
  created_at: string;
  updated_at: string;
}

interface ChatType {
  id: string;
  name: string;
  description?: string;
}

export default function ChatsPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [chats, setChats] = useState<Chat[]>([]);
  const [chatTypes, setChatTypes] = useState<ChatType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showNewChat, setShowNewChat] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [selectedChatType, setSelectedChatType] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const userData = authService.getUser();
    if (userData) setUser(userData);
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [chatsRes, typesRes] = await Promise.all([
        api.get('/chats'),
        api.get('/chat-types'),
      ]);
      setChats(chatsRes.data);
      setChatTypes(typesRes.data);
    } catch (err: any) {
      setError('Não foi possível carregar os dados');
    } finally {
      setLoading(false);
    }
  };

  const createChat = async () => {
    if (!newTitle.trim() || !selectedChatType) return;
    setCreating(true);
    try {
      const res = await api.post('/chats', {
        title: newTitle.trim(),
        chat_type_id: selectedChatType,
      });
      router.push(`/dashboard/chat/${res.data.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao criar chat');
      setCreating(false);
    }
  };

  const deleteChat = async (chatId: string) => {
    try {
      await api.delete(`/chats/${chatId}`);
      setChats(chats.filter(c => c.id !== chatId));
    } catch {
      setError('Erro ao deletar chat');
    }
  };

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });

  const userInitials = user
    ? (user.username || user.email || 'U').substring(0, 2).toUpperCase()
    : 'U';

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-950 overflow-hidden">
        <Sidebar
          userName={user?.username || user?.name || 'Usuário'}
          userEmail={user?.email || ''}
          userInitials={userInitials}
        />
        <div className="flex-1 flex flex-col md:ml-64 ml-0">
          {/* Header */}
          <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-6 py-5 shrink-0">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">Meus Chats</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Gerencie suas conversas</p>
              </div>
              <button
                onClick={() => setShowNewChat(true)}
                className="btn-primary !w-auto flex items-center gap-2 !py-2.5 !px-4 !rounded-xl"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Novo Chat
              </button>
            </div>
          </div>

          {/* New Chat Modal */}
          {showNewChat && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
              <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setShowNewChat(false)} />
              <div className="relative card p-6 w-full max-w-md animate-fade-in">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Novo Chat</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Título</label>
                    <input
                      type="text"
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                      placeholder="Ex: Estudo para prova de matemática"
                      className="input-field"
                      autoFocus
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Tipo de Chat</label>
                    {chatTypes.length === 0 ? (
                      <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20">
                        <p className="text-xs text-amber-700 dark:text-amber-400">
                          Nenhum tipo de chat disponível. Faça upload de dados primeiro na página de{' '}
                          <Link href="/dashboard/upload" className="font-medium underline">Upload</Link>.
                        </p>
                      </div>
                    ) : (
                      <select
                        value={selectedChatType}
                        onChange={(e) => setSelectedChatType(e.target.value)}
                        className="input-field"
                      >
                        <option value="">Selecione um tipo</option>
                        {chatTypes.map((ct) => (
                          <option key={ct.id} value={ct.id}>{ct.name}</option>
                        ))}
                      </select>
                    )}
                  </div>
                  <div className="flex gap-3 pt-2">
                    <button onClick={() => setShowNewChat(false)} className="btn-secondary flex-1 !rounded-xl">Cancelar</button>
                    <button
                      onClick={createChat}
                      disabled={!newTitle.trim() || !selectedChatType || creating}
                      className="btn-primary flex-1 !rounded-xl flex items-center justify-center gap-2"
                    >
                      {creating && (
                        <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                      )}
                      {creating ? 'Criando...' : 'Criar Chat'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Content */}
          <div className="flex-1 overflow-auto p-6">
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <svg className="w-6 h-6 animate-spin text-brand-600 dark:text-brand-400" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              </div>
            ) : error ? (
              <div className="card p-8 text-center">
                <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-500/10 flex items-center justify-center mx-auto mb-4">
                  <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                  </svg>
                </div>
                <p className="text-gray-600 dark:text-gray-400 text-sm">{error}</p>
                <button onClick={() => { setError(''); loadData(); }} className="mt-4 text-brand-600 dark:text-brand-400 text-sm font-medium hover:underline">
                  Tentar novamente
                </button>
              </div>
            ) : chats.length === 0 ? (
              <div className="card p-12 text-center">
                <div className="w-16 h-16 rounded-2xl bg-brand-50 dark:bg-brand-500/10 flex items-center justify-center mx-auto mb-5">
                  <svg className="w-8 h-8 text-brand-600 dark:text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
                  </svg>
                </div>
                <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">Nenhum chat ainda</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">Crie seu primeiro chat para começar uma conversa inteligente.</p>
                <button onClick={() => setShowNewChat(true)} className="btn-primary !w-auto !px-6 !rounded-xl inline-flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                  </svg>
                  Criar primeiro chat
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {chats.map((chat) => (
                  <Link
                    key={chat.id}
                    href={`/dashboard/chat/${chat.id}`}
                    className="card p-4 flex items-center justify-between group hover:border-brand-200 dark:hover:border-brand-500/30 transition-colors block"
                  >
                    <div className="min-w-0 flex-1">
                      <h3 className="text-sm font-medium text-gray-900 dark:text-white">{chat.title}</h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        Criado em {formatDate(chat.created_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-4">
                      <button
                        onClick={(e) => { e.preventDefault(); e.stopPropagation(); deleteChat(chat.id); }}
                        className="opacity-0 group-hover:opacity-100 p-2 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                        </svg>
                      </button>
                      <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                      </svg>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
