'use client';

import { useState, useEffect } from 'react';
import { Crown, Zap, Check, ArrowRight, RefreshCw, AlertCircle, Sparkles, Shield, TrendingUp } from 'lucide-react';
import DashboardLayout from '@/components/DashboardLayout';
import Toast from '@/components/Toast';
import BudgetProgressBar from '@/components/BudgetProgressBar';
import api from '@/lib/api';

const PLANS = [
  {
    level: 'LEVEL_02',
    name: 'Lite',
    price: 'R$ 39',
    period: '/mês',
    tokens: 1000000,
    tokensLabel: '1.000.000',
    description: 'Para uma rotina leve de estudos',
    color: 'brand',
    gradient: 'from-brand-500 to-brand-600',
    bgGradient: 'from-brand-50 to-brand-100/50 dark:from-brand-900/20 dark:to-brand-900/10',
    borderColor: 'border-brand-200/60 dark:border-brand-700/30',
    features: ['1.000.000 créditos por mês', 'Modelos essenciais de IA', 'Bom para dúvidas e revisões pontuais'],
  },
  {
    level: 'LEVEL_03',
    name: 'Plus',
    price: 'R$ 79',
    period: '/mês',
    tokens: 8000000,
    tokensLabel: '8.000.000',
    description: 'Para estudar com mais constância',
    color: 'brand',
    gradient: 'from-brand-600 to-brand-700',
    bgGradient: 'from-brand-50 to-indigo-50 dark:from-brand-900/30 dark:to-indigo-900/10',
    borderColor: 'border-brand-300/60 dark:border-brand-600/30',
    popular: true,
    features: ['8.000.000 créditos por mês', 'Acesso a todos os modelos de IA', 'Mais flexibilidade para estudos diários', 'Suporte prioritário'],
  },
  {
    level: 'LEVEL_04',
    name: 'Max',
    price: 'R$ 199',
    period: '/mês',
    tokens: 18000000,
    tokensLabel: '18.000.000',
    description: 'Para quem usa com frequência alta',
    color: 'brand',
    gradient: 'from-brand-700 to-brand-800',
    bgGradient: 'from-indigo-50 to-purple-50 dark:from-brand-900/40 dark:to-purple-900/10',
    borderColor: 'border-brand-400/60 dark:border-brand-500/30',
    features: ['18.000.000 créditos por mês', 'Acesso a todos os modelos de IA', 'Suporte prioritário', 'Mais espaço para uso avançado'],
  },
];

