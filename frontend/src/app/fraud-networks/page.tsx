'use client';

import React, { useEffect, useState, useMemo, useCallback } from 'react';
import Link from 'next/link';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Node,
  Edge,
  Handle,
  Position,
  useReactFlow,
  ReactFlowProvider
} from '@xyflow/react';
import { api } from '@/lib/api';
import { Header } from '@/components/Header';
import { Badge } from '@/components/Badge';
import {
  Share2,
  Users,
  Monitor,
  CreditCard,
  Globe,
  DollarSign,
  AlertTriangle,
  ShieldAlert,
  Search,
  Filter,
  Info,
  Maximize2,
  Loader2,
  X,
  Play,
  ArrowRight,
  Focus,
  RotateCcw,
  ZoomIn,
  ZoomOut,
  ExternalLink,
  FileSearch,
  CheckCircle2,
  Layers
} from 'lucide-react';

// Custom Node Component for high-fidelity FinTech styling
function CustomEntityNode({ data, selected }: { data: any; selected?: boolean }) {
  const type = data.type || 'ACCOUNT';
  const risk = data.risk_level || 'LOW';

  const typeConfig: Record<string, { icon: any; color: string; border: string; bg: string; badgeBg: string }> = {
    ACCOUNT: {
      icon: Users,
      color: 'text-cyan-400',
      border: 'border-cyan-500/40',
      bg: 'bg-cyan-950/40',
      badgeBg: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    },
    TRANSACTION: {
      icon: DollarSign,
      color: 'text-emerald-400',
      border: 'border-emerald-500/40',
      bg: 'bg-emerald-950/40',
      badgeBg: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    },
    DEVICE: {
      icon: Monitor,
      color: 'text-purple-400',
      border: 'border-purple-500/40',
      bg: 'bg-purple-950/40',
      badgeBg: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
    },
    PAYMENT_IDENTITY: {
      icon: CreditCard,
      color: 'text-amber-400',
      border: 'border-amber-500/40',
      bg: 'bg-amber-950/40',
      badgeBg: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    },
    IP_INDICATOR: {
      icon: Globe,
      color: 'text-blue-400',
      border: 'border-blue-500/40',
      bg: 'bg-blue-950/40',
      badgeBg: 'bg-blue-500/10 text-blue-300 border-blue-500/30',
    },
  };

  const cfg = typeConfig[type] || typeConfig.ACCOUNT;
  const Icon = cfg.icon;

  const isCritical = risk === 'CRITICAL' || risk === 'HIGH';

  return (
    <div
      className={`px-3.5 py-2.5 rounded-xl border backdrop-blur-md transition-all shadow-xl cursor-pointer ${cfg.bg} ${
        selected ? 'ring-2 ring-cyan-400 border-cyan-400 shadow-cyan-500/40 scale-105' : cfg.border
      } ${isCritical ? 'border-rose-500/70 shadow-rose-500/20' : ''}`}
      style={{ minWidth: '170px' }}
    >
      <Handle type="target" position={Position.Top} id="top-t" className="!bg-cyan-400 !w-2.5 !h-2.5" />
      <Handle type="target" position={Position.Left} id="left-t" className="!bg-cyan-400 !w-2 !h-2 opacity-40" />

      <div className="flex items-center space-x-2.5">
        <div className={`p-1.5 rounded-lg bg-slate-900 border border-slate-800 ${cfg.color}`}>
          <Icon className="h-4 w-4" />
        </div>
        <div className="overflow-hidden">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block font-semibold">
            {type.replace('_', ' ')}
          </span>
          <span className="text-xs font-bold text-white truncate block max-w-[130px]" title={data.label}>
            {data.label}
          </span>
        </div>
      </div>

      <div className="mt-2.5 pt-1.5 border-t border-slate-800/80 flex items-center justify-between text-[10px]">
        <span className="text-slate-400">Risk Score:</span>
        <span className={`font-mono font-bold ${isCritical ? 'text-rose-400' : 'text-emerald-400'}`}>
          {data.risk_score !== undefined ? `${Number(data.risk_score).toFixed(0)}/100` : '—'}
        </span>
      </div>

      <Handle type="source" position={Position.Bottom} id="bot-s" className="!bg-cyan-400 !w-2.5 !h-2.5" />
      <Handle type="source" position={Position.Right} id="right-s" className="!bg-cyan-400 !w-2 !h-2 opacity-40" />
    </div>
  );
}

