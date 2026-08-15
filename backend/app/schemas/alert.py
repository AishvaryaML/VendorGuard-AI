from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AlertBase(BaseModel):
    vendor_id: str
    alert_type: str = Field(..., description="Policy Change, Risk Score Drop, Compliance Violation, Security Threat")
    severity: str = Field(default="Medium", description="Low, Medium, High, Critical")
    title: str = Field(..., max_length=255)
    description: str


class AlertCreate(AlertBase):
    pass


class AlertResponse(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_read: bool
    created_at: datetime
