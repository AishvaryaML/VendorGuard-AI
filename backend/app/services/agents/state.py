from typing import List, Dict, Optional, Any, TypedDict


class VendorRiskState(TypedDict, total=False):
    workflow_id: str
    vendor_id: str
    vendor_name: str
    domain: str
    website_url: str
    current_step: str
    status: str  # pending, crawling, indexing, auditing, awaiting_approval, completed, rejected, failed
    discovered_documents: List[Dict[str, Any]]
    indexed_chunks_count: int
    risk_assessment_id: Optional[str]
    overall_score: float
    risk_tier: str
    category_scores: Dict[str, float]
    key_findings: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    executive_summary: str
    requires_human_approval: bool
    human_approved: Optional[bool]
    approval_notes: Optional[str]
    alerts_created: List[Dict[str, Any]]
    errors: List[str]
