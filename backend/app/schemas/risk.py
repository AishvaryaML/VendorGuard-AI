from datetime import datetime
from typing import Optional, List, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from app.models.vendor import RiskTier


class RiskFindingSchema(BaseModel):
    category: Literal["Privacy", "Security", "Compliance", "Legal"] = Field(
        ...,
        description="The risk dimension category."
    )
    finding: str = Field(
        ...,
        description="Clear, concise description of the risk finding."
    )
    severity: Literal["Low", "Medium", "High", "Critical"] = Field(
        ...,
        description="Severity level of the finding."
    )
    evidence: str = Field(
        ...,
        description="Verbatim text quote from the policy document supporting this finding."
    )
    source_url: str = Field(
        ...,
        description="URL of the policy document where evidence text was found."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0."
    )
    recommendation: str = Field(
        ...,
        description="Actionable mitigation recommendation for this risk finding."
    )
    is_verified: bool = Field(
        default=True,
        description="Whether the evidence quote was verified against stored policy text."
    )


class AIAssessmentResultSchema(BaseModel):
    summary: str = Field(
        ...,
        description="Executive summary of the vendor's policy risk evaluation."
    )
    findings: List[RiskFindingSchema] = Field(
        default_factory=list,
        description="List of evidence-backed risk findings across Privacy, Security, Compliance, and Legal."
    )


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
