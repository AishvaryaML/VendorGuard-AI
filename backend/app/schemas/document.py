from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class PolicyVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    version_number: int
    content_hash: str
    raw_content: str
    summary: Optional[str] = None
    change_summary: Optional[str] = None
    crawled_at: datetime


class DocumentBase(BaseModel):
    document_type: str = Field(..., description="Privacy Policy, Terms of Service, Security Center, etc.")
    title: str = Field(..., max_length=255)
    url: str


class DocumentCreate(DocumentBase):
    vendor_id: str


class DocumentResponse(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    vendor_id: str
    current_version_hash: Optional[str] = None
    last_crawled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    versions: List[PolicyVersionResponse] = []
