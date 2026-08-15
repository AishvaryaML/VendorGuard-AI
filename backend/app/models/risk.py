import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any
from sqlalchemy import String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class RiskAssessment(Base, TimestampMixin):
    __tablename__ = "risk_assessments"

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
    assessment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False
    )

    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0) # 0 to 100
    risk_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="Medium") # Low, Medium, High, Critical
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_findings: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True) # List of key risk findings
    citations: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True) # Document quote citations
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Completed") # Completed, Failed, In Progress

    # Relationships
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="risk_assessments")
    category_scores: Mapped[List["CategoryScore"]] = relationship(
        "CategoryScore",
        back_populates="assessment",
        cascade="all, delete-orphan"
    )


class CategoryScore(Base):
    __tablename__ = "category_scores"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    assessment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("risk_assessments.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    category_name: Mapped[str] = mapped_column(String(50), nullable=False) # Privacy, Security, Compliance, Legal
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0) # 0 to 100
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    findings: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    # Relationships
    assessment: Mapped["RiskAssessment"] = relationship("RiskAssessment", back_populates="category_scores")
