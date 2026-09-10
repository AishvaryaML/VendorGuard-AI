from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MonitoringTriggerRequest(BaseModel):
    vendor_id: Optional[str] = Field(None, description="Optional vendor ID to trigger monitoring specifically.")
    force: Optional[bool] = Field(False, description="If True, ignores schedule and forces re-crawl & evaluation.")


class VendorMonitoringResult(BaseModel):
    vendor_id: str
    vendor_name: str
    status: str = Field(..., description="Success, Skipped, or Failed")
    documents_checked: int = 0
    documents_changed: int = 0
    risk_reassessed: bool = False
    alerts_generated: int = 0
    error_detail: Optional[str] = None


class MonitoringTriggerResponse(BaseModel):
    job_id: str
    status: str = "pending"
    message: str = "Monitoring job accepted"
    total_vendors: int


class MonitoringJobStatusResponse(BaseModel):
    job_id: str
    status: str
    total_vendors: int
    completed_vendors: int
    current_vendor: Optional[str] = None
    successful_vendors: int
    failed_vendors: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class VendorMonitoringStatusResponse(BaseModel):
    vendor_id: str
    vendor_name: str
    monitoring_frequency: str
    last_monitored_at: Optional[datetime] = None
    next_monitoring_due: Optional[datetime] = None
    is_due: bool
    documents_count: int
    active_alerts_count: int
    last_risk_score: float
    last_risk_tier: str
