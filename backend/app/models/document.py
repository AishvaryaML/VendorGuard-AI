import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin



class Document(Base, TimestampMixin):
    __tablename__ = "documents"

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
    document_type: Mapped[str] = mapped_column(String(100), nullable=False) # Privacy Policy, Terms of Service, Security Center, etc.
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    current_version_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True) # SHA-256 hash
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="documents")
    versions: Mapped[List["PolicyVersion"]] = relationship(
        "PolicyVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="PolicyVersion.version_number.desc()"
    )


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

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
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False) # SHA-256 hash
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="versions")
