'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  ShieldAlert,
  LayoutDashboard,
  ArrowLeftRight,
  Share2,
  FileSearch,
  Bot,
  CreditCard,
  History,
  Settings as SettingsIcon,
  ShieldCheck,
  Activity
} from 'lucide-react';

const navItems = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Transactions', href: '/transactions', icon: ArrowLeftRight },
  { name: 'Fraud Networks', href: '/fraud-networks', icon: Share2, highlight: true },
  { name: 'Investigation Workspace', href: '/investigations', icon: FileSearch },
  { name: 'AI Investigation Center', href: '/ai-investigation', icon: Bot },
  { name: 'Payment Operations', href: '/payments', icon: CreditCard },
  { name: 'Audit Center', href: '/audit', icon: History },
  { name: 'Settings', href: '/settings', icon: SettingsIcon },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800/80 flex flex-col h-screen fixed left-0 top-0 z-40">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-slate-800/80 space-x-3 bg-slate-950/80 backdrop-blur">
        <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-blue-600 via-cyan-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <ShieldAlert className="h-5 w-5 text-white" />
        </div>
        <div>
          <span className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
            Agent<span className="text-cyan-400">Shield</span>
          </span>
          <p className="text-[10px] text-slate-400 font-medium tracking-wider uppercase">PayPal AI Fraud Ops</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 mb-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
          Autonomous Security
        </div>
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-blue-600/15 text-cyan-300 border border-blue-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80'
              }`}
            >
              <div className="flex items-center space-x-3">
                <Icon className={`h-4 w-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                <span>{item.name}</span>
              </div>
              {item.highlight && (
                <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse shadow-sm shadow-cyan-400/50" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Live Sentinel Indicator */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950">
        <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-emerald-400 animate-pulse" />
              Sentinel Engine
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono border border-emerald-500/20">
              ACTIVE
            </span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Multi-Agent NetworkX graph analysis streaming continuous telemetry.
          </p>
        </div>
      </div>
    </aside>
  );
}
