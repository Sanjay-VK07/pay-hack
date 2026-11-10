'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Header } from '@/components/Header';
import { Badge } from '@/components/Badge';
import {
  CreditCard,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  ShieldAlert,
  Loader2,
  Lock,
  ArrowRight
} from 'lucide-react';

export default function PaymentsPage() {
  const [payments, setPayments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refundingId, setRefundingId] = useState<string | null>(null);
  const [checkingRefundId, setCheckingRefundId] = useState<string | null>(null);
  const [confirmModal, setConfirmModal] = useState<any | null>(null);
  const [refundReason, setRefundReason] = useState('AgentShield verified fraud syndicate remediation');

  const fetchPayments = async () => {
    setLoading(true);
    try {
      const data = await api.getPayments();
      setPayments(data);
    } catch (err) {
      console.error('Failed to load payments:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPayments();
  }, []);

  const handleExecuteRefund = async () => {
    if (!confirmModal) return;
    setRefundingId(confirmModal.id);
    try {
      const res = await api.refundPayment(confirmModal.id, {
        reason: refundReason,
        investigator: 'Chief Risk Officer',
      });
      alert(`Refund Status: ${res.refund_status}. ${res.is_simulated ? '[Simulated Sandbox Mode]' : '[Live PayPal Sandbox]'}`);
      setConfirmModal(null);
      await fetchPayments();
    } catch (err: any) {
      alert(`Refund Error: ${err.message}`);
    } finally {
      setRefundingId(null);
    }
  };

  const handleCheckRefund = async (paymentId: string) => {
    setCheckingRefundId(paymentId);
    try {
      const result = await api.verifyRefundStatus(paymentId);
      alert(`Refund Status: ${result.refund_status}`);
      await fetchPayments();
    } catch (err: any) {
      alert(`Status Check: ${err.message}`);
    } finally {
      setCheckingRefundId(null);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Header onRefresh={fetchPayments} />

      <main className="p-8 space-y-6 flex-1 max-w-[1600px] w-full mx-auto">
        {/* Title */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <span>Payment Operations & Financial Remediation</span>
              <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                PayPal Developer Platform
              </span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Authorized PayPal Sandbox Order captures, idempotent refund executions, and fraud mitigation holds
            </p>
          </div>
        </div>

        {/* Security Rules Banner */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-start space-x-3.5 backdrop-blur">
          <ShieldAlert className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1 text-xs">
            <span className="font-bold text-white block">Strict FinTech Financial Safety Protocol</span>
            <p className="text-slate-400 leading-relaxed">
              Refunds are strictly idempotent and restricted to verified completed captures. Reversals for high-risk transactions require prior multi-agent investigation and mandatory human sign-off.
            </p>
          </div>
        </div>

        {/* Payments Table */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden shadow-xl">
          <div className="p-4 border-b border-slate-800/80 bg-slate-950 flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Settled & Captured Operations ({payments.length})
            </span>
            <span className="text-xs text-slate-400 font-mono">Sandbox API: Active</span>
          </div>

          <div className="overflow-x-auto">
            {loading ? (
              <div className="p-16 text-center">
                <Loader2 className="h-6 w-6 text-cyan-400 animate-spin mx-auto mb-2" />
                <p className="text-xs text-slate-400">Loading payment ledger...</p>
              </div>
            ) : payments.length === 0 ? (
              <div className="p-16 text-center text-xs text-slate-400">
                No active PayPal payment records found. Load the demo dataset from the top toolbar.
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 font-medium uppercase tracking-wider text-[11px] border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Payment ID</th>
                    <th className="py-3 px-4">PayPal Capture ID</th>
                    <th className="py-3 px-4">Txn Reference</th>
                    <th className="py-3 px-4">Amount</th>
                    <th className="py-3 px-4">Settlement</th>
                    <th className="py-3 px-4">Refund Status</th>
                    <th className="py-3 px-4">Integration Mode</th>
                    <th className="py-3 px-4 text-right">Remediation Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 text-slate-300">
                  {payments.map((p) => {
                    const isRefunded = p.refund_status === 'COMPLETED';
                    const isProcessing = p.refund_status === 'PROCESSING';
                    const isUncaptured = !p.capture_id || p.payment_status === 'UNCAPTURED' || p.refund_status === 'INELIGIBLE';
                    const canRefund = Boolean(p.capture_id)
                      && ['COMPLETED', 'CAPTURED'].includes(p.payment_status)
                      && p.approval_status === 'APPROVED'
                      && !isRefunded
                      && !isProcessing;
                    return (
                      <tr key={p.id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-3.5 px-4 font-mono font-medium text-white">{p.id}</td>
                        <td className="py-3.5 px-4 font-mono text-cyan-400">
                          {p.capture_id || <span className="text-amber-400/80 italic text-[11px]">No Capture</span>}
                        </td>
                        <td className="py-3.5 px-4 font-mono text-slate-300">{p.transaction_ref}</td>
                        <td className="py-3.5 px-4 font-mono font-bold text-white">
                          ${p.amount.toFixed(2)} {p.currency}
                        </td>
                        <td className="py-3.5 px-4">
                          <Badge type="status" value={p.payment_status} />
                        </td>
                        <td className="py-3.5 px-4">
                          {isRefunded || isProcessing ? (
                            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                              <CheckCircle2 className="h-3 w-3" />
                              <span>{isRefunded ? 'REFUNDED' : 'PROCESSING'}</span>
                            </span>
                          ) : isUncaptured ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                              INELIGIBLE
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-400 border border-slate-700">
                              NONE
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase border ${
                            p.is_simulated
                              ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                              : 'bg-blue-500/10 text-cyan-300 border-blue-500/30'
                          }`}>
                            {p.is_simulated ? 'SIMULATED SANDBOX' : 'LIVE PAYPAL SANDBOX'}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          {isProcessing ? (
                            <button
                              onClick={() => handleCheckRefund(p.id)}
                              disabled={checkingRefundId === p.id}
                              className="px-3 py-1 bg-cyan-700 hover:bg-cyan-600 text-white rounded-md text-xs font-semibold transition-all disabled:cursor-wait disabled:opacity-50"
                            >
                              {checkingRefundId === p.id ? 'Checking…' : 'Check PayPal Status'}
                            </button>
                          ) : isRefunded ? (
                            <span className="text-[11px] text-slate-400 font-mono">Reversed</span>
                          ) : isUncaptured ? (
                            <span
                              className="inline-flex items-center px-2.5 py-1 rounded text-[11px] font-mono text-amber-400/90 bg-amber-500/10 border border-amber-500/30"
                              title="Uncaptured transaction has no settled PayPal funds to reverse."
                            >
                              Ineligible (No Capture)
                            </span>
                          ) : (
                            <button
                              onClick={() => setConfirmModal(p)}
                              disabled={!canRefund}
                              title={!canRefund ? 'Refund requires a completed capture and explicit human approval.' : undefined}
                              className="px-3 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded-md text-xs font-semibold shadow-sm transition-all disabled:cursor-not-allowed disabled:opacity-40"
                            >
                              Execute Refund
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </main>

      {/* Confirmation Modal */}
      {confirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400">
                <RotateCcw className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Execute PayPal Reversal</h3>
                <p className="text-xs text-slate-400">Reverses captured funds to the original payer</p>
              </div>
            </div>

            <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Payment ID:</span>
                <span className="text-white font-mono">{confirmModal.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">PayPal Capture Ref:</span>
                <span className="text-cyan-400 font-mono">{confirmModal.capture_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Reversal Amount:</span>
                <span className="text-white font-mono font-bold">${confirmModal.amount?.toFixed(2)} {confirmModal.currency}</span>
              </div>
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Reason for Reversal</label>
              <textarea
                rows={2}
                value={refundReason}
                onChange={(e) => setRefundReason(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setConfirmModal(null)}
                className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteRefund}
                disabled={refundingId !== null}
                className="px-4 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-rose-600/20 transition-all flex items-center space-x-1.5"
              >
                {refundingId ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                <span>Confirm & Execute Reversal</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
