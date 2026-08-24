import difflib
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.vendor import Vendor, RiskTier, MonitoringFrequency
from app.models.document import Document, PolicyVersion
from app.models.risk import RiskAssessment, CategoryScore
from app.models.alert import Alert
from app.models.audit import AuditLog
from app.services.crawler import VendorCrawlerService
from app.services.vendor_service import get_vendor_by_id
from app.services.risk_engine import AIRiskEngine, get_latest_vendor_risk_assessment

logger = logging.getLogger("vendorguard.monitoring")

# Thresholds for Risk Degradation Alerting
DEGRADATION_OVERALL_SCORE_THRESHOLD = 10.0  # Overall score jump >= 10 points
DEGRADATION_CATEGORY_SCORE_THRESHOLD = 15.0  # Category score jump >= 15 points

TIER_SEVERITY_ORDER = {
    RiskTier.LOW: 1,
    RiskTier.MEDIUM: 2,
    RiskTier.HIGH: 3,
    RiskTier.CRITICAL: 4,
}


def get_frequency_timedelta(frequency: MonitoringFrequency) -> timedelta:
    """Returns timedelta corresponding to Vendor monitoring frequency."""
    if frequency == MonitoringFrequency.DAILY:
        return timedelta(hours=24)
    elif frequency == MonitoringFrequency.WEEKLY:
        return timedelta(hours=168)  # 7 days
    elif frequency == MonitoringFrequency.MONTHLY:
        return timedelta(hours=720)  # 30 days
    return timedelta(hours=24)


def is_vendor_due_for_monitoring(vendor: Vendor, now: Optional[datetime] = None) -> bool:
    """
    Determines if a vendor is due for scheduled monitoring based on last_monitored_at and monitoring_frequency.
    """
    if not vendor.last_monitored_at:
        return True

    now = now or datetime.now(timezone.utc)
    # Handle both naive and aware timestamps defensively
    last_mon = vendor.last_monitored_at
    if last_mon.tzinfo is None:
        last_mon = last_mon.replace(tzinfo=timezone.utc)

    interval = get_frequency_timedelta(vendor.monitoring_frequency)
    return (now - last_mon) >= interval


def get_next_monitoring_due_time(vendor: Vendor) -> Optional[datetime]:
    """Calculates next scheduled monitoring time for a vendor."""
    if not vendor.last_monitored_at:
        return datetime.now(timezone.utc)
    last_mon = vendor.last_monitored_at
    if last_mon.tzinfo is None:
        last_mon = last_mon.replace(tzinfo=timezone.utc)
    return last_mon + get_frequency_timedelta(vendor.monitoring_frequency)


def generate_policy_diff(old_text: str, new_text: str) -> str:
    """
    Generates a lightweight text diff summary between previous and new PolicyVersion content.
    Identifies line additions, removals, and overall modification volume.
    """
    if not old_text:
        return "Initial policy document content captured."
    if not new_text:
        return "Policy document text emptied."

    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))

    added_count = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed_count = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

    if added_count == 0 and removed_count == 0:
        return "No text changes detected."

    return f"Policy text updated: +{added_count} line(s) added, -{removed_count} line(s) removed."


