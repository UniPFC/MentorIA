'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Upload, FileSpreadsheet, X, RefreshCw, ChevronDown } from 'lucide-react';
import DashboardLayout from '@/components/DashboardLayout';
import { Button, Input, Badge, EmptyState } from '@/components/ui';
import { PageSpinner } from '@/components/ui/Spinner';
import Toast from '@/components/Toast';
import api from '@/lib/api';

interface IngestionJob {
  id: string;
  chat_type_id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_chunks: number;
  processed_chunks: number;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export default function UploadPage() {
  const [chatTypeName, setChatTypeName] = useState('');
  const [description, setDescription] = useState('');
  const [isPublic, setIsPublic] = useState(false);
  const [questionColumn, setQuestionColumn] = useState('question');
  const [answerColumn, setAnswerColumn] = useState('answer');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [dragOver, setDragOver] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadJobs = useCallback(async () => {
    try {
      setLoadingJobs(true);
      const res = await api.get('/upload/jobs/');
      setJobs(Array.isArray(res.data) ? res.data : []);
    } catch {
      setJobs([]);
    } finally {
      setLoadingJobs(false);
    }
  }, []);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  // Poll active jobs and show toast on failure
  useEffect(() => {
    const hasActive = jobs.some((j) => j.status === 'pending' || j.status === 'processing');
    if (!hasActive) return;
    
    const interval = setInterval(() => {
      loadJobs().then(() => {
        // Check for newly failed jobs
        jobs.forEach((job) => {
          if (job.status === 'failed' && job.error_message) {
            setToast({ 
              message: `Upload falhou: ${job.error_message}`, 
              type: 'error' 
            });
          }
        });
      });
    }, 5000);
    
    return () => clearInterval(interval);
  }, [jobs, loadJobs]);

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
      if (description.trim()) formData.append('description', description.trim());
      formData.append('is_public', String(isPublic));
      formData.append('question_column', questionColumn.trim());
      formData.append('answer_column', answerColumn.trim());

      await api.post('/upload/chat-type', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setToast({ message: 'Upload enviado para processamento!', type: 'success' });
      setChatTypeName('');
      setDescription('');
      setIsPublic(false);
      setQuestionColumn('question');
      setAnswerColumn('answer');
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

  const handleDeleteJob = async (jobId: string) => {
    try {
      await api.delete(`/upload/jobs/${jobId}`);
      loadJobs();
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || 'Erro ao excluir upload', type: 'error' });
    }
  };

  const statusConfig: Record<string, { label: string; variant: 'success' | 'info' | 'warning' | 'danger' }> = {
    completed: { label: 'Concluído', variant: 'success' },
    processing: { label: 'Processando', variant: 'info' },
    pending: { label: 'Pendente', variant: 'warning' },
    failed: { label: 'Falhou', variant: 'danger' },
  };

  const formatDate = (d: string) =>
    new Date(d).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <DashboardLayout>
      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-extrabold text-gray-900 dark:text-white tracking-tight">Upload de Dados</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Envie planilhas Excel ou CSV com colunas de pergunta e resposta
          </p>
        </div>

        {/* Upload Form */}
        <div className="card p-6 space-y-5 animate-slide-up" style={{ animationDelay: '0.1s', animationFillMode: 'both' }}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Nome do Tipo de Chat"
              value={chatTypeName}
              onChange={(e) => setChatTypeName(e.target.value)}
              placeholder="Ex: Matemática ENEM 2024"
              required
            />
            <Input
              label="Descrição (opcional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Descrição da base de conhecimento"
            />
          </div>