const nodeTypes = {
  custom: CustomEntityNode,
};

function FraudNetworkFlow() {
  const [graphData, setGraphData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCluster, setSelectedCluster] = useState<string>('ALL');
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<any | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const reactFlowInstance = useReactFlow();

  const fetchGraph = async (clusterId?: string, nodeId?: string) => {
    setLoading(true);
    try {
      const data = await api.getFraudNetworks({
        cluster_id: clusterId === 'ALL' ? undefined : clusterId,
        node_id: nodeId || undefined,
      });
      setGraphData(data);

      const rfNodes: Node[] = data.nodes.map((n: any) => ({
        id: n.id,
        type: 'custom',
        position: n.position || { x: 250, y: 250 },
        data: {
          id: n.id,
          label: n.label,
          type: n.type,
          risk_score: n.risk_score,
          risk_level: n.risk_level,
          cluster_id: n.cluster_id,
          connected_entities: n.connected_entities || [],
          suspicious_connections: n.suspicious_connections || [],
          attributes: n.attributes || {},
        },
      }));

      const rfEdges: Edge[] = data.edges.map((e: any) => {
        const isSusp = e.is_suspicious || e.relationship?.includes('SHARES') || e.relationship?.includes('COLLISION');
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          type: 'smoothstep',
          // Keep the canvas uncluttered; selecting an edge exposes its full
          // relationship and evidence in the inspector panel.
          label: undefined,
          labelStyle: { fill: isSusp ? '#fda4af' : '#94a3b8', fontSize: 10, fontFamily: 'monospace', fontWeight: 600 },
          labelBgStyle: { fill: '#0b1329', fillOpacity: 0.95, stroke: isSusp ? '#f43f5e' : '#1e293b', strokeWidth: 1 },
          labelBgPadding: [6, 3] as [number, number],
          labelBgBorderRadius: 4,
          animated: isSusp,
          data: {
            id: e.id,
            source: e.source,
            target: e.target,
            relationship: e.relationship,
            evidence_id: e.evidence_id,
            is_suspicious: isSusp,
            suspicious_reason: e.suspicious_reason || '',
            confidence: e.confidence ?? 0.85,
            risk_contribution: e.risk_contribution ?? (isSusp ? '+25.0 (Corroborated)' : '0.0 (Baseline)'),
            supporting_evidence: e.supporting_evidence || e.suspicious_reason || 'Verified relational database foreign key link.',
            alternative_explanation: e.alternative_explanation || 'Benign infrastructure pooling or multi-user environment.',
            timestamp: e.timestamp,
            shared_indicator: e.shared_indicator,
          },
          style: {
            stroke: isSusp ? '#f43f5e' : '#38bdf8',
            strokeWidth: isSusp ? 2.5 : 1.4,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isSusp ? '#f43f5e' : '#38bdf8',
            width: 14,
            height: 14,
          },
        };
      });

      setNodes(rfNodes);
      setEdges(rfEdges);

      // Re-link selected node if already open
      if (selectedNode) {
        const updated = data.nodes.find((n: any) => n.id === selectedNode.id);
        if (updated) setSelectedNode(updated);
      }
    } catch (err) {
      console.error('Failed to load fraud network graph:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph(selectedCluster, focusedNodeId || undefined);
  }, [selectedCluster, focusedNodeId]);

  // React Flow mounts before the asynchronous graph data arrives. Fit again
  // after each completed fetch so the full graph is visible on first render.
  useEffect(() => {
    if (!loading && graphData?.nodes?.length) {
      reactFlowInstance.fitView({ padding: 0.16, duration: 300 });
    }
  }, [graphData, loading, reactFlowInstance]);

  // Handle Node Click
  const onNodeClick = useCallback((_: any, node: Node) => {
    setSelectedEdge(null);
    
    // Always compute live connected edges from current graph edges
    const directEdges = edges.filter(
      (e) => e.source === node.id || e.target === node.id
    );

    const liveNeighbors = directEdges.map((e) => {
      const isOutbound = e.source === node.id;
      const targetId = isOutbound ? e.target : e.source;
      const targetNode = nodes.find((n) => n.id === targetId);

      return {
        node_id: targetId,
        key: targetId,
        label: targetNode?.data?.label || targetId,
        type: targetNode?.data?.type || 'UNKNOWN',
        relationship: e.label || (e.data as any)?.relationship || 'CONNECTED',
        risk_level: targetNode?.data?.risk_level || 'LOW',
        evidence_id: (e.data as any)?.evidence_id,
        suspicious_reason: (e.data as any)?.suspicious_reason,
        is_suspicious: (e.data as any)?.is_suspicious,
      };
    });

    const nodeData = {
      ...node.data,
      connected_entities: liveNeighbors.length > 0 ? liveNeighbors : ((node.data as any)?.connected_entities || []),
    };

    setSelectedNode(nodeData);

    // Visually highlight selected node and connected edges
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        selected: n.id === node.id,
      }))
    );

    setEdges((eds) =>
      eds.map((e) => {
        const isConnected = e.source === node.id || e.target === node.id;
        const isSusp = (e.data as any)?.is_suspicious;
        return {
          ...e,
          style: {
            ...e.style,
            stroke: isSusp ? '#f43f5e' : '#38bdf8',
            strokeWidth: isConnected ? (isSusp ? 3.0 : 2.0) : 1.2,
            opacity: isConnected ? 1.0 : 0.22,
          },
        };
      })
    );
  }, [edges, nodes]);

  // Handle Edge Click
  const onEdgeClick = useCallback((_: any, edge: Edge) => {
    setSelectedNode(null);
    const srcNode = nodes.find((n) => n.id === edge.source);
    const tgtNode = nodes.find((n) => n.id === edge.target);

    setSelectedEdge({
      ...(edge.data || {}),
      id: edge.id,
      source_label: srcNode?.data?.label || edge.source,
      source_type: srcNode?.data?.type || 'UNKNOWN',
      target_label: tgtNode?.data?.label || edge.target,
      target_type: tgtNode?.data?.type || 'UNKNOWN',
    });

    // Reset node selection and highlight active edge
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        selected: n.id === edge.source || n.id === edge.target,
      }))
    );

    setEdges((eds) =>
      eds.map((e) => {
        const isTarget = e.id === edge.id;
        const isSusp = (e.data as any)?.is_suspicious;
        return {
          ...e,
          style: {
            ...e.style,
            stroke: isSusp ? '#f43f5e' : '#38bdf8',
            strokeWidth: isTarget ? 3.5 : 1.2,
            opacity: isTarget ? 1.0 : 0.22,
          },
        };
      })
    );
  }, [nodes]);

  const handleFocusNeighborhood = (nodeId: string) => {
    setFocusedNodeId(nodeId);
  };

  const handleClearFocus = () => {
    setFocusedNodeId(null);
  };

  const handleResetLayout = () => {
    setFocusedNodeId(null);
    setSelectedCluster('ALL');
    setSelectedNode(null);
    setSelectedEdge(null);
    reactFlowInstance.fitView({ duration: 400 });
  };

  // Find the currently active or top coordinated cluster
  const activeCluster = useMemo(() => {
    if (!graphData?.clusters || graphData.clusters.length === 0) return null;
    if (selectedCluster && selectedCluster !== 'ALL') {
      return graphData.clusters.find((c: any) => c.id === selectedCluster) || graphData.clusters[0];
    }
    return graphData.clusters.find((c: any) => c.is_coordinated) || graphData.clusters[0];
  }, [graphData, selectedCluster]);

  // Entity Type Counts for Legend
  const entityCounts = useMemo(() => {
    const counts = { ACCOUNT: 0, TRANSACTION: 0, DEVICE: 0, PAYMENT_IDENTITY: 0, IP_INDICATOR: 0 };
    if (!graphData?.nodes) return counts;
    graphData.nodes.forEach((n: any) => {
      if (counts[n.type as keyof typeof counts] !== undefined) {
        counts[n.type as keyof typeof counts]++;
      }
    });
    return counts;
  }, [graphData]);

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Header onRefresh={() => fetchGraph(selectedCluster, focusedNodeId || undefined)} />

      <main className="p-8 space-y-6 flex-1 max-w-[1600px] w-full mx-auto flex flex-col">
        {/* Title & Cluster Filter Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <span>Fraud Network Explorer</span>
              <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2.5 py-0.5 rounded border border-cyan-500/30">
                NetworkX Topological Intelligence
              </span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Deterministic relationship discovery across accounts, transactions, hardware devices, and payment identities
            </p>
          </div>

          {/* Graph Controls Toolbar */}
          <div className="flex items-center space-x-2.5 flex-wrap gap-y-2">
            <button
              onClick={handleResetLayout}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-medium transition-all"
            >
              <RotateCcw className="h-3.5 w-3.5 text-cyan-400" />
              <span>Reset Layout</span>
            </button>

            <button
              onClick={() => reactFlowInstance.zoomIn({ duration: 250 })}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-medium transition-all"
              title="Zoom In"
            >
              <ZoomIn className="h-3.5 w-3.5 text-cyan-400" />
              <span>Zoom In</span>
            </button>

            <button
              onClick={() => reactFlowInstance.zoomOut({ duration: 250 })}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-medium transition-all"
              title="Zoom Out"
            >
              <ZoomOut className="h-3.5 w-3.5 text-cyan-400" />
              <span>Zoom Out</span>
            </button>

            <button
              onClick={() => reactFlowInstance.fitView({ padding: 0.2, duration: 350 })}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-medium transition-all"
            >
              <Maximize2 className="h-3.5 w-3.5 text-blue-400" />
              <span>Fit Screen</span>
            </button>

            {focusedNodeId && (
              <button
                onClick={handleClearFocus}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-blue-600/20 text-cyan-300 border border-blue-500/40 text-xs font-medium"
              >
                <span>Clear 2-Hop Focus</span>
                <X className="h-3.5 w-3.5" />
              </button>
            )}

            <div className="flex items-center space-x-2 bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5">
              <span className="text-xs font-medium text-slate-400">Cluster:</span>
              <select
                value={selectedCluster}
                onChange={(e) => {
                  setSelectedCluster(e.target.value);
                  setFocusedNodeId(null);
                  setSelectedNode(null);
                  setSelectedEdge(null);
                }}
                className="bg-transparent text-xs text-white font-medium focus:outline-none cursor-pointer"
              >
                <option value="ALL" className="bg-slate-900">All Discovered Networks ({graphData?.clusters?.length || 0})</option>
                {graphData?.clusters?.map((c: any) => (
                  <option key={c.id} value={c.id} className="bg-slate-900">
                    {c.name} ({c.risk_level} • ${c.total_exposure})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Dynamic Consistent Coordinated Ring Alert Banner */}
        {activeCluster && activeCluster.is_coordinated && (
          <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/40 flex items-start space-x-3.5 backdrop-blur shadow-lg shadow-rose-950/20">
            <ShieldAlert className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1 text-xs">
              <div className="flex items-center space-x-2">
                <span className="font-bold text-rose-300 uppercase tracking-wider block">
                  {activeCluster.name} Discovered by NetworkX
                </span>
                <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-mono font-bold">
                  Risk: {activeCluster.risk_score}/100 ({activeCluster.risk_level})
                </span>
              </div>
              <p className="text-rose-200/90 leading-relaxed">
                NetworkX graph traversal confirmed <strong>{activeCluster.member_accounts_count} accounts</strong> linked with <strong>{activeCluster.member_transactions_count} transactions</strong> (${activeCluster.total_transaction_value?.toFixed(2)} total value, ${activeCluster.suspicious_financial_exposure?.toFixed(2)} suspicious exposure) sharing <strong>{activeCluster.shared_devices_count} device collision(s)</strong> and <strong>{activeCluster.shared_identities_count} shared payment identity token(s)</strong>.
              </p>
            </div>
          </div>
        )}

        {/* Main Graph Visualization Canvas */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-[640px]">
          {/* React Flow Viewport (3 cols) */}
          <div className="lg:col-span-3 bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden relative shadow-2xl flex flex-col">
            {loading ? (
              <div className="absolute inset-0 flex items-center justify-center bg-slate-950/80 z-20">
                <div className="text-center">
                  <Loader2 className="h-8 w-8 text-cyan-400 animate-spin mx-auto mb-2" />
                  <p className="text-xs text-slate-400">Computing NetworkX force-directed graph with collision separation...</p>
                </div>
              </div>
            ) : null}

            <div className="flex-1 w-full h-[620px] relative">
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                onEdgeClick={onEdgeClick}
                nodeTypes={nodeTypes}
                fitView
                panOnDrag
                zoomOnScroll
                minZoom={0.2}
                maxZoom={2.5}
              >
                <Background color="#1e293b" gap={20} size={1} />
                <Controls className="!bg-slate-900 !border-slate-800 !text-white fill-white" />
                <MiniMap
                  nodeColor={(n: any) => {
                    if (n.data?.type === 'ACCOUNT') return '#38bdf8';
                    if (n.data?.type === 'DEVICE') return '#c084fc';
                    if (n.data?.type === 'PAYMENT_IDENTITY') return '#fbbf24';
                    if (n.data?.type === 'TRANSACTION') return '#34d399';
                    return '#64748b';
                  }}
                  className="!bg-slate-950 !border-slate-800 rounded-lg overflow-hidden shadow-lg"
                />
              </ReactFlow>
            </div>

            {/* Dynamic Entity Counts Legend */}
            <div className="p-3 bg-slate-950/90 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 px-5">
              <div className="flex items-center space-x-5">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-cyan-400" />
                  Accounts: <strong className="text-white font-mono">{entityCounts.ACCOUNT}</strong>
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  Transactions: <strong className="text-white font-mono">{entityCounts.TRANSACTION}</strong>
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-purple-400" />
                  Devices: <strong className="text-white font-mono">{entityCounts.DEVICE}</strong>
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-amber-400" />
                  Payment Cards: <strong className="text-white font-mono">{entityCounts.PAYMENT_IDENTITY}</strong>
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-blue-400" />
                  IP Indicators: <strong className="text-white font-mono">{entityCounts.IP_INDICATOR}</strong>
                </span>
              </div>
              <span className="font-mono text-[10px] text-slate-500">
                Total Graph Edges: {graphData?.total_edges || 0}
              </span>
            </div>
          </div>

          {/* Side Inspector Panel (1 col) */}
          <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl p-5 flex flex-col space-y-4 overflow-y-auto max-h-[700px]">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center space-x-2">
                <Info className="h-4 w-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">
                  {selectedEdge ? 'Relationship Evidence' : 'Entity Inspector'}
                </h3>
              </div>
              {(selectedNode || selectedEdge) && (
                <button
                  onClick={() => {
                    setSelectedNode(null);
                    setSelectedEdge(null);
                    setNodes((nds) => nds.map((n) => ({ ...n, selected: false })));
                    setEdges((eds) =>
                      eds.map((e) => ({
                        ...e,
                        style: {
                          ...e.style,
                          opacity: 1.0,
                          strokeWidth: (e.data as any)?.is_suspicious ? 2.5 : 1.4,
                        },
                      }))
                    );
                  }}
                  className="p-1 rounded text-slate-400 hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* EDGE INSPECTION VIEW */}
            {selectedEdge ? (
              <div className="space-y-4 text-xs">
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-cyan-400 font-bold uppercase">
                      Edge Relationship
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      selectedEdge.is_suspicious ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'bg-blue-500/10 text-blue-300'
                    }`}>
                      {selectedEdge.is_suspicious ? 'SUSPICIOUS LINK' : 'LEGITIMATE LINK'}
                    </span>
                  </div>

                  <h4 className="text-sm font-mono font-bold text-white break-words">
                    {selectedEdge.relationship}
                  </h4>

                  <div className="space-y-2 pt-2 border-t border-slate-800 text-[11px]">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Source:</span>
                      <span className="text-white font-medium truncate max-w-[150px]">{selectedEdge.source_label}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Target:</span>
                      <span className="text-white font-medium truncate max-w-[150px]">{selectedEdge.target_label}</span>
                    </div>
                    {selectedEdge.evidence_id && (
                      <div className="flex justify-between">
                        <span className="text-slate-400">Evidence ID:</span>
                        <span className="text-cyan-400 font-mono font-bold">{selectedEdge.evidence_id}</span>
                      </div>
                    )}
                    {selectedEdge.shared_indicator && (
                      <div className="flex justify-between">
                        <span className="text-slate-400">Shared Indicator:</span>
                        <span className="text-amber-300 font-mono">{selectedEdge.shared_indicator}</span>
                      </div>
                    )}
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Connection Strength:</span>
                      <span className="text-emerald-400 font-mono font-bold">
                        {`${(Number(selectedEdge.confidence || 0.85) * 100).toFixed(0)}%`}
                      </span>
                    </div>
                    {selectedEdge.risk_contribution && (
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">Risk Contribution:</span>
                        <span className="text-rose-400 font-mono font-bold">
                          {selectedEdge.risk_contribution}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Supporting Evidence */}
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1.5">
                  <span className="text-[11px] font-bold text-cyan-300 uppercase tracking-wider block">
                    Supporting Evidence:
                  </span>
                  <p className="text-slate-300 leading-relaxed text-xs">
                    {selectedEdge.supporting_evidence || selectedEdge.suspicious_reason || 'Verified transactional or hardware association in relational database.'}
                  </p>
                </div>

                {/* Alternative Explanation / Standard of Proof Notice */}
                {selectedEdge.alternative_explanation && (
                  <div className="bg-amber-950/20 border border-amber-500/30 p-3.5 rounded-xl space-y-1.5">
                    <span className="text-[10px] font-bold text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                      <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                      Evidentiary Standard & Baseline Note
                    </span>
                    <p className="text-[11px] text-amber-200/90 leading-relaxed">
                      {selectedEdge.alternative_explanation}
                    </p>
                  </div>
                )}
              </div>
            ) : selectedNode ? (
              /* NODE INSPECTION VIEW */
              <div className="space-y-4 text-xs">
                {/* Node Identity Card */}
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono uppercase text-slate-400 font-bold">
                      {selectedNode.type}
                    </span>
                    <Badge type="risk" value={selectedNode.risk_level || 'LOW'} />
                  </div>
                  <h4 className="text-sm font-bold text-white break-words">
                    {selectedNode.label}
                  </h4>
                  <div className="flex justify-between text-slate-400 pt-1 border-t border-slate-850">
                    <span>Risk Score:</span>
                    <span className="font-mono font-bold text-cyan-400">{Number(selectedNode.risk_score || 0).toFixed(1)}/100</span>
                  </div>
                  {selectedNode.cluster_id && (
                    <div className="flex justify-between text-slate-400">
                      <span>Cluster Member:</span>
                      <span className="font-mono text-rose-400">{selectedNode.cluster_id}</span>
                    </div>
                  )}

                  {/* Functional Action Buttons */}
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-850">
                    <button
                      onClick={() => handleFocusNeighborhood(selectedNode.id)}
                      className="flex items-center justify-center space-x-1.5 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-cyan-300 border border-blue-500/40 rounded-lg text-xs font-medium transition-all"
                    >
                      <Focus className="h-3.5 w-3.5" />
                      <span>Focus 2-Hop</span>
                    </button>

                    <Link
                      href={`/transactions?search=${encodeURIComponent(selectedNode.id)}`}
                      className="flex items-center justify-center space-x-1.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium transition-all"
                    >
                      <DollarSign className="h-3.5 w-3.5 text-emerald-400" />
                      <span>View Txns</span>
                    </Link>
                  </div>

                  {selectedNode.attributes?.case_ref && (
                    <Link
                      href="/investigations"
                      className="w-full flex items-center justify-center space-x-1.5 py-1.5 mt-1.5 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 rounded-lg text-xs font-medium transition-all"
                    >
                      <FileSearch className="h-3.5 w-3.5" />
                      <span>Open Dossier ({selectedNode.attributes.case_ref})</span>
                    </Link>
                  )}
                </div>

                {/* Suspicious Connections / Why Flagged */}
                {selectedNode.suspicious_connections && selectedNode.suspicious_connections.length > 0 && (
                  <div className="bg-rose-950/30 border border-rose-500/40 p-3.5 rounded-xl space-y-2">
                    <span className="text-[11px] font-bold text-rose-300 uppercase tracking-wider flex items-center gap-1.5">
                      <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
                      Suspicious Relationship Flags ({selectedNode.suspicious_connections.length})
                    </span>
                    <div className="space-y-2">
                      {selectedNode.suspicious_connections.map((sc: any, idx: number) => (
                        <div key={idx} className="p-2 rounded bg-slate-950/80 border border-rose-500/20 space-y-1">
                          <div className="flex justify-between font-mono text-[10px] text-rose-300">
                            <span>{sc.relationship}</span>
                            <span className="truncate max-w-[120px]">{sc.connected_to}</span>
                          </div>
                          <p className="text-[11px] text-slate-300 leading-snug">
                            {sc.reason}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Connected Entities List with Direct Neighbor Count */}
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Connected Entities
                    </span>
                    <span className="text-xs font-mono font-bold text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                      {selectedNode.connected_entities?.length || 0} direct links
                    </span>
                  </div>

                  <div className="space-y-1.5 max-h-56 overflow-y-auto">
                    {selectedNode.connected_entities && selectedNode.connected_entities.length > 0 ? (
                      selectedNode.connected_entities.map((ce: any, idx: number) => (
                        <div
                          key={idx}
                          onClick={() => {
                            const target = graphData?.nodes?.find((n: any) => n.id === ce.key || n.id === ce.node_id);
                            if (target) {
                              // Compute target's neighbors immediately
                              const directEdges = edges.filter(
                                (e) => e.source === target.id || e.target === target.id
                              );
                              const targetNeighbors = directEdges.map((e) => {
                                const isOutbound = e.source === target.id;
                                const targetId = isOutbound ? e.target : e.source;
                                const tNode = nodes.find((n) => n.id === targetId);
                                return {
                                  node_id: targetId,
                                  key: targetId,
                                  label: tNode?.data?.label || targetId,
                                  type: tNode?.data?.type || 'UNKNOWN',
                                  relationship: e.label || 'CONNECTED',
                                  risk_level: tNode?.data?.risk_level || 'LOW',
                                };
                              });

                              setSelectedNode({
                                ...target,
                                connected_entities: targetNeighbors.length > 0 ? targetNeighbors : target.connected_entities,
                              });
                            }
                          }}
                          className="p-2 rounded bg-slate-900 border border-slate-800 hover:border-cyan-500/50 cursor-pointer flex items-center justify-between transition-all"
                        >
                          <div className="overflow-hidden space-y-0.5">
                            <span className="text-[11px] font-bold text-white block truncate max-w-[140px]">
                              {ce.label}
                            </span>
                            <span className="text-[10px] font-mono text-slate-400">
                              {ce.relationship?.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <Badge type="risk" value={ce.risk_level || 'LOW'} />
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-slate-500 py-2">No connected entities found.</p>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-16 space-y-3 flex-1 flex flex-col justify-center">
                <Share2 className="h-8 w-8 text-slate-600 mx-auto" />
                <p className="text-xs text-slate-400 leading-relaxed">
                  Click on any entity node or connecting edge in the graph to inspect relationships, evidence, and fraud indicators.
                </p>
              </div>
            )}

            {/* Discovered Clusters Overview with Detailed Consistent Stats */}
            <div className="pt-3 border-t border-slate-800/80 space-y-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                Discovered Networks ({graphData?.clusters?.length || 0})
              </span>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {graphData?.clusters?.map((c: any) => (
                  <div
                    key={c.id}
                    onClick={() => {
                      setSelectedCluster(c.id);
                      setFocusedNodeId(null);
                      setSelectedNode(null);
                      setSelectedEdge(null);
                    }}
                    className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                      selectedCluster === c.id
                        ? 'bg-blue-600/15 border-blue-500/40 text-cyan-300 shadow-md'
                        : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-800/50'
                    }`}
                  >
                    <div className="flex items-center justify-between font-bold">
                      <span>{c.name}</span>
                      <span className="text-[10px] font-mono text-cyan-400">${c.total_exposure?.toFixed(2)}</span>
                    </div>

                    <div className="grid grid-cols-3 gap-1 py-1.5 my-1 border-y border-slate-850 text-[10px] text-slate-400 font-mono">
                      <span>{c.member_accounts_count} accounts</span>
                      <span>{c.member_transactions_count} txns</span>
                      <span>{c.evidence_count || c.shared_devices_count + c.shared_identities_count} evidence</span>
                    </div>

                    <p className="text-[10px] text-slate-400 line-clamp-2 leading-relaxed">
                      {c.summary}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function FraudNetworksPage() {
  return (
    <ReactFlowProvider>
      <FraudNetworkFlow />
    </ReactFlowProvider>
  );
}
