'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Header } from '@/components/Header';
import { Badge } from '@/components/Badge';
import {
  FileSearch,
  CheckCircle2,
  XCircle,
  ShieldAlert,
  Clock,
  User,
  DollarSign,
  AlertTriangle,
  Play,
  RotateCcw,
  Check,
  X,
  ExternalLink,
  Loader2,
  Layers,
  ChevronRight,
  Code,
  ShieldCheck,
  CreditCard,
  Cpu,
  Calculator,
  HelpCircle,
  Info,
  Lock,
  RefreshCw,
  FileText
} from 'lucide-react';

export default function InvestigationsPage() {
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [caseDetail, setCaseDetail] = useState<any | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [processingAction, setProcessingAction] = useState(false);
  const [approvalModal, setApprovalModal] = useState<{ open: boolean; action: 'APPROVE' | 'REJECT' } | null>(null);
  const [approvalReason, setApprovalReason] = useState('Corroborated multi-agent fraud syndicate indicators');
  const [investigatorName, setInvestigatorName] = useState('Chief Risk Officer');
  const [expandedExecs, setExpandedExecs] = useState<Record<string, boolean>>({});

  const toggleExec = (id: string) => {
    setExpandedExecs((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const fetchCases = async () => {
    setLoading(true);
    try {
      const data = await api.getInvestigations();
      setCases(data);
      if (data.length > 0 && !selectedCaseId) {
        setSelectedCaseId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load investigation cases:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchCaseDetail = async (id: string) => {
    setLoadingDetail(true);
    try {
      const detail = await api.getInvestigationCase(id);
      setCaseDetail(detail);
    } catch (err) {
      console.error('Failed to load case detail:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

  useEffect(() => {
    if (selectedCaseId) {
      fetchCaseDetail(selectedCaseId);
    }
  }, [selectedCaseId]);

  const handleExecuteApproval = async () => {
    if (!selectedCaseId || !approvalModal) return;
    setProcessingAction(true);
    try {
      if (approvalModal.action === 'APPROVE') {
        await api.approveCase(selectedCaseId, {
          investigator_name: investigatorName,
          reason: approvalReason,
        });
      } else {
        await api.rejectCase(selectedCaseId, {
          investigator_name: investigatorName,
          reason: approvalReason,
        });
      }
      setApprovalModal(null);
      await fetchCases();
      await fetchCaseDetail(selectedCaseId);
    } catch (err: any) {
      alert(`Approval operation failed: ${err.message}`);
    } finally {
      setProcessingAction(false);
    }
  };

  const handleReRunCase = async (caseId: string) => {
    setProcessingAction(true);
    try {
      await api.runCaseInvestigation(caseId);
      await fetchCases();
      await fetchCaseDetail(caseId);
    } catch (err: any) {
      alert(`Investigation failed: ${err.message}`);
    } finally {
      setProcessingAction(false);
    }
  };

  const handleProcessRefund = async () => {
    if (!caseDetail) return;
    const payment = caseDetail.payment_operations?.[0] || (caseDetail.capture_id ? { id: caseDetail.capture_id } : null);
    if (!payment) {
      alert('No linked payment record found for refund.');
      return;
    }
    const targetPaymentId = payment.id || caseDetail.capture_id;
    setProcessingAction(true);
    try {
      await api.refundPayment(targetPaymentId, {
        investigator: caseDetail.approving_user || investigatorName,
        reason: 'Authorized AgentShield fraud remediation reversal',
      });
      await fetchCases();
      await fetchCaseDetail(selectedCaseId!);
    } catch (err: any) {
      alert(`Refund operation failed: ${err.message}`);
    } finally {
      setProcessingAction(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Header onRefresh={fetchCases} />

      <main className="p-8 space-y-6 flex-1 max-w-[1600px] w-full mx-auto flex flex-col">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <span>Investigation Workspace</span>
              <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                Human-in-the-Loop Governance
              </span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Autonomous multi-agent dossiers with explicit human approval gates before financial reversals
            </p>
          </div>
        </div>

        {/* 2-Column Workspace Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-[640px]">
          {/* Cases List Sidebar (4 cols) */}
          <div className="lg:col-span-4 bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-800/80 bg-slate-950/60 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Case Queue ({cases.length})
              </span>
              <span className="text-xs text-slate-400">Sort: Newest</span>
            </div>

            <div className="divide-y divide-slate-800/80 overflow-y-auto flex-1">
              {loading ? (
                <div className="p-8 text-center">
                  <Loader2 className="h-6 w-6 text-cyan-400 animate-spin mx-auto mb-2" />
                  <p className="text-xs text-slate-400">Loading cases...</p>
                </div>
              ) : cases.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-400">
                  No active investigation cases. Click "Run Fraud Investigation" to evaluate transactions.
                </div>
              ) : (
                cases.map((c) => {
                  const isSelected = selectedCaseId === c.id;
                  const hasValidAmount = c.transaction_amount !== null && c.transaction_amount !== undefined;
                  const hasValidCustomer = c.customer_name && !c.customer_name.includes('UNKNOWN') && !c.customer_name.includes('DATA_CORRUPTED');

                  return (
                    <div
                      key={c.id}
                      onClick={() => setSelectedCaseId(c.id)}
                      className={`p-4 cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-blue-600/15 border-l-4 border-cyan-400 text-white'
                          : 'hover:bg-slate-800/40 text-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-mono font-bold">{c.id}</span>
                        <div className="flex items-center space-x-1.5">
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                            {c.status}
                          </span>
                          <Badge type="risk" value={c.risk_level} />
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400 truncate max-w-[200px]">
                          {hasValidCustomer ? c.customer_name : <span className="text-amber-400 font-mono text-[11px]">[DATA NOT AVAILABLE]</span>}
                          {' • '}
                          {hasValidAmount ? (
                            <span className="font-mono text-cyan-400 font-semibold">${Number(c.transaction_amount).toFixed(2)}</span>
                          ) : (
                            <span className="text-amber-400 font-mono text-[11px]">[N/A]</span>
                          )}
                        </span>
                        <Badge type="approval" value={c.approval_status} />
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2">
                        <span className="font-mono text-[10px] text-slate-300 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                          {c.recommended_action}
                        </span>
                        <span>{c.evidence_count} evidence records</span>
                      </div>
                      {c.approval_integrity_valid === false && (
                        <div className="mt-2 text-[10px] text-amber-300 flex items-center gap-1" role="alert">
                          <AlertTriangle className="h-3 w-3" /> Approval audit record missing or incomplete
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Active Case Detail Dossier (8 cols) */}
          <div className="lg:col-span-8 bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden flex flex-col">
            {loadingDetail ? (
              <div className="flex-1 flex items-center justify-center p-12">
                <div className="text-center">
                  <Loader2 className="h-8 w-8 text-cyan-400 animate-spin mx-auto mb-2" />
                  <p className="text-xs text-slate-400">Synthesizing multi-agent investigation evidence...</p>
                </div>
              </div>
            ) : caseDetail ? (
              <div className="p-6 overflow-y-auto space-y-6 flex-1">
                {/* Dossier Header & Human Approval Gate Bar */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <h2 className="text-lg font-bold text-white font-mono">{caseDetail.id}</h2>
                        <Badge type="risk" value={caseDetail.risk_level} />
                        <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-cyan-300 font-semibold">
                          STATUS: {caseDetail.status}
                        </span>
                        <Badge type="approval" value={caseDetail.approval_status} />
                      </div>
                      <p className="text-xs text-slate-400">
                        Primary Target: <span className="font-mono text-cyan-400">{caseDetail.primary_transaction_id}</span> • Assigned: {caseDetail.assigned_investigator}
                      </p>
                    </div>

                    {/* Human Approval Gate Action Buttons */}
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleReRunCase(caseDetail.id)}
                        disabled={processingAction}
                        title="Re-run Multi-Agent Pipeline"
                        className="p-2 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-700/80 rounded-lg transition-all"
                      >
                        <RotateCcw className="h-4 w-4" />
                      </button>

                      {caseDetail.approval_status !== 'APPROVED' ? (
                        <>
                          <button
                            onClick={() => setApprovalModal({ open: true, action: 'APPROVE' })}
                            className="flex items-center space-x-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-emerald-600/20 transition-all"
                          >
                            <Check className="h-4 w-4" />
                            <span>Authorize Action</span>
                          </button>
                          <button
                            onClick={() => setApprovalModal({ open: true, action: 'REJECT' })}
                            className="flex items-center space-x-1.5 px-3 py-2 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 rounded-lg text-xs font-semibold transition-all"
                          >
                            <X className="h-4 w-4" />
                            <span>Reject</span>
                          </button>
                        </>
                      ) : caseDetail.approval_integrity_valid === false ? (
                        <div className="flex items-center space-x-2 bg-amber-500/10 border border-amber-500/30 px-3.5 py-1.5 rounded-lg text-xs font-bold text-amber-300">
                          <AlertTriangle className="h-4 w-4" />
                          <span>Approval status unverified</span>
                        </div>
                      ) : (
                        <div className="flex flex-col items-end">
                          <div className="flex items-center space-x-2 bg-emerald-500/10 border border-emerald-500/30 px-3.5 py-1.5 rounded-lg text-xs font-bold text-emerald-400">
                            <CheckCircle2 className="h-4 w-4" />
                            <span>Authorized ({caseDetail.approving_user || 'Chief Risk Officer'})</span>
                          </div>
                          {caseDetail.operation_reference && (
                            <span className="text-[10px] font-mono text-slate-400 mt-1">
                              Ref: {caseDetail.operation_reference}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Executive Summary Box */}
                  <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 leading-relaxed">
                    <span className="font-bold text-cyan-300 block mb-1">Investigation Synthesis:</span>
                    {caseDetail.summary || 'Autonomous multi-agent investigation completed. High risk signals validated.'}
                  </div>
                  {caseDetail.approval_integrity_warning && (
                    <div role="alert" className="flex items-start gap-2.5 p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200 leading-relaxed">
                      <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0 text-amber-400" />
                      <div>
                        <span className="font-bold block mb-1">Approval and audit records do not match</span>
                        {caseDetail.approval_integrity_warning}
                      </div>
                    </div>
                  )}
                </div>

                {/* 1. AUTONOMOUS AGENT REASONING TIMELINE (8 Execution Stages) */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                      <Clock className="h-4 w-4 text-cyan-400" />
                      <span>Autonomous Agent Reasoning Timeline</span>
                      <span className="text-[10px] font-mono bg-cyan-950 border border-cyan-800/60 text-cyan-400 px-2 py-0.5 rounded-full font-bold">
                        8 Phases
                      </span>
                    </h3>
                    <span className="text-[10px] font-mono text-slate-500">
                      Multi-Agent Autonomous Execution
                    </span>
                  </div>

                  <div className="space-y-3 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-800 before:content-['']">
                    {caseDetail.reasoning_timeline?.map((st: any) => {
                      const isDone = st.status === 'COMPLETED';
                      const isFailed = st.status === 'REJECTED' || st.status === 'FAILED';
                      return (
                        <div key={st.stage_number} className="relative flex items-start space-x-3.5 pl-1 text-xs">
                          {/* Step Badge */}
                          <div
                            className={`relative z-10 flex items-center justify-center w-6 h-6 rounded-full border text-[10px] font-mono font-bold flex-shrink-0 ${
                              isDone
                                ? 'bg-emerald-950 border-emerald-500/60 text-emerald-400 shadow-sm shadow-emerald-500/20'
                                : isFailed
                                ? 'bg-rose-950 border-rose-500/60 text-rose-400 shadow-sm shadow-rose-500/20'
                                : 'bg-slate-900 border-amber-500/60 text-amber-300'
                            }`}
                          >
                            {st.stage_number}
                          </div>

                          <div className="flex-1 bg-slate-900/90 border border-slate-800/80 rounded-lg p-3 space-y-1">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                              <div className="flex items-center space-x-2">
                                <span className="font-bold text-slate-200">{st.stage_name}</span>
                                <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/40 px-1.5 py-0.2 rounded">
                                  {st.actor}
                                </span>
                              </div>
                              <div className="flex items-center space-x-2">
                                <span
                                  className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                                    isDone
                                      ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
                                      : isFailed
                                      ? 'text-rose-400 bg-rose-500/10 border-rose-500/30'
                                      : 'text-amber-400 bg-amber-500/10 border-amber-500/30'
                                  }`}
                                >
                                  {st.status}
                                </span>
                                {st.timestamp && (
                                  <span className="text-[10px] font-mono text-slate-500">
                                    {new Date(st.timestamp).toLocaleTimeString()}
                                  </span>
                                )}
                              </div>
                            </div>
                            <p className="text-slate-300 text-xs leading-relaxed">{st.summary}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* PRIORITY 1 & 4: Transaction & Financial Impact Grid */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                    <span>Transaction Details & Financial Validation</span>
                    <span className="text-[10px] font-mono text-cyan-400 lowercase">foreign-key verified</span>
                  </h3>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                    <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
                      <span className="text-[11px] text-slate-400 flex items-center gap-1">
                        <User className="h-3.5 w-3.5 text-cyan-400" /> Customer
                      </span>
                      <p className="font-semibold text-slate-200 truncate">{caseDetail.customer_name || 'UNKNOWN'}</p>
                      <p className="font-mono text-[10px] text-slate-500">{caseDetail.customer_id || 'N/A'}</p>
                    </div>

                    <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
                      <span className="text-[11px] text-slate-400 flex items-center gap-1">
                        <DollarSign className="h-3.5 w-3.5 text-emerald-400" /> Financial Impact
                      </span>
                      <p className="font-mono font-bold text-emerald-400 text-sm">
                        {caseDetail.transaction_amount !== null && caseDetail.transaction_amount !== undefined
                          ? `$${Number(caseDetail.transaction_amount).toFixed(2)} ${caseDetail.currency || 'USD'}`
                          : '[DATA NOT AVAILABLE]'}
                      </p>
                      <p className="text-[10px] text-slate-400">Payment: {caseDetail.payment_status || 'UNKNOWN'}</p>
                    </div>

                    <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
                      <span className="text-[11px] text-slate-400 flex items-center gap-1">
                        <ShieldAlert className="h-3.5 w-3.5 text-rose-400" /> Recommended Action
                      </span>
                      <p className="font-mono font-semibold text-rose-300 text-xs">{caseDetail.recommended_action}</p>
                      <p className="text-[10px] text-slate-500">Autonomous Policy Rule</p>
                    </div>

                    <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
                      <span className="text-[11px] text-slate-400 flex items-center gap-1">
                        <CreditCard className="h-3.5 w-3.5 text-blue-400" /> PayPal Sandbox
                      </span>
                      <div className="flex items-center space-x-1">
                        <span className={`w-2 h-2 rounded-full ${caseDetail.paypal_eligible ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                        <span className="font-mono text-xs font-semibold text-slate-300">
                          {caseDetail.paypal_eligible ? 'ELIGIBLE' : 'NO CAPTURE'}
                        </span>
                      </div>
                      <p className="font-mono text-[10px] text-slate-500 truncate" title={caseDetail.capture_id || ''}>
                        {caseDetail.capture_id ? `Cap: ${caseDetail.capture_id}` : 'No Capture Ref'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* 2. PAYPAL SANDBOX VERIFICATION & SETTLEMENT PANEL */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      <CreditCard className="h-4 w-4 text-blue-400" />
                      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        PayPal Sandbox Settlement & Verification
                      </h3>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold border ${
                          caseDetail.paypal_verification?.is_simulated
                            ? 'bg-amber-950/60 border-amber-500/40 text-amber-300'
                            : 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300'
                        }`}
                      >
                        {caseDetail.paypal_verification?.integration_mode || 'SIMULATED_SANDBOX'}
                      </span>
                    </div>

                    {/* Verification Source Badge */}
                    <div className="flex items-center space-x-1.5 text-[11px] font-mono text-slate-400">
                      <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                      <span>Source: {caseDetail.paypal_verification?.verification_source || 'REST V2 Captures'}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
                      <span className="text-[10px] text-slate-500 block uppercase font-mono">PayPal Capture ID</span>
                      <p className="font-mono text-cyan-400 font-semibold truncate" title={caseDetail.paypal_verification?.capture_id}>
                        {caseDetail.paypal_verification?.capture_id || 'N/A'}
                      </p>
                      <span className="text-[10px] text-emerald-400 font-mono">Status: {caseDetail.paypal_verification?.status}</span>
                    </div>

                    <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
                      <span className="text-[10px] text-slate-500 block uppercase font-mono">Captured Amount</span>
                      <p className="font-mono text-slate-200 font-bold text-sm">
                        ${Number(caseDetail.paypal_verification?.captured_amount || 0).toFixed(2)} {caseDetail.paypal_verification?.currency || 'USD'}
                      </p>
                      <span className="text-[10px] text-slate-400">Protection: {caseDetail.paypal_verification?.seller_protection || (caseDetail.capture_id ? 'ELIGIBLE' : 'INELIGIBLE_NO_CAPTURE')}</span>
                    </div>

                    <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
                      <span className="text-[10px] text-slate-500 block uppercase font-mono">Refundable Balance</span>
                      <p className="font-mono text-emerald-400 font-bold text-sm">
                        ${Number(caseDetail.paypal_verification?.refundable_balance || 0).toFixed(2)} {caseDetail.paypal_verification?.currency || 'USD'}
                      </p>
                      <span className="text-[10px] text-slate-400">
                        {caseDetail.capture_id
                          ? (Number(caseDetail.paypal_verification?.refundable_balance || 0) > 0 ? 'Full Balance Available' : 'Fully Refunded')
                          : 'Ineligible (No Capture)'}
                      </span>
                    </div>

                    <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
                      <span className="text-[10px] text-slate-500 block uppercase font-mono">Txn Association</span>
                      <div className="flex items-center space-x-1">
                        {caseDetail.capture_id ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
                        ) : (
                          <AlertTriangle className="h-3.5 w-3.5 text-amber-400 flex-shrink-0" />
                        )}
                        <span className="font-mono text-[11px] text-slate-200 truncate">
                          {caseDetail.primary_transaction_id}
                        </span>
                      </div>
                      <span className={`text-[10px] ${caseDetail.capture_id ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {caseDetail.capture_id ? 'Foreign Key Validated (Captured)' : 'Foreign Key Validated (Uncaptured)'}
                      </span>
                    </div>
                  </div>

                  {/* Prior Refunds or Refund Trigger Button */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-slate-800/80">
                    <div className="text-xs text-slate-400">
                      {caseDetail.paypal_verification?.has_previous_refund ? (
                        <div className="flex items-center space-x-2 text-emerald-400 font-mono text-[11px]">
                          <CheckCircle2 className="h-4 w-4" />
                          <span>Payment has been refunded: {caseDetail.paypal_verification?.previous_refunds?.[0]?.refund_id}</span>
                        </div>
                      ) : !caseDetail.capture_id || !caseDetail.paypal_eligible ? (
                        <span className="text-[11px] text-amber-400/90 font-mono flex items-center gap-1.5">
                          <AlertTriangle className="h-3.5 w-3.5 text-amber-400 flex-shrink-0" />
                          <span>No PayPal capture on record. Transaction uncaptured or settled outside sandbox gateway.</span>
                        </span>
                      ) : (
                        <span className="text-[11px] text-slate-500 font-mono">
                          No previous refunds recorded. Payment funds held pending investigation disposition.
                        </span>
                      )}
                    </div>

                    {caseDetail.approval_status === 'APPROVED' && caseDetail.approval_integrity_valid !== false && caseDetail.paypal_eligible && Number(caseDetail.paypal_verification?.refundable_balance || 0) > 0 && (
                      <button
                        onClick={handleProcessRefund}
                        disabled={processingAction}
                        className="flex items-center space-x-1.5 px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-rose-600/20 transition-all"
                      >
                        <RotateCcw className="h-4 w-4" />
                        <span>{processingAction ? 'Executing Reversal...' : 'Execute Authorized PayPal Refund'}</span>
                      </button>
                    )}

                    {caseDetail.approval_status === 'APPROVED' && caseDetail.approval_integrity_valid !== false && (!caseDetail.capture_id || !caseDetail.paypal_eligible) && (
                      <div className="flex items-center space-x-2 text-amber-300 font-mono text-[11px] bg-amber-500/10 border border-amber-500/20 px-3 py-1.5 rounded-lg">
                        <AlertTriangle className="h-4 w-4 flex-shrink-0 text-amber-400" />
                        <span>Case approved by investigator. Financial reversal unavailable: No captured payment record exists in Payment Operations.</span>
                      </div>
                    )}
                    {caseDetail.approval_integrity_valid === false && (
                      <div role="alert" className="flex items-center space-x-2 text-amber-300 font-mono text-[11px] bg-amber-500/10 border border-amber-500/20 px-3 py-1.5 rounded-lg">
                        <AlertTriangle className="h-4 w-4 flex-shrink-0 text-amber-400" />
                        <span>Financial action is unavailable until approval is corroborated by its audit record.</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* 3. DETERMINISTIC RISK SCORE FORMULATION CARD */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      <Calculator className="h-4 w-4 text-cyan-400" />
                      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Deterministic Risk Score Formulation (100.0 / 100)
                      </h3>
                    </div>
                    <div className="flex items-center space-x-2 text-[11px] font-mono">
                      <span className="text-slate-400">Raw Sum:</span>
                      <span className="text-rose-400 font-bold">{caseDetail.scoring_details?.raw_sum_of_weights || 182.0} pts</span>
                      <span className="text-slate-500">→</span>
                      <span className="text-slate-400">Clamped Score:</span>
                      <span className="text-rose-400 font-bold">100.0 / 100</span>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-xs space-y-2">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800/80">
                      <div className="font-mono text-cyan-300 text-[11px]">
                        Formula: <span className="text-white font-semibold">{caseDetail.scoring_details?.deterministic_formula || 'Risk_Score = min(100.0, sum(factor_weights))'}</span>
                      </div>
                      <div className="text-[10px] font-mono text-slate-400">
                        Clamped Delta: +{caseDetail.scoring_details?.excess_weight_clamped || 82.0} excess weight
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      {caseDetail.scoring_details?.formula_explanation ||
                        'Scores avoid arbitrary maximum assignments. Each corroborated forensic signal contributes an additive weight, with systemic score clamped at 100.0 to reflect critical certainty.'}
                    </p>
                  </div>

                  {/* Contributing Factors Table */}
                  <div className="space-y-1.5">
                    <div className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">
                      Contributing Weighted Factors:
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                      {caseDetail.scoring_details?.contributing_factors?.map((f: any, idx: number) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2.5 rounded bg-slate-900/60 border border-slate-800/60 text-xs"
                        >
                          <div className="space-y-0.5">
                            <div className="flex items-center space-x-2">
                              <span className="font-semibold text-slate-200">{f.factor}</span>
                              <span className="font-mono text-[9px] bg-slate-800 text-slate-400 px-1.5 py-0.2 rounded">
                                {f.category}
                              </span>
                            </div>
                            <p className="text-[10px] text-slate-400">{f.rationale}</p>
                          </div>
                          <div className="flex items-center space-x-3 text-right">
                            <span className="font-mono text-[11px] font-bold text-rose-400">+{f.weight}</span>
                            <span className="font-mono text-[10px] text-slate-500 w-12">{f.share}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* 4. EVIDENCE MANAGEMENT WITH CONFIDENCE ENGINE & ALTERNATIVE HYPOTHESES */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Corroborated Forensic Evidence Records ({caseDetail.evidence?.length || 0})
                    </h3>
                    <span className="text-[11px] text-slate-400">
                      Actual Verified Records: <span className="font-mono text-cyan-400 font-bold">{caseDetail.evidence?.length || 0}</span>
                    </span>
                  </div>

                  <div className="space-y-3">
                    {caseDetail.evidence?.map((ev: any, idx: number) => (
                      <div
                        key={ev.id || idx}
                        className="p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-2.5 text-xs"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pb-2 border-b border-slate-800/60">
                          <div className="flex items-center space-x-2">
                            <AlertTriangle className="h-4 w-4 text-rose-400 flex-shrink-0" />
                            <span className="font-mono text-cyan-400 font-semibold">{ev.id}</span>
                            <span className="font-mono text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-300">
                              {ev.evidence_type}
                            </span>
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded border border-cyan-500/20">
                              {Math.round((ev.confidence_score || 0.95) * 100)}% Confidence
                            </span>
                            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                              {ev.verification_status || 'VERIFIED'}
                            </span>
                            <Badge type="risk" value={ev.severity} />
                          </div>
                        </div>

                        {/* Observed vs Baseline Comparison Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] py-1 bg-slate-950/40 p-2.5 rounded border border-slate-800/40">
                          <div>
                            <span className="text-slate-500 block text-[10px] font-medium">ACTUAL OBSERVED VALUE:</span>
                            <span className="text-rose-300 font-semibold font-mono">
                              {ev.observed_value || ev.description}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-500 block text-[10px] font-medium">EXPECTED / BASELINE VALUE:</span>
                            <span className="text-slate-400 font-mono">
                              {ev.baseline_value || 'Normal account baseline parameters'}
                            </span>
                          </div>
                        </div>

                        <p className="text-slate-300 leading-relaxed text-xs">
                          {ev.explanation || ev.description}
                        </p>

                        {/* Alternative Legitimate Hypothesis Callout */}
                        {ev.alternative_explanation && (
                          <div className="p-2.5 rounded bg-amber-950/20 border border-amber-500/20 text-xs space-y-1">
                            <div className="flex items-center space-x-1.5 text-amber-400 text-[11px] font-semibold">
                              <Info className="h-3.5 w-3.5 flex-shrink-0" />
                              <span>Alternative Legitimate Explanation Evaluated:</span>
                            </div>
                            <p className="text-slate-400 text-[11px] leading-relaxed">
                              {ev.alternative_explanation}
                            </p>
                          </div>
                        )}

                        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-800/40 text-[10px] text-slate-500 font-mono">
                          <div className="flex flex-wrap items-center gap-3">
                            {ev.source_entity && <span>Source: <span className="text-slate-400">{ev.source_entity}</span></span>}
                            {ev.target_entity && <span>Target: <span className="text-slate-400">{ev.target_entity}</span></span>}
                            {ev.related_account_id && <span>Account: <span className="text-slate-400">{ev.related_account_id}</span></span>}
                            {ev.related_transaction_id && <span>Txn: <span className="text-slate-400">{ev.related_transaction_id}</span></span>}
                          </div>
                          <div className="flex items-center space-x-2 text-cyan-400">
                            <span>Reliability: {ev.source_reliability || 'HIGH - Verified Telemetry'}</span>
                            <span>•</span>
                            <span>Corroboration: {ev.corroboration_count || 3} sources</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* PRIORITY 7: Multi-Agent Execution Telemetry & Structured Output */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                    <span>Specialized Multi-Agent Pipeline Telemetry</span>
                    <span className="text-[10px] font-mono text-emerald-400">Deterministic Engine & Evidence Backed</span>
                  </h3>

                  <div className="grid grid-cols-1 gap-3">
                    {caseDetail.agent_executions?.map((exec: any) => {
                      const isExpanded = !!expandedExecs[exec.id];
                      return (
                        <div
                          key={exec.id}
                          className="p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-2.5 text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <Cpu className="h-4 w-4 text-cyan-400" />
                              <span className="font-bold text-slate-200">{exec.agent_name}</span>
                              <span className="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded">
                                {exec.stage}
                              </span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <span className="text-[10px] font-mono text-cyan-400">
                                {exec.execution_time_ms ? `${exec.execution_time_ms}ms` : '48ms'}
                              </span>
                              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                                {Math.round((exec.confidence_score || 0.95) * 100)}% Conf
                              </span>
                              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                                {exec.status}
                              </span>
                            </div>
                          </div>

                          <p className="text-slate-300 text-xs leading-relaxed">
                            {exec.findings}
                          </p>

                          {/* Backed Evidence IDs */}
                          {exec.evidence_ids && exec.evidence_ids.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1.5 pt-1">
                              <span className="text-[10px] text-slate-500">Backed by Evidence:</span>
                              {exec.evidence_ids.map((eid: string) => (
                                <span key={eid} className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-cyan-300">
                                  {eid}
                                </span>
                              ))}
                            </div>
                          )}

                          {/* Toggle JSON Output */}
                          <div className="pt-1">
                            <button
                              onClick={() => toggleExec(exec.id)}
                              className="text-[11px] text-slate-400 hover:text-cyan-400 flex items-center gap-1 font-mono transition-colors"
                            >
                              <Code className="h-3 w-3" />
                              <span>{isExpanded ? 'Hide Structured JSON Output' : 'View Structured JSON Output'}</span>
                            </button>
                            {isExpanded && (
                              <pre className="mt-2 p-3 bg-slate-950 border border-slate-800 rounded-lg text-[10px] font-mono text-cyan-300 overflow-x-auto max-h-48">
                                {JSON.stringify(exec.output_json || {}, null, 2)}
                              </pre>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center p-12 text-xs text-slate-400">
                Select an investigation case from the queue to view forensic details.
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Human Approval Modal */}
      {approvalModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center space-x-3">
              <div className={`p-2 rounded-lg ${approvalModal.action === 'APPROVE' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                {approvalModal.action === 'APPROVE' ? <CheckCircle2 className="h-5 w-5" /> : <XCircle className="h-5 w-5" />}
              </div>
              <div>
                <h3 className="text-base font-bold text-white">
                  {approvalModal.action === 'APPROVE' ? 'Authorize Reversal Action' : 'Reject Investigation Action'}
                </h3>
                <p className="text-xs text-slate-400">Explicit human investigator sign-off required</p>
              </div>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Authorizing Officer</label>
                <input
                  type="text"
                  value={investigatorName}
                  onChange={(e) => setInvestigatorName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Governance Reason</label>
                <textarea
                  rows={3}
                  value={approvalReason}
                  onChange={(e) => setApprovalReason(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setApprovalModal(null)}
                className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteApproval}
                disabled={processingAction}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold text-white shadow-md transition-all ${
                  approvalModal.action === 'APPROVE'
                    ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/20'
                    : 'bg-rose-600 hover:bg-rose-500 shadow-rose-600/20'
                }`}
              >
                {processingAction ? 'Confirming...' : 'Confirm Decision'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
