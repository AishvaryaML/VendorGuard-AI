import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base
from app.models.base import TimestampMixin

class ComplianceStatus(str, enum.Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    GAP = "GAP"
    NOT_ASSESSED = "NOT_ASSESSED"

class ComplianceAssessment(Base, TimestampMixin):
    __tablename__ = "compliance_assessments"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    vendor_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    framework: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    control_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    status: Mapped[ComplianceStatus] = mapped_column(
        SQLEnum(ComplianceStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ComplianceStatus.NOT_ASSESSED,
        nullable=False
    )
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    source_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gap_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # Relationships
    vendor = relationship("Vendor")
