import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor for auth (if needed later)
api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default api;

// API endpoints
export const dashboardApi = {
  getKPIs: (params) => api.get('/dashboard/kpis', { params }),
  getSalesTrend: (params) => api.get('/dashboard/sales-trend', { params }),
  getTopItems: (params) => api.get('/dashboard/top-items', { params }),
  getStoreComparison: (params) => api.get('/dashboard/store-comparison', { params }),
  getDepartmentPerformance: (params) => api.get('/dashboard/department-performance', { params }),
  getHourlyHeatmap: (params) => api.get('/dashboard/hourly-heatmap', { params }),
  getTenderMix: (params) => api.get('/dashboard/tender-mix', { params }),

  // Microsoft Dynamics 365 Sales Hub-like features
  getSalesTargets: (params) => api.get('/dashboard/targets', { params }),
  getPeriodComparison: (params) => api.get('/dashboard/period-comparison', { params }),
  getPromotions: (params) => api.get('/dashboard/promotions', { params }),
  getStaffPerformance: (params) => api.get('/dashboard/staff-performance', { params }),
  getForecast: (params) => api.get('/dashboard/forecast', { params }),
  getCustomerMetrics: (params) => api.get('/dashboard/customer-metrics', { params }),
  getExecutiveScorecard: (params) => api.get('/dashboard/executive-scorecard', { params }),
};

export const reconciliationApi = {
  getShiftSummaries: (params) => api.get('/reconciliation/shift-summaries', { params }),
  getEODSummaries: (params) => api.get('/reconciliation/eod-summaries', { params }),
  getDailyReconciliation: (storeId, date) => api.get(`/reconciliation/daily-reconciliation/${storeId}/${date}`),
  getCashVarianceReport: (params) => api.get('/reconciliation/cash-variance-report', { params }),
  getDiscrepancies: (params) => api.get('/reconciliation/discrepancies', { params }),
};

export const pricingApi = {
  getPriceList: () => api.get('/pricing/price-list'),
  createPriceChange: (data) => api.post('/pricing/price-changes', data),
  getPriceChanges: (params) => api.get('/pricing/price-changes', { params }),
  approvePriceChange: (changeId) => api.post(`/pricing/price-changes/${changeId}/approve`),
  rejectPriceChange: (changeId, reason) => api.post(`/pricing/price-changes/${changeId}/reject`, null, { params: { reason } }),
  exportPriceList: () => api.post('/pricing/export-price-list'),
  processInboxPriceChanges: () => api.post('/pricing/process-inbox-price-changes'),
  sendAcknowledgement: (changeId, status) => api.post(`/pricing/send-ack/${changeId}`, null, { params: { status } }),
};

export const connectorsApi = {
  importTLogXML: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/connectors/import/tlog-xml', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  importTLogJSON: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/connectors/import/tlog-json', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  importPriceList: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/connectors/import/price-list', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  getImports: (params) => api.get('/connectors/imports', { params }),
};

export const aiApi = {
  processInvoice: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/ai/process-invoice', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  processInboxInvoices: () => api.post('/ai/process-inbox-invoices'),
  matchInvoiceToPO: (invoiceId, poNumber) => api.post('/ai/match-invoice-to-po', null, { params: { invoice_id: invoiceId, po_number: poNumber } }),
  getInvoiceStatus: (invoiceId) => api.get(`/ai/invoice-status/${invoiceId}`),
  getExtractedData: (invoiceId) => api.get(`/ai/extracted-data/${invoiceId}`),
  createGoodsReceipt: (invoiceId, items) => api.post('/ai/create-goods-receipt', { invoice_id: invoiceId, received_items: items }),
};

export const hubApi = {
  getStatus: () => api.get('/hub/status'),
  start: (config) => api.post('/hub/start', config),
  stop: () => api.post('/hub/stop'),
  runCycle: () => api.post('/hub/cycle'),
  getInboxFiles: () => api.get('/hub/inbox-files'),
  getOutboxFiles: () => api.get('/hub/outbox-files'),
  getOutboxFile: (filename) => api.get(`/hub/outbox-file/${filename}`),
  simulateStoreSubmission: (storeId) => api.post('/hub/simulate-store-submission', null, { params: { store_id: storeId } }),
  getHubOverview: () => api.get('/hub/overview'),
  processInbox: () => api.post('/hub/process-inbox'),
  processStoreOutbox: () => api.post('/hub/process-store-outbox'),
  getHubConfig: () => api.get('/hub/config'),
  updateHubConfig: (config) => api.put('/hub/config', config),
};