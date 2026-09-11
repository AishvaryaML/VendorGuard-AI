from datetime import datetime
from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class MaterialityTier(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class RiskPostureImpact(str, Enum):
    FAVORABLE = "Favorable"
    NEUTRAL = "Neutral"
    ADVERSE = "Adverse"


class RiskPillar(str, Enum):
    PRIVACY = "Privacy"
    SECURITY = "Security"
    COMPLIANCE = "Compliance"
    LEGAL = "Legal"
    MULTIPLE = "Multiple"


class DiffLineType(str, Enum):
    ADDED = "added"
    DELETED = "deleted"
    UNCHANGED = "unchanged"
    HEADER = "header"


class WordDiffSchema(BaseModel):
    type: str = Field(..., description="'added', 'deleted', or 'unchanged'")
    text: str


class DiffLineSchema(BaseModel):
    type: DiffLineType
    old_line_no: Optional[int] = None
    new_line_no: Optional[int] = None
    content: str
    word_diffs: Optional[List[WordDiffSchema]] = None


class SideBySideRowSchema(BaseModel):
    row_type: str = Field(..., description="'unchanged', 'modified', 'added', or 'deleted'")
    left_line_no: Optional[int] = None
    left_content: Optional[str] = None
    left_type: Optional[str] = None
    right_line_no: Optional[int] = None
    right_content: Optional[str] = None
    right_type: Optional[str] = None
    left_words: Optional[List[WordDiffSchema]] = None
    right_words: Optional[List[WordDiffSchema]] = None


class DiffHunkSchema(BaseModel):
    old_start: int
    old_lines_count: int
    new_start: int
    new_lines_count: int
    header: str
    lines: List[DiffLineSchema]


class DiffStatsSchema(BaseModel):
    total_lines_old: int = 0
    total_lines_new: int = 0
    added_lines: int = 0
    deleted_lines: int = 0
    changed_lines: int = 0
    is_identical: bool = False
    is_truncated: bool = False
    truncation_note: Optional[str] = None


class DeterministicDiffSchema(BaseModel):
    stats: DiffStatsSchema
    unified_hunks: List[DiffHunkSchema] = []
    side_by_side_rows: List[SideBySideRowSchema] = []
    raw_unified_diff: str = ""


class ClauseChangeItem(BaseModel):
    clause_title: str = Field(..., description="Name or topic of affected clause, e.g. Data Retention, Dispute Resolution")
    change_type: str = Field(..., description="Added, Modified, Removed, Clarified")
    intent: str = Field(..., description="What the change accomplishes")
    impact_level: str = Field(..., description="Low, Medium, High, or Critical")
    risk_pillar: str = Field(..., description="Privacy, Security, Compliance, or Legal")
    quote: Optional[str] = Field(None, description="Verbatim snippet from changed text")


class SemanticImpactSchema(BaseModel):
    executive_change_summary: str = Field(..., description="Plain-English synthesis of what contractual/security terms changed")
    materiality: MaterialityTier = Field(..., description="Overall materiality: Low, Medium, High, or Critical")
    affected_clauses: List[str] = Field(default_factory=list, description="Titles or labels of affected clauses")
    clause_category: str = Field(..., description="Primary category of changes (e.g., Data Privacy, Security Controls, Legal Liability)")
    modification_intent: str = Field(..., description="Primary business or contractual objective behind the change")
    affected_risk_pillar: RiskPillar = Field(..., description="Primary risk pillar impacted: Privacy, Security, Compliance, Legal, or Multiple")
    risk_posture: RiskPostureImpact = Field(..., description="Impact on enterprise risk posture: Favorable, Neutral, or Adverse")
    risk_delta_explanation: str = Field(..., description="Detailed explanation of why risk increased, decreased, or remained neutral")
    clause_breakdown: List[ClauseChangeItem] = Field(default_factory=list, description="Individual clause change analyses")


class PolicyVersionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    version_number: int
    content_hash: str
    crawled_at: datetime
    summary: Optional[str] = None
    change_summary: Optional[str] = None
    line_count: int = 0


class PolicyDiffResponse(BaseModel):
    vendor_id: str
    vendor_name: str
    document_id: str
    document_title: str
    document_type: str
    old_version: PolicyVersionSummary
    new_version: PolicyVersionSummary
    deterministic_diff: DeterministicDiffSchema
    semantic_impact: SemanticImpactSchema
    is_cached: bool = False
    analyzed_at: datetime
