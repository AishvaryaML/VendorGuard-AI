from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ReportVendorInfo(BaseModel):
    vendor_id: str
    name: str
    domain: str
    website_url: str
    status: str
    monitoring_frequency: str
    risk_tier: str
    current_risk_score: float
    last_monitored_at: Optional[datetime] = None


class ReportExecutiveSummary(BaseModel):
    summary_text: str
    overall_risk_tier: str
    overall_score: float
    policy_posture: str
    policy_changes_detected: bool
    key_highlights: List[str] = Field(default_factory=list)


class ReportCategoryScore(BaseModel):
    category: str
    score: float
    justification: Optional[str] = None


class ReportFinding(BaseModel):
    category: str
    severity: str
    finding: str
    evidence: Optional[str] = None
    source_url: Optional[str] = None
    recommendation: Optional[str] = None
    is_verified: bool = True


class ReportEvidenceItem(BaseModel):
    category: str
    document_type: str
    title: str
    source_url: str
    quote: str
    is_verified: bool = True


class ReportPolicySnapshot(BaseModel):
    document_id: str
    document_type: str
    title: str
    url: str
    current_version_hash: Optional[str] = None
    version_number: int = 1
    last_crawled_at: Optional[datetime] = None
    change_summary: Optional[str] = None


class VendorSecurityReport(BaseModel):
    vendor: ReportVendorInfo
    executive_summary: ReportExecutiveSummary
    risk_overview: List[ReportCategoryScore]
    findings: List[ReportFinding]
    evidence: List[ReportEvidenceItem]
    recommendations: List[str]
    policy_snapshots: List[ReportPolicySnapshot]
    has_assessment_data: bool
    generated_at: datetime
