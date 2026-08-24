import logging
from typing import Optional, List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("vendorguard.scheduler")


class SchedulerManager:
    """
    Singleton Scheduler Manager for VendorGuard Continuous Monitoring.
    Wraps APScheduler AsyncIOScheduler and integrates cleanly with FastAPI lifespan.
    """

    _instance: Optional["SchedulerManager"] = None
    _scheduler: Optional[AsyncIOScheduler] = None

    def __new__(cls) -> "SchedulerManager":
        if cls._instance is None:
            cls._instance = super(SchedulerManager, cls).__new__(cls)
        return cls._instance

    @property
    def scheduler(self) -> AsyncIOScheduler:
        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler()
        return self._scheduler

    def start(self) -> None:
        """Starts the scheduler cleanly if not already running."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("APScheduler Continuous Monitoring Service started.")
        else:
            logger.debug("APScheduler is already running.")

    def shutdown(self, wait: bool = False) -> None:
        """Shuts down the scheduler cleanly if running."""
        if self._scheduler:
            if self._scheduler.running:
                self._scheduler.shutdown(wait=wait)
                logger.info("APScheduler Continuous Monitoring Service shut down.")
            self._scheduler = None
        else:
            logger.debug("APScheduler is not running.")

    @property
    def is_running(self) -> bool:
        return self._scheduler.running if (self._scheduler is not None) else False

    def add_monitoring_job(
        self,
        func,
        hours: int = 1,
        job_id: str = "vendor_continuous_monitoring"
    ) -> None:
        """Adds or replaces a periodic background monitoring job."""
        if not self.scheduler.get_job(job_id):
            self.scheduler.add_job(
                func,
                trigger=IntervalTrigger(hours=hours),
                id=job_id,
                name="Periodic Vendor Policy & Risk Monitoring",
                replace_existing=True,
                max_instances=1
            )
            logger.info(f"Added monitoring job '{job_id}' running every {hours} hour(s).")

    def get_jobs_info(self) -> List[Dict[str, Any]]:
        """Returns details about currently scheduled background jobs."""
        if not self._scheduler:
            return []
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs


scheduler_manager = SchedulerManager()
