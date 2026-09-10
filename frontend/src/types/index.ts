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
  job_id: string;
  status: string;
  message: string;
  total_vendors: number;
}

export interface MonitoringJobStatusResponse {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  total_vendors: number;
  completed_vendors: number;
  current_vendor?: string | null;
  successful_vendors: number;
  failed_vendors: number;
  started_at: string;
  completed_at?: string | null;
  error?: string | null;
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

// Assistant RAG Chat Types
export interface ChatMessagePayload {
  role: 'user' | 'assistant';
  content: string;
}

export interface AssistantCitation {
  document_type: string;
  title: string;
  source_url: string;
  snippet: string;
  similarity_score: number;
  chunk_id: string;
}

export interface AssistantChatRequest {
  vendor_id: string;
  message: string;
  conversation_history?: ChatMessagePayload[];
}

export interface AssistantChatResponse {
  vendor_id: string;
  answer: string;
  sources: AssistantCitation[];
  timestamp: string;
}

// Agentic Workflow Types
export interface WorkflowRunRequest {
  vendor_id: string;
  force_recrawl?: boolean;
  force_reindex?: boolean;
}

export interface WorkflowApprovalRequest {
  approved: boolean;
  notes?: string;
}

export interface WorkflowStatusResponse {
  workflow_id: string;
  vendor_id: string;
  vendor_name: string;
  domain: string;
  status: string;
  current_step: string;
  overall_score: number;
  risk_tier: RiskTier;
  requires_human_approval: boolean;
  human_approved?: boolean | null;
  approval_notes?: string | null;
  executive_summary: string;
  indexed_chunks_count: number;
  errors: string[];
}

// Executive Security Assessment Report Types
export interface ReportVendorInfo {
  vendor_id: string;
  name: string;
  domain: string;
  website_url: string;
  status: string;
  monitoring_frequency: string;
  risk_tier: string;
  current_risk_score: number;
  last_monitored_at?: string | null;
}

export interface ReportExecutiveSummary {
  summary_text: string;
  overall_risk_tier: string;
  overall_score: number;
  policy_posture: string;
  policy_changes_detected: boolean;
  key_highlights: string[];
}

export interface ReportCategoryScore {
  category: string;
  score: number;
  justification?: string | null;
}

export interface ReportFinding {
  category: string;
  severity: string;
  finding: string;
  evidence?: string | null;
  source_url?: string | null;
  recommendation?: string | null;
  is_verified: boolean;
}

export interface ReportEvidenceItem {
  category: string;
  document_type: string;
  title: string;
  source_url: string;
  quote: string;
  is_verified: boolean;
}

export interface ReportPolicySnapshot {
  document_id: string;
  document_type: string;
  title: string;
  url: string;
  current_version_hash?: string | null;
  version_number: number;
  last_crawled_at?: string | null;
  change_summary?: string | null;
}

export interface VendorSecurityReport {
  vendor: ReportVendorInfo;
  executive_summary: ReportExecutiveSummary;
  risk_overview: ReportCategoryScore[];
  findings: ReportFinding[];
  evidence: ReportEvidenceItem[];
  recommendations: string[];
  policy_snapshots: ReportPolicySnapshot[];
  has_assessment_data: boolean;
  generated_at: string;
}
