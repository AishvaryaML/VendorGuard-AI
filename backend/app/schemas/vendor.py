from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, Field, ConfigDict
from app.models.vendor import RiskTier, VendorStatus, MonitoringFrequency


class VendorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Vendor display name")
    domain: str = Field(..., min_length=3, max_length=255, description="Primary domain e.g. slack.com")
    industry: Optional[str] = Field(None, max_length=100)
    website_url: str = Field(..., description="Full website URL")
    monitoring_frequency: MonitoringFrequency = Field(default=MonitoringFrequency.DAILY)


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    website_url: Optional[str] = None
    risk_tier: Optional[RiskTier] = None
    current_risk_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    status: Optional[VendorStatus] = None
    monitoring_frequency: Optional[MonitoringFrequency] = None


class VendorResponse(VendorBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    risk_tier: RiskTier
    current_risk_score: float
    status: VendorStatus
    last_monitored_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
