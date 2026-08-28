import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.risk_engine import AIRiskEngine
from app.schemas.risk import AIAssessmentResultSchema
from app.services.agents.state import VendorRiskState

logger = logging.getLogger("vendorguard.agents.risk_auditor")


class RiskAuditorAgent:
    """
    Specialized Risk Auditor Agent responsible for:
    - Calling existing AIRiskEngine to run evidence-backed risk analysis
    - Preserving deterministic category scoring formulas and severity penalties
    - Interpreting key risk findings and mapping risk tier
    - Preparing risk assessment data for approval evaluation
    """

    def __init__(self, risk_engine: Optional[AIRiskEngine] = None):
        self.risk_engine = risk_engine or AIRiskEngine()

    async def run(
        self,
        state: VendorRiskState,
        db: AsyncSession,
        mock_ai_result: Optional[AIAssessmentResultSchema] = None
    ) -> Dict[str, Any]:
        vendor_id = state.get("vendor_id")
        vendor_name = state.get("vendor_name", vendor_id)
        logger.info(f"RiskAuditorAgent executing for vendor '{vendor_name}'")

        state["current_step"] = "risk_auditor"
        state["status"] = "auditing"

        try:
            db.expire_all()
            # Delegate to existing AIRiskEngine without duplicating scoring formulas
            assessment = await self.risk_engine.analyze_vendor(
                db=db,
                vendor_id=vendor_id,
                mock_result=mock_ai_result
            )

            cat_scores_dict = {
                cs.category_name: cs.score for cs in assessment.category_scores
            }

            logger.info(
                f"RiskAuditorAgent completed: Vendor '{vendor_name}' Score: {assessment.overall_score}, "
                f"Tier: {assessment.risk_tier}"
            )

            return {
                "risk_assessment_id": assessment.id,
                "overall_score": assessment.overall_score,
                "risk_tier": assessment.risk_tier,
                "category_scores": cat_scores_dict,
                "key_findings": assessment.key_findings or [],
                "current_step": "risk_auditor",
                "status": "risk_audit_completed",
            }

        except Exception as exc:
            err_msg = f"RiskAuditorAgent failed for vendor '{vendor_name}': {str(exc)}"
            logger.error(err_msg, exc_info=True)
            errors = state.get("errors", [])
            errors.append(err_msg)
            return {
                "current_step": "risk_auditor",
                "status": "failed",
                "errors": errors
            }
