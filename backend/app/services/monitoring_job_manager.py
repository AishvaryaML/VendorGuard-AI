import uuid
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from app.core.database import AsyncSessionLocal
from app.services.monitoring import MonitoringService

logger = logging.getLogger("vendorguard.monitoring.jobs")


@dataclass
class MonitoringJob:
    """Represents a continuous monitoring background execution job."""
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    total_vendors: int = 0
    completed_vendors: int = 0
    current_vendor: Optional[str] = None
    successful_vendors: int = 0
    failed_vendors: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "total_vendors": self.total_vendors,
            "completed_vendors": self.completed_vendors,
            "current_vendor": self.current_vendor,
            "successful_vendors": self.successful_vendors,
            "failed_vendors": self.failed_vendors,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


class BaseMonitoringJobStore(ABC):
    """Abstract interface for monitoring job persistence."""

    @abstractmethod
    def create_job(self, total_vendors: int) -> MonitoringJob:
        """Creates and stores a new monitoring job."""
        pass

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[MonitoringJob]:
        """Retrieves a monitoring job by its ID."""
        pass

    @abstractmethod
    def update_job(self, job: MonitoringJob) -> None:
        """Updates the status and progress of an existing job."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clears all jobs (primarily for test teardown)."""
        pass


class InMemoryMonitoringJobStore(BaseMonitoringJobStore):
    """In-memory thread-safe implementation of monitoring job store."""

    def __init__(self):
        self._jobs: Dict[str, MonitoringJob] = {}

    def create_job(self, total_vendors: int) -> MonitoringJob:
        job_id = str(uuid.uuid4())
        job = MonitoringJob(
            job_id=job_id,
            status="pending",
            total_vendors=total_vendors,
            completed_vendors=0,
            current_vendor=None,
            successful_vendors=0,
            failed_vendors=0,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            error=None
        )
        self._jobs[job_id] = job
        logger.info(f"Created monitoring job '{job_id}' for {total_vendors} vendor(s).")
        return job

    def get_job(self, job_id: str) -> Optional[MonitoringJob]:
        return self._jobs.get(job_id)

    def update_job(self, job: MonitoringJob) -> None:
        self._jobs[job.job_id] = job

    def clear(self) -> None:
        self._jobs.clear()


# Global Singleton Job Store
_job_store_instance: Optional[BaseMonitoringJobStore] = None


def get_monitoring_job_store() -> BaseMonitoringJobStore:
    """Returns the active monitoring job store singleton."""
    global _job_store_instance
    if _job_store_instance is None:
        _job_store_instance = InMemoryMonitoringJobStore()
    return _job_store_instance


async def run_monitoring_job_task(
    job_id: str,
    vendor_ids: List[str],
    force: bool = False,
    mock_risk_result: Optional[Any] = None
) -> None:
    """
    Background worker function executed via FastAPI BackgroundTasks.
    Uses its own isolated database sessions via AsyncSessionLocal.
    Provides per-vendor failure isolation and maintains real-time job progress.
    """
    job_store = get_monitoring_job_store()
    job = job_store.get_job(job_id)

    if not job:
        logger.error(f"Cannot execute monitoring job '{job_id}': Job not found in store.")
        return

    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    job_store.update_job(job)

    if not vendor_ids:
        logger.info(f"Monitoring job '{job_id}' has 0 vendors to process. Marking completed.")
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job_store.update_job(job)
        return

    monitoring_service = MonitoringService()

    try:
        for v_id in vendor_ids:
            # Use isolated database session per vendor
            async with AsyncSessionLocal() as session:
                try:
                    from app.models.vendor import Vendor
                    from sqlalchemy import select

                    v_res = await session.execute(select(Vendor).where(Vendor.id == v_id))
                    vendor = v_res.scalar_one_or_none()
                    vendor_name = vendor.name if vendor else f"Vendor {v_id}"

                    job.current_vendor = vendor_name
                    job_store.update_job(job)

                    logger.info(f"Job '{job_id}': Monitoring vendor '{vendor_name}' ({v_id})...")
                    res = await monitoring_service.monitor_single_vendor(
                        db=session,
                        vendor_id=v_id,
                        force=force,
                        mock_risk_result=mock_risk_result
                    )

                    if res.get("status") in ("Success", "Skipped"):
                        job.successful_vendors += 1
                    else:
                        job.failed_vendors += 1

                except Exception as exc:
                    logger.error(f"Job '{job_id}': Error monitoring vendor {v_id}: {str(exc)}", exc_info=True)
                    job.failed_vendors += 1

                finally:
                    job.completed_vendors += 1
                    job_store.update_job(job)

        # Job complete
        job.current_vendor = None
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job_store.update_job(job)
        logger.info(
            f"Monitoring job '{job_id}' completed: {job.completed_vendors}/{job.total_vendors} processed "
            f"({job.successful_vendors} successful, {job.failed_vendors} failed)."
        )

    except Exception as fatal_exc:
        logger.critical(f"Fatal error executing monitoring job '{job_id}': {str(fatal_exc)}", exc_info=True)
        job.current_vendor = None
        job.status = "failed"
        job.error = str(fatal_exc)
        job.completed_at = datetime.now(timezone.utc)
        job_store.update_job(job)
