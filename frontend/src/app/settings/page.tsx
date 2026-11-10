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
  Loader2
} from 'lucide-react';

export default function SettingsPage() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const data = await api.getDemoStatus();
      setStatus(data);
    } catch (err) {
      console.error('Failed to load settings status:', err);
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
              Enterprise Configuration
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
                      {status?.has_gemini ? 'CONFIGURED & CONNECTED' : 'UNSET (FALLBACK ACTIVE)'}
                    </span>
                  </div>
                </div>

                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <span className="text-xs text-slate-400 font-medium block">OpenAI API</span>
                  <div className="flex items-center space-x-2">
                    <span className={`h-2 w-2 rounded-full ${status?.has_openai ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                    <span className="text-xs font-mono font-bold text-white">
                      {status?.has_openai ? 'CONFIGURED & CONNECTED' : 'UNSET (FALLBACK ACTIVE)'}
                    </span>
                  </div>
                </div>

                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <span className="text-xs text-slate-400 font-medium block">Deterministic Investigation Engine</span>
                  <div className="flex items-center space-x-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-400" />
                    <span className="text-xs font-mono font-bold text-emerald-400">
                      ACTIVE & GUARANTEED
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
                    <p className="text-xs text-slate-400">OAuth 2.0, REST API Orders v2, Captures v2, and Idempotent Refunds</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-[11px] text-slate-400 font-mono">Gateway Mode:</span>
                    <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${
                      status?.integration_mode === 'LIVE_PAYPAL_SANDBOX'
                        ? 'bg-emerald-950/80 border-emerald-800 text-emerald-300'
                        : 'bg-indigo-950/80 border-indigo-800 text-indigo-300'
                    }`}>
                      {status?.integration_mode || 'SIMULATED_SANDBOX'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-2 text-xs">
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <span className="text-slate-400 block font-medium">Credentials Status</span>
                  <div className="flex items-center space-x-2">
                    <span className={`h-2 w-2 rounded-full ${status?.paypal_credentials_status === 'CONFIGURED' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                    <span className="font-mono font-bold text-white">
                      {status?.paypal_credentials_status === 'CONFIGURED' ? 'CONFIGURED' : 'MISSING (ENV UNSET)'}
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
                      status?.paypal_connectivity === 'REACHABLE' ? 'bg-emerald-400' : 'bg-cyan-400'
                    }`} />
                    <span className="font-mono font-bold text-white">
                      {status?.paypal_connectivity === 'REACHABLE' ? 'REACHABLE' : 'SIMULATION FALLBACK'}
                    </span>
                  </div>
                  <span className="text-[11px] text-cyan-400 block font-mono truncate" title={status?.paypal_base_url}>
                    {status?.paypal_base_url}
                  </span>
                </div>

                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <span className="text-slate-400 block font-medium">Last Live API Verification</span>
                  <div className="flex items-center space-x-2">
                    <span className={`h-2 w-2 rounded-full ${status?.last_api_verification ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                    <span className="font-mono font-bold text-slate-200 text-[11px] truncate" title={status?.last_api_verification || 'None'}>
                      {status?.last_api_verification ? new Date(status.last_api_verification).toLocaleTimeString() : 'None (Simulation Active)'}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 block">
                    {status?.last_api_verification ? 'Live Sandbox verified' : 'No live call made'}
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
                  <h3 className="text-base font-bold text-white">Enterprise Security & Secrets Masking</h3>
                  <p className="text-xs text-slate-400">All credentials isolated in backend environment variables</p>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 space-y-2 leading-relaxed">
                <p>
                  ✓ Secret keys, API tokens, and webhook HMAC credentials are never rendered or transmitted to client browser bundles.
                </p>
                <p>
                  ✓ Deterministic risk engine calculates unalterable factual scores to prevent hallucination in financial decisions.
                </p>
                <p>
                  ✓ Human-in-the-Loop approval gate strictly enforces authorized signatures before any payment reversal can dispatch.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
