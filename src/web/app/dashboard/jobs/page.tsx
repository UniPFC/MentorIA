'use client';

import { useState, useEffect, useCallback } from 'react';
import { Briefcase, FileSpreadsheet, RefreshCw, Trash2, CheckCircle, Clock, AlertCircle, Loader2 } from 'lucide-react';
import DashboardLayout from '@/components/DashboardLayout';
import { Badge, EmptyState } from '@/components/ui';
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

export default function JobsPage() {
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const loadJobs = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/upload/jobs/');
      setJobs(Array.isArray(res.data) ? res.data : []);
    } catch {
      setJobs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadJobs(); }, [loadJobs]);

  useEffect(() => {
    const hasActive = jobs.some((j) => j.status === 'pending' || j.status === 'processing');
    if (!hasActive) return;
    const interval = setInterval(loadJobs, 5000);
    return () => clearInterval(interval);
  }, [jobs, loadJobs]);

  const handleDelete = async (jobId: string) => {
    try {
      await api.delete(`/upload/jobs/${jobId}`);
      setToast({ message: 'Job removido', type: 'success' });
      loadJobs();
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || 'Erro ao remover upload', type: 'error' });
    }
  };

  const statusConfig: Record<string, { label: string; variant: 'success' | 'info' | 'warning' | 'danger'; icon: any }> = {
    completed: { label: 'Concluído', variant: 'success', icon: CheckCircle },
    processing: { label: 'Processando', variant: 'info', icon: Loader2 },
    pending: { label: 'Pendente', variant: 'warning', icon: Clock },
    failed: { label: 'Falhou', variant: 'danger', icon: AlertCircle },
  };

  const formatDate = (d: string) =>
    new Date(d).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });

  const summary = {
    total: jobs.length,
    completed: jobs.filter((j) => j.status === 'completed').length,
    processing: jobs.filter((j) => j.status === 'processing' || j.status === 'pending').length,
    failed: jobs.filter((j) => j.status === 'failed').length,
  };

  return (
    <DashboardLayout>
      <div className="flex-1 overflow-auto p-6 space-y-6">
        <div className="flex items-center justify-between animate-fade-in">
          <div>
            <h1 className="text-2xl font-extrabold text-gray-900 dark:text-white tracking-tight">Histórico de Uploads</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Acompanhe o processamento dos seus arquivos enviados
            </p>
          </div>
          <button
            onClick={loadJobs}
            className="p-2.5 rounded-xl text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:bg-gray-800 transition-all duration-200 active:scale-[0.95]"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 animate-slide-up" style={{ animationDelay: '0.1s', animationFillMode: 'both' }}>
          {[
            { label: 'Total', value: summary.total, color: 'text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-800' },
            { label: 'Concluídos', value: summary.completed, color: 'text-emerald-600 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-500/10' },
            { label: 'Em progresso', value: summary.processing, color: 'text-brand-600 bg-brand-50 dark:text-brand-400 dark:bg-brand-500/10' },
            { label: 'Falharam', value: summary.failed, color: 'text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-500/10' },
          ].map((s) => (
            <div key={s.label} className={`rounded-2xl p-4 ${s.color} transition-all duration-300 hover:shadow-sm`}>
              <p className="text-2xl font-extrabold">{s.value}</p>
              <p className="text-xs mt-0.5 opacity-70">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Jobs List */}
        {loading ? (
          <div className="card overflow-hidden divide-y divide-gray-100 dark:divide-gray-800 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="px-6 py-4 flex items-center gap-3">
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
            icon={<Briefcase className="w-8 h-8" />}
            title="Nenhum upload encontrado"
            description="Faça upload de um arquivo na página de Upload para iniciar o processamento"
          />
        ) : (
          <div className="card overflow-hidden divide-y divide-gray-100 dark:divide-gray-800">
            {jobs.map((job) => {
              const config = statusConfig[job.status] || statusConfig.pending;
              const StatusIcon = config.icon;
              const progress = job.total_chunks > 0 ? Math.round((job.processed_chunks / job.total_chunks) * 100) : 0;

              return (
                <div key={job.id} className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                        job.status === 'completed' ? 'bg-emerald-50 dark:bg-emerald-500/10' :
                        job.status === 'failed' ? 'bg-red-50 dark:bg-red-500/10' :
                        'bg-brand-50 dark:bg-brand-500/10'
                      }`}>
                        <StatusIcon className={`w-5 h-5 ${
                          job.status === 'completed' ? 'text-emerald-600 dark:text-emerald-400' :
                          job.status === 'failed' ? 'text-red-600 dark:text-red-400' :
                          job.status === 'processing' ? 'text-brand-600 dark:text-brand-400 animate-spin' :
                          'text-amber-600 dark:text-amber-400'
                        }`} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{job.filename}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          {formatDate(job.created_at)}
                          {job.total_chunks > 0 && ` · ${job.processed_chunks}/${job.total_chunks} chunks`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0 ml-4">
                      <Badge variant={config.variant} dot>{config.label}</Badge>
                      {(job.status === 'completed' || job.status === 'failed') && (
                        <button
                          onClick={() => handleDelete(job.id)}
                          className="p-1.5 rounded-xl text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all duration-200"
                          title="Remover"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  {(job.status === 'processing' || job.status === 'completed') && job.total_chunks > 0 && (
                    <div className="mt-3 ml-13">
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
                    <p className="mt-2 ml-13 text-xs text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-500/5 rounded-lg px-3 py-2">
                      {job.error_message}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </DashboardLayout>
  );
}
