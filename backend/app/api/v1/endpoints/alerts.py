from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertResponse, AlertListResponse, AlertUpdate

router = APIRouter()


@router.get("", response_model=AlertListResponse)

async def list_alerts(
    vendor_id: Optional[str] = Query(None, description="Filter alerts by vendor ID"),
    alert_type: Optional[str] = Query(None, description="Filter alerts by type (e.g. Policy Change, Risk Degradation)"),
    severity: Optional[str] = Query(None, description="Filter alerts by severity (Low, Medium, High, Critical)"),
    is_read: Optional[bool] = Query(None, description="Filter alerts by read status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves persisted alerts with support for pagination and multi-field filtering.
    """
    stmt = select(Alert)
    count_stmt = select(func.count(Alert.id))

    if vendor_id:
        stmt = stmt.where(Alert.vendor_id == vendor_id)
        count_stmt = count_stmt.where(Alert.vendor_id == vendor_id)
    if alert_type:
        stmt = stmt.where(Alert.alert_type == alert_type)
        count_stmt = count_stmt.where(Alert.alert_type == alert_type)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
        count_stmt = count_stmt.where(Alert.severity == severity)
    if is_read is not None:
        stmt = stmt.where(Alert.is_read.is_(is_read))
        count_stmt = count_stmt.where(Alert.is_read.is_(is_read))


    # Order by creation date descending
    stmt = stmt.order_by(Alert.created_at.desc()).offset(skip).limit(limit)

    total = (await db.execute(count_stmt)).scalar() or 0
    res = await db.execute(stmt)
    alerts = list(res.scalars().all())

    return AlertListResponse(
        items=[AlertResponse.model_validate(a) for a in alerts],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/vendor/{vendor_id}", response_model=List[AlertResponse])
async def get_vendor_alerts(
    vendor_id: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves alerts specifically for a single vendor.
    """
    stmt = (
        select(Alert)
        .where(Alert.vendor_id == vendor_id)
        .order_by(Alert.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(stmt)
    alerts = list(res.scalars().all())
    return [AlertResponse.model_validate(a) for a in alerts]


@router.patch("/{alert_id}/read", response_model=AlertResponse)
async def mark_alert_as_read(
    alert_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Marks an alert as read.
    """
    stmt = select(Alert).where(Alert.id == alert_id)
    res = await db.execute(stmt)
    alert = res.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID '{alert_id}' not found."
        )

    alert.is_read = True
    await db.commit()
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)
