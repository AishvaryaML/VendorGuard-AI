import axios from 'axios';
import {
  SystemHealth,
  Vendor,
  VendorCreate,
  Document,
  RiskAssessment,
  Alert,
  AlertListResponse,
  MonitoringTriggerResponse,
  MonitoringJobStatusResponse,
  VendorMonitoringStatus,
  AssistantChatRequest,
  AssistantChatResponse,
  WorkflowRunRequest,
  WorkflowApprovalRequest,
  WorkflowStatusResponse,
  VendorSecurityReport,
  PolicyVersionSummary,
  PolicyDiffResponse,
} from '../types';


export const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30s default timeout for standard API operations
});

export const healthApi = {
  checkHealth: async (): Promise<SystemHealth> => {
    const response = await apiClient.get<SystemHealth>('/health');
    return response.data;
  },
};

export const vendorApi = {
  createVendor: async (data: VendorCreate): Promise<Vendor> => {
    const response = await apiClient.post<Vendor>('/vendors/', data, {
      timeout: 60000, // 60s timeout for initial discovery crawl
    });
    return response.data;
  },
  listVendors: async (skip: number = 0, limit: number = 200): Promise<Vendor[]> => {
    const response = await apiClient.get<Vendor[]>('/vendors/', { params: { skip, limit } });
    return response.data;
  },
  getVendor: async (vendorId: string): Promise<Vendor> => {
    const response = await apiClient.get<Vendor>(`/vendors/${vendorId}`);
    return response.data;
  },
  getVendorDocuments: async (vendorId: string): Promise<Document[]> => {
    const response = await apiClient.get<Document[]>(`/vendors/${vendorId}/documents`);
    return response.data;
  },
  recrawlVendorDocuments: async (vendorId: string): Promise<Document[]> => {
    const response = await apiClient.post<Document[]>(`/vendors/${vendorId}/crawl`, null, {
      timeout: 60000,
    });
    return response.data;
  },
};

export const riskApi = {
  analyzeVendor: async (vendorId: string): Promise<RiskAssessment> => {
    const response = await apiClient.post<RiskAssessment>(`/vendors/${vendorId}/analyze`, null, {
      timeout: 120000, // 120s timeout for AI risk analysis with local Ollama
    });
    return response.data;
  },
  getRiskAssessment: async (vendorId: string): Promise<RiskAssessment> => {
    const response = await apiClient.get<RiskAssessment>(`/vendors/${vendorId}/risk-assessment`);
    return response.data;
  },
};

export const monitoringApi = {
  triggerMonitoring: async (vendorId?: string, force: boolean = false): Promise<MonitoringTriggerResponse> => {
    const params: Record<string, any> = { force };
    if (vendorId) params.vendor_id = vendorId;
    const response = await apiClient.post<MonitoringTriggerResponse>('/monitoring/trigger', null, {
      params,
      timeout: 15000,
    });
    return response.data;
  },
  getJobStatus: async (jobId: string): Promise<MonitoringJobStatusResponse> => {
    const response = await apiClient.get<MonitoringJobStatusResponse>(`/monitoring/jobs/${jobId}`);
    return response.data;
  },
  getVendorStatus: async (vendorId: string): Promise<VendorMonitoringStatus> => {
    const response = await apiClient.get<VendorMonitoringStatus>(`/monitoring/status/${vendorId}`);
    return response.data;
  },
};

export const alertsApi = {
  listAlerts: async (params?: {
    vendor_id?: string;
    alert_type?: string;
    severity?: string;
    is_read?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<AlertListResponse> => {
    const response = await apiClient.get<AlertListResponse>('/alerts', { params });
    return response.data;
  },
  getVendorAlerts: async (vendorId: string): Promise<Alert[]> => {
    const response = await apiClient.get<Alert[]>(`/alerts/vendor/${vendorId}`);
    return response.data;
  },
  markAsRead: async (alertId: string): Promise<Alert> => {
    const response = await apiClient.patch<Alert>(`/alerts/${alertId}/read`);
    return response.data;
  },
};

export const assistantApi = {
  chat: async (payload: AssistantChatRequest): Promise<AssistantChatResponse> => {
    const response = await apiClient.post<AssistantChatResponse>('/assistant/chat', payload, {
      timeout: 120000, // 120s timeout for local Ollama RAG inference
    });
    return response.data;
  },
};

export const agenticApi = {
  runWorkflow: async (payload: WorkflowRunRequest): Promise<WorkflowStatusResponse> => {
    const response = await apiClient.post<WorkflowStatusResponse>('/agentic/workflow/run', payload, {
      timeout: 120000, // 120s timeout for multi-agent workflow initiation
    });
    return response.data;
  },
  getWorkflowStatus: async (workflowId: string): Promise<WorkflowStatusResponse> => {
    const response = await apiClient.get<WorkflowStatusResponse>(`/agentic/workflow/status/${workflowId}`);
    return response.data;
  },
  approveWorkflow: async (workflowId: string, payload: WorkflowApprovalRequest): Promise<WorkflowStatusResponse> => {
    const response = await apiClient.post<WorkflowStatusResponse>(`/agentic/workflow/approve/${workflowId}`, payload, {
      timeout: 120000, // 120s timeout for workflow resumption
    });
    return response.data;
  },
};

export const reportsApi = {
  getVendorReport: async (vendorId: string): Promise<VendorSecurityReport> => {
    const response = await apiClient.get<VendorSecurityReport>(`/vendors/${vendorId}/report`);
    return response.data;
  },
  downloadReportMarkdown: async (vendorId: string, filename?: string): Promise<void> => {
    const response = await apiClient.get(`/vendors/${vendorId}/report/markdown`, {
      responseType: 'blob',
    });
    const blob = new Blob([response.data], { type: 'text/markdown;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename || `vendor-report-${vendorId}.md`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
  downloadReportPdf: async (vendorId: string, filename?: string): Promise<void> => {
    const response = await apiClient.get(`/vendors/${vendorId}/report/pdf`, {
      responseType: 'blob',
    });
    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename || `vendor-report-${vendorId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};

export const policyDiffApi = {
  getDocumentVersions: async (vendorId: string, documentId: string): Promise<PolicyVersionSummary[]> => {
    const response = await apiClient.get<PolicyVersionSummary[]>(
      `/vendors/${vendorId}/documents/${documentId}/versions`
    );
    return response.data;
  },
  getPolicyDiff: async (
    vendorId: string,
    documentId: string,
    v1: string,
    v2: string
  ): Promise<PolicyDiffResponse> => {
    const response = await apiClient.get<PolicyDiffResponse>(
      `/vendors/${vendorId}/documents/${documentId}/diff`,
      {
        params: { v1, v2 },
        timeout: 120000, // 120s timeout for LLM semantic analysis
      }
    );
    return response.data;
  },
};

