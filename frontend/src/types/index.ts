export type RiskTier = 'Low' | 'Medium' | 'High' | 'Critical';
export type VendorStatus = 'Active' | 'Under Review' | 'Archived';
export type MonitoringFrequency = 'Daily' | 'Weekly' | 'Monthly';

export interface SystemHealth {
  status: string;
  app_name: string;
  environment: string;
  version: string;
  database: string;
  timestamp: string;
}

export interface Vendor {
  id: string;
  name: string;
  domain: string;
  industry: string;
  website_url: string;
  risk_tier: RiskTier;
  current_risk_score: number;
  status: VendorStatus;
  monitoring_frequency: MonitoringFrequency;
  last_monitored_at?: string;
  created_at: string;
  updated_at: string;
}

export interface RiskCategoryScores {
  privacy: number;
  security: number;
  compliance: number;
  legal: number;
  overall: number;
}
