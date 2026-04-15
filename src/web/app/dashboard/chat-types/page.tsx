'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { Search, LayoutGrid, List, Trash2, Globe, Lock, MessageSquare, Calendar, User, Sparkles, Shield, Upload, Star, Edit2 } from 'lucide-react';
import DashboardLayout from '@/components/DashboardLayout';
import { Button, Input, Modal, Badge, EmptyState, Card } from '@/components/ui';
import ChatTypeEditModal from '@/components/ChatTypeEditModal';

import { PageSpinner } from '@/components/ui/Spinner';
import Toast from '@/components/Toast';
import api from '@/lib/api';

interface ChatType {
  id: string;
  name: string;
  description?: string;
  tags?: string[];
  is_public: boolean;
  owner_id?: string;
  owner_name?: string;
  collection_name: string;
  created_at: string;
  is_favorited?: boolean;
}

export default function ChatTypesPage() {
  const [chatTypes, setChatTypes] = useState<ChatType[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [tab, setTab] = useState<'my-types' | 'explore'>('my-types');
  const [showDelete, setShowDelete] = useState<string | null>(null);
  const [editingChatType, setEditingChatType] = useState<ChatType | null>(null);
  const [updating, setUpdating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const loadChatTypes = useCallback(async () => {
    try {
      setLoading(true);
      const params: any = { limit: 100 };
      
      if (tab === 'my-types') {
        // Meus tipos: privados + públicos favoritados
        const res = await api.get('/chat-types/', { params });
        const data = res.data;
        setChatTypes(data.chat_types || []);
        setTotal(data.total || 0);
      } else {
        // Explorar: todos os públicos com busca
        if (search) params.query = search;
        params.is_public = true;
        const res = await api.get('/chat-types/search/', { params });
        const data = res.data;
        setChatTypes(data.chat_types || []);
        setTotal(data.total || 0);
      }
    } catch (error) {
      console.error('Error loading chat types:', error);
    } finally {
      setLoading(false);
    }
  }, [tab, search]);

  useEffect(() => {
    loadChatTypes();
  }, [loadChatTypes]);

  const handleDelete = async () => {
    if (!showDelete) return;
    setDeleting(true);
    try {
      await api.delete(`/chat-types/${showDelete}`);
      setToast({ message: 'Tipo de chat excluído', type: 'success' });
      setShowDelete(null);
      loadChatTypes();
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || 'Erro ao excluir', type: 'error' });
    } finally {
      setDeleting(false);
    }
  };

  const handleToggleFavorite = async (chatTypeId: string, isFavorited: boolean) => {
    try {
      if (isFavorited) {
        await api.delete(`/chat-types/${chatTypeId}/favorite`);
        setToast({ message: 'Removido dos favoritos', type: 'success' });
      } else {
        await api.post(`/chat-types/${chatTypeId}/favorite`);
        setToast({ message: 'Adicionado aos favoritos', type: 'success' });
      }
      loadChatTypes();
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || 'Erro ao favoritar', type: 'error' });
    }
  };

  const handleUpdate = async (data: { name: string; description?: string; tags: string[]; is_public: boolean }) => {
    if (!editingChatType) return;
    setUpdating(true);
    try {
      await api.patch(`/chat-types/${editingChatType.id}`, data);
      setToast({ message: 'Tipo de chat atualizado com sucesso', type: 'success' });
      setEditingChatType(null);
      loadChatTypes();
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || 'Erro ao atualizar', type: 'error' });
    } finally {
      setUpdating(false);
    }
  };

  const formatDate = (d: string) =>
    new Date(d).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });

  return (
    <DashboardLayout>
      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fade-in">
          <div>
            <h1 className="text-2xl font-extrabold text-gray-900 dark:text-white tracking-tight">Tipos de Chat</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Gerencie suas bases de conhecimento ({total} total)
            </p>
          </div>
          <Link href="/dashboard/upload">
            <Button icon={<Upload className="w-4 h-4" />}>
              Upload de Dados
            </Button>
          </Link>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-4 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => { setTab('my-types'); setSearch(''); }}
            className={`px-4 py-3 font-semibold text-sm transition-all duration-200 border-b-2 ${
              tab === 'my-types'
                ? 'text-brand-600 dark:text-brand-400 border-brand-600 dark:border-brand-400'
                : 'text-gray-600 dark:text-gray-400 border-transparent hover:text-gray-900 dark:hover:text-gray-300'
            }`}
          >
            Meus Tipos
          </button>
          <button
            onClick={() => { setTab('explore'); setSearch(''); }}
            className={`px-4 py-3 font-semibold text-sm transition-all duration-200 border-b-2 ${
              tab === 'explore'
                ? 'text-brand-600 dark:text-brand-400 border-brand-600 dark:border-brand-400'
                : 'text-gray-600 dark:text-gray-400 border-transparent hover:text-gray-900 dark:hover:text-gray-300'
            }`}
          >
            Explorar
          </button>
        </div>

        {/* Search and View Mode */}
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
          {tab === 'explore' && (
            <div className="flex-1 w-full sm:max-w-sm">
              <Input
                placeholder="Buscar tipos públicos..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                icon={<Search className="w-4 h-4" />}
              />
            </div>
          )}
          <div className="ml-auto flex items-center bg-gray-100 dark:bg-gray-800 rounded-xl p-0.5">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-lg transition-all duration-200 ${viewMode === 'grid' ? 'bg-white dark:bg-gray-700 shadow-sm' : 'text-gray-500'}`}
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-lg transition-all duration-200 ${viewMode === 'list' ? 'bg-white dark:bg-gray-700 shadow-sm' : 'text-gray-500'}`}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card p-5 space-y-3">
                <div className="h-5 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
            ))}
          </div>
        ) : chatTypes.length === 0 ? (
          <EmptyState
            icon={<MessageSquare className="w-8 h-8" />}
            title={search ? 'Nenhum resultado encontrado' : 'Nenhum tipo de chat'}
            description={search ? 'Tente outra busca' : 'Faça um upload de dados para criar seu primeiro tipo de chat'}
            action={!search ? <Link href="/dashboard/upload"><Button icon={<Upload className="w-4 h-4" />}>Upload de Dados</Button></Link> : undefined}
          />
        ) : viewMode === 'grid' ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 animate-slide-up" style={{ animationFillMode: 'both' }}>
            {chatTypes.map((ct) => {
              const isMentorIA = ct.owner_name === 'MentorIA';
              return (
              <Card key={ct.id} hover className={`h-full flex flex-col relative overflow-hidden ${isMentorIA ? 'ring-2 ring-brand-400/40 dark:ring-brand-400/30 border-brand-200 dark:border-brand-500/30 shadow-lg shadow-brand-500/15 dark:shadow-brand-500/10 animate-glow-pulse' : ''}`}>
                {isMentorIA && (
                  <>
                    <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-brand-500 via-violet-500 to-brand-500 bg-300% animate-gradient" />
                    <div className="absolute inset-0 overflow-hidden pointer-events-none">
                      <div className="absolute inset-0 -translate-x-full animate-shimmer-slide bg-gradient-to-r from-transparent via-white/5 to-transparent" style={{ animationDuration: '4s', animationIterationCount: 'infinite' }} />
                    </div>
                  </>
                )}
                <div className="p-5 flex-1 flex flex-col">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-gray-900 dark:text-white truncate">{ct.name}</h3>
                        {isMentorIA && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-gradient-to-r from-brand-500 via-violet-500 to-brand-600 text-white text-[10px] font-bold uppercase tracking-wider shrink-0 shadow-md shadow-brand-500/30 dark:shadow-brand-500/20">
                            <Sparkles className="w-3 h-3" />
                            Oficial
                          </span>
                        )}
                      </div>
                      {ct.description && (
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">{ct.description}</p>
                      )}
                      {ct.tags && ct.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {ct.tags.slice(0, 3).map((tag) => (
                            <span key={tag} className="inline-flex items-center px-2 py-1 rounded-md bg-brand-100 dark:bg-brand-500/20 text-brand-700 dark:text-brand-300 text-xs font-medium">
                              #{tag}
                            </span>
                          ))}
                          {ct.tags.length > 3 && (
                            <span 
                              className="inline-flex items-center px-2 py-1 rounded-md bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs font-medium cursor-help group/tags relative"
                              title={ct.tags.slice(3).join(', ')}
                            >
                              +{ct.tags.length - 3}
                              <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 hidden group-hover/tags:block z-50">
                                <div className="bg-gray-900 dark:bg-gray-800 text-white text-[10px] py-1 px-2 rounded shadow-lg whitespace-nowrap border border-transparent dark:border-gray-700">
                                  {ct.tags.slice(3).join(', ')}
                                </div>
                                <div className="w-2 h-2 bg-gray-900 dark:bg-gray-800 rotate-45 -mt-1 mx-auto border-r border-b border-transparent dark:border-gray-700"></div>
                              </div>
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    <Badge variant={ct.is_public ? 'success' : 'default'} dot>
                      {ct.is_public ? 'Público' : 'Privado'}
                    </Badge>
                  </div>
                  {isMentorIA ? (
                    <div className="flex items-center gap-2 mb-3 px-2.5 py-1.5 rounded-lg bg-gradient-to-r from-brand-50/80 to-violet-50/80 dark:from-brand-500/10 dark:to-violet-500/10 border border-brand-200/60 dark:border-brand-500/15">
                      <Shield className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400 shrink-0" />
                      <p className="text-[11px] text-brand-700 dark:text-brand-300 font-medium">Conteúdo revisado e verificado pelo MentorIA</p>
                    </div>
                  ) : (
                    <div className="h-[34px] mb-3" aria-hidden="true" />
                  )}
                  <div className="flex items-center gap-4 text-xs text-gray-400 dark:text-gray-500 mt-auto">
                    {ct.owner_name && (
                      <span className={`flex items-center gap-1 ${isMentorIA ? 'text-brand-500 dark:text-brand-400 font-semibold' : ''}`}>
                        {isMentorIA ? <Sparkles className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
                        {ct.owner_name}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      {formatDate(ct.created_at)}
                    </span>
                  </div>
                </div>
                <div className={`px-5 py-3 border-t flex items-center justify-between ${isMentorIA ? 'border-brand-200/50 dark:border-brand-500/15 bg-gradient-to-r from-brand-50/50 to-violet-50/50 dark:from-brand-500/5 dark:to-violet-500/5' : 'border-gray-100 dark:border-gray-800'}`}>
                  <Link
                    href={`/dashboard/chats?chat_type_id=${ct.id}`}
                    className="text-sm text-brand-600 dark:text-brand-400 font-semibold hover:text-brand-700 dark:hover:text-brand-300 transition-colors"
                  >
                    Ver Chats
                  </Link>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleToggleFavorite(ct.id, ct.is_favorited || false); }}
                      className={`p-1.5 rounded-xl transition-all duration-200 ${
                        ct.is_favorited
                          ? 'text-yellow-500 hover:text-yellow-600 bg-yellow-50 dark:bg-yellow-500/10'
                          : 'text-gray-400 hover:text-yellow-500 hover:bg-yellow-50 dark:hover:bg-yellow-500/10'
                      }`}
                      title={ct.is_favorited ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
                    >
                      <Star className={`w-4 h-4 ${ct.is_favorited ? 'fill-current' : ''}`} />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setEditingChatType(ct); }}
                      className="p-1.5 rounded-xl text-gray-400 hover:text-brand-500 hover:bg-brand-50 dark:hover:bg-brand-500/10 transition-all duration-200"
                      title="Editar tipo de chat"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setShowDelete(ct.id); }}
                      className="p-1.5 rounded-xl text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all duration-200"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </Card>
              );
            })}
          </div>
        ) : (
          <div className="card overflow-hidden animate-slide-up" style={{ animationFillMode: 'both' }}>
            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              {chatTypes.map((ct) => {
                const isMentorIA = ct.owner_name === 'MentorIA';
                return (
                <div key={ct.id} className={`flex items-center justify-between px-5 py-4 transition-all duration-200 group ${isMentorIA ? 'bg-gradient-to-r from-brand-50/50 via-violet-50/30 to-brand-50/50 dark:from-brand-500/5 dark:via-violet-500/5 dark:to-brand-500/5 hover:from-brand-50/80 hover:via-violet-50/50 hover:to-brand-50/80 dark:hover:from-brand-500/10 dark:hover:via-violet-500/10 dark:hover:to-brand-500/10 shadow-sm shadow-brand-500/5' : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}`}>
                  <div className="flex items-center gap-4 min-w-0 flex-1">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                      isMentorIA
                        ? 'bg-gradient-to-br from-brand-500 via-violet-500 to-brand-600 text-white shadow-md shadow-brand-500/30'
                        : ct.is_public
                          ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400'
                          : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                    }`}>
                      {isMentorIA ? <Sparkles className="w-5 h-5" /> : ct.is_public ? <Globe className="w-5 h-5" /> : <Lock className="w-5 h-5" />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-gray-900 dark:text-white truncate group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">{ct.name}</h3>
                        {isMentorIA && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-gradient-to-r from-brand-500 via-violet-500 to-brand-600 text-white text-[9px] font-bold uppercase tracking-wider shrink-0 shadow-sm shadow-brand-500/25">
                            <Sparkles className="w-2.5 h-2.5" />
                            Oficial
                          </span>
                        )}
                      </div>
                      {ct.description && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">{ct.description}</p>
                      )}
                      {ct.tags && ct.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {ct.tags.slice(0, 2).map((tag) => (
                            <span key={tag} className="inline-flex items-center px-1.5 py-0.5 rounded text-brand-700 dark:text-brand-300 text-[10px] font-medium bg-brand-100 dark:bg-brand-500/20">
                              #{tag}
                            </span>
                          ))}
                          {ct.tags.length > 2 && (
                            <span 
                              className="inline-flex items-center px-1.5 py-0.5 rounded text-gray-600 dark:text-gray-400 text-[10px] font-medium bg-gray-100 dark:bg-gray-700 cursor-help group/tags relative"
                              title={ct.tags.slice(2).join(', ')}
                            >
                              +{ct.tags.length - 2}
                              <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 hidden group-hover/tags:block z-50">
                                <div className="bg-gray-900 dark:bg-gray-800 text-white text-[9px] py-1 px-1.5 rounded shadow-lg whitespace-nowrap border border-transparent dark:border-gray-700">
                                  {ct.tags.slice(2).join(', ')}
                                </div>
                                <div className="w-1.5 h-1.5 bg-gray-900 dark:bg-gray-800 rotate-45 -mt-0.5 mx-auto border-r border-b border-transparent dark:border-gray-700"></div>
                              </div>
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 ml-4 shrink-0">
                    <span className="text-xs text-gray-400">{formatDate(ct.created_at)}</span>
                    <Link
                      href={`/dashboard/chats?chat_type_id=${ct.id}`}
                      className="text-xs text-brand-600 dark:text-brand-400 font-semibold hover:text-brand-700 dark:hover:text-brand-300 transition-colors"
                    >
                      Chats
                    </Link>
                    <button
                      onClick={() => handleToggleFavorite(ct.id, ct.is_favorited || false)}
                      className={`p-1.5 rounded-xl transition-all duration-200 ${
                        ct.is_favorited
                          ? 'text-yellow-500 hover:text-yellow-600 bg-yellow-50 dark:bg-yellow-500/10'
                          : 'text-gray-400 hover:text-yellow-500 hover:bg-yellow-50 dark:hover:bg-yellow-500/10'
                      }`}
                      title={ct.is_favorited ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
                    >
                      <Star className={`w-4 h-4 ${ct.is_favorited ? 'fill-current' : ''}`} />
                    </button>
                    <button
                      onClick={() => setEditingChatType(ct)}
                      className="p-1.5 rounded-xl text-gray-400 hover:text-brand-500 hover:bg-brand-50 dark:hover:bg-brand-500/10 transition-all duration-200"
                      title="Editar"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setShowDelete(ct.id)}
                      className="p-1.5 rounded-xl text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all duration-200"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Edit Modal */}
      <ChatTypeEditModal
        open={!!editingChatType}
        onClose={() => setEditingChatType(null)}
        chatType={editingChatType || undefined}
        onSave={handleUpdate}
        loading={updating}
      />

      {/* Delete Confirmation */}
      <Modal
        open={!!showDelete}
        onClose={() => setShowDelete(null)}
        title="Excluir Tipo de Chat"
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowDelete(null)}>Cancelar</Button>
            <Button variant="danger" onClick={handleDelete} loading={deleting}>Excluir</Button>
          </>
        }
      >
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Tem certeza que deseja excluir este tipo de chat? Todos os dados associados serão removidos permanentemente.
        </p>
      </Modal>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </DashboardLayout>
  );
}
