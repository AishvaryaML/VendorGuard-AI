from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class WorkflowRunRequest(BaseModel):
    vendor_id: str = Field(..., description="Vendor ID to initiate multi-agent risk workflow.")
    force_recrawl: bool = Field(default=False, description="Forces homepage re-crawl during discovery.")
    force_reindex: bool = Field(default=False, description="Forces vector re-indexing during policy audit.")


class WorkflowApprovalRequest(BaseModel):
    approved: bool = Field(..., description="True to approve assessment, False to reject.")
    notes: Optional[str] = Field(default=None, description="Optional analyst approval notes.")


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    vendor_id: str
    vendor_name: str
    domain: str
    status: str
    current_step: str
    overall_score: float
    risk_tier: str
    requires_human_approval: bool
    human_approved: Optional[bool] = None
    approval_notes: Optional[str] = None
    executive_summary: str = ""
    indexed_chunks_count: int = 0
    errors: List[str] = Field(default_factory=list)
