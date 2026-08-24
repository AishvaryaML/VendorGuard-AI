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
  VendorMonitoringStatus,
} from '../types';

export const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 45000, // 45s timeout for crawler/AI operations
});

export const healthApi = {
  checkHealth: async (): Promise<SystemHealth> => {
    const response = await apiClient.get<SystemHealth>('/health');
    return response.data;
  },
};

export const vendorApi = {
  createVendor: async (data: VendorCreate): Promise<Vendor> => {
    const response = await apiClient.post<Vendor>('/vendors/', data);
    return response.data;
  },
  listVendors: async (skip: number = 0, limit: number = 100): Promise<Vendor[]> => {
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
    const response = await apiClient.post<Document[]>(`/vendors/${vendorId}/crawl`);
    return response.data;
  },
};

export const riskApi = {
  analyzeVendor: async (vendorId: string): Promise<RiskAssessment> => {
    const response = await apiClient.post<RiskAssessment>(`/vendors/${vendorId}/analyze`);
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
    const response = await apiClient.post<MonitoringTriggerResponse>('/monitoring/trigger', null, { params });
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
