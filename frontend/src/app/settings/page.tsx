'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Header } from '@/components/Header';
import {
  Settings as SettingsIcon,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Cpu,
  CreditCard,
  Database,
  Lock,
  Server,
  Loader2,
  Info
} from 'lucide-react';

export default function SettingsPage() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const data = await api.getDemoStatus();
      setStatus(data);
    } catch (err) {
      console.error('Failed to load settings status:', err);
      setLoadError('Could not reach the local API. Integration status is unavailable.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Header onRefresh={fetchStatus} />

      <main className="p-8 space-y-6 flex-1 max-w-[1200px] w-full mx-auto">
        {/* Title */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <span>System Settings & Integrations</span>
            <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
              Local Demo Configuration
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Environment status, AI model abstractions, and PayPal Sandbox API gateway connections
          </p>
        </div>

        {loading ? (
          <div className="p-20 text-center">
            <Loader2 className="h-8 w-8 text-cyan-400 animate-spin mx-auto mb-2" />
            <p className="text-xs text-slate-400">Loading system configuration...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {loadError && <div role="alert" className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-sm text-rose-200">{loadError}</div>}
            {/* AI Providers Card */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 space-y-4">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-lg bg-blue-500/10 text-cyan-400">
                  <Cpu className="h-5 w-5" />
                </div>
                <div className="flex-1 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <h3 className="text-base font-bold text-white">AI Provider Abstraction</h3>
                    <p className="text-xs text-slate-400">Active intelligence configuration and model fallback strategy</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-[11px] text-slate-400 font-mono">Active Provider:</span>
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-800 text-cyan-300">
                      {status?.active_provider || 'DETERMINISTIC_ENGINE'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <span className="text-xs text-slate-400 font-medium block">Google Gemini API</span>
                  <div className="flex items-center space-x-2">
                    <span className={`h-2 w-2 rounded-full ${status?.has_gemini ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                    <span className="text-xs font-mono font-bold text-white">
                      {status?.has_gemini ? 'KEY CONFIGURED • NOT PROBED' : 'NOT CONFIGURED'}
                    </span>
                  </div>
                </div>

                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <span className="text-xs text-slate-400 font-medium block">OpenAI API</span>
                  <div className="flex items-center space-x-2">
                    <span className={`h-2 w-2 rounded-full ${status?.has_openai ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                    <span className="text-xs font-mono font-bold text-white">
                      {status?.has_openai ? 'KEY CONFIGURED • NOT PROBED' : 'NOT CONFIGURED'}
                    </span>
                  </div>
                </div>

                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <span className="text-xs text-slate-400 font-medium block">Deterministic Investigation Engine</span>
                  <div className="flex items-center space-x-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-400" />
                    <span className="text-xs font-mono font-bold text-emerald-400">
                      ACTIVE
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* PayPal Sandbox Gateway */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 space-y-4">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-lg bg-indigo-500/10 text-indigo-400">
                  <CreditCard className="h-5 w-5" />
                </div>
                <div className="flex-1 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <h3 className="text-base font-bold text-white">PayPal Sandbox Gateway</h3>
                    <p className="text-xs text-slate-400">OAuth 2.0 Client Credentials Grant & REST API V2 Integrations</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-[11px] text-slate-400 font-mono">OAuth 2.0 Status:</span>
                    <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${
                      status?.paypal_oauth_status === 'AUTHENTICATED'
                        ? 'bg-emerald-950/80 border-emerald-800 text-emerald-300'
                        : status?.paypal_oauth_status === 'FAILED'
                          ? 'bg-rose-950/80 border-rose-800 text-rose-300'
                          : 'bg-slate-900 border-slate-700 text-slate-300'
                    }`}>
                      {status?.paypal_oauth_status === 'AUTHENTICATED' ? 'OAUTH AUTHENTICATED' : (status?.paypal_oauth_status || 'STATUS UNKNOWN')}
                    </span>
                  </div>
                </div>
              </div>

              {/* Status Notice Banner distinguishing OAuth from Settlement execution */}
              <div className="p-3.5 rounded-lg bg-blue-950/40 border border-blue-800/60 text-xs text-blue-200/90 space-y-1">
                <div className="flex items-center space-x-2 font-semibold text-white">
                  <Info className="h-4 w-4 text-cyan-400 flex-shrink-0" />
                  <span>Integration Status & Demo Dataset Notice</span>
                </div>
                <p className="text-slate-300 leading-relaxed text-[11px]">
                  PayPal Sandbox OAuth status is <strong>{status?.paypal_oauth_status || 'unknown'}</strong>; connectivity is <strong>{status?.paypal_connectivity || 'unknown'}</strong>. Live order creation was verified against Sandbox (<code className="text-cyan-300 font-mono">CREATED · Awaiting Buyer</code>). Buyer approval, capture, and refund are unperformed and unverified. Pre-seeded demo records are local simulations (<code className="text-amber-300 font-mono">SIMULATED SANDBOX</code>).
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-2 text-xs">
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <span className="text-slate-400 block font-medium">Credentials Status</span>
                  <div className="flex items-center space-x-2">
                    <span className={`h-2 w-2 rounded-full ${status?.paypal_credentials_status === 'CONFIGURED' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                    <span className="font-mono font-bold text-white">
                      {status?.paypal_credentials_status || 'UNKNOWN'}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 block font-mono">
                    PAYPAL_CLIENT_ID / SECRET
                  </span>
                </div>

                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <span className="text-slate-400 block font-medium">OAuth 2.0 Auth</span>
                  <div className="flex items-center space-x-2">
                    <span className={`h-2 w-2 rounded-full ${
                      status?.paypal_oauth_status === 'AUTHENTICATED' ? 'bg-emerald-400' : (status?.paypal_oauth_status === 'FAILED' ? 'bg-rose-400' : 'bg-slate-600')
                    }`} />
                    <span className="font-mono font-bold text-white">
                      {status?.paypal_oauth_status || 'NOT CONFIGURED'}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 block font-mono">
                    Client Credentials Grant
                  </span>
                </div>

                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <span className="text-slate-400 block font-medium">Sandbox Connectivity</span>
                  <div className="flex items-center space-x-2">
                    <span className={`h-2 w-2 rounded-full ${
                      status?.paypal_connectivity === 'REACHABLE' ? 'bg-emerald-400' : (status?.paypal_connectivity === 'UNREACHABLE' ? 'bg-rose-400' : 'bg-slate-600')
                    }`} />
                    <span className="font-mono font-bold text-white">
                      {status?.paypal_connectivity || 'UNKNOWN'}
                    </span>
                  </div>
                  <span className="text-[11px] text-cyan-400 block font-mono truncate" title={status?.paypal_base_url}>
                    {status?.paypal_base_url}
                  </span>
                </div>

                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <span className="text-slate-400 block font-medium">Last OAuth Token Probe</span>
                  <div className="flex items-center space-x-2">
                    <span className={`h-2 w-2 rounded-full ${status?.last_api_verification ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                    <span className="font-mono font-bold text-slate-200 text-[11px] truncate" title={status?.last_api_verification || 'None'}>
                      {status?.last_api_verification ? new Date(status.last_api_verification).toLocaleTimeString() : 'None'}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 block">
                    {status?.last_api_verification ? 'OAuth probe verified' : 'No live probe made'}
                  </span>
                </div>
              </div>
            </div>

            {/* Cryptographic Secrets & Data Isolation */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 space-y-4">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-400">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Local Demo Security Notes</h3>
                  <p className="text-xs text-slate-400">All credentials isolated in backend environment variables</p>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 space-y-2 leading-relaxed">
                <p>
                  ✓ Secret values are not displayed in this status screen. Keep credentials in backend environment variables and out of source control.
                </p>
                <p>
                  ✓ The deterministic rules calculate the risk score. Optional AI summaries may explain evidence but do not make the payment decision.
                </p>
                <p>
                  ✓ Human-in-the-Loop approval gate requires explicit human review and a named decision-maker before any payment reversal can be queued. API endpoints are loopback-only; caller identity is not independently authenticated in this demo.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
