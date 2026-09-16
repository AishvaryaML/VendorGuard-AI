import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.vendor import Vendor
from app.models.compliance import ComplianceAssessment, ComplianceStatus
from app.schemas.compliance import (
    ComplianceAssessmentResult,
    ComplianceFrameworkSummarySchema,
    ComplianceCrosswalkResponse
)
from app.services.rag.retriever import RAGRetriever
from app.services.llm import get_llm_service
from app.services.risk_engine import validate_evidence
from app.services.compliance.catalog import COMPLIANCE_CATALOG, get_catalog_by_framework

logger = logging.getLogger("vendorguard.compliance_service")

class ComplianceService:
    def __init__(self):
        self.rag_retriever = RAGRetriever()
        self.llm_service = get_llm_service()

    async def get_or_compute_compliance(
        self,
        db: AsyncSession,
        vendor_id: str,
        framework: Optional[str] = None
    ) -> ComplianceCrosswalkResponse:
        
        # 1. Verify vendor exists
        stmt = select(Vendor).where(Vendor.id == vendor_id)
        res = await db.execute(stmt)
        vendor = res.scalar_one_or_none()
        
        if not vendor:
            raise ValueError(f"Vendor with ID '{vendor_id}' not found.")

        # 2. Get existing assessments from DB to act as a cache
        query = select(ComplianceAssessment).where(ComplianceAssessment.vendor_id == vendor_id)
        if framework:
            query = query.where(ComplianceAssessment.framework == framework)
        
        res = await db.execute(query)
        existing_assessments = list(res.scalars().all())
        
        # 2b. Cache Invalidation: Check if there are new policy versions since the assessment
        if existing_assessments:
            from app.models.document import Document, PolicyVersion
            oldest_assessment_date = min(a.assessed_at for a in existing_assessments)
            
            # Check if any document for this vendor has a policy version newer than oldest_assessment_date
            newer_version_query = (
                select(PolicyVersion)
                .join(Document, Document.id == PolicyVersion.document_id)
                .where(Document.vendor_id == vendor_id)
                .where(PolicyVersion.crawled_at > oldest_assessment_date)
                .limit(1)
            )
            newer_version_res = await db.execute(newer_version_query)
            has_newer_version = newer_version_res.scalar_one_or_none() is not None
            
            if has_newer_version:
                logger.info(f"Newer policy versions detected for vendor {vendor_id}. Invalidating compliance cache.")
                # Delete old assessments for the vendor (and framework if specified, but usually safer to clear all for the vendor)
                delete_query = select(ComplianceAssessment).where(ComplianceAssessment.vendor_id == vendor_id)
                if framework:
                    delete_query = delete_query.where(ComplianceAssessment.framework == framework)
                to_delete = (await db.execute(delete_query)).scalars().all()
                for record in to_delete:
                    await db.delete(record)
                await db.commit()
                existing_assessments = []

        existing_map = {(a.framework, a.control_id): a for a in existing_assessments}
        
        # 3. Figure out which controls we need to compute
        target_controls = COMPLIANCE_CATALOG
        if framework:
            target_controls = get_catalog_by_framework(framework)

        results: List[ComplianceAssessmentResult] = []
        
        for control in target_controls:
            existing = existing_map.get((control.framework, control.control_id))
            # Cache check - we skip if we already have it assessed
            if existing:
                results.append(ComplianceAssessmentResult(
                    framework=existing.framework,
                    control_id=existing.control_id,
                    control_title=control.control_title,
                    status=existing.status.value,
                    confidence=existing.confidence,
                    evidence_quote=existing.evidence,
                    source_url=existing.source_url,
                    source_document=existing.source_document_id,
                    source_version=existing.source_version_id,
                    explanation=existing.explanation,
                    gap_reason=existing.gap_reason
                ))
            else:
                # Need to compute using RAG
                query_str = f"{control.control_title}. {control.required_evidence}"
                
                # Fetch chunks from RAG
                retrieval_results = await self.rag_retriever.search(
                    vendor_id=vendor_id,
                    query=query_str,
                    top_k=5,
                    db=db
                )
                
                evidence_text_parts = []
                for idx, rr in enumerate(retrieval_results):
                    evidence_text_parts.append(
                        f"--- EVIDENCE {idx + 1} ---\n"
                        f"Source URL: {rr.source_url}\n"
                        f"Doc ID: {rr.document_id}\n"
                        f"Version ID: {rr.policy_version_id}\n"
                        f"Text: {rr.text}\n"
                    )
                
                evidence_text = "\n".join(evidence_text_parts)
                
                # Default empty outcome if no chunks found
                if not retrieval_results:
                    result = ComplianceAssessmentResult(
                        framework=control.framework,
                        control_id=control.control_id,
                        control_title=control.control_title,
                        status="NOT_ASSESSED",
                        confidence=0.0,
                        gap_reason="No relevant policy evidence found for this vendor."
                    )
                else:
                    # Ask LLM
                    result = await self.llm_service.analyze_compliance_control(
                        vendor_name=vendor.name,
                        control_framework=control.framework,
                        control_id=control.control_id,
                        control_title=control.control_title,
                        control_description=control.control_description,
                        required_evidence=control.required_evidence,
                        evidence_text=evidence_text
                    )
                    
                    # Verify evidence if PASS or PARTIAL
                    if result.status in ["PASS", "PARTIAL"] and result.evidence_quote:
                        full_context_text = " ".join([rr.text for rr in retrieval_results])
                        is_valid = validate_evidence(result.evidence_quote, full_context_text)
                        
                        if not is_valid:
                            logger.warning(f"Failed to verify evidence quote for {control.control_id}. Downgrading to NOT_ASSESSED.")
                            result.status = "NOT_ASSESSED"
                            result.evidence_quote = None
                            result.gap_reason = "LLM provided an invalid evidence quote that could not be verified against the source."
                            result.confidence = 0.0

                    # Link source doc info if source URL is provided
                    if result.source_url:
                        matching_rr = next((rr for rr in retrieval_results if rr.source_url == result.source_url), None)
                        if matching_rr:
                            result.source_document = matching_rr.document_id
                            result.source_version = matching_rr.policy_version_id

                # Save to database
                db_record = ComplianceAssessment(
                    vendor_id=vendor_id,
                    framework=result.framework,
                    control_id=result.control_id,
                    status=ComplianceStatus(result.status),
                    confidence=result.confidence,
                    evidence=result.evidence_quote,
                    source_url=result.source_url,
                    source_document_id=result.source_document,
                    source_version_id=result.source_version,
                    explanation=result.explanation,
                    gap_reason=result.gap_reason
                )
                db.add(db_record)
                results.append(result)
        
        await db.commit()

        # Build summaries
        frameworks = set(r.framework for r in results)
        summaries = []
        for fw in frameworks:
            fw_results = [r for r in results if r.framework == fw]
            total = len(fw_results)
            passes = sum(1 for r in fw_results if r.status == "PASS")
            partials = sum(1 for r in fw_results if r.status == "PARTIAL")
            gaps = sum(1 for r in fw_results if r.status == "GAP")
            not_assessed = sum(1 for r in fw_results if r.status == "NOT_ASSESSED")
            
            coverage = 0.0
            if total > 0:
                coverage = round((passes + (partials * 0.5)) / total * 100, 2)
                
            summaries.append(ComplianceFrameworkSummarySchema(
                framework=fw,
                pass_count=passes,
                partial_count=partials,
                gap_count=gaps,
                not_assessed_count=not_assessed,
                coverage_percentage=coverage
            ))
            
        return ComplianceCrosswalkResponse(
            vendor_id=vendor_id,
            summaries=summaries,
            assessments=results
        )

compliance_service = ComplianceService()
