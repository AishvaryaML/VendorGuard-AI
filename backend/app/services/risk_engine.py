import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.vendor import Vendor, RiskTier
from app.models.document import Document, PolicyVersion
from app.models.risk import RiskAssessment, CategoryScore
from app.schemas.risk import RiskFindingSchema, AIAssessmentResultSchema

logger = logging.getLogger("vendorguard.risk_engine")

CATEGORIES = ["Privacy", "Security", "Compliance", "Legal"]
CATEGORY_WEIGHTS = {
    "Privacy": 0.30,
    "Security": 0.30,
    "Compliance": 0.20,
    "Legal": 0.20,
}

SEVERITY_PENALTIES = {
    "Low": 10.0,
    "Medium": 20.0,
    "High": 35.0,
    "Critical": 50.0,
}


def normalize_text(text: str) -> str:
    """Normalizes text by collapsing whitespace and stripping trailing spaces."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip().lower()


def validate_evidence(evidence_quote: str, raw_policy_text: str) -> bool:
    """
    Verifies whether an LLM-provided evidence quote actually exists within the raw policy text.
    Uses normalized substring matching to handle minor whitespace differences.
    """
    if not evidence_quote or not raw_policy_text:
        return False

    norm_quote = normalize_text(evidence_quote)
    norm_policy = normalize_text(raw_policy_text)

    if not norm_quote:
        return False

    return norm_quote in norm_policy


def calculate_category_scores(
    findings: List[RiskFindingSchema]
) -> Dict[str, Tuple[float, str, List[Dict[str, Any]]]]:
    """
    Deterministically computes category scores (0 to 100) from verified findings.
    Returns dictionary mapping category name to (score, justification, category_findings_list).
    """
    results = {}

    for cat in CATEGORIES:
        cat_findings = [f for f in findings if f.category == cat]
        score = 0.0
        verified_count = 0
        severity_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}

        for finding in cat_findings:
            if finding.is_verified:
                verified_count += 1
                penalty = SEVERITY_PENALTIES.get(finding.severity, 10.0)
                score += penalty
                if finding.severity in severity_counts:
                    severity_counts[finding.severity] += 1
            else:
                logger.warning(
                    f"Finding discarded from score calculation due to unverified evidence: '{finding.finding}'"
                )

        score = min(100.0, round(score, 2))

        if verified_count == 0:
            justification = f"No verified risk findings identified for {cat}."
        else:
            parts = [f"{count} {sev}" for sev, count in severity_counts.items() if count > 0]
            justification = f"Score derived from {verified_count} verified finding(s): " + ", ".join(parts) + "."

        cat_findings_dict = [f.model_dump() for f in cat_findings]
        results[cat] = (score, justification, cat_findings_dict)

    return results


def calculate_overall_score(category_scores: Dict[str, float]) -> float:
    """
    Calculates overall vendor risk score using weighted category scores:
    Privacy: 30%, Security: 30%, Compliance: 20%, Legal: 20%.
    """
    overall = (
        category_scores.get("Privacy", 0.0) * CATEGORY_WEIGHTS["Privacy"]
        + category_scores.get("Security", 0.0) * CATEGORY_WEIGHTS["Security"]
        + category_scores.get("Compliance", 0.0) * CATEGORY_WEIGHTS["Compliance"]
        + category_scores.get("Legal", 0.0) * CATEGORY_WEIGHTS["Legal"]
    )
    return round(min(100.0, max(0.0, overall)), 2)


def determine_risk_tier(overall_score: float) -> RiskTier:
    """
    Maps overall risk score to RiskTier:
    0–24.99 -> Low
    25–49.99 -> Medium
    50–74.99 -> High
    75–100 -> Critical
    """
    if overall_score < 25.0:
        return RiskTier.LOW
    elif overall_score < 50.0:
        return RiskTier.MEDIUM
    elif overall_score < 75.0:
        return RiskTier.HIGH
    else:
        return RiskTier.CRITICAL


class AIRiskEngine:
    """
    Modular AI Risk Analytics Engine.
    Consumes stored policy documents for a vendor and produces an explainable, evidence-backed assessment.
    """

    def __init__(self, openai_api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = openai_api_key or settings.OPENAI_API_KEY
        self.model_name = model_name or settings.LLM_MODEL

    async def _call_llm(self, prompt: str) -> AIAssessmentResultSchema:
        """Invokes OpenAI LLM API to return structured risk assessment data."""
        if not self.api_key:
            raise ValueError(
                "LLM API key is not configured. Please supply OPENAI_API_KEY in environment."
            )

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            system_instruction = (
                "You are an expert AI Risk & Security Auditor. "
                "Analyze vendor policy documents and return structured JSON matching the requested schema. "
                "For every finding, provide exact verbatim quotes as evidence from the provided policy text, "
                "specify the document source URL, category (Privacy, Security, Compliance, or Legal), "
                "severity (Low, Medium, High, Critical), confidence (0.0 to 1.0), and actionable recommendation. "
                "Do NOT invent quotes or URLs not present in the supplied policy text."
            )

            response = await client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                response_format=AIAssessmentResultSchema,
                temperature=0.1,
            )

            return response.choices[0].message.parsed

        except Exception as exc:
            logger.error("OpenAI API call failed: %s", str(exc), exc_info=True)
            raise RuntimeError(f"LLM API call failed: {str(exc)}") from exc

    async def analyze_vendor(
        self,
        db: AsyncSession,
        vendor_id: str,
        mock_result: Optional[AIAssessmentResultSchema] = None
    ) -> RiskAssessment:
        """
        Executes end-to-end risk assessment for a vendor:
        1. Loads vendor & stored PolicyVersions.
        2. Formats policy documents into prompt context.
        3. Calls LLM (or uses mock_result if supplied in tests).
        4. Validates evidence against stored policy text.
        5. Computes category scores & overall weighted score.
        6. Maps risk tier.
        7. Persists RiskAssessment & CategoryScore in DB and updates Vendor.
        """
        # Fetch vendor with documents & versions
        stmt = (
            select(Vendor)
            .options(
                selectinload(Vendor.documents).selectinload(Document.versions)
            )
            .where(Vendor.id == vendor_id)
        )
        res = await db.execute(stmt)
        vendor = res.scalar_one_or_none()

        if not vendor:
            raise ValueError(f"Vendor with ID '{vendor_id}' not found.")

        # Gather latest policy version text per document
        doc_contexts: List[Dict[str, str]] = []
        full_text_by_url: Dict[str, str] = {}
        all_raw_texts: List[str] = []

        for doc in vendor.documents:
            if doc.versions:
                # Latest version is first because of order_by version_number desc
                latest_ver = doc.versions[0]
                doc_contexts.append({
                    "document_type": doc.document_type,
                    "title": doc.title,
                    "url": doc.url,
                    "raw_content": latest_ver.raw_content
                })
                full_text_by_url[doc.url] = latest_ver.raw_content
                all_raw_texts.append(latest_ver.raw_content)

        if not doc_contexts:
            raise ValueError(
                f"Vendor '{vendor.name}' has no stored policy document content to analyze. Please crawl the vendor first."
            )

        # Build LLM Prompt
        prompt_parts = [
            f"Analyze vendor '{vendor.name}' (Domain: {vendor.domain}) using the following legal/security policy documents:\n"
        ]
        for idx, doc_ctx in enumerate(doc_contexts, 1):
            prompt_parts.append(
                f"--- DOCUMENT {idx}: {doc_ctx['document_type']} ---"
                f"\nURL: {doc_ctx['url']}"
                f"\nTITLE: {doc_ctx['title']}"
                f"\nCONTENT:\n{doc_ctx['raw_content']}\n"
            )

        prompt = "\n".join(prompt_parts)

        # Obtain LLM Assessment
        if mock_result is not None:
            ai_result = mock_result
        else:
            ai_result = await self._call_llm(prompt)

        # Validate Evidence Quotes
        validated_findings: List[RiskFindingSchema] = []
        citations_list: List[Dict[str, Any]] = []

        for finding in ai_result.findings:
            source_url = finding.source_url
            target_text = full_text_by_url.get(source_url)

            # Fallback search across all document texts if URL didn't match directly
            if not target_text:
                target_text = "\n".join(all_raw_texts)

            is_valid = validate_evidence(finding.evidence, target_text)

            finding.is_verified = is_valid
            validated_findings.append(finding)

            citations_list.append({
                "category": finding.category,
                "finding": finding.finding,
                "severity": finding.severity,
                "evidence": finding.evidence,
                "source_url": source_url,
                "is_verified": is_valid,
                "confidence": finding.confidence
            })

            if not is_valid:
                logger.warning(
                    f"Evidence validation failed for finding '{finding.finding}' from URL {source_url}."
                )

        # Calculate deterministic category scores
        cat_scoring = calculate_category_scores(validated_findings)

        cat_score_dict = {cat: data[0] for cat, data in cat_scoring.items()}

        # Calculate overall score & risk tier
        overall_score = calculate_overall_score(cat_score_dict)
        risk_tier = determine_risk_tier(overall_score)

        # Prepare Key Findings summary
        key_findings_summary = [
            {
                "category": f.category,
                "finding": f.finding,
                "severity": f.severity,
                "recommendation": f.recommendation,
                "is_verified": f.is_verified
            }
            for f in validated_findings
        ]

        now_utc = datetime.now(timezone.utc)

        # Create RiskAssessment record
        assessment = RiskAssessment(
            vendor_id=vendor_id,
            assessment_date=now_utc,
            overall_score=overall_score,
            risk_tier=risk_tier.value,
            summary=ai_result.summary,
            key_findings=key_findings_summary,
            citations=citations_list,
            status="Completed"
        )
        db.add(assessment)
        await db.commit()
        await db.refresh(assessment)

        # Add CategoryScore records
        for cat_name, (score, justification, cat_findings_dict) in cat_scoring.items():
            cat_score_record = CategoryScore(
                assessment_id=assessment.id,
                category_name=cat_name,
                score=score,
                justification=justification,
                findings=cat_findings_dict
            )
            db.add(cat_score_record)

        # Update Vendor current risk score & tier
        vendor.current_risk_score = overall_score
        vendor.risk_tier = risk_tier
        vendor.last_monitored_at = now_utc

        await db.commit()
        await db.refresh(assessment)

        # Re-query assessment with category scores populated
        stmt_full = (
            select(RiskAssessment)
            .options(selectinload(RiskAssessment.category_scores))
            .where(RiskAssessment.id == assessment.id)
        )
        full_res = await db.execute(stmt_full)
        final_assessment = full_res.scalar_one()

        return final_assessment


async def get_latest_vendor_risk_assessment(
    db: AsyncSession, vendor_id: str
) -> Optional[RiskAssessment]:
    """Retrieves the latest persisted RiskAssessment for a vendor."""
    stmt = (
        select(RiskAssessment)
        .options(selectinload(RiskAssessment.category_scores))
        .where(RiskAssessment.vendor_id == vendor_id)
        .order_by(RiskAssessment.assessment_date.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().first()
