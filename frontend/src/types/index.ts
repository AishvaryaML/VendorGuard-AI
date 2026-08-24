export type RiskTier = 'Low' | 'Medium' | 'High' | 'Critical';
export type VendorStatus = 'Active' | 'Under Review' | 'Archived';
export type MonitoringFrequency = 'Daily' | 'Weekly' | 'Monthly';
export type RiskCategoryName = 'Privacy' | 'Security' | 'Compliance' | 'Legal';

export interface SystemHealth {
  status: string;
  app_name: string;
  environment: string;
}

export interface PolicyVersion {
  id: string;
  document_id: string;
  version_number: number;
  content_hash: string;
  raw_content: string;
  summary?: string;
  change_summary?: string;
  crawled_at: string;
}

export interface Document {
  id: string;
  vendor_id: string;
  document_type: string;
  title: string;
  url: string;
  current_version_hash?: string;
  last_crawled_at?: string;
  created_at: string;
  updated_at: string;
  versions?: PolicyVersion[];
}

export interface VendorCreate {
  name: string;
  website_url: string;
  industry?: string;
  monitoring_frequency?: MonitoringFrequency;
}

export interface Vendor {
  id: string;
  name: string;
  domain: string;
  industry?: string;
  website_url: string;
  risk_tier: RiskTier;
  current_risk_score: number;
  status: VendorStatus;
  monitoring_frequency: MonitoringFrequency;
  last_monitored_at?: string;
  created_at: string;
  updated_at: string;
  documents?: Document[];
}

export interface RiskFinding {
  category: RiskCategoryName;
  finding: string;
  severity: RiskTier;
  evidence: string;
  source_url: string;
  confidence: number;
  recommendation: string;
  is_verified: boolean;
}

export interface CategoryScoreResponse {
  id: string;
  assessment_id: string;
  category_name: RiskCategoryName;
  score: number;
  justification?: string;
  findings?: RiskFinding[];
}

export interface RiskAssessment {
  id: string;
  vendor_id: string;
  assessment_date: string;
  overall_score: number;
  risk_tier: RiskTier;
  summary?: string;
  key_findings?: RiskFinding[];
  citations?: Array<{
    category: string;
    finding: string;
    severity: string;
    evidence: string;
    source_url: string;
    is_verified: boolean;
    confidence: number;
  }>;
  status: string;
  created_at: string;
  category_scores: CategoryScoreResponse[];
}

export interface Alert {
  id: string;
  vendor_id: string;
  alert_type: string;
  severity: RiskTier;
  title: string;
  description: string;
  is_read: boolean;
  created_at: string;
}

export interface AlertListResponse {
  items: Alert[];
  total: number;
  skip: number;
  limit: number;
}

export interface VendorMonitoringResult {
  vendor_id: string;
  vendor_name: string;
  status: string;
  documents_checked: number;
  documents_changed: number;
  risk_reassessed: boolean;
  alerts_generated: number;
  error_detail?: string;
}

export interface MonitoringTriggerResponse {
  message: string;
  timestamp: string;

  monitored_count: number;
  results: VendorMonitoringResult[];
}

export interface VendorMonitoringStatus {
  vendor_id: string;
  vendor_name: string;
  monitoring_frequency: string;
  last_monitored_at?: string;
  next_monitoring_due?: string;
  is_due: boolean;
  documents_count: number;
  active_alerts_count: number;
  last_risk_score: number;
  last_risk_tier: string;
}
