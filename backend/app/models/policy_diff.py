import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class PolicyDiff(Base, TimestampMixin):
    __tablename__ = "policy_diffs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    old_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("policy_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    new_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("policy_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    executive_change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    materiality: Mapped[str] = mapped_column(String(20), nullable=False, default="Low")
    affected_clauses: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    clause_category: Mapped[str] = mapped_column(String(100), nullable=False)
    modification_intent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    affected_risk_pillar: Mapped[str] = mapped_column(String(50), nullable=False, default="Multiple")
    risk_posture: Mapped[str] = mapped_column(String(20), nullable=False, default="Neutral")
    risk_delta_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clause_breakdown: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("old_version_id", "new_version_id", name="uq_policy_diff_version_pair"),
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document")
    old_version: Mapped["PolicyVersion"] = relationship("PolicyVersion", foreign_keys=[old_version_id])
    new_version: Mapped["PolicyVersion"] = relationship("PolicyVersion", foreign_keys=[new_version_id])