class MonitoringService:
    """
    Dedicated Service for Continuous Vendor Risk Monitoring.
    Handles scheduled re-crawling, SHA-256 delta detection, lightweight text diffing,
    risk reassessment triggers, risk degradation alerting, and alert deduplication.
    """

    def __init__(self, crawler: Optional[VendorCrawlerService] = None, risk_engine: Optional[AIRiskEngine] = None):
        self.crawler = crawler or VendorCrawlerService()
        self.risk_engine = risk_engine or AIRiskEngine()

    async def monitor_single_vendor(
        self,
        db: AsyncSession,
        vendor_id: str,
        force: bool = False,
        mock_risk_result: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Monitors a single vendor:
        1. Verifies vendor and checks if due (unless force=True).
        2. Re-crawls policy pages.
        3. Detects document changes via SHA-256 hash comparison.
        4. If changed: creates new PolicyVersion with diff summary + Policy Change Alert.
        5. If changed: triggers Phase 3 RiskEngine re-assessment.
        6. Compares previous vs. new RiskAssessment for risk degradation (overall score >= 10, category >= 15, tier jump).
        7. Generates Risk Degradation Alert if criteria met.
        8. Updates vendor last_monitored_at.
        """
        now_utc = datetime.now(timezone.utc)

        stmt = (
            select(Vendor)
            .options(
                selectinload(Vendor.documents).selectinload(Document.versions),
                selectinload(Vendor.risk_assessments).selectinload(RiskAssessment.category_scores),
                selectinload(Vendor.alerts)
            )
            .where(Vendor.id == vendor_id)
        )
        res = await db.execute(stmt)
        vendor = res.scalar_one_or_none()

        if not vendor:
            raise ValueError(f"Vendor with ID '{vendor_id}' not found.")

        if not force and not is_vendor_due_for_monitoring(vendor, now_utc):
            logger.info(f"Vendor '{vendor.name}' is not due for monitoring yet. Skipping.")
            return {
                "vendor_id": vendor_id,
                "vendor_name": vendor.name,
                "status": "Skipped",
                "reason": "Not due for monitoring",
                "documents_checked": 0,
                "documents_changed": 0,
                "risk_reassessed": False,
                "alerts_generated": 0
            }

        logger.info(f"Starting continuous monitoring cycle for vendor '{vendor.name}' ({vendor.domain})...")

        documents_checked = 0
        documents_changed = 0
        alerts_generated = 0
        has_any_document_changed = False

        # Get previous risk assessment before crawl/reassessment
        previous_assessment = await get_latest_vendor_risk_assessment(db, vendor_id)

        try:
            # 1. Crawl vendor website
            crawl_data = await self.crawler.crawl_vendor(vendor.website_url)
            raw_crawled_docs = crawl_data.get("documents", [])

            for doc_data in raw_crawled_docs:
                doc_type = doc_data["document_type"]
                doc_url = doc_data["url"]
                doc_title = doc_data["title"]
                clean_text = doc_data["clean_text"]
                content_hash = doc_data["content_hash"]
                documents_checked += 1

                # Check if document exists in DB
                doc_stmt = (
                    select(Document)
                    .options(selectinload(Document.versions))
                    .where(Document.vendor_id == vendor_id, Document.document_type == doc_type)
                )
                doc_res = await db.execute(doc_stmt)
                existing_doc = doc_res.scalar_one_or_none()

                if not existing_doc:
                    # New Document discovered
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

                    # Create initial PolicyVersion v1
                    version = PolicyVersion(
                        document_id=document.id,
                        version_number=1,
                        content_hash=content_hash,
                        raw_content=clean_text,
                        summary=f"Initial discovery of {doc_type}.",
                        change_summary="Initial policy document content captured.",
                        crawled_at=now_utc
                    )
                    db.add(version)
                    await db.commit()

                    documents_changed += 1
                    has_any_document_changed = True

                else:
                    document = existing_doc
                    latest_version = document.versions[0] if document.versions else None

                    if latest_version and latest_version.content_hash == content_hash:
                        # Hash UNCHANGED -> Update last_crawled_at ONLY. Do NOT create duplicate version or alert or run LLM!
                        document.last_crawled_at = now_utc
                        await db.commit()
                    else:
                        # Hash CHANGED! Increment version and compute text diff
                        next_version_num = (latest_version.version_number + 1) if latest_version else 1
                        old_text = latest_version.raw_content if latest_version else ""
                        diff_summary = generate_policy_diff(old_text, clean_text)

                        new_version = PolicyVersion(
                            document_id=document.id,
                            version_number=next_version_num,
                            content_hash=content_hash,
                            raw_content=clean_text,
                            summary=f"Updated policy text detected for {doc_type}.",
                            change_summary=diff_summary,
                            crawled_at=now_utc
                        )
                        db.add(new_version)

                        document.current_version_hash = content_hash
                        document.last_crawled_at = now_utc

                        # Generate Policy Change Alert (with deduplication check)
                        alert_title = f"Policy Updated: {doc_type}"
                        alert_desc = f"Text content modified for {document.title} (v{next_version_num}). {diff_summary}"

                        dedup_stmt = select(Alert).where(
                            Alert.vendor_id == vendor_id,
                            Alert.alert_type == "Policy Change",
                            Alert.title == alert_title
                        )
                        existing_alert = (await db.execute(dedup_stmt)).scalars().first()

                        if not existing_alert or existing_alert.description != alert_desc:
                            change_alert = Alert(
                                vendor_id=vendor_id,
                                alert_type="Policy Change",
                                severity="Low",
                                title=alert_title,
                                description=alert_desc
                            )
                            db.add(change_alert)
                            alerts_generated += 1

                        await db.commit()

                        documents_changed += 1
                        has_any_document_changed = True

            # 2. Risk Reassessment Trigger
            risk_reassessed = False
            if has_any_document_changed:
                logger.info(f"Policy changes detected for '{vendor.name}'. Triggering Phase 3 RiskEngine re-assessment...")
                
                new_assessment = await self.risk_engine.analyze_vendor(
                    db=db,
                    vendor_id=vendor_id,
                    mock_result=mock_risk_result
                )
                risk_reassessed = True

                # Compare Previous vs. New Risk Assessment for Risk Degradation Alerting
                if previous_assessment and new_assessment:
                    degradation_alerts = await self._evaluate_risk_degradation(
                        db=db,
                        vendor=vendor,
                        prev_assessment=previous_assessment,
                        new_assessment=new_assessment
                    )
                    alerts_generated += degradation_alerts

            # Update Vendor last_monitored_at
            vendor.last_monitored_at = now_utc
            
            # Log Audit entry
            audit = AuditLog(
                vendor_id=vendor_id,
                action="MONITORING_COMPLETED",
                actor="Monitoring Service",
                details={
                    "checked": documents_checked,
                    "changed": documents_changed,
                    "risk_reassessed": risk_reassessed,
                    "alerts_generated": alerts_generated
                }
            )
            db.add(audit)
            await db.commit()

            return {
                "vendor_id": vendor_id,
                "vendor_name": vendor.name,
                "status": "Success",
                "documents_checked": documents_checked,
                "documents_changed": documents_changed,
                "risk_reassessed": risk_reassessed,
                "alerts_generated": alerts_generated
            }

        except Exception as exc:
            logger.error(f"Error monitoring vendor '{vendor.name}': {str(exc)}", exc_info=True)
            # Update vendor last_monitored_at even on failure to avoid continuous failing loop
            vendor.last_monitored_at = now_utc
            audit = AuditLog(
                vendor_id=vendor_id,
                action="MONITORING_FAILED",
                actor="Monitoring Service",
                details={"error": str(exc)}
            )
            db.add(audit)
            await db.commit()

            return {
                "vendor_id": vendor_id,
                "vendor_name": vendor.name,
                "status": "Failed",
                "documents_checked": documents_checked,
                "documents_changed": documents_changed,
                "risk_reassessed": False,
                "alerts_generated": alerts_generated,
                "error_detail": str(exc)
            }

    async def _evaluate_risk_degradation(
        self,
        db: AsyncSession,
        vendor: Vendor,
        prev_assessment: RiskAssessment,
        new_assessment: RiskAssessment
    ) -> int:
        """
        Evaluates risk score degradation between previous and new assessments.
        Generates Risk Degradation Alert if:
        1. Overall score increases by >= 10.0 points
        2. Any category score increases by >= 15.0 points
        3. Risk tier worsens (e.g. Low -> Medium, Medium -> High)
        Returns count of degradation alerts created.
        """
        overall_delta = new_assessment.overall_score - prev_assessment.overall_score
        
        # Risk Tier comparison
        prev_tier = RiskTier(prev_assessment.risk_tier) if prev_assessment.risk_tier in [t.value for t in RiskTier] else RiskTier.MEDIUM
        new_tier = RiskTier(new_assessment.risk_tier) if new_assessment.risk_tier in [t.value for t in RiskTier] else RiskTier.MEDIUM
        
        prev_tier_order = TIER_SEVERITY_ORDER.get(prev_tier, 2)
        new_tier_order = TIER_SEVERITY_ORDER.get(new_tier, 2)
        tier_worsened = new_tier_order > prev_tier_order

        # Category Score comparison
        prev_cat_scores = {c.category_name: c.score for c in (prev_assessment.category_scores or [])}
        new_cat_scores = {c.category_name: c.score for c in (new_assessment.category_scores or [])}

        degraded_categories = []
        for cat_name, new_score in new_cat_scores.items():
            prev_score = prev_cat_scores.get(cat_name, 0.0)
            cat_delta = new_score - prev_score
            if cat_delta >= DEGRADATION_CATEGORY_SCORE_THRESHOLD:
                degraded_categories.append((cat_name, prev_score, new_score, cat_delta))

        overall_degraded = overall_delta >= DEGRADATION_OVERALL_SCORE_THRESHOLD

        if not (overall_degraded or tier_worsened or degraded_categories):
            logger.info(f"No material risk degradation for vendor '{vendor.name}'. Overall delta: {overall_delta:+.2f}")
            return 0

        # Build Risk Degradation Alert
        reasons = []
        if overall_degraded:
            reasons.append(f"Overall risk score increased by +{overall_delta:.1f} pts (from {prev_assessment.overall_score:.1f} to {new_assessment.overall_score:.1f})")
        if tier_worsened:
            reasons.append(f"Risk Tier escalated from {prev_tier.value} to {new_tier.value}")
        for cat_name, p_sc, n_sc, c_delta in degraded_categories:
            reasons.append(f"{cat_name} category score increased by +{c_delta:.1f} pts ({p_sc:.1f} -> {n_sc:.1f})")

        alert_severity = "Critical" if new_tier == RiskTier.CRITICAL else "High"
        alert_title = f"Risk Degradation Detected: {vendor.name}"
        alert_desc = f"Material risk degradation identified for vendor '{vendor.name}'. " + "; ".join(reasons) + "."

        # Alert Deduplication Check
        dedup_stmt = select(Alert).where(
            Alert.vendor_id == vendor.id,
            Alert.alert_type == "Risk Degradation",
            Alert.title == alert_title,
            Alert.description == alert_desc
        )
        existing_alert = (await db.execute(dedup_stmt)).scalars().first()

        if not existing_alert:
            deg_alert = Alert(
                vendor_id=vendor.id,
                alert_type="Risk Degradation",
                severity=alert_severity,
                title=alert_title,
                description=alert_desc
            )
            db.add(deg_alert)
            await db.commit()
            logger.warning(f"Risk Degradation Alert generated for vendor '{vendor.name}': {alert_desc}")
            return 1

        return 0

    async def run_monitoring_cycle(
        self,
        db: AsyncSession,
        target_vendor_id: Optional[str] = None,
        force: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Batch monitoring runner:
        Iterates over all registered vendors (or specified vendor) and monitors each safely.
        Ensures a failure for one vendor does not interrupt monitoring for other vendors.
        """
        if target_vendor_id:
            stmt = select(Vendor).where(Vendor.id == target_vendor_id)
        else:
            stmt = select(Vendor).where(Vendor.status == "Active")

        res = await db.execute(stmt)
        vendors = list(res.scalars().all())

        results = []
        for v in vendors:
            try:
                res_dict = await self.monitor_single_vendor(db=db, vendor_id=v.id, force=force)
                results.append(res_dict)
            except Exception as exc:
                logger.error(f"Unhandled error in monitoring loop for vendor ID {v.id}: {str(exc)}")
                results.append({
                    "vendor_id": v.id,
                    "vendor_name": v.name,
                    "status": "Failed",
                    "error_detail": str(exc)
                })

        return results
