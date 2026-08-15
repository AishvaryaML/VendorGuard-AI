from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.vendor import RiskTier


class CategoryScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_id: str
    category_name: str
    score: float = Field(..., ge=0.0, le=100.0)
    justification: Optional[str] = None
    findings: Optional[Any] = None


class RiskAssessmentBase(BaseModel):
    vendor_id: str
    overall_score: float = Field(..., ge=0.0, le=100.0)
    risk_tier: RiskTier
    summary: Optional[str] = None
    key_findings: Optional[Any] = None
    citations: Optional[Any] = None
    status: str = "Completed"


class RiskAssessmentCreate(RiskAssessmentBase):
    pass


class RiskAssessmentResponse(RiskAssessmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_date: datetime
    created_at: datetime
    category_scores: List[CategoryScoreResponse] = []
