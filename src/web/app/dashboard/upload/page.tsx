'use client';

import { useState, useEffect, useRef } from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import Sidebar from '@/components/Sidebar';
import Toast from '@/components/Toast';
import { authService } from '@/lib/auth';
import api from '@/lib/api';

interface Job {
  id: number;
  status: string;
  file_name: string;
  created_at: string;
}

export default function UploadPage() {
  const [user, setUser] = useState<any>(null);
  const [chatTypeName, setChatTypeName] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const userData = authService.getUser();
    if (userData) setUser(userData);
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      setLoadingJobs(true);
      const res = await api.get('/jobs');
      setJobs(res.data);
    } catch {
      // Jobs may not exist yet
    } finally {
      setLoadingJobs(false);
    }
  };

  const handleUpload = async () => {
    if (!file || !chatTypeName.trim()) {
      setToast({ message: 'Preencha o nome e selecione um arquivo', type: 'error' });
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('name', chatTypeName.trim());

      await api.post('/upload/chat-type', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setToast({ message: 'Upload realizado com sucesso!', type: 'success' });
      setChatTypeName('');
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      loadJobs();
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || 'Erro ao fazer upload', type: 'error' });
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) setFile(droppedFile);
  };

  const statusColors: Record<string, string> = {
    completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400',
    processing: 'bg-brand-100 text-brand-700 dark:bg-brand-500/10 dark:text-brand-400',
    pending: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
    failed: 'bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400',
  };

  const statusLabels: Record<string, string> = {
    completed: 'Concluído',
    processing: 'Processando',
    pending: 'Pendente',
    failed: 'Falhou',
  };

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
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Upload de Dados</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Envie documentos para a base de conhecimento</p>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto p-6 space-y-6">
            {/* Upload Form */}
            <div className="card p-6 space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Nome do Tipo de Chat</label>
                <input
                  type="text"
                  value={chatTypeName}
                  onChange={(e) => setChatTypeName(e.target.value)}
                  placeholder="Ex: ENEM 2024, Matemática, História..."
                  className="input-field"
                />
              </div>

              {/* Drop Zone */}
              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                  dragOver
                    ? 'border-brand-500 bg-brand-50 dark:bg-brand-500/5'
                    : 'border-gray-300 dark:border-gray-700 hover:border-brand-400 dark:hover:border-brand-500/50'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  accept=".pdf,.txt,.md,.csv,.json,.docx"
                  className="hidden"
                />
                <div className="w-12 h-12 rounded-xl bg-brand-50 dark:bg-brand-500/10 flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-brand-600 dark:text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                  </svg>
                </div>
                {file ? (
                  <>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{file.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{(file.size / 1024).toFixed(1)} KB</p>
                  </>
                ) : (
                  <>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">Arraste um arquivo ou clique para selecionar</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">PDF, TXT, MD, CSV, JSON, DOCX</p>
                  </>
                )}
              </div>

              <button
                onClick={handleUpload}
                disabled={uploading || !file || !chatTypeName.trim()}
                className="btn-primary flex items-center justify-center gap-2 !w-auto px-6"
              >
                {uploading && (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                )}
                {uploading ? 'Enviando...' : 'Enviar Arquivo'}
              </button>
            </div>

            {/* Jobs History */}
            <div className="card overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
                <h2 className="text-base font-semibold text-gray-900 dark:text-white">Histórico de Uploads</h2>
              </div>
              {loadingJobs ? (
                <div className="flex items-center justify-center py-12">
                  <svg className="w-5 h-5 animate-spin text-brand-600 dark:text-brand-400" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                </div>
              ) : jobs.length === 0 ? (
                <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  Nenhum upload realizado ainda
                </div>
              ) : (
                <div className="divide-y divide-gray-100 dark:divide-gray-800">
                  {jobs.map((job) => (
                    <div key={job.id} className="px-6 py-4 flex items-center justify-between">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">{job.file_name || `Job #${job.id}`}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          {new Date(job.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })}
                        </p>
                      </div>
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[job.status] || 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'}`}>
                        {statusLabels[job.status] || job.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      </div>
    </ProtectedRoute>
  );
}
