const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const apiKey = process.env.NEXT_PUBLIC_AGENTSHIELD_API_KEY;
  const headers = {
    'Content-Type': 'application/json',
    ...(apiKey ? { 'X-AgentShield-Key': apiKey } : {}),
    ...(options.headers || {}),
  };

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || `Request failed with status ${res.status}`);
    }
    return (await res.json()) as T;
  } catch (err: any) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  // Dashboard
  getDashboardSummary: () => request<any>('/dashboard/summary'),

  // Transactions
  getTransactions: (params: { risk_category?: string; status?: string; search?: string; limit?: number; offset?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.risk_category) query.append('risk_category', params.risk_category);
    if (params.status) query.append('status', params.status);
    if (params.search) query.append('search', params.search);
    if (params.limit) query.append('limit', String(params.limit));
    if (params.offset) query.append('offset', String(params.offset));
    return request<any[]>(`/transactions?${query.toString()}`);
  },
  getTransactionDetail: (id: string) => request<any>(`/transactions/${id}`),
  ingestTransaction: (data: any) => request<any>('/transactions/ingest', { method: 'POST', body: JSON.stringify(data) }),
  analyzeTransaction: (id: string) => request<any>(`/transactions/${id}/analyze`, { method: 'POST' }),

  // Fraud Networks
  getFraudNetworks: (params: { cluster_id?: string; node_id?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.cluster_id) query.append('cluster_id', params.cluster_id);
    if (params.node_id) query.append('node_id', params.node_id);
    return request<any>(`/fraud-networks?${query.toString()}`);
  },
  getClusterDetails: (clusterId: string) => request<any>(`/fraud-networks/${clusterId}`),

  // Investigations
  getInvestigations: (params: { status?: string; risk_level?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.append('status', params.status);
    if (params.risk_level) query.append('risk_level', params.risk_level);
    return request<any[]>(`/investigations?${query.toString()}`);
  },
  getInvestigationCase: (caseId: string) => request<any>(`/investigations/${caseId}`),
  runCaseInvestigation: (caseId: string) => request<any>(`/investigations/${caseId}/run`, { method: 'POST' }),
  approveCase: (caseId: string, data: { investigator_name: string; reason: string }) =>
    request<any>(`/investigations/${caseId}/approve`, { method: 'POST', body: JSON.stringify({ action: 'APPROVE', ...data }) }),
  rejectCase: (caseId: string, data: { investigator_name: string; reason: string }) =>
    request<any>(`/investigations/${caseId}/reject`, { method: 'POST', body: JSON.stringify({ action: 'REJECT', ...data }) }),

  // Agents
  getAgentExecutions: (params: { case_id?: string; stage?: string; limit?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.case_id) query.append('case_id', params.case_id);
    if (params.stage) query.append('stage', params.stage);
    if (params.limit) query.append('limit', String(params.limit));
    return request<any[]>(`/agents/executions?${query.toString()}`);
  },

  // Payments
  getPayments: (params: { status?: string; limit?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.append('status', params.status);
    if (params.limit) query.append('limit', String(params.limit));
    return request<any[]>(`/payments?${query.toString()}`);
  },
  verifyPaymentCapture: (paymentId: string) => request<any>(`/payments/${paymentId}/verify`),
  createPayPalOrder: (data: { amount: number; currency?: string; transaction_ref?: string; case_id?: string; description?: string }) =>
    request<any>('/payments/orders/create', { method: 'POST', body: JSON.stringify(data) }),
  capturePayPalOrder: (orderId: string) =>
    request<any>(`/payments/orders/${orderId}/capture`, { method: 'POST' }),
  refundPayment: (paymentId: string, data: { reason?: string; investigator?: string; currency?: string; amount?: number } = {}) =>
    request<any>(`/payments/${paymentId}/refund`, { method: 'POST', body: JSON.stringify({ payment_id: paymentId, ...data }) }),
  verifyRefundStatus: (paymentId: string) => request<any>(`/payments/${paymentId}/refund/verify`, { method: 'POST' }),

  // Audit
  getAuditLogs: (params: { event_type?: string; actor?: string; limit?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.event_type) query.append('event_type', params.event_type);
    if (params.actor) query.append('actor', params.actor);
    if (params.limit) query.append('limit', String(params.limit));
    return request<any[]>(`/audit?${query.toString()}`);
  },

  // Demo Control
  getDemoStatus: () => request<any>('/demo/status'),
  seedDemo: () => request<any>('/demo/seed', { method: 'POST' }),
  resetDemo: () => request<any>('/demo/reset', { method: 'POST' }),
  simulateLegitTransaction: () => request<any>('/demo/simulate-transaction', { method: 'POST' }),
  triggerSuspiciousAttack: () => request<any>('/demo/trigger-suspicious', { method: 'POST' }),
  runFullInvestigation: () => request<any>('/demo/run-investigation', { method: 'POST' }),
};
