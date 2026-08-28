import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.alert import Alert
from app.models.audit import AuditLog
from app.services.agents.state import VendorRiskState

logger = logging.getLogger("vendorguard.agents.executive_report")


class ExecutiveReportAgent:
    """
    Specialized Executive Report Agent responsible for:
    - Synthesizing verified risk assessment into an executive-level summary & actionable recommendations
    - Including evidence citations and category score breakdowns
    - Reusing existing Alert and AuditLog infrastructure to record risk updates without duplicating alerts
    """

    def __init__(self, openai_api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = openai_api_key or settings.OPENAI_API_KEY
        self.model_name = model_name or settings.LLM_MODEL

    async def _generate_summary_llm(
        self,
        vendor_name: str,
        overall_score: float,
        risk_tier: str,
        category_scores: Dict[str, float],
        key_findings: List[Dict[str, Any]]
    ) -> str:
        if not self.api_key or not self.api_key.strip():
            return (
                f"Executive Summary for {vendor_name}: Overall Risk Score is {overall_score} ({risk_tier} Risk Tier). "
                f"Category Breakdown: " + ", ".join(f"{k}: {v}" for k, v in category_scores.items()) + ". "
                f"Verified findings: {len(key_findings)} risk item(s) identified."
            )

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            prompt = (
                f"Synthesize an executive security & risk report summary for vendor '{vendor_name}'.\n"
                f"Overall Score: {overall_score}/100\n"
                f"Risk Tier: {risk_tier}\n"
                f"Category Scores: {category_scores}\n"
                f"Key Findings: {key_findings}\n\n"
                f"Provide a 2-3 paragraph executive summary covering risk posture, key vulnerabilities, "
                f"and strategic recommendations for security analysts."
            )

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a Chief Information Security Officer (CISO) executive reporting assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )

            summary = response.choices[0].message.content
            return summary.strip() if summary else f"Executive report generated for {vendor_name}."

        except Exception as exc:
            logger.warning(f"LLM call failed for ExecutiveReportAgent: {str(exc)}. Falling back to structured summary.")
            return (
                f"Executive Summary for {vendor_name}: Overall Risk Score is {overall_score} ({risk_tier} Risk Tier). "
                f"Category Breakdown: " + ", ".join(f"{k}: {v}" for k, v in category_scores.items()) + "."
            )

    async def run(
        self,
        state: VendorRiskState,
        db: AsyncSession,
        mock_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        vendor_id = state.get("vendor_id")
        vendor_name = state.get("vendor_name", vendor_id)
        overall_score = state.get("overall_score", 0.0)
        risk_tier = state.get("risk_tier", "Medium")
        cat_scores = state.get("category_scores", {})
        key_findings = state.get("key_findings", [])

        logger.info(f"ExecutiveReportAgent executing for vendor '{vendor_name}'")

        state["current_step"] = "executive_report"

        try:
            if mock_summary is not None:
                summary = mock_summary
            else:
                summary = await self._generate_summary_llm(
                    vendor_name=vendor_name,
                    overall_score=overall_score,
                    risk_tier=risk_tier,
                    category_scores=cat_scores,
                    key_findings=key_findings
                )

            # Record high-risk alert using existing Alert model if risk is Critical/High
            created_alerts = []
            if risk_tier in ("Critical", "High"):
                alert = Alert(
                    vendor_id=vendor_id,
                    alert_type="Agentic Workflow High Risk",
                    severity="High" if risk_tier == "High" else "Critical",
                    title=f"Multi-Agent Audit Completed: {risk_tier} Risk Tier ({overall_score})",
                    description=f"Automated risk audit completed for {vendor_name}. Score: {overall_score} ({risk_tier})."
                )
                db.add(alert)
                await db.commit()
                await db.refresh(alert)
                created_alerts.append({
                    "alert_id": alert.id,
                    "title": alert.title,
                    "severity": alert.severity,
                })

            # Record AuditLog entry
            audit = AuditLog(
                vendor_id=vendor_id,
                action="AGENTIC_WORKFLOW_COMPLETED",
                actor="LangGraph Multi-Agent System",
                details={
                    "workflow_id": state.get("workflow_id"),
                    "overall_score": overall_score,
                    "risk_tier": risk_tier,
                    "human_approved": state.get("human_approved"),
                }
            )
            db.add(audit)
            await db.commit()

            logger.info(f"ExecutiveReportAgent completed for vendor '{vendor_name}'")

            return {
                "executive_summary": summary,
                "alerts_created": created_alerts,
                "current_step": "executive_report",
                "status": "completed",
            }

        except Exception as exc:
            err_msg = f"ExecutiveReportAgent failed for '{vendor_name}': {str(exc)}"
            logger.error(err_msg, exc_info=True)
            errors = state.get("errors", [])
            errors.append(err_msg)
            return {
                "current_step": "executive_report",
                "status": "failed",
                "errors": errors
            }
