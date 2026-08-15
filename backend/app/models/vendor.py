import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Float, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base
from app.models.base import TimestampMixin


class RiskTier(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class VendorStatus(str, enum.Enum):
    ACTIVE = "Active"
    UNDER_REVIEW = "Under Review"
    ARCHIVED = "Archived"


class MonitoringFrequency(str, enum.Enum):
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"


class Vendor(Base, TimestampMixin):
    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    website_url: Mapped[str] = mapped_column(String(512), nullable=False)
    
    risk_tier: Mapped[RiskTier] = mapped_column(
        SQLEnum(RiskTier, values_callable=lambda obj: [e.value for e in obj]),
        default=RiskTier.MEDIUM,
        nullable=False
    )
    current_risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[VendorStatus] = mapped_column(
        SQLEnum(VendorStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=VendorStatus.ACTIVE,
        nullable=False
    )
    monitoring_frequency: Mapped[MonitoringFrequency] = mapped_column(
        SQLEnum(MonitoringFrequency, values_callable=lambda obj: [e.value for e in obj]),
        default=MonitoringFrequency.DAILY,
        nullable=False
    )
    
    last_monitored_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="vendor",
        cascade="all, delete-orphan"
    )
    risk_assessments: Mapped[List["RiskAssessment"]] = relationship(
        "RiskAssessment",
        back_populates="vendor",
        cascade="all, delete-orphan"
    )
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert",
        back_populates="vendor",
        cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="vendor",
        cascade="all, delete-orphan"
    )
