'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Header } from '@/components/Header';
import { Badge } from '@/components/Badge';
import {
  Bot,
  Layers,
  ArrowRight,
  Clock,
  CheckCircle2,
  AlertCircle,
  Code2,
  ChevronDown,
  ChevronUp,
  Cpu,
  Loader2,
  Play,
  Filter,
  FileSearch,
  ShieldAlert
} from 'lucide-react';

export default function AIInvestigationPage() {
  const [executions, setExecutions] = useState<any[]>([]);
  const [cases, setCases] = useState<any[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);
  const [expandedJson, setExpandedJson] = useState<Record<string, boolean>>({});
  const [runningPipeline, setRunningPipeline] = useState(false);

  const fetchCasesAndExecutions = async (caseId?: string) => {
    setLoading(true);
    try {
      const [casesData, execData] = await Promise.all([
        api.getInvestigations(),
        api.getAgentExecutions({
          case_id: caseId && caseId !== 'ALL' ? caseId : undefined,
          limit: 50,
        }),
      ]);
      setCases(casesData);
      setExecutions(execData);
    } catch (err) {
      console.error('Failed to fetch agent executions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCasesAndExecutions(selectedCaseId);
  }, [selectedCaseId]);

  const toggleJson = (id: string) => {
    setExpandedJson((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleTriggerPipeline = async () => {
    setRunningPipeline(true);
    try {
      await api.runFullInvestigation();
      await fetchCasesAndExecutions(selectedCaseId);
    } catch (err: any) {
      alert(`Pipeline execution error: ${err.message}`);
    } finally {
      setRunningPipeline(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Header onRefresh={() => fetchCasesAndExecutions(selectedCaseId)} />

      <main className="p-8 space-y-6 flex-1 max-w-[1600px] w-full mx-auto">
        {/* Title & Dispatch Button */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <span>AI Investigation Center</span>
              <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                Multi-Agent Orchestration Telemetry
              </span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Live sequential DAG reasoning logs with structured outputs, confidence scores, and unalterable factual risk factors
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5">
              <span className="text-xs text-slate-400 font-medium">Filter Dossier:</span>
              <select
                value={selectedCaseId}
                onChange={(e) => setSelectedCaseId(e.target.value)}
                className="bg-transparent text-xs text-white font-mono focus:outline-none cursor-pointer"
              >
                <option value="ALL" className="bg-slate-900">All Case Telemetry</option>
                {cases.map((c) => (
                  <option key={c.id} value={c.id} className="bg-slate-900">
                    {c.id} ({c.risk_level} • ${c.transaction_amount?.toFixed(2)})
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleTriggerPipeline}
              disabled={runningPipeline}
              className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-blue-500/20 transition-all disabled:opacity-50"
            >
              {runningPipeline ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 fill-current" />}
              <span>Dispatch Multi-Agent Pipeline</span>
            </button>
          </div>
        </div>

        {/* Pipeline Architecture Visual Roadmap */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 overflow-x-auto">
          <div className="flex items-center justify-between min-w-[800px] space-x-3 text-xs">
            {[
              { stage: 'Transaction Intel', desc: 'Velocity & Value Spikes' },
              { stage: 'Identity Intel', desc: 'Emulator & Card Collisions' },
              { stage: 'Graph Engine', desc: 'NetworkX Ring Traversal' },
              { stage: 'Fraud Investigation', desc: 'Multi-Account Synthesis' },
              { stage: 'Risk Assessment', desc: 'Deterministic Risk & Anomaly' },
              { stage: 'Autonomous Response', desc: 'Human-Gated PayPal Action' },
            ].map((st, idx) => (
              <React.Fragment key={st.stage}>
                <div className="flex-1 bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-1">
                  <span className="text-[10px] font-mono text-cyan-400 font-bold">STAGE 0{idx + 1}</span>
                  <div className="font-semibold text-white truncate">{st.stage}</div>
                  <div className="text-[11px] text-slate-400 truncate">{st.desc}</div>
                </div>
                {idx < 5 && <ArrowRight className="h-4 w-4 text-slate-600 flex-shrink-0" />}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Executions Feed */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Live Execution Telemetry ({executions.length} stages)</h3>
            <span className="text-xs text-slate-400 font-mono">Backend Stream: Active</span>
          </div>

          {loading ? (
            <div className="text-center py-20">
              <Loader2 className="h-8 w-8 text-cyan-400 animate-spin mx-auto mb-2" />
              <p className="text-xs text-slate-400">Loading multi-agent execution telemetry...</p>
            </div>
          ) : executions.length === 0 ? (
            <div className="text-center py-20 bg-slate-900/40 border border-slate-800/80 rounded-xl p-8">
              <Bot className="h-10 w-10 text-slate-600 mx-auto mb-3" />
              <p className="text-sm font-medium text-slate-300">No agent executions recorded yet.</p>
              <p className="text-xs text-slate-500 mt-1">Click "Dispatch Multi-Agent Pipeline" to run investigation.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {executions.map((exec) => {
                const isExpanded = expandedJson[exec.id];
                return (
                  <div
                    key={exec.id}
                    className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 space-y-3 transition-all hover:border-slate-700/80"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 rounded-lg bg-blue-500/10 text-cyan-400">
                          <Cpu className="h-4 w-4" />
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm font-bold text-white">{exec.agent_name}</span>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-950 text-cyan-300 border border-slate-800">
                              {exec.stage}
                            </span>
                          </div>
                          <span className="text-xs text-slate-400 font-mono">
                            Case Dossier: <span className="text-slate-200">{exec.case_id}</span>
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-3">
                        <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          Confidence: {(exec.confidence_score * 100).toFixed(0)}%
                        </span>
                        <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(exec.started_at).toLocaleTimeString()}
                        </span>
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                          {exec.status}
                        </span>
                      </div>
                    </div>

                    {/* Agent Summary Findings */}
                    <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 text-xs text-slate-300 leading-relaxed font-sans">
                      <span className="font-semibold text-cyan-300 block mb-1">Synthesized Findings:</span>
                      {exec.findings}
                    </div>

                    {/* Expandable JSON Payload */}
                    <div className="pt-2 flex items-center justify-between text-xs">
                      <button
                        onClick={() => toggleJson(exec.id)}
                        className="inline-flex items-center space-x-1.5 text-slate-400 hover:text-cyan-300 font-mono text-[11px] transition-colors"
                      >
                        <Code2 className="h-3.5 w-3.5" />
                        <span>{isExpanded ? 'Hide Raw Agent JSON' : 'Inspect Output JSON'}</span>
                        {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      </button>
                    </div>

                    {isExpanded && (
                      <pre className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-cyan-300 overflow-x-auto max-h-72">
                        {JSON.stringify(exec.output_json, null, 2)}
                      </pre>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
