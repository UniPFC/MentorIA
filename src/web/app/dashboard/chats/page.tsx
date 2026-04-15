'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  Plus, MessageSquare, Trash2, Search, Calendar,
  AlertCircle, Loader2, FolderOpen, Sparkles, ChevronDown, X,
} from 'lucide-react';
import DashboardLayout from '@/components/DashboardLayout';
import { Button, Input, Modal, Spinner, EmptyState, Badge } from '@/components/ui';
import api from '@/lib/api';

interface Chat {
  id: string;
  title: string;
  chat_type_id: string;
  llm_model?: string | null;
  llm_provider?: string | null;
  created_at: string;
  updated_at: string;
}

interface ChatType {
  id: string;
  name: string;
  description?: string;
  owner_name?: string;
}

function ChatsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const chatTypeIdFromUrl = searchParams?.get('chat_type_id');
  
  const [chats, setChats] = useState<Chat[]>([]);
  const [chatTypes, setChatTypes] = useState<ChatType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [filterChatTypeId, setFilterChatTypeId] = useState('');

  // Create modal
  const [showNew, setShowNew] = useState(false);
  const [chatTitle, setChatTitle] = useState('');
  const [selectedType, setSelectedType] = useState(chatTypeIdFromUrl || '');
  const [typeSearch, setTypeSearch] = useState('');
  const [typeDropdownOpen, setTypeDropdownOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Delete modal
  const [deleteTarget, setDeleteTarget] = useState<Chat | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadData();
  }, [chatTypeIdFromUrl]);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setTypeDropdownOpen(false);
      }
    };
    if (typeDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      setTimeout(() => searchInputRef.current?.focus(), 50);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [typeDropdownOpen]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [chatsRes, typesRes] = await Promise.all([
        api.get('/chats/'),
        api.get('/chat-types/'),
      ]);
      setChats(chatsRes.data);
      setChatTypes(typesRes.data.chat_types || []);
    } catch {
      setError('Não foi possível carregar os dados');
    } finally {
      setLoading(false);
    }
  };

  const createChat = async () => {
    if (!selectedType) return;
    setCreating(true);
    try {
      const res = await api.post('/chats', {
        chat_type_id: selectedType,
        ...(chatTitle.trim() && { title: chatTitle.trim() }),
      });
      router.push(`/dashboard/chat/${res.data.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao criar chat');
      setCreating(false);
    }
  };

  const deleteChat = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.delete(`/chats/${deleteTarget.id}`);
      setChats((prev) => prev.filter((c) => c.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch {
      setError('Erro ao deletar chat');
    } finally {
      setDeleting(false);
    }
  };

  const formatDate = (d: string) =>
    new Date(d).toLocaleDateString('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });

  const getChatTypeName = (id: string) =>
    chatTypes.find((ct) => ct.id === id)?.name || 'Desconhecido';

  const filtered = chats.filter((c) => {
    const matchesSearch = c.title.toLowerCase().includes(search.toLowerCase());
    const matchesType = !filterChatTypeId || c.chat_type_id === filterChatTypeId;
    return matchesSearch && matchesType;
  });

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="bg-white dark:bg-gray-900 border-b border-gray-200/80 dark:border-gray-800 px-6 py-5 shrink-0">
        <div className="flex items-center justify-between animate-fade-in">
          <div>
            <h1 className="text-xl font-extrabold text-gray-900 dark:text-white tracking-tight">Meus Chats</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              {chats.length} conversa{chats.length !== 1 ? 's' : ''}
            </p>
          </div>
          <Button onClick={() => setShowNew(true)} icon={<Plus className="w-4 h-4" />}>
            Novo Chat
          </Button>
        </div>

        {/* Search and Filter */}
        {chats.length > 0 && (
          <div className="mt-4 flex flex-col sm:flex-row gap-3 animate-fade-in" style={{ animationDelay: '0.1s' }}>
            <div className="flex-1 max-w-md">
              <Input
                placeholder="Buscar chats..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                icon={<Search className="w-4 h-4" />}
              />
            </div>
            {chatTypes.length > 0 && (
              <div className="relative">
                <button
                  onClick={() => setTypeDropdownOpen(!typeDropdownOpen)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg border-2 transition-all text-sm font-medium ${
                    filterChatTypeId
                      ? 'border-brand-300 dark:border-brand-500/30 bg-brand-50 dark:bg-brand-500/5 text-brand-700 dark:text-brand-300'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 text-gray-700 dark:text-gray-300'
                  }`}
                >
                  <FolderOpen className="w-4 h-4" />
                  {filterChatTypeId ? getChatTypeName(filterChatTypeId) : 'Todos os tipos'}
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform ${typeDropdownOpen ? 'rotate-180' : ''}`} />
                </button>
                
                {typeDropdownOpen && (
                  <div className="absolute z-50 top-full mt-2 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg shadow-black/10 dark:shadow-black/30 overflow-hidden animate-scale-in">
                    <button
                      onClick={() => { setFilterChatTypeId(''); setTypeDropdownOpen(false); }}
                      className={`w-full flex items-center gap-2 px-3 py-2.5 text-left text-sm transition-colors ${
                        !filterChatTypeId
                          ? 'bg-brand-50 dark:bg-brand-500/10 text-brand-700 dark:text-brand-300'
                          : 'hover:bg-gray-50 dark:hover:bg-gray-700/50 text-gray-900 dark:text-white'
                      }`}
                    >
                      <FolderOpen className="w-3.5 h-3.5" />
                      Todos os tipos
                      {!filterChatTypeId && <svg className="w-4 h-4 ml-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>}
                    </button>
                    {chatTypes.map((ct) => (
                      <button
                        key={ct.id}
                        onClick={() => { setFilterChatTypeId(ct.id); setTypeDropdownOpen(false); }}
                        className={`w-full flex items-center gap-2 px-3 py-2.5 text-left text-sm transition-colors ${
                          filterChatTypeId === ct.id
                            ? 'bg-brand-50 dark:bg-brand-500/10 text-brand-700 dark:text-brand-300'
                            : 'hover:bg-gray-50 dark:hover:bg-gray-700/50 text-gray-900 dark:text-white'
                        }`}
                      >
                        <FolderOpen className="w-3.5 h-3.5" />
                        {ct.name}
                        {filterChatTypeId === ct.id && <svg className="w-4 h-4 ml-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6 animate-slide-up" style={{ animationFillMode: 'both' }}>
        {loading ? (
          <div className="space-y-2 max-w-4xl animate-pulse">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-gray-200 dark:bg-gray-700" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
                  <div className="h-3 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
            <p className="text-sm text-gray-600 dark:text-gray-400">{error}</p>
            <button
              onClick={() => { setError(''); loadData(); }}
              className="mt-3 text-brand-600 dark:text-brand-400 text-sm font-medium hover:underline"
            >
              Tentar novamente
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<MessageSquare className="w-8 h-8" />}
            title={search ? 'Nenhum chat encontrado' : 'Nenhum chat ainda'}
            description={search ? 'Tente outro termo de busca.' : 'Crie seu primeiro chat para começar uma conversa inteligente.'}
            action={!search ? (
              <Button onClick={() => setShowNew(true)} icon={<Plus className="w-4 h-4" />}>
                Criar primeiro chat
              </Button>
            ) : undefined}
          />
        ) : (
          <div className="space-y-2">
            {filtered.map((chat) => (
              <div
                key={chat.id}
                className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200/80 dark:border-gray-800 hover:border-brand-300 dark:hover:border-brand-500/40 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300 group"
              >
                <div className="flex items-center gap-4 p-4">
                  <div className="w-11 h-11 rounded-xl bg-brand-50 dark:bg-brand-500/10 flex items-center justify-center shrink-0">
                    <MessageSquare className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                  </div>

                  <Link href={`/dashboard/chat/${chat.id}`} className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white truncate group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
                      {chat.title}
                    </h3>
                    <div className="flex items-center gap-3 mt-1">
                      <Badge variant="info">{getChatTypeName(chat.chat_type_id)}</Badge>
                      {chat.llm_model && (
                        <span className="text-[10px] text-gray-400 dark:text-gray-500 font-mono">
                          {chat.llm_model}
                        </span>
                      )}
                    </div>
                  </Link>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs text-gray-400 dark:text-gray-500 hidden sm:flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {formatDate(chat.updated_at)}
                    </span>
                    <button
                      onClick={() => setDeleteTarget(chat)}
                      className="p-2 rounded-xl text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all duration-200 opacity-0 group-hover:opacity-100"
                      title="Deletar chat"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Modal */}
      <Modal
        open={showNew}
        onClose={() => { setShowNew(false); setSelectedType(''); setTypeSearch(''); setChatTitle(''); setTypeDropdownOpen(false); }}
        title="Novo Chat"
        footer={
          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => { setShowNew(false); setSelectedType(''); setTypeSearch(''); setChatTitle(''); setTypeDropdownOpen(false); }} className="flex-1">
              Cancelar
            </Button>
            <Button
              onClick={createChat}
              disabled={!selectedType}
              loading={creating}
              className="flex-1"
            >
              Criar
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          {chatTypes.length === 0 ? (
            <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20">
              <p className="text-xs text-amber-700 dark:text-amber-400">
                Nenhum tipo de chat disponível. Faça upload de dados primeiro na página de{' '}
                <Link href="/dashboard/upload" className="font-medium underline">Upload</Link>.
              </p>
            </div>
          ) : (
            <>
              {/* Title input (optional) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Título <span className="text-gray-400 dark:text-gray-500 font-normal">(opcional)</span>
                </label>
                <Input
                  placeholder="Ex: Dúvidas sobre o projeto..."
                  value={chatTitle}
                  onChange={(e) => setChatTitle(e.target.value)}
                  maxLength={200}
                />
              </div>

              {/* Chat type combobox */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Base de dados <span className="text-red-400">*</span>
                </label>
                <div className="relative" ref={dropdownRef}>
                  {/* Trigger button */}
                  <button
                    type="button"
                    onClick={() => setTypeDropdownOpen(!typeDropdownOpen)}
                    className={`w-full flex items-center gap-3 p-3 rounded-xl border-2 transition-all text-left ${
                      typeDropdownOpen
                        ? 'border-brand-500 dark:border-brand-400 ring-2 ring-brand-500/20'
                        : selectedType
                          ? 'border-brand-300 dark:border-brand-500/30 bg-brand-50/50 dark:bg-brand-500/5'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                    } bg-white dark:bg-gray-800`}
                  >
                    {selectedType ? (() => {
                      const ct = chatTypes.find(t => t.id === selectedType);
                      const isMentorIA = ct?.owner_name === 'MentorIA';
                      return (
                        <>
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                            isMentorIA
                              ? 'bg-gradient-to-br from-brand-500 to-violet-500 shadow-sm shadow-brand-500/20'
                              : 'bg-brand-100 dark:bg-brand-500/20'
                          }`}>
                            {isMentorIA ? (
                              <Sparkles className="w-3.5 h-3.5 text-white" />
                            ) : (
                              <FolderOpen className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0 flex items-center gap-1.5">
                            <span className="text-sm font-medium text-gray-900 dark:text-white truncate">{ct?.name}</span>
                            {isMentorIA && (
                              <span className="inline-flex items-center px-1.5 py-0.5 rounded-md bg-gradient-to-r from-brand-500 to-violet-500 text-white text-[9px] font-bold uppercase tracking-wider shrink-0">
                                Oficial
                              </span>
                            )}
                          </div>
                          <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); setSelectedType(''); }}
                            className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </>
                      );
                    })() : (
                      <>
                        <div className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center shrink-0">
                          <FolderOpen className="w-3.5 h-3.5 text-gray-400" />
                        </div>
                        <span className="text-sm text-gray-400 dark:text-gray-500 flex-1">Selecione uma base de dados...</span>
                      </>
                    )}
                    <ChevronDown className={`w-4 h-4 text-gray-400 shrink-0 transition-transform duration-200 ${typeDropdownOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {/* Dropdown */}
                  {typeDropdownOpen && (
                    <div className="absolute z-50 w-full mt-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl shadow-black/10 dark:shadow-black/30 overflow-hidden animate-scale-in">
                      {/* Search inside dropdown */}
                      <div className="p-2 border-b border-gray-100 dark:border-gray-700/50">
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                          <input
                            ref={searchInputRef}
                            type="text"
                            placeholder="Buscar base de dados..."
                            value={typeSearch}
                            onChange={(e) => setTypeSearch(e.target.value)}
                            className="w-full pl-9 pr-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500 dark:focus:border-brand-400 text-gray-900 dark:text-white placeholder-gray-400"
                          />
                        </div>
                      </div>

                      {/* Results list */}
                      <div className="max-h-52 overflow-y-auto py-1">
                        {chatTypes
                          .filter((ct) => ct.name.toLowerCase().includes(typeSearch.toLowerCase()) || (ct.description || '').toLowerCase().includes(typeSearch.toLowerCase()))
                          .sort((a, b) => {
                            const aOfficial = a.owner_name === 'MentorIA' ? 0 : 1;
                            const bOfficial = b.owner_name === 'MentorIA' ? 0 : 1;
                            return aOfficial - bOfficial;
                          })
                          .map((ct) => {
                            const isMentorIA = ct.owner_name === 'MentorIA';
                            const isSelected = selectedType === ct.id;
                            return (
                              <button
                                key={ct.id}
                                type="button"
                                onClick={() => { setSelectedType(ct.id); setTypeDropdownOpen(false); setTypeSearch(''); }}
                                className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors ${
                                  isSelected
                                    ? 'bg-brand-50 dark:bg-brand-500/10'
                                    : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                                }`}
                              >
                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                                  isSelected
                                    ? 'bg-brand-100 dark:bg-brand-500/20'
                                    : isMentorIA
                                      ? 'bg-gradient-to-br from-brand-500 to-violet-500 shadow-sm shadow-brand-500/20'
                                      : 'bg-gray-100 dark:bg-gray-700'
                                }`}>
                                  {isMentorIA && !isSelected ? (
                                    <Sparkles className="w-3.5 h-3.5 text-white" />
                                  ) : (
                                    <FolderOpen className={`w-3.5 h-3.5 ${
                                      isSelected
                                        ? 'text-brand-600 dark:text-brand-400'
                                        : 'text-gray-500 dark:text-gray-400'
                                    }`} />
                                  )}
                                </div>
                                <div className="min-w-0 flex-1">
                                  <div className="flex items-center gap-1.5">
                                    <span className={`text-sm font-medium truncate ${
                                      isSelected ? 'text-brand-700 dark:text-brand-300' : 'text-gray-900 dark:text-white'
                                    }`}>{ct.name}</span>
                                    {isMentorIA && (
                                      <span className="inline-flex items-center px-1.5 py-0.5 rounded-md bg-gradient-to-r from-brand-500 to-violet-500 text-white text-[9px] font-bold uppercase tracking-wider shrink-0">
                                        Oficial
                                      </span>
                                    )}
                                  </div>
                                  {ct.description && (
                                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">{ct.description}</p>
                                  )}
                                </div>
                                {isSelected && (
                                  <svg className="w-4 h-4 text-brand-600 dark:text-brand-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                                  </svg>
                                )}
                              </button>
                            );
                          })}
                        {chatTypes.filter((ct) => ct.name.toLowerCase().includes(typeSearch.toLowerCase())).length === 0 && (
                          <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">Nenhuma base encontrada</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </Modal>

      {/* Delete Confirmation */}
      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Deletar Chat"
        size="sm"
        footer={
          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => setDeleteTarget(null)} className="flex-1">
              Cancelar
            </Button>
            <Button variant="danger" onClick={deleteChat} loading={deleting} className="flex-1">
              Deletar
            </Button>
          </div>
        }
      >
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Tem certeza que deseja deletar <strong className="text-gray-900 dark:text-white">{deleteTarget?.title}</strong>?
          Todas as mensagens serão perdidas.
        </p>
      </Modal>
    </DashboardLayout>
  );
}

export default function ChatsPage() {
  return (
    <Suspense fallback={<div className="p-6">Carregando...</div>}>
      <ChatsPageContent />
    </Suspense>
  );
}
