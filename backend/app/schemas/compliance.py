from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ComplianceControlSchema(BaseModel):
    framework: str = Field(..., description="E.g., SOC 2 Type II, ISO 27001, GDPR, HIPAA, NIST SP 800-53")
    control_id: str
    control_title: str
    control_description: str
    required_evidence: str
    category: str

class ComplianceEvidenceSchema(BaseModel):
    quote: str
    source_document_id: str
    source_version_id: str
    source_url: str

class ComplianceAssessmentResult(BaseModel):
    framework: str
    control_id: str
    control_title: str
    status: str = Field(..., description="PASS, PARTIAL, GAP, NOT_ASSESSED")
    confidence: float
    evidence_quote: Optional[str] = None
    source_url: Optional[str] = None
    source_document: Optional[str] = None
    source_version: Optional[str] = None
    explanation: Optional[str] = None
    gap_reason: Optional[str] = None

class ComplianceFrameworkSummarySchema(BaseModel):
    framework: str
    pass_count: int
    partial_count: int
    gap_count: int
    not_assessed_count: int
    coverage_percentage: float

class ComplianceCrosswalkResponse(BaseModel):
    vendor_id: str
    summaries: List[ComplianceFrameworkSummarySchema]
    assessments: List[ComplianceAssessmentResult]