export default function PlansPage() {
  const [user, setUser] = useState<any>(null);
  const [subscription, setSubscription] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [refilling, setRefilling] = useState(false);
  const [skipPayment, setSkipPayment] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [userRes, subRes] = await Promise.all([
        api.get('/auth/me'),
        api.get('/payments/subscription'),
      ]);
      setUser(userRes.data);
      setSubscription(subRes.data);
    } catch {
      setToast({ message: 'Erro ao carregar dados', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (targetLevel: string) => {
    setUpgrading(targetLevel);
    try {
      const res = await api.post('/payments/subscribe', {
        target_level: targetLevel,
        skip_payment: skipPayment,
      });
      const data = res.data;

      if (data.checkout_url) {
        window.location.href = data.checkout_url;
        return;
      }

      setToast({ message: 'Plano atualizado com sucesso!', type: 'success' });
      await loadData();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Erro ao processar upgrade';
      setToast({ message: msg, type: 'error' });
    } finally {
      setUpgrading(null);
    }
  };

  const handleRefill = async () => {
    setRefilling(true);
    try {
      const res = await api.post('/payments/refill', {
        skip_payment: skipPayment,
      });
      const data = res.data;

      if (data.checkout_url) {
        window.location.href = data.checkout_url;
        return;
      }

      setToast({ message: `Créditos recarregados! +${data.amount_refilled?.toLocaleString()} créditos`, type: 'success' });
      await loadData();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Erro ao recarregar créditos';
      setToast({ message: msg, type: 'error' });
    } finally {
      setRefilling(false);
    }
  };

  const getLevelOrder = (level: string) => {
    const order: Record<string, number> = { LEVEL_01: 1, LEVEL_02: 2, LEVEL_03: 3, LEVEL_04: 4, LEVEL_05: 5 };
    return order[level] || 1;
  };

  const isCurrentPlan = (planLevel: string) => user?.level === planLevel;
  const canUpgrade = (planLevel: string) => {
    if (user?.level === 'LEVEL_05') return false;
    return getLevelOrder(planLevel) > getLevelOrder(user?.level || 'LEVEL_01');
  };

  const isUnlimited = user?.level === 'LEVEL_05';
  const percentage = isUnlimited
    ? 100
    : user?.max_token_budget && user?.max_token_budget > 0
    ? (user.token_budget / user.max_token_budget) * 100
    : 0;

  const currentPlan = PLANS.find(p => p.level === user?.level);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const getLevelLabel = (level: string) => {
    const labels: Record<string, string> = {
      'LEVEL_01': 'Gratuito',
      'LEVEL_02': 'Lite',
      'LEVEL_03': 'Plus',
      'LEVEL_04': 'Max',
      'LEVEL_05': 'Admin',
    };
    return labels[level] || level;
  };

  const subscriptionStatusLabel = (status: string | null) => {
    const labels: Record<string, string> = {
      active: 'Ativa',
      canceled: 'Cancelada',
      past_due: 'Pagamento Pendente',
      unpaid: 'Não Paga',
      ended: 'Encerrada',
    };
    return status ? (labels[status] || status) : null;
  };

  const subscriptionStatusColor = (status: string | null) => {
    if (status === 'active') return 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20';
    if (status === 'canceled' || status === 'ended') return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-500/10 border-gray-200 dark:border-gray-500/20';
    return 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/20';
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex-1 overflow-auto p-6 space-y-6 animate-pulse">
          <div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-80 bg-gray-200 dark:bg-gray-700 rounded-2xl" />
            ))}
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="flex-1 overflow-auto p-6 space-y-8">
        {/* Header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-extrabold text-gray-900 dark:text-white tracking-tight">Planos e Créditos</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Escolha o plano ideal e gerencie seus créditos</p>
        </div>

        {/* Current Status Card */}
        <div className="card overflow-hidden animate-slide-up" style={{ animationDelay: '0.05s', animationFillMode: 'both' }}>
          <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-800 flex items-center gap-3">
            <Crown className="w-5 h-5 text-brand-500" />
            <h2 className="text-base font-bold text-gray-900 dark:text-white">Status Atual</h2>
          </div>
          <div className="p-6">
            <div className="flex flex-col sm:flex-row gap-6">
              {/* Plan */}
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${currentPlan?.gradient || 'from-gray-400 to-gray-500'} text-white flex items-center justify-center shadow-lg flex-shrink-0`}>
                  <Crown className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wide">Plano</p>
                  <div className="flex items-center gap-2">
                    <p className="text-lg font-bold text-gray-900 dark:text-white">{currentPlan?.name || getLevelLabel(user?.level)}</p>
                    {subscription?.has_subscription && (
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${subscriptionStatusColor(subscription.status)}`}>
                        {subscriptionStatusLabel(subscription.status)}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Period start */}
              {subscription?.period_start && (
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-500 text-white flex items-center justify-center shadow-lg flex-shrink-0">
                    <TrendingUp className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wide">Início</p>
                    <p className="text-sm font-bold text-gray-900 dark:text-white">{formatDate(subscription.period_start)}</p>
                  </div>
                </div>
              )}

              {/* Period end */}
              {subscription?.period_end && (
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-400 to-amber-500 text-white flex items-center justify-center shadow-lg flex-shrink-0">
                    <Shield className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wide">
                      {subscription.status === 'canceled' ? 'Ativo até' : 'Próxima cobrança'}
                    </p>
                    <p className="text-sm font-bold text-gray-900 dark:text-white">{formatDate(subscription.period_end)}</p>
                  </div>
                </div>
              )}

              {/* Budget */}
              <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-brand-400 to-brand-500 text-white flex items-center justify-center shadow-lg flex-shrink-0">
                  <Zap className="w-6 h-6" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wide">Créditos</p>
                  <BudgetProgressBar current={isUnlimited ? 10000 : (user?.token_budget || 0)} max={isUnlimited ? 10000 : (user?.max_token_budget || 10000)} showLabel={true} isAdmin={isUnlimited} />
                </div>
              </div>
            </div>

            {/* Refill section */}
            {user?.level !== 'LEVEL_05' && percentage < 100 && (
              <div className="mt-6 pt-6 border-t border-gray-100 dark:border-gray-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">Recarregar créditos</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    Adicione mais {((user?.max_token_budget || 0) - (user?.token_budget || 0)).toLocaleString()} créditos ao seu saldo atual
                  </p>
                </div>
                <button
                  onClick={handleRefill}
                  disabled={refilling}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-brand-500 to-brand-600 text-white text-sm font-semibold hover:from-brand-600 hover:to-brand-700 transition-all duration-200 active:scale-95 disabled:opacity-60 disabled:pointer-events-none shadow-lg shadow-brand-500/20 flex-shrink-0"
                >
                  {refilling ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Zap className="w-4 h-4" />
                  )}
                  {refilling ? 'Processando...' : 'Recarregar'}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Plans Grid */}
        <div className="animate-slide-up" style={{ animationDelay: '0.1s', animationFillMode: 'both' }}>
          <h2 className="text-base font-bold text-gray-900 dark:text-white mb-4">Planos Disponíveis</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {PLANS.map((plan) => {
              const isCurrent = isCurrentPlan(plan.level);
              const upgradeable = canUpgrade(plan.level);

              return (
                <div
                  key={plan.level}
                  className={`relative rounded-2xl border overflow-hidden flex flex-col transition-all duration-300 ${
                    isCurrent
                      ? `${plan.borderColor} shadow-lg ring-2 ring-brand-500/30`
                      : `border-gray-200/60 dark:border-gray-700/40 hover:border-brand-300/60 dark:hover:border-brand-600/40 hover:shadow-lg`
                  }`}
                >
                  {/* Popular badge */}
                  {plan.popular && !isCurrent && (
                    <div className="absolute top-3 right-3 flex items-center gap-1 px-2 py-0.5 bg-brand-500 text-white text-[10px] font-bold rounded-full">
                      <Sparkles className="w-2.5 h-2.5" />
                      Mais escolhido
                    </div>
                  )}

                  {/* Current badge */}
                  {isCurrent && (
                    <div className="absolute top-3 right-3 flex items-center gap-1 px-2 py-0.5 bg-emerald-500 text-white text-[10px] font-bold rounded-full">
                      <Check className="w-2.5 h-2.5" />
                      Atual
                    </div>
                  )}

                  {/* Header */}
                  <div className={`bg-gradient-to-br ${plan.bgGradient} px-5 py-5 border-b border-gray-200/40 dark:border-gray-700/30`}>
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${plan.gradient} flex items-center justify-center shadow-lg mb-3`}>
                      <Crown className="w-5 h-5 text-white" />
                    </div>
                    <h3 className="text-base font-bold text-gray-900 dark:text-white">{plan.name}</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{plan.description}</p>
                    <div className="mt-3 flex items-baseline gap-1">
                      <span className="text-2xl font-extrabold text-gray-900 dark:text-white">{plan.price}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">{plan.period}</span>
                    </div>
                  </div>

                  {/* Features */}
                  <div className="p-5 flex flex-col flex-1 gap-4 bg-white dark:bg-gray-900">
                    <div className="flex items-center gap-2 p-2.5 rounded-xl bg-brand-50 dark:bg-brand-500/10 border border-brand-200/50 dark:border-brand-500/20">
                      <Zap className="w-4 h-4 text-brand-500 flex-shrink-0" />
                      <span className="text-xs font-bold text-brand-700 dark:text-brand-300">{plan.tokensLabel} créditos/mês</span>
                    </div>
                    <ul className="space-y-2 flex-1">
                      {plan.features.map((feature, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <Check className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                          <span className="text-xs text-gray-600 dark:text-gray-400">{feature}</span>
                        </li>
                      ))}
                    </ul>

                    {/* CTA */}
                    <div className="mt-auto">
                      {isCurrent ? (
                        <div className="w-full py-2 px-4 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 text-xs font-semibold text-center">
                          Plano atual
                        </div>
                      ) : upgradeable ? (
                        <button
                          onClick={() => handleUpgrade(plan.level)}
                          disabled={upgrading === plan.level}
                          className={`w-full py-2 px-4 rounded-xl bg-gradient-to-r ${plan.gradient} text-white text-xs font-semibold hover:opacity-90 transition-all duration-200 active:scale-95 disabled:opacity-60 disabled:pointer-events-none flex items-center justify-center gap-2 shadow-md`}
                        >
                          {upgrading === plan.level ? (
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <ArrowRight className="w-3.5 h-3.5" />
                          )}
                          {upgrading === plan.level ? 'Processando...' : 'Fazer Upgrade'}
                        </button>
                      ) : (
                        <div className="w-full py-2 px-4 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 text-xs font-semibold text-center">
                          Plano inferior
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Skip payment toggle (DEV) */}
        <div className="card p-4 animate-slide-up" style={{ animationDelay: '0.15s', animationFillMode: 'both' }}>
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-500/20 flex items-center justify-center">
                <TrendingUp className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900 dark:text-white">Modo de Desenvolvimento</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Ativar skip_payment para aplicar mudanças sem gateway de pagamento</p>
              </div>
            </div>
            <button
              onClick={() => setSkipPayment(!skipPayment)}
              className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                skipPayment ? 'bg-brand-500' : 'bg-gray-200 dark:bg-gray-700'
              }`}
            >
              <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                skipPayment ? 'translate-x-5' : 'translate-x-0'
              }`} />
            </button>
          </div>
          {skipPayment && (
            <div className="mt-3 flex items-center gap-2 p-2.5 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-lg">
              <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
              <p className="text-xs text-amber-700 dark:text-amber-300">
                Skip payment ativo — upgrades e recargas serão aplicados imediatamente sem pagamento (requer SKIP_PAYMENT=True no servidor)
              </p>
            </div>
          )}
        </div>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </DashboardLayout>
  );
}
