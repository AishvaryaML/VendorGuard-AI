from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.vendor import Vendor, RiskTier, VendorStatus, MonitoringFrequency
from app.models.document import Document, PolicyVersion
from app.models.alert import Alert
from app.models.audit import AuditLog
from app.schemas.vendor import VendorCreate, VendorUpdate
from app.services.crawler import VendorCrawlerService, normalize_url, extract_domain
from app.core.logging import logger


async def create_vendor_and_discover_documents(
    db: AsyncSession,
    vendor_in: VendorCreate,
    crawler_service: Optional[VendorCrawlerService] = None
) -> Tuple[Vendor, List[Document]]:
    """
    Creates a new Vendor profile in DB and triggers the document discovery / crawling pipeline.
    Persists discovered Documents and PolicyVersions with SHA-256 versioning.
    """
    normalized_url = normalize_url(vendor_in.website_url)
    domain = extract_domain(normalized_url)

    # Check if Vendor already exists by domain
    stmt = select(Vendor).where(Vendor.domain == domain)
    res = await db.execute(stmt)
    existing_vendor = res.scalar_one_or_none()

    if existing_vendor:
        vendor = existing_vendor
    else:
        vendor = Vendor(
            name=vendor_in.name,
            domain=domain,
            industry=vendor_in.industry,
            website_url=normalized_url,
            risk_tier=RiskTier.MEDIUM,
            current_risk_score=0.0,
            status=VendorStatus.ACTIVE,
            monitoring_frequency=vendor_in.monitoring_frequency
        )
        db.add(vendor)
        await db.commit()
        await db.refresh(vendor)

        # Log Audit event
        audit = AuditLog(
            vendor_id=vendor.id,
            action="VENDOR_CREATED",
            actor="System API",
            details={"name": vendor.name, "domain": domain, "website_url": normalized_url}
        )
        db.add(audit)
        await db.commit()

    # Run discovery crawl
    crawler = crawler_service or VendorCrawlerService()
    crawl_data = await crawler.crawl_vendor(normalized_url)

    # Process and persist documents
    documents = await sync_vendor_crawled_documents(db, vendor.id, crawl_data["documents"])

    # Update vendor last_monitored_at timestamp
    vendor.last_monitored_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(vendor)

    return vendor, documents


async def sync_vendor_crawled_documents(
    db: AsyncSession,
    vendor_id: str,
    raw_documents: List[Dict[str, Any]]
) -> List[Document]:
    """
    Persists crawled documents and applies SHA-256 versioning logic:
    - If new document: creates Document + PolicyVersion (v1).
    - If hash unchanged: updates last_crawled_at timestamp only (no duplicate version).
    - If hash changed: creates new PolicyVersion (v+1) and triggers Alert.
    """
    processed_documents: List[Document] = []
    now_utc = datetime.now(timezone.utc)

    for doc_data in raw_documents:
        doc_type = doc_data["document_type"]
        doc_url = doc_data["url"]
        doc_title = doc_data["title"]
        clean_text = doc_data["clean_text"]
        content_hash = doc_data["content_hash"]

        # Check existing document for this vendor
        stmt = (
            select(Document)
            .options(selectinload(Document.versions))
            .where(Document.vendor_id == vendor_id, Document.document_type == doc_type)
        )
        res = await db.execute(stmt)
        existing_doc = res.scalar_one_or_none()

        if not existing_doc:
            # Create new Document
            document = Document(
                vendor_id=vendor_id,
                document_type=doc_type,
                title=doc_title,
                url=doc_url,
                current_version_hash=content_hash,
                last_crawled_at=now_utc
            )
            db.add(document)
            await db.commit()
            await db.refresh(document)

            # Create Initial Policy Version v1
            version = PolicyVersion(
                document_id=document.id,
                version_number=1,
                content_hash=content_hash,
                raw_content=clean_text,
                summary=f"Initial discovery of {doc_type}.",
                crawled_at=now_utc
            )
            db.add(version)
            await db.commit()
            processed_documents.append(document)

        else:
            document = existing_doc
            latest_version = document.versions[0] if document.versions else None

            if latest_version and latest_version.content_hash == content_hash:
                # Hash is identical - do NOT create a new version
                document.last_crawled_at = now_utc
                await db.commit()
                processed_documents.append(document)
            else:
                # Hash has changed! Increment version & create new PolicyVersion
                next_version_num = (latest_version.version_number + 1) if latest_version else 1
                
                new_version = PolicyVersion(
                    document_id=document.id,
                    version_number=next_version_num,
                    content_hash=content_hash,
                    raw_content=clean_text,
                    summary=f"Updated policy text detected for {doc_type}.",
                    change_summary="Content modification detected via SHA-256 hash delta.",
                    crawled_at=now_utc
                )
                db.add(new_version)

                # Update document current_version_hash
                document.current_version_hash = content_hash
                document.last_crawled_at = now_utc

                # Create Alert for policy change
                alert = Alert(
                    vendor_id=vendor_id,
                    alert_type="Policy Change",
                    severity="Low",
                    title=f"Policy Updated: {doc_type}",
                    description=f"A change in text content (SHA-256 delta) was detected for {document.title}."
                )
                db.add(alert)

                await db.commit()
                processed_documents.append(document)

    return processed_documents


async def get_vendor_by_id(db: AsyncSession, vendor_id: str) -> Optional[Vendor]:
    """Retrieves a Vendor by ID with documents and risk assessments loaded."""
    stmt = (
        select(Vendor)
        .options(
            selectinload(Vendor.documents).selectinload(Document.versions),
            selectinload(Vendor.risk_assessments),
            selectinload(Vendor.alerts)
        )
        .where(Vendor.id == vendor_id)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def list_vendors(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Vendor]:
    """Lists vendor records ordered by created_at desc."""
    stmt = select(Vendor).order_by(Vendor.created_at.desc()).offset(skip).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())
