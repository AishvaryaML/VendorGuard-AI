import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.alert import Alert
from app.models.audit import AuditLog
from app.services.agents.state import VendorRiskState
from app.services.llm import BaseLLMService, get_llm_service

logger = logging.getLogger("vendorguard.agents.executive_report")


class ExecutiveReportAgent:
    """
    Specialized Executive Report Agent responsible for:
    - Synthesizing verified risk assessment into an executive-level summary & actionable recommendations
    - Including evidence citations and category score breakdowns
    - Reusing existing Alert and AuditLog infrastructure to record risk updates without duplicating alerts
    - Using configured LLM provider abstraction (Ollama or OpenAI)
    """

    def __init__(
        self,
        llm_service: Optional[BaseLLMService] = None,
        openai_api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.llm_service = llm_service or get_llm_service(api_key=openai_api_key, model_name=model_name)
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
        return await self.llm_service.generate_executive_summary(
            vendor_name=vendor_name,
            overall_score=overall_score,
            risk_tier=risk_tier,
            category_scores=category_scores,
            key_findings=key_findings
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
