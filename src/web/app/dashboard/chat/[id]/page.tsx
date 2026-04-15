'use client';

import { useState, useEffect, useRef, FormEvent } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ProtectedRoute from '@/components/ProtectedRoute';
import { authService } from '@/lib/auth';
import api from '@/lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
}

interface ChatData {
  id: string;
  title: string;
  chat_type_id: string;
  messages: Message[];
  llm_model?: string;
  llm_provider?: string;
}

interface ChatListItem {
  id: string;
  title: string;
  chat_type_id: string;
  created_at: string;
  updated_at: string;
}

export default function ChatPage() {
  const params = useParams();
  const router = useRouter();
  const chatId = params.id as string;

  const [chat, setChat] = useState<ChatData | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [user, setUser] = useState<any>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [chatList, setChatList] = useState<ChatListItem[]>([]);
  const [chatListLoading, setChatListLoading] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const [currentSources, setCurrentSources] = useState<any[]>([]);
  const [titlePollingActive, setTitlePollingActive] = useState(false);
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [showModelSelector, setShowModelSelector] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const modelSelectorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const userData = authService.getUser();
    if (userData) setUser(userData);
    loadChat();
    loadChatList();
    loadAvailableModels();
  }, [chatId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Close model selector when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modelSelectorRef.current && !modelSelectorRef.current.contains(event.target as Node)) {
        setShowModelSelector(false);
      }
    };

    if (showModelSelector) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showModelSelector]);

  // Poll for title updates when sending message
  useEffect(() => {
    if (!titlePollingActive) return;

    const interval = setInterval(async () => {
      try {
        const res = await api.get(`/chats/${chatId}`);
        const newChat = res.data;
        
        // If title changed, update it
        if (newChat.title && newChat.title !== chat?.title) {
          setChat(newChat);
          setChatList((prev) =>
            prev.map((c) =>
              c.id === chatId ? { ...c, title: newChat.title } : c
            )
          );
          // Stop polling once title is updated
          setTitlePollingActive(false);
        }
      } catch (err) {
        // Silently fail on polling
      }
    }, 1000); // Poll every 1 second

    return () => clearInterval(interval);
  }, [titlePollingActive, chatId, chat?.title]);

  // Auto-close sidebar on mobile
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)');
    if (mq.matches) setSidebarOpen(false);
    const handler = (e: MediaQueryListEvent) => { if (e.matches) setSidebarOpen(false); };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const loadChat = async () => {
    try {
      setLoading(true);
      const res = await api.get(`/chats/${chatId}`);
      setChat(res.data);
      setMessages(res.data.messages || []);
      
      // Sync messages: if there are unsaved messages, reload to get the latest
      // This handles the case where user left during streaming and returns
      if (res.data.messages && res.data.messages.length > 0) {
        const lastMessage = res.data.messages[res.data.messages.length - 1];
        // If the last message is from assistant, it means the response was saved
        if (lastMessage.role === 'assistant') {
          // Messages are in sync
        }
      }
    } catch (err: any) {
      setError('Não foi possível carregar o chat');
    } finally {
      setLoading(false);
    }
  };

  const loadChatList = async () => {
    try {
      setChatListLoading(true);
      const res = await api.get('/chats/');
      setChatList(Array.isArray(res.data) ? res.data : res.data.chats || []);
    } catch {
      // silently fail — sidebar is auxiliary
    } finally {
      setChatListLoading(false);
    }
  };

  const loadAvailableModels = async () => {
    try {
      const res = await api.get('/chats/models/available');
      setAvailableModels(res.data.models || []);
    } catch (err) {
      console.error('Failed to load models:', err);
    }
  };

  const updateChatModel = async (model: string, provider: string) => {
    try {
      await api.patch(`/chats/${chatId}/model`, {
        llm_model: model,
        llm_provider: provider,
      });
      setChat((prev) => prev ? { ...prev, llm_model: model, llm_provider: provider } : null);
      setShowModelSelector(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao atualizar modelo');
      setTimeout(() => setError(''), 4000);
    }
  };

  const sendMessage = async (e: FormEvent) => {
    e.preventDefault();
    const content = input.trim();
    if (!content || sending) return;

    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setInput('');
    setSending(true);
    setCurrentSources([]); // Clear previous sources
    setTitlePollingActive(true); // Start polling for title updates

    try {
      // Use streaming endpoint (API is on different port/host)
      const apiUrl = typeof window !== 'undefined' && (window as any).__API_URL__ 
        ? (window as any).__API_URL__ 
        : 'http://localhost:8000';
      
      // Get token from Cookies or localStorage (same as api.ts)
      const getCookie = (name: string) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop()?.split(';').shift();
        return null;
      };
      
      const token = getCookie('authToken') || localStorage.getItem('authToken');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const response = await fetch(`${apiUrl}/api/v1/chats/${chatId}/messages/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';
      let streamSources: any[] = [];
      let assistantMessageId = `assistant-${Date.now()}`;
      let assistantMessageCreated = false;

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n').filter((line) => line.trim());

          for (const line of lines) {
            try {
              const data = JSON.parse(line);

              if (data.type === 'token') {
                const isFirstToken = assistantContent === '';
                assistantContent += data.content;

                if (isFirstToken) {
                  // First token: create the assistant message
                  assistantMessageCreated = true;
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: assistantMessageId,
                      role: 'assistant',
                      content: assistantContent,
                      created_at: new Date().toISOString(),
                    },
                  ]);
                } else {
                  // Subsequent tokens: update existing message
                  setMessages((prev) => 
                    prev.map((msg) =>
                      msg.id === assistantMessageId
                        ? { ...msg, content: assistantContent }
                        : msg
                    )
                  );
                }
              } else if (data.type === 'sources') {
                streamSources = data.content || [];
                setCurrentSources(streamSources);
              } else if (data.type === 'message') {
                // Final message from backend, update with real ID
                const finalMessage = data.content;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, id: finalMessage.id }
                      : msg
                  )
                );
              } else if (data.type === 'error') {
                throw new Error(data.content);
              }
            } catch (parseErr) {
              // Silently skip parse errors
            }
          }
        }
      }
    } catch (err: any) {
      // Connection lost during streaming
      // Try to sync messages - the backend may have saved the response
      try {
        setError('Conexão perdida. Sincronizando mensagens...');
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
        await loadChat(); // Reload chat to get any saved messages
        setError(''); // Clear error if sync successful
      } catch (syncErr) {
        // If sync fails, show the original error
        setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
        setInput(content);
        setError(err.message || 'Erro ao enviar mensagem');
        setTimeout(() => setError(''), 4000);
      }
      setTitlePollingActive(false);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(e);
    }
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  };

  const userInitials = user
    ? (user.username || user.email || 'U').substring(0, 2).toUpperCase()
    : 'U';

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-950 overflow-hidden">
        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm md:hidden transition-opacity"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Chat history sidebar */}
        <aside
          className={`
            fixed md:relative z-40 md:z-auto h-full
            bg-white dark:bg-gray-900 border-r border-gray-200/80 dark:border-gray-800
            flex flex-col shrink-0
            transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]
            ${sidebarOpen
              ? 'w-72 translate-x-0'
              : 'w-0 -translate-x-full md:translate-x-0 md:w-0'
            }
          `}
        >
          <div className={`w-72 h-full flex flex-col ${sidebarOpen ? 'opacity-100' : 'opacity-0 md:opacity-0'} transition-opacity duration-200`}>
            {/* Sidebar header */}
            <div className="px-4 py-4 border-b border-gray-200/80 dark:border-gray-800 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-sm shadow-brand-500/20">
                  <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
                  </svg>
                </div>
                <h2 className="text-sm font-bold text-gray-900 dark:text-white">Conversas</h2>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Chat list */}
            <div className="flex-1 overflow-y-auto py-2 px-2">
              {chatListLoading ? (
                <div className="space-y-2 px-1 py-2">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="h-14 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
                  ))}
                </div>
              ) : chatList.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                  <div className="w-10 h-10 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-3">
                    <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                    </svg>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Nenhuma conversa</p>
                </div>
              ) : (
                chatList.map((c) => {
                  const isActive = c.id === chatId;
                  return (
                    <Link
                      key={c.id}
                      href={`/dashboard/chat/${c.id}`}
                      onClick={() => { if (window.innerWidth < 768) setSidebarOpen(false); }}
                      className={`group flex items-center gap-3 mb-1 px-3 py-2.5 rounded-xl text-left transition-all duration-200 ${
                        isActive
                          ? 'bg-brand-50 dark:bg-brand-500/10 shadow-sm'
                          : 'hover:bg-gray-50 dark:hover:bg-gray-800/60'
                      }`}
                    >
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
                        isActive
                          ? 'bg-brand-100 dark:bg-brand-500/20'
                          : 'bg-gray-100 dark:bg-gray-800 group-hover:bg-gray-200 dark:group-hover:bg-gray-700'
                      }`}>
                        <svg className={`w-4 h-4 ${isActive ? 'text-brand-600 dark:text-brand-400' : 'text-gray-400 dark:text-gray-500'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                        </svg>
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className={`text-sm font-medium truncate ${
                          isActive
                            ? 'text-brand-700 dark:text-brand-300'
                            : 'text-gray-700 dark:text-gray-200'
                        }`}>
                          {c.title || 'Chat sem título'}
                        </p>
                        <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5">
                          {new Date(c.updated_at || c.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })}
                        </p>
                      </div>
                      {isActive && (
                        <div className="w-1.5 h-1.5 rounded-full bg-brand-500 shrink-0" />
                      )}
                    </Link>
                  );
                })
              )}
            </div>

            {/* Sidebar footer */}
            <div className="px-3 py-3 border-t border-gray-200/80 dark:border-gray-800 space-y-1 shrink-0">
              <Link
                href="/dashboard/chats"
                className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-500/10 transition-all duration-200 active:scale-[0.98]"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Novo Chat
              </Link>
              <Link
                href="/dashboard"
                className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-300 transition-all duration-200"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" />
                </svg>
                Voltar ao Dashboard
              </Link>
            </div>
          </div>
        </aside>

        {/* Main chat area — expands/contracts with sidebar */}
        <div className="flex-1 flex flex-col min-w-0 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]">
          {/* Header */}
          <header className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-b border-gray-200/60 dark:border-gray-800/60 px-4 md:px-6 py-3 flex items-center gap-3 shrink-0">
            {/* Toggle sidebar */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 -ml-1 rounded-xl text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-200 active:scale-95"
              title={sidebarOpen ? 'Fechar conversas' : 'Abrir conversas'}
            >
              <svg className={`w-5 h-5 transition-transform duration-300 ${sidebarOpen ? 'rotate-0' : 'rotate-180'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M18.75 19.5l-7.5-7.5 7.5-7.5m-6 15L5.25 12l7.5-7.5" />
              </svg>
            </button>

            {/* Divider */}
            <div className="w-px h-6 bg-gray-200 dark:bg-gray-700" />

            {/* Chat info */}
            <div className="min-w-0 flex-1 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shrink-0 shadow-sm shadow-brand-500/20">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                </svg>
              </div>
              <div className="min-w-0 flex-1">
                <h1 className="text-sm font-bold text-gray-900 dark:text-white truncate">
                  {loading ? 'Carregando...' : chat?.title || 'Chat'}
                </h1>
                <p className="text-[11px] text-gray-500 dark:text-gray-400">
                  {messages.length} {messages.length === 1 ? 'mensagem' : 'mensagens'}
                </p>
              </div>
            </div>

            {/* Header actions */}
            <button
              onClick={() => setShowSources(!showSources)}
              className="p-2 rounded-xl text-amber-500 dark:text-amber-400 hover:text-amber-600 dark:hover:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-500/10 transition-all duration-200 ring-2 ring-amber-500/20 dark:ring-amber-400/20"
              title="Fontes"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.66V6.75a9 9 0 015.25-1.5m-5.25 0A2.25 2.25 0 113.75 7.5M5.25 7.5A2.25 2.25 0 018.25 5.25M5.25 7.5A2.25 2.25 0 018.25 5.25m6.75.75a2.25 2.25 0 100-4.5 2.25 2.25 0 000 4.5z" />
              </svg>
            </button>
            <Link
              href="/dashboard"
              className="p-2 rounded-xl text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-200"
              title="Dashboard"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
              </svg>
            </Link>
          </header>

          {/* Messages area */}
          <div className="flex-1 overflow-y-auto bg-gradient-to-b from-gray-50 to-white dark:from-gray-950 dark:to-gray-900">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-3">
                  <div className="relative">
                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg shadow-brand-500/25 animate-pulse-soft">
                      <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                      </svg>
                    </div>
                  </div>
                  <p className="text-xs font-medium text-gray-400 dark:text-gray-500">Carregando conversa...</p>
                </div>
              </div>
            ) : messages.length === 0 ? (
              /* Empty state */
              <div className="flex flex-col items-center justify-center h-full px-6 text-center animate-fade-in">
                <div className="relative mb-6">
                  <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-brand-100 to-brand-50 dark:from-brand-500/20 dark:to-brand-500/5 flex items-center justify-center shadow-lg shadow-brand-500/10">
                    <svg className="w-10 h-10 text-brand-500 dark:text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                    </svg>
                  </div>
                  <div className="absolute -bottom-1 -right-1 w-7 h-7 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-md shadow-brand-500/30">
                    <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                    </svg>
                  </div>
                </div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">Inicie a conversa</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md leading-relaxed">
                  Envie uma mensagem para começar. A IA responderá com base nos documentos carregados nesta base de dados.
                </p>
                <div className="flex flex-wrap items-center justify-center gap-2 mt-6">
                  {['O que você sabe?', 'Com oque pode me ajudar?', 'Como funciona?', 'Crie um teste de estudo!'].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => { setInput(suggestion); inputRef.current?.focus(); }}
                      className="px-4 py-2 rounded-xl text-xs font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-500/10 border border-brand-200 dark:border-brand-500/20 hover:bg-brand-100 dark:hover:bg-brand-500/15 hover:border-brand-300 dark:hover:border-brand-500/30 transition-all duration-200 active:scale-[0.97]"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              /* Messages list */
              <div className="max-w-3xl mx-auto px-4 md:px-6 py-6">
                {messages.map((msg, idx) => (
                  <div
                    key={msg.id}
                    className={`flex gap-3 mb-6 animate-fade-in ${msg.role === 'user' ? 'justify-end' : ''}`}
                    style={{ animationDelay: `${Math.min(idx * 0.03, 0.3)}s`, animationFillMode: 'both' }}
                  >
                    {/* Assistant avatar */}
                    {msg.role === 'assistant' && (
                      <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shrink-0 mt-0.5 shadow-md shadow-brand-500/20 ring-2 ring-white dark:ring-gray-900">
                        <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                        </svg>
                      </div>
                    )}

                    {/* Message content */}
                    <div className={`max-w-[75%] min-w-0 ${msg.role === 'user' ? 'order-first' : ''}`}>
                      {msg.role === 'assistant' && (
                        <p className="text-[10px] font-bold uppercase tracking-wider text-brand-600 dark:text-brand-400 mb-1.5 ml-1">MentorIA</p>
                      )}
                      <div
                        className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                          msg.role === 'user'
                            ? 'bg-gradient-to-br from-brand-600 to-brand-700 text-white rounded-br-md shadow-md shadow-brand-500/20'
                            : 'bg-white dark:bg-gray-800/80 border border-gray-200/80 dark:border-gray-700/60 text-gray-800 dark:text-gray-200 rounded-bl-md shadow-sm'
                        }`}
                      >
                        {msg.role === 'assistant' ? (
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            className="prose prose-sm dark:prose-invert max-w-none prose-p:my-2 prose-p:leading-relaxed prose-pre:bg-gray-100 dark:prose-pre:bg-gray-900 prose-pre:text-gray-900 dark:prose-pre:text-gray-100 prose-code:text-brand-600 dark:prose-code:text-brand-400 prose-code:bg-gray-100 dark:prose-code:bg-gray-900 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-strong:text-gray-900 dark:prose-strong:text-white prose-headings:text-gray-900 dark:prose-headings:text-white prose-a:text-brand-600 dark:prose-a:text-brand-400 prose-ul:my-2 prose-ol:my-2 prose-li:my-1"
                          >
                            {msg.content}
                          </ReactMarkdown>
                        ) : (
                          <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                        )}
                      </div>
                      <p className={`text-[10px] mt-1.5 px-1 ${msg.role === 'user' ? 'text-right' : ''} text-gray-400 dark:text-gray-500`}>
                        {formatTime(msg.created_at)}
                      </p>
                    </div>

                    {/* User avatar */}
                    {msg.role === 'user' && (
                      <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-gray-200 to-gray-300 dark:from-gray-600 dark:to-gray-700 flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold text-gray-600 dark:text-gray-200 ring-2 ring-white dark:ring-gray-900 shadow-sm">
                        {userInitials}
                      </div>
                    )}
                  </div>
                ))}

                {/* Typing indicator */}
                {sending && messages[messages.length - 1]?.role !== 'assistant' && (
                  <div className="flex gap-3 mb-6 animate-fade-in">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shrink-0 shadow-md shadow-brand-500/20 ring-2 ring-white dark:ring-gray-900">
                      <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-brand-600 dark:text-brand-400 mb-1.5 ml-1">MentorIA</p>
                      <div className="bg-white dark:bg-gray-800/80 border border-gray-200/80 dark:border-gray-700/60 rounded-2xl rounded-bl-md px-5 py-4 shadow-sm">
                        <div className="flex items-center gap-1.5">
                          <div className="w-2 h-2 rounded-full bg-brand-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                          <div className="w-2 h-2 rounded-full bg-brand-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                          <div className="w-2 h-2 rounded-full bg-brand-600 animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Sources panel */}
          {showSources && (
            <div className="absolute right-0 top-0 bottom-0 w-80 bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 shadow-lg flex flex-col z-20">
              {/* Header */}
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between shrink-0">
                <h2 className="text-sm font-bold text-gray-900 dark:text-white">Fontes & Referências</h2>
                <button
                  onClick={() => setShowSources(false)}
                  className="p-1 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Sources list */}
              <div className="flex-1 overflow-y-auto px-4 py-4">
                {currentSources.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center py-8">
                    <svg className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.66V6.75a9 9 0 015.25-1.5m-5.25 0A2.25 2.25 0 113.75 7.5M5.25 7.5A2.25 2.25 0 018.25 5.25M5.25 7.5A2.25 2.25 0 018.25 5.25m6.75.75a2.25 2.25 0 100-4.5 2.25 2.25 0 000 4.5z" />
                    </svg>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Nenhuma fonte disponível</p>
                    <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1">As fontes aparecerão aqui após cada resposta</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {currentSources.map((source, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700/50 hover:border-brand-300 dark:hover:border-brand-500/30 transition-all group"
                      >
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <div className="flex-1 min-w-0">
                            <p className="text-[10px] font-medium text-gray-500 dark:text-gray-500 mb-1.5">
                              Pergunta
                            </p>
                            <p className="text-[11px] text-gray-700 dark:text-gray-300 mb-3 leading-relaxed">
                              {source.question}
                            </p>
                            <p className="text-[10px] font-medium text-gray-500 dark:text-gray-500 mb-1.5">
                              Resposta
                            </p>
                            <div className="text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-900/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                              <p className="whitespace-pre-wrap break-words leading-relaxed">{source.answer}</p>
                            </div>
                          </div>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(`Q: ${source.question}\nA: ${source.answer}`);
                            }}
                            className="p-1.5 rounded-lg text-gray-400 hover:text-brand-600 dark:hover:text-brand-400 hover:bg-white dark:hover:bg-gray-700 transition-all opacity-0 group-hover:opacity-100 shrink-0"
                            title="Copiar"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Error banner */}
          {error && (
            <div className="px-4 py-2 bg-red-50 dark:bg-red-500/10 border-t border-red-200/60 dark:border-red-500/20 animate-slide-up">
              <p className="text-xs text-red-600 dark:text-red-400 text-center font-medium">{error}</p>
            </div>
          )}

          {/* Input area */}
          <div className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-t border-gray-200/60 dark:border-gray-800/60 px-4 md:px-6 py-4 shrink-0">
            <form onSubmit={sendMessage} className="max-w-3xl mx-auto">
              <div className="flex items-end gap-2 bg-gray-50 dark:bg-gray-800/50 rounded-2xl border border-gray-200/80 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600 focus-within:border-brand-500 dark:focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-500/20 dark:focus-within:ring-brand-400/20 transition-all duration-200 px-4 py-2.5">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Digite sua mensagem..."
                  rows={1}
                  className="flex-1 bg-transparent border-none outline-none focus:ring-0 focus:ring-offset-0 appearance-none resize-none text-sm text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 max-h-32 py-1.5 leading-relaxed"
                  disabled={sending || loading}
                  style={{ minHeight: '36px' }}
                  onInput={(e) => {
                    const target = e.target as HTMLTextAreaElement;
                    target.style.height = 'auto';
                    target.style.height = Math.min(target.scrollHeight, 128) + 'px';
                  }}
                />

                {/* Model selector in input area */}
                <div ref={modelSelectorRef} className="relative shrink-0 flex items-center">
                  <button
                    type="button"
                    onClick={() => setShowModelSelector(!showModelSelector)}
                    className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-all duration-200"
                    title={`Modelo: ${chat?.llm_model || 'Padrão'}`}
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </button>

                  {/* Model dropdown in input area */}
                  {showModelSelector && (
                    <div className="absolute bottom-full right-0 mb-2 w-56 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-lg z-50">
                      <div className="p-2 border-b border-gray-200 dark:border-gray-700">
                        <p className="text-xs font-semibold text-gray-900 dark:text-white px-2">Modelo</p>
                      </div>
                      <div className="max-h-48 overflow-y-auto">
                        {availableModels.length === 0 ? (
                          <div className="p-2 text-xs text-gray-500 dark:text-gray-400 text-center">
                            Nenhum modelo
                          </div>
                        ) : (
                          availableModels.map((model) => (
                            <button
                              key={`${model.model}-${model.provider}`}
                              type="button"
                              onClick={() => updateChatModel(model.model, model.provider)}
                              className={`w-full text-left px-3 py-2 text-xs transition-colors ${
                                chat?.llm_model === model.model && chat?.llm_provider === model.provider
                                  ? 'bg-brand-50 dark:bg-brand-500/20 text-brand-700 dark:text-brand-300'
                                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50'
                              }`}
                            >
                              <p className="font-medium text-[11px]">{model.model}</p>
                              <p className="text-[9px] text-gray-500 dark:text-gray-400">
                                {model.provider}
                              </p>
                            </button>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={!input.trim() || sending || loading}
                  className="shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-brand-600 to-brand-700 hover:from-brand-500 hover:to-brand-600 disabled:from-gray-300 disabled:to-gray-300 dark:disabled:from-gray-600 dark:disabled:to-gray-700 text-white flex items-center justify-center transition-all duration-200 disabled:cursor-not-allowed active:scale-[0.93] shadow-md shadow-brand-500/25 hover:shadow-lg hover:shadow-brand-500/30 disabled:shadow-none"
                >
                  {sending ? (
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                    </svg>
                  )}
                </button>
              </div>
              <p className="text-[10px] text-gray-400 dark:text-gray-500 text-center mt-2.5 select-none">
                Enter para enviar · Shift+Enter para nova linha
              </p>
            </form>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