          {/* Advanced Options Section */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
            >
              <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                Opções Avançadas
              </span>
              <ChevronDown
                className={`w-4 h-4 text-gray-500 transition-transform duration-300 ${
                  showAdvanced ? 'rotate-180' : ''
                }`}
              />
            </button>

            {showAdvanced && (
              <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-4 space-y-4 bg-gray-50/50 dark:bg-gray-800/30">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Coluna de Perguntas
                    </label>
                    <Input
                      value={questionColumn}
                      onChange={(e) => setQuestionColumn(e.target.value)}
                      placeholder="question"
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Nome exato da coluna que contém as perguntas
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Coluna de Respostas
                    </label>
                    <Input
                      value={answerColumn}
                      onChange={(e) => setAnswerColumn(e.target.value)}
                      placeholder="answer"
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Nome exato da coluna que contém as respostas
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                  <input
                    type="checkbox"
                    id="is-public"
                    checked={isPublic}
                    onChange={(e) => setIsPublic(e.target.checked)}
                    className="w-4 h-4 text-brand-600 bg-gray-100 border-gray-300 rounded focus:ring-brand-500 dark:focus:ring-brand-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                  />
                  <label htmlFor="is-public" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Tornar público (outros usuários poderão usar este tipo de chat)
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* Drop Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 ${
              dragOver
                ? 'border-brand-500 bg-brand-50 dark:bg-brand-500/5 scale-[1.01] shadow-lg shadow-brand-500/10'
                : file
                  ? 'border-emerald-300 bg-emerald-50/50 dark:border-emerald-600 dark:bg-emerald-500/5'
                  : 'border-gray-300 dark:border-gray-700 hover:border-brand-400 dark:hover:border-brand-500/50 hover:shadow-sm'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              accept=".xlsx,.xls,.csv"
              className="hidden"
            />
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-emerald-100 dark:bg-emerald-500/10 flex items-center justify-center">
                  <FileSpreadsheet className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{file.name}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{formatFileSize(file.size)}</p>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <>
                <div className="w-12 h-12 rounded-xl bg-brand-50 dark:bg-brand-500/10 flex items-center justify-center mx-auto mb-3">
                  <Upload className="w-6 h-6 text-brand-600 dark:text-brand-400" />
                </div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  Arraste um arquivo ou clique para selecionar
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Excel (.xlsx, .xls) ou CSV
                </p>
              </>
            )}
          </div>

          <div className="flex justify-end">
            <Button
              onClick={handleUpload}
              loading={uploading}
              disabled={!file || !chatTypeName.trim()}
              icon={<Upload className="w-4 h-4" />}
            >
              {uploading ? 'Enviando...' : 'Enviar Arquivo'}
            </Button>
          </div>
        </div>

        {/* Jobs History */}
        <div className="card overflow-hidden animate-slide-up" style={{ animationDelay: '0.2s', animationFillMode: 'both' }}>
          <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
            <h2 className="text-base font-bold text-gray-900 dark:text-white">Uploads Recentes</h2>
            <button
              onClick={loadJobs}
              className="p-2 rounded-xl text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:text-gray-300 dark:hover:bg-gray-800 transition-all duration-200 active:scale-[0.95]"
              title="Atualizar"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {loadingJobs ? (
            <div className="py-6 space-y-3 animate-pulse">
              {[1, 2].map((i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-3">
                  <div className="w-10 h-10 rounded-lg bg-gray-200 dark:bg-gray-700" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-40 bg-gray-200 dark:bg-gray-700 rounded" />
                    <div className="h-3 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
                  </div>
                </div>
              ))}
            </div>
          ) : jobs.length === 0 ? (
            <EmptyState
              icon={<FileSpreadsheet className="w-8 h-8" />}
              title="Nenhum upload encontrado"
              description="Faça upload de um arquivo para iniciar o processamento"
            />
          ) : (
            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              {jobs.map((job) => {
                const config = statusConfig[job.status] || statusConfig.pending;
                const progress = job.total_chunks > 0
                  ? Math.round((job.processed_chunks / job.total_chunks) * 100)
                  : 0;

                return (
                  <div key={job.id} className="px-6 py-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <FileSpreadsheet className="w-5 h-5 text-gray-400 shrink-0" />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{job.filename}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{formatDate(job.created_at)}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0 ml-4">
                        <Badge variant={config.variant} dot>{config.label}</Badge>
                        {(job.status === 'completed' || job.status === 'failed') && (
                          <button
                            onClick={() => handleDeleteJob(job.id)}
                            className="p-1 rounded text-gray-400 hover:text-red-500 transition-colors"
                            title="Remover"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>

                    {(job.status === 'processing' || job.status === 'completed') && job.total_chunks > 0 && (
                      <div className="mt-2">
                        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
                          <span>{job.processed_chunks}/{job.total_chunks} linhas</span>
                          <span>{progress}%</span>
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full transition-all duration-500 ${
                              job.status === 'completed' ? 'bg-emerald-500' : 'bg-brand-500'
                            }`}
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {job.error_message && (
                      <div className="mt-3 p-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30">
                        <p className="text-xs font-medium text-red-700 dark:text-red-400">
                          <span className="font-bold">Erro:</span> {job.error_message}
                        </p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </DashboardLayout>
  );
}
