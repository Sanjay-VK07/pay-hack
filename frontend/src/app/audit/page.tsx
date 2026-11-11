'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Header } from '@/components/Header';
import {
  History,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  User,
  ShieldAlert,
  Loader2,
  Code
} from 'lucide-react';

export default function AuditPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const [actorFilter, setActorFilter] = useState('');

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await api.getAuditLogs({
        event_type: eventTypeFilter || undefined,
        actor: actorFilter || undefined,
        limit: 100,
      });
      setLogs(data);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [eventTypeFilter]);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchLogs();
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Header onRefresh={fetchLogs} />

      <main className="p-8 space-y-6 flex-1 max-w-[1600px] w-full mx-auto">
        {/* Title */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <span>Chronological Audit Trail</span>
              <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                Chronological Audit Ledger
              </span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Chronological tracking of all agent decisions, human approvals, and payment lifecycle events in relational storage
            </p>
          </div>
        </div>

        {/* Filter Bar */}
        <form onSubmit={handleFilterSubmit} className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2 flex-1 min-w-[240px]">
            <Search className="h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Filter by actor (e.g. Chief Risk Officer, Agent)..."
              value={actorFilter}
              onChange={(e) => setActorFilter(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-400">Event Type:</span>
            <select
              value={eventTypeFilter}
              onChange={(e) => setEventTypeFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Events</option>
              <option value="MULTI_AGENT_INVESTIGATION">MULTI_AGENT_INVESTIGATION</option>
              <option value="HUMAN_APPROVAL_GRANTED">HUMAN_APPROVAL_GRANTED</option>
              <option value="SIMULATED_REFUND_EXECUTED">SIMULATED_REFUND_EXECUTED</option>
              <option value="PAYPAL_REFUND_REQUESTED">PAYPAL_REFUND_REQUESTED</option>
              <option value="PAYPAL_REFUND_PENDING">PAYPAL_REFUND_PENDING</option>
              <option value="PAYPAL_REFUND_CONFIRMED">PAYPAL_REFUND_CONFIRMED</option>
              <option value="PAYPAL_REFUND_FAILED">PAYPAL_REFUND_FAILED</option>
              <option value="PAYPAL_REFUND_EXECUTED">PAYPAL_REFUND_EXECUTED (Legacy)</option>
              <option value="TRANSACTION_INGESTED">TRANSACTION_INGESTED</option>
              <option value="DEMO_DATASET_LOADED">DEMO_DATASET_LOADED</option>
            </select>
          </div>

          <button
            type="submit"
            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-all"
          >
            Apply Filter
          </button>
        </form>

        {/* Audit Log Table */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            {loading ? (
              <div className="p-16 text-center">
                <Loader2 className="h-6 w-6 text-cyan-400 animate-spin mx-auto mb-2" />
                <p className="text-xs text-slate-400">Retrieving audit trail...</p>
              </div>
            ) : logs.length === 0 ? (
              <div className="p-16 text-center text-xs text-slate-400">
                No audit entries matching filter criteria.
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 font-medium uppercase tracking-wider text-[11px] border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Event ID</th>
                    <th className="py-3 px-4">Event Type</th>
                    <th className="py-3 px-4">Actor</th>
                    <th className="py-3 px-4">Case / Txn</th>
                    <th className="py-3 px-4">State Transition</th>
                    <th className="py-3 px-4">API Operation Ref</th>
                    <th className="py-3 px-4 text-right">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 text-slate-300">
                  {logs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-white">{log.id}</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-500/10 text-cyan-300 border border-blue-500/20">
                          {log.event_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-200 font-medium">{log.actor}</td>
                      <td className="py-3 px-4 font-mono text-slate-400">
                        {log.case_id || log.transaction_id || 'SYSTEM'}
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px]">
                        <span className="text-slate-400">{log.previous_state || '—'}</span>
                        <span className="text-slate-600 mx-1.5">→</span>
                        <span className="text-cyan-400 font-semibold">{log.new_state || '—'}</span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400 text-[11px]">
                        {log.api_ref || '—'}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-slate-400 text-[11px]">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
