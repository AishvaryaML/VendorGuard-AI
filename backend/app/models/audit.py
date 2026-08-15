import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    vendor_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False) # VENDOR_CREATED, ANALYSIS_STARTED, ANALYSIS_COMPLETED, ALERT_GENERATED, POLICY_UPDATED
    actor: Mapped[str] = mapped_column(String(100), default="System", nullable=False)
    details: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        index=True,
        nullable=False
    )

    # Relationships
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor", back_populates="audit_logs")
