from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.vendor import Vendor
from app.models.document import Document
from app.models.alert import Alert
from app.schemas.monitoring_schema import (
    MonitoringTriggerRequest,
    MonitoringTriggerResponse,
    MonitoringJobStatusResponse,
    VendorMonitoringResult,
    VendorMonitoringStatusResponse,
)
from app.services.monitoring import (
    MonitoringService,
    is_vendor_due_for_monitoring,
    get_next_monitoring_due_time,
)
from app.services.monitoring_job_manager import (
    get_monitoring_job_store,
    run_monitoring_job_task,
)

router = APIRouter()


@router.post("/trigger", response_model=MonitoringTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_monitoring(
    background_tasks: BackgroundTasks,
    req: Optional[MonitoringTriggerRequest] = None,
    vendor_id: Optional[str] = Query(None, description="Optional vendor ID to trigger specifically"),
    force: bool = Query(False, description="If True, forces monitoring even if not due"),
    db: AsyncSession = Depends(get_db)
):
    """
    Asynchronously triggers continuous risk monitoring cycle for all due vendors or a specified vendor.
    Immediately creates a background monitoring job and returns HTTP 202 Accepted.
    Crawing, hash change detection, diffing, and risk evaluation execute in the background.
    """
    target_id = vendor_id or (req.vendor_id if req else None)
    should_force = force or (req.force if req else False)

    if target_id:
        vendor_stmt = select(Vendor).where(Vendor.id == target_id)
        res = await db.execute(vendor_stmt)
        vendor = res.scalar_one_or_none()
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vendor with ID '{target_id}' not found."
            )
        due_vendor_ids = [target_id]
    else:
        # Determine which active vendors are due for monitoring
        stmt = select(Vendor).where(Vendor.status == "Active")
        res = await db.execute(stmt)
        active_vendors = list(res.scalars().all())

        if should_force:
            due_vendor_ids = [v.id for v in active_vendors]
        else:
            now_utc = datetime.now(timezone.utc)
            due_vendor_ids = [v.id for v in active_vendors if is_vendor_due_for_monitoring(v, now_utc)]

    # Create background monitoring job
    job_store = get_monitoring_job_store()
    job = job_store.create_job(total_vendors=len(due_vendor_ids))

    # Queue background execution using safe isolated sessions
    background_tasks.add_task(
        run_monitoring_job_task,
        job.job_id,
        due_vendor_ids,
        should_force
    )

    return MonitoringTriggerResponse(
        job_id=job.job_id,
        status=job.status,
        message="Monitoring job accepted",
        total_vendors=job.total_vendors
    )


@router.get("/jobs/{job_id}", response_model=MonitoringJobStatusResponse)
async def get_monitoring_job_status(job_id: str):
    """
    Retrieves current progress and metrics for an asynchronous background monitoring job.
    Returns pending, running, completed, or failed state with counts.
    """
    job_store = get_monitoring_job_store()
    job = job_store.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring job '{job_id}' not found."
        )

    return MonitoringJobStatusResponse(**job.to_dict())


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
