from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.vendor import Vendor
from app.models.document import Document
from app.models.alert import Alert
from app.schemas.monitoring_schema import (
    MonitoringTriggerRequest,
    MonitoringTriggerResponse,
    VendorMonitoringResult,
    VendorMonitoringStatusResponse,
)
from app.services.monitoring import (
    MonitoringService,
    is_vendor_due_for_monitoring,
    get_next_monitoring_due_time,
)

router = APIRouter()


@router.post("/trigger", response_model=MonitoringTriggerResponse, status_code=status.HTTP_200_OK)
async def trigger_monitoring(
    req: Optional[MonitoringTriggerRequest] = None,
    vendor_id: Optional[str] = Query(None, description="Optional vendor ID to trigger specifically"),
    force: bool = Query(False, description="If True, forces monitoring even if not due"),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually triggers continuous risk monitoring cycle for all due vendors or a specified vendor.
    Re-crawls policy pages, detects SHA-256 hash changes, computes text diffs,
    triggers Phase 3 risk reassessment when changes occur, and generates risk degradation alerts.
    """
    target_id = vendor_id or (req.vendor_id if req else None)
    should_force = force or (req.force if req else False)

    if target_id:
        vendor_stmt = select(Vendor).where(Vendor.id == target_id)
        res = await db.execute(vendor_stmt)
        if not res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vendor with ID '{target_id}' not found."
            )

    service = MonitoringService()
    results_raw = await service.run_monitoring_cycle(db=db, target_vendor_id=target_id, force=should_force)

    results = [VendorMonitoringResult(**res) for res in results_raw]

    return MonitoringTriggerResponse(
        message=f"Monitoring cycle completed for {len(results)} vendor(s).",
        timestamp=datetime.now(timezone.utc),
        monitored_count=len(results),
        results=results
    )


@router.get("/status/{vendor_id}", response_model=VendorMonitoringStatusResponse)
async def get_vendor_monitoring_status(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves detailed continuous monitoring metadata and status for a specific vendor.
    Returns last crawl time, next due time, frequency, documents count, active alerts, and risk tier.
    """
    vendor_stmt = select(Vendor).where(Vendor.id == vendor_id)
    res = await db.execute(vendor_stmt)
    vendor = res.scalar_one_or_none()

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID '{vendor_id}' not found."
        )

    now_utc = datetime.now(timezone.utc)
    is_due = is_vendor_due_for_monitoring(vendor, now_utc)
    next_due = get_next_monitoring_due_time(vendor)

    # Count documents
    doc_count_stmt = select(func.count(Document.id)).where(Document.vendor_id == vendor_id)
    doc_count = (await db.execute(doc_count_stmt)).scalar() or 0

    # Count unread alerts
    alert_count_stmt = select(func.count(Alert.id)).where(Alert.vendor_id == vendor_id, Alert.is_read == False)
    active_alerts_count = (await db.execute(alert_count_stmt)).scalar() or 0

    return VendorMonitoringStatusResponse(
        vendor_id=vendor.id,
        vendor_name=vendor.name,
        monitoring_frequency=vendor.monitoring_frequency.value,
        last_monitored_at=vendor.last_monitored_at,
        next_monitoring_due=next_due,
        is_due=is_due,
        documents_count=doc_count,
        active_alerts_count=active_alerts_count,
        last_risk_score=vendor.current_risk_score,
        last_risk_tier=vendor.risk_tier.value
    )
