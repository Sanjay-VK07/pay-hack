'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Header } from '@/components/Header';
import { Badge } from '@/components/Badge';
import {
  ShieldAlert,
  ArrowUpRight,
  TrendingUp,
  AlertTriangle,
  Users,
  Share2,
  DollarSign,
  CheckCircle2,
  CreditCard,
  Bot,
  ExternalLink,
  Loader2,
  Clock
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar
} from 'recharts';

const RISK_COLORS: Record<string, string> = {
  LOW: '#10b981',
  MEDIUM: '#f59e0b',
  HIGH: '#f97316',
  CRITICAL: '#f43f5e',
};

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchSummary = async () => {
    try {
      const res = await api.getDashboardSummary();
      setData(res);
    } catch (err) {
      console.error('Failed to load dashboard summary:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex flex-col">
        <Header onRefresh={fetchSummary} />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="h-8 w-8 text-cyan-400 animate-spin mx-auto mb-3" />
            <p className="text-sm text-slate-400">Loading FinTech telemetry...</p>
          </div>
        </div>
      </div>
    );
  }

  const riskPieData = data?.risk_distribution
    ? Object.entries(data.risk_distribution).map(([name, value]) => ({
        name,
        value: Number(value),
      }))
    : [];

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Header onRefresh={fetchSummary} />

      <main className="p-8 space-y-8 flex-1 max-w-[1600px] w-full mx-auto">
        {/* Title & Live Status */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <span>Payment Fraud Command Center</span>
              <span className="text-xs font-normal text-slate-400 px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
                v1.0.0
              </span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Deterministic transaction evaluation & graph-based multi-agent investigation network
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <Link
              href="/fraud-networks"
              className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-blue-600/10 hover:bg-blue-600/20 text-cyan-300 border border-blue-500/30 text-xs font-medium transition-all"
            >
              <Share2 className="h-3.5 w-3.5 text-cyan-400" />
              <span>Explore Fraud Network Graph</span>
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
            <Link
              href="/investigations"
              className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700/80 text-xs font-medium transition-all"
            >
              <span>Review Open Cases</span>
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>

        {/* 8 Primary Metrics Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* 1. Total Transactions */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 backdrop-blur shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Total Transactions
              </span>
              <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                <TrendingUp className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-white font-mono">
                {data?.total_transactions_analyzed ?? 0}
              </span>
              <span className="text-xs font-medium text-emerald-400 flex items-center">
                100% Ingested
              </span>
            </div>
          </div>

          {/* 2. Suspicious Transactions */}
          <div className="bg-slate-900/60 border border-rose-500/20 rounded-xl p-5 backdrop-blur shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Suspicious Transactions
              </span>
              <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400">
                <AlertTriangle className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-rose-400 font-mono">
                {data?.suspicious_transactions ?? 0}
              </span>
              <span className="text-xs font-medium text-rose-400/80">
                Flagged for Review
              </span>
            </div>
          </div>

          {/* 3. Fraud Networks Discovered */}
          <div className="bg-slate-900/60 border border-cyan-500/20 rounded-xl p-5 backdrop-blur shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Fraud Networks
              </span>
              <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
                <Share2 className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-cyan-300 font-mono">
                {data?.fraud_networks_discovered ?? 0}
              </span>
              <span className="text-xs font-medium text-cyan-400">
                NetworkX Corroborated
              </span>
            </div>
          </div>

          {/* 4. Estimated Exposure */}
          <div className="bg-slate-900/60 border border-amber-500/20 rounded-xl p-5 backdrop-blur shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Financial Exposure
              </span>
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
                <DollarSign className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-amber-300 font-mono">
                ${data?.estimated_financial_exposure?.toLocaleString('en-US', { minimumFractionDigits: 2 }) ?? '0.00'}
              </span>
              <span className="text-xs font-medium text-amber-400">
                High-Risk Capital
              </span>
            </div>
          </div>

          {/* 5. Active Cases */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 backdrop-blur shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Active Cases
              </span>
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                <ShieldAlert className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-white font-mono">
                {data?.active_investigation_cases ?? 0}
              </span>
              <span className="text-xs font-medium text-slate-400">
                Awaiting Gate Review
              </span>
            </div>
          </div>

          {/* 6. High-Risk Accounts */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 backdrop-blur shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                High-Risk Accounts
              </span>
              <div className="p-2 rounded-lg bg-orange-500/10 text-orange-400">
                <Users className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-orange-400 font-mono">
                {data?.high_risk_accounts ?? 0}
              </span>
              <span className="text-xs font-medium text-orange-400/80">
                Profile Watchlist
              </span>
            </div>
          </div>

          {/* 7. Resolved Cases */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 backdrop-blur shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Resolved Cases
              </span>
              <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                <CheckCircle2 className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-emerald-400 font-mono">
                {data?.resolved_cases ?? 0}
              </span>
              <span className="text-xs font-medium text-emerald-400">
                Remediated
              </span>
            </div>
          </div>

          {/* 8. PayPal Operations */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 backdrop-blur shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                PayPal Operations
              </span>
              <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                <CreditCard className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-blue-300 font-mono">
                {data?.paypal_operations_count ?? 0}
              </span>
              <span className="text-xs font-medium text-blue-400">
                Captures / Refunds
              </span>
            </div>
          </div>
        </div>

        {/* Analytics Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Trend Chart (2 cols) */}
          <div className="lg:col-span-2 bg-slate-900/70 border border-slate-800/80 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-white">Transaction & Fraud Exposure Trajectory</h3>
                <p className="text-xs text-slate-400">Daily velocity versus detected suspicious exposure ($)</p>
              </div>
              <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                Last 7 Days
              </span>
            </div>

            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data?.daily_trend || []}>
                  <defs>
                    <linearGradient id="colorExposure" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="day" stroke="#64748b" fontSize={12} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={12} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0b1329',
                      borderColor: '#1e293b',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="exposure"
                    name="Fraud Exposure ($)"
                    stroke="#f43f5e"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorExposure)"
                  />
                  <Area
                    type="monotone"
                    dataKey="volume"
                    name="Volume (Count)"
                    stroke="#38bdf8"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorVolume)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Risk Tier Distribution (1 col) */}
          <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl p-6 flex flex-col justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">Risk Tier Distribution</h3>
              <p className="text-xs text-slate-400 mb-4">Breakdown across deterministic threat tiers</p>

              <div className="h-44 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={riskPieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={70}
                      paddingAngle={4}
                    >
                      {riskPieData.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={RISK_COLORS[entry.name] || '#64748b'}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0b1329',
                        borderColor: '#1e293b',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800">
              {riskPieData.map((tier) => (
                <div key={tier.name} className="flex items-center space-x-2">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: RISK_COLORS[tier.name] }}
                  />
                  <span className="text-xs text-slate-300 font-medium">{tier.name}:</span>
                  <span className="text-xs font-mono text-white">{String(tier.value)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Operational Tables Grid: Recent Transactions & Active Cases */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Transactions */}
          <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl overflow-hidden flex flex-col">
            <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white">Recent Transaction Stream</h3>
                <p className="text-xs text-slate-400">Live evaluated marketplace transactions</p>
              </div>
              <Link
                href="/transactions"
                className="text-xs text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1"
              >
                <span>View Table in AG Grid</span>
                <ExternalLink className="h-3 w-3" />
              </Link>
            </div>

            <div className="divide-y divide-slate-800/80 overflow-y-auto max-h-96">
              {data?.recent_transactions?.map((t: any) => (
                <div key={t.id} className="p-4 hover:bg-slate-800/40 transition-colors flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-mono font-medium text-slate-200">{t.id}</span>
                      <Badge type="risk" value={t.risk_category} />
                    </div>
                    <p className="text-xs text-slate-400">
                      {t.customer_name} • <span className="font-mono text-slate-400">{t.ip_address || 'No IP'}</span>
                    </p>
                  </div>

                  <div className="text-right">
                    <span className="text-sm font-mono font-bold text-white">
                      ${t.amount.toFixed(2)} {t.currency}
                    </span>
                    <p className="text-[11px] text-slate-400">
                      Risk: <span className="font-mono text-cyan-400">{t.risk_score.toFixed(1)}/100</span>
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Active Investigation Cases */}
          <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl overflow-hidden flex flex-col">
            <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white">Investigation Cases</h3>
                <p className="text-xs text-slate-400">Multi-Agent corroborated security dossiers</p>
              </div>
              <Link
                href="/investigations"
                className="text-xs text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1"
              >
                <span>Open Workspace</span>
                <ExternalLink className="h-3 w-3" />
              </Link>
            </div>

            <div className="divide-y divide-slate-800/80 overflow-y-auto max-h-96">
              {data?.recent_cases?.map((c: any) => (
                <div key={c.id} className="p-4 hover:bg-slate-800/40 transition-colors flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-mono font-bold text-slate-200">{c.id}</span>
                      <Badge type="risk" value={c.risk_level} />
                      <Badge type="approval" value={c.status} />
                    </div>
                    <p className="text-xs text-slate-400">
                      Ref: <span className="font-mono text-cyan-400">{c.primary_transaction_id}</span> • {c.evidence_count} corroborating evidence items
                    </p>
                    {c.approval_integrity_valid === false && (
                      <p className="text-[10px] text-amber-300 flex items-center gap-1" role="alert">
                        <AlertTriangle className="h-3 w-3" /> Approval audit record missing or incomplete
                      </p>
                    )}
                  </div>

                  <div className="text-right">
                    <span className="text-xs font-semibold text-slate-200 block">
                      {c.recommended_action}
                    </span>
                    <span className="text-[10px] text-slate-400 flex items-center justify-end gap-1 mt-0.5">
                      <Clock className="h-3 w-3" />
                      {new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Latest Multi-Agent Activity Stream */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
                <Bot className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Autonomous Agent Activity Stream</h3>
                <p className="text-xs text-slate-400">Real-time reasoning logs across the specialized investigation agents</p>
              </div>
            </div>
            <Link
              href="/ai-investigation"
              className="text-xs text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1"
            >
              <span>View Full Orchestration Pipeline</span>
              <ExternalLink className="h-3 w-3" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {data?.recent_agent_activities?.slice(0, 3).map((agent: any) => (
              <div key={agent.id} className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-200">{agent.agent_name}</span>
                  <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                    {(agent.confidence_score * 100).toFixed(0)}% Conf
                  </span>
                </div>
                <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">
                  {agent.findings || 'Completed stage analysis and passed output tokens to downstream DAG.'}
                </p>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
