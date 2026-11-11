'use client';

import React, { useState } from 'react';
import { api } from '@/lib/api';
import {
  Play,
  CheckCircle2,
  Loader2
} from 'lucide-react';

interface HeaderProps {
  onRefresh?: () => void;
}

export function Header({ onRefresh }: HeaderProps) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const handleAction = async (name: string, fn: () => Promise<any>) => {
    setLoadingAction(name);
    try {
      const res = await fn();
      setToastMessage(res.message || `Action '${name}' executed successfully!`);
      setTimeout(() => setToastMessage(null), 4000);
      if (onRefresh) onRefresh();
    } catch (err: any) {
      setToastMessage(`Error: ${err.message || 'Action failed'}`);
      setTimeout(() => setToastMessage(null), 5000);
    } finally {
      setLoadingAction(null);
    }
  };

  return (
    <header className="h-16 bg-slate-950/90 border-b border-slate-800/80 sticky top-0 z-30 px-8 flex items-center justify-between backdrop-blur-md">
      {/* Left: Environment & Tagline */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2 bg-blue-500/10 border border-blue-500/20 px-2.5 py-1 rounded-full">
          <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
          <span className="text-xs font-semibold text-cyan-300 tracking-wide uppercase">
            DEMO MODE • PAYPAL SANDBOX
          </span>
        </div>
        <span className="text-xs text-slate-400 hidden lg:inline">
          Intelligence Behind Every Transaction
        </span>
      </div>

      {/* Center: Toast feedback if active */}
      {toastMessage && (
        <div className="absolute left-1/2 -translate-x-1/2 flex items-center space-x-2 bg-slate-900 border border-cyan-500/40 px-4 py-1.5 rounded-full shadow-lg text-xs font-medium text-cyan-300 animate-in fade-in slide-in-from-top-2">
          <CheckCircle2 className="h-3.5 w-3.5 text-cyan-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Right: Quick Action Demo Toolbar */}
      <div className="flex items-center space-x-2">
        <button
          onClick={() => handleAction('Run Investigation', () => api.runFullInvestigation())}
          disabled={loadingAction !== null}
          className="flex items-center space-x-1.5 px-3 py-1.5 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-md text-xs font-medium shadow-md shadow-blue-500/20 transition-all disabled:opacity-50"
        >
          {loadingAction === 'Run Investigation' ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5 fill-current" />
          )}
          <span>Run Fraud Investigation</span>
        </button>

      </div>
    </header>
  );
}
