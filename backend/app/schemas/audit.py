from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class AuditLogBase(BaseModel):
    vendor_id: Optional[str] = None
    action: str = Field(..., max_length=100)
    actor: str = Field(default="System", max_length=100)
    details: Optional[Any] = None


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogResponse(AuditLogBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp: datetime
