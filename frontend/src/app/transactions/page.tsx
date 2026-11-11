'use client';

import React, { useEffect, useState, useMemo, useRef } from 'react';
import Link from 'next/link';
import { AgGridReact } from 'ag-grid-react';
import { ColDef, GridReadyEvent, RowClickedEvent } from 'ag-grid-community';
import { api } from '@/lib/api';
import { Header } from '@/components/Header';
import { Badge } from '@/components/Badge';
import {
  Search,
  Download,
  Filter,
  X,
  ShieldAlert,
  Play,
  CheckCircle2,
  AlertTriangle,
  Monitor,
  CreditCard,
  User,
  Globe,
  Loader2,
  Layers,
  FileSearch,
  ArrowRight
} from 'lucide-react';

export default function TransactionsPage() {
  const [rowData, setRowData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState<string>('ALL');
  const [selectedTxn, setSelectedTxn] = useState<any | null>(null);
  const [txnDetail, setTxnDetail] = useState<any | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const gridRef = useRef<AgGridReact>(null);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const data = await api.getTransactions({
        risk_category: riskFilter === 'ALL' ? undefined : riskFilter,
        search: searchQuery || undefined,
        limit: 200,
      });
      setRowData(data);
    } catch (err) {
      console.error('Failed to fetch transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, [riskFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchTransactions();
  };

  const onRowClicked = async (event: RowClickedEvent) => {
    setSelectedTxn(event.data);
    setLoadingDetail(true);
    try {
      const detail = await api.getTransactionDetail(event.data.id);
      setTxnDetail(detail);
    } catch (err) {
      console.error('Failed to load transaction detail:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleRunAnalysis = async (txnId: string) => {
    setAnalyzing(true);
    try {
      await api.analyzeTransaction(txnId);
      // Reload both table and drawer
      await fetchTransactions();
      const detail = await api.getTransactionDetail(txnId);
      setTxnDetail(detail);
      setSelectedTxn(detail);
    } catch (err) {
      console.error('Failed to analyze transaction:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  const onExportCsv = () => {
    if (gridRef.current?.api) {
      gridRef.current.api.exportDataAsCsv({
        fileName: `AgentShield_Transactions_${new Date().toISOString().slice(0, 10)}.csv`,
      });
    }
  };

  // AG Grid Column Definitions
  const columnDefs = useMemo<ColDef[]>(() => [
    {
      field: 'id',
      headerName: 'Transaction ID',
      width: 175,
      minWidth: 160,
      pinned: 'left',
      cellRenderer: (params: any) => (
        <span className="font-mono text-cyan-400 font-medium cursor-pointer hover:underline">
          {params.value}
        </span>
      ),
    },
    {
      field: 'customer_name',
      headerName: 'Customer',
      width: 275,
      minWidth: 230,
      wrapText: false,
      cellRenderer: (params: any) => (
        <div className="flex flex-col justify-center min-w-0 w-full h-full leading-tight py-1">
          <span className="font-medium text-slate-200 text-xs truncate" title={params.value || params.data.customer_id}>
            {params.value || params.data.customer_id}
          </span>
          <span className="text-[10px] text-slate-400 font-mono truncate" title={params.data.customer_email}>
            {params.data.customer_email || params.data.customer_id}
          </span>
        </div>
      ),
    },
    {
      field: 'amount',
      headerName: 'Amount',
      width: 155,
      minWidth: 135,
      cellRenderer: (params: any) => (
        <span className="font-mono font-bold text-white whitespace-nowrap">
          ${params.value !== undefined ? Number(params.value).toFixed(2) : '0.00'} {params.data?.currency || 'USD'}
        </span>
      ),
    },
    {
      field: 'risk_category',
      headerName: 'Risk Category',
      width: 155,
      minWidth: 140,
      cellRenderer: (params: any) => <Badge type="risk" value={params.value} />,
    },
    {
      field: 'risk_score',
      headerName: 'Risk Score',
      width: 155,
      minWidth: 140,
      cellRenderer: (params: any) => {
        const val = params.value ?? 0;
        const color = val >= 85
          ? 'text-rose-400 bg-rose-500/10 border-rose-500/30'
          : val >= 65
          ? 'text-orange-400 bg-orange-500/10 border-orange-500/30'
          : val >= 40
          ? 'text-amber-400 bg-amber-500/10 border-amber-500/30'
          : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
        return (
          <div className="flex items-center h-full">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-mono font-bold border whitespace-nowrap ${color}`}>
              {val.toFixed(1)} / 100
            </span>
          </div>
        );
      },
    },
    {
      field: 'payment_status',
      headerName: 'Payment Status',
      width: 160,
      minWidth: 140,
      cellRenderer: (params: any) => <Badge type="status" value={params.value} />,
    },
    {
      field: 'investigation_status',
      headerName: 'Investigation',
      width: 175,
      minWidth: 155,
      cellRenderer: (params: any) => {
        const val = params.value || 'NONE';
        const color = val === 'INVESTIGATING' ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30' : val === 'RESOLVED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-slate-800 text-slate-400 border-slate-700';
        return (
          <span className={`px-2 py-0.5 rounded text-[11px] font-mono border whitespace-nowrap ${color}`}>
            {val}
          </span>
        );
      },
    },
    {
      field: 'device_id',
      headerName: 'Device ID',
      width: 180,
      minWidth: 150,
      cellRenderer: (params: any) => (
        <span className="font-mono text-xs text-slate-400 truncate" title={params.value}>
          {params.value || '—'}
        </span>
      ),
    },
    {
      field: 'ip_address',
      headerName: 'IP Address',
      width: 160,
      minWidth: 135,
      cellRenderer: (params: any) => (
        <span className="font-mono text-xs text-slate-300">
          {params.value || '—'}
        </span>
      ),
    },
    {
      field: 'timestamp',
      headerName: 'Timestamp',
      width: 195,
      minWidth: 180,
      cellRenderer: (params: any) => (
        <span className="text-xs text-slate-400 font-mono whitespace-nowrap">
          {params.value ? new Date(params.value).toLocaleString() : '—'}
        </span>
      ),
    },
  ], []);

  const defaultColDef = useMemo<ColDef>(() => ({
    sortable: true,
    filter: true,
    resizable: true,
  }), []);

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Header onRefresh={fetchTransactions} />

      <main className="p-4 sm:p-6 lg:p-8 space-y-6 flex-1 max-w-[1600px] w-full mx-auto min-w-0">
        {/* Page Title & Controls */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <span>Transaction Intelligence</span>
              <span className="text-xs font-mono text-slate-400 px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
                AG Grid Transaction Table
              </span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Transaction ledger with heuristic risk scores and linked-record context
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onExportCsv}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700/80 rounded-md text-xs font-medium transition-all"
            >
              <Download className="h-3.5 w-3.5 text-cyan-400" />
              <span>Export CSV</span>
            </button>
          </div>
        </div>

        {/* Filters Toolbar */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
          <form onSubmit={handleSearchSubmit} className="flex items-center space-x-2 flex-1 max-w-md">
            <div className="relative flex-1">
              <Search className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search transaction ID, customer, account ID, or IP..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
              />
            </div>
            <button
              type="submit"
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium transition-all"
            >
              Search
            </button>
          </form>

          {/* Risk Level Pills */}
          <div className="flex items-center space-x-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
            {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((tier) => (
              <button
                key={tier}
                onClick={() => setRiskFilter(tier)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  riskFilter === tier
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                {tier}
              </button>
            ))}
          </div>
        </div>

        {/* AG Grid Table */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl overflow-hidden shadow-xl">
          <div className="p-3 bg-slate-950 border-b border-slate-800/80 flex items-center justify-between text-xs">
            <span className="text-slate-400 font-medium">
              Transaction Records: <strong className="text-white font-mono">{rowData.length}</strong> loaded
            </span>
            <span className="text-slate-500 font-mono text-[11px]">
              Click any row to open forensic intelligence drawer
            </span>
          </div>
          <div className="ag-theme-alpine-dark w-full min-w-0 h-[560px] sm:h-[620px]">
            <AgGridReact
              ref={gridRef}
              rowData={rowData}
              columnDefs={columnDefs}
              defaultColDef={defaultColDef}
              rowSelection="single"
              rowHeight={58}
              headerHeight={44}
              pagination={true}
              paginationPageSize={10}
              paginationPageSizeSelector={[10, 20, 50, 100]}
              onRowClicked={onRowClicked}
              animateRows={true}
              enableCellTextSelection={true}
              suppressHorizontalScroll={false}
            />
          </div>
        </div>
      </main>

      {/* Transaction Details Slide-over Drawer */}
      {selectedTxn && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/70 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-xl bg-slate-900 border-l border-slate-800 shadow-2xl h-full flex flex-col animate-in slide-in-from-right duration-200">
            {/* Drawer Header */}
            <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="text-base font-bold text-white font-mono">{selectedTxn.id}</span>
                  <Badge type="risk" value={selectedTxn.risk_category} />
                </div>
                <p className="text-xs text-slate-400">
                  Transaction Forensic Intelligence Dossier
                </p>
              </div>

              <button
                onClick={() => setSelectedTxn(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="p-6 overflow-y-auto flex-1 space-y-6">
              {loadingDetail ? (
                <div className="text-center py-16">
                  <Loader2 className="h-6 w-6 text-cyan-400 animate-spin mx-auto mb-2" />
                  <p className="text-xs text-slate-400">Loading forensic evidence...</p>
                </div>
              ) : (
                <>
                  {/* Financial & Risk Summary Card */}
                  <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Amount & Settlement
                      </span>
                      <Badge type="status" value={selectedTxn.payment_status} />
                    </div>
                    <div className="flex items-baseline justify-between">
                      <span className="text-3xl font-bold font-mono text-white">
                        ${selectedTxn.amount?.toFixed(2)} {selectedTxn.currency}
                      </span>
                      <span className="text-sm font-mono font-bold text-cyan-400">
                        Risk: {selectedTxn.risk_score?.toFixed(1)}/100
                      </span>
                    </div>

                    <div className="pt-3 border-t border-slate-800/80 flex flex-col space-y-2">
                      <button
                        onClick={() => handleRunAnalysis(selectedTxn.id)}
                        disabled={analyzing}
                        className="w-full flex items-center justify-center space-x-2 py-2 rounded-lg bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-xs font-medium shadow-md shadow-blue-500/20 transition-all disabled:opacity-50"
                      >
                        {analyzing ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Play className="h-3.5 w-3.5 fill-current" />
                        )}
                        <span>Run Investigation Analysis</span>
                      </button>

                      {txnDetail?.investigations && txnDetail.investigations.length > 0 && (
                        <Link
                          href="/investigations"
                          className="w-full flex items-center justify-center space-x-2 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-cyan-300 border border-cyan-500/30 text-xs font-medium transition-all"
                        >
                          <FileSearch className="h-3.5 w-3.5 text-cyan-400" />
                          <span>Review Case Dossier ({txnDetail.investigations[0].id || 'Active Case'})</span>
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Link>
                      )}
                    </div>
                  </div>

                  {/* Customer Account Details */}
                  {txnDetail?.customer && (
                    <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-5 space-y-3">
                      <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
                        <User className="h-4 w-4 text-cyan-400" />
                        <span>Customer Profile</span>
                      </div>
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div>
                          <span className="text-slate-400 block">Name</span>
                          <span className="text-white font-medium">{txnDetail.customer.full_name}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block">Email</span>
                          <span className="text-white font-mono">{txnDetail.customer.email}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block">Account Age</span>
                          <span className="text-white font-mono">{txnDetail.customer.account_age_days} days</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block">Risk Rating</span>
                          <Badge type="risk" value={txnDetail.customer.risk_rating} />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Device & Hardware Profile */}
                  {txnDetail?.device && (
                    <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-5 space-y-3">
                      <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
                        <Monitor className="h-4 w-4 text-blue-400" />
                        <span>Hardware & Device Fingerprint</span>
                      </div>
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div>
                          <span className="text-slate-400 block">Device Type</span>
                          <span className="text-white font-medium">{txnDetail.device.device_type}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block">Emulator Runtime</span>
                          <span className={txnDetail.device.is_emulator ? 'text-rose-400 font-bold' : 'text-emerald-400'}>
                            {txnDetail.device.is_emulator ? 'YES (EMULATOR DETECTED)' : 'NO (PHYSICAL HARDWARE)'}
                          </span>
                        </div>
                        <div className="col-span-2">
                          <span className="text-slate-400 block">Fingerprint Hash</span>
                          <span className="text-slate-300 font-mono text-[11px] break-all">{txnDetail.device.device_fingerprint}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Payment Identity & Credential Details */}
                  {txnDetail?.payment_identity && (
                    <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-5 space-y-3">
                      <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
                        <CreditCard className="h-4 w-4 text-indigo-400" />
                        <span>Payment Identity Token</span>
                      </div>
                      <div className="space-y-2 text-xs">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Card / Account Mask</span>
                          <span className="text-white font-mono font-medium">{txnDetail.payment_identity.masked_value}</span>
                        </div>
                        {txnDetail.payment_identity.risk_flags?.length > 0 && (
                          <div className="p-2 rounded bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[11px]">
                            Flags: {txnDetail.payment_identity.risk_flags.join(', ')}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* IP Indicator */}
                  <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-5 space-y-2">
                    <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
                      <Globe className="h-4 w-4 text-emerald-400" />
                      <span>Network Indicator</span>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-slate-400">IP Origin Address</span>
                      <span className="text-white font-mono">{selectedTxn.ip_address || '192.168.1.1'}</span>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
