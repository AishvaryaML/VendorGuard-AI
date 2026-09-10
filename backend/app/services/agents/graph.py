import uuid
import logging
import aiosqlite
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings
from app.services.agents.state import VendorRiskState
from app.services.agents.discovery_agent import DiscoveryAgent
from app.services.agents.policy_auditor_agent import PolicyAuditorAgent
from app.services.agents.risk_auditor_agent import RiskAuditorAgent
from app.services.agents.executive_report_agent import ExecutiveReportAgent
from app.schemas.risk import AIAssessmentResultSchema

logger = logging.getLogger("vendorguard.agents.graph")


async def get_checkpointer(custom_conn_str: Optional[str] = None) -> BaseCheckpointSaver:
    """
    Returns the appropriate persistent checkpointer based on database configuration.
    Uses AsyncPostgresSaver for PostgreSQL environments and AsyncSqliteSaver for SQLite/Local Dev.
    """
    target_url = custom_conn_str or settings.CHECKPOINT_DATABASE_URL or settings.DATABASE_URL

    if "postgres" in target_url.lower():
        try:
            from psycopg_pool import AsyncConnectionPool
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            pg_url = target_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgres+asyncpg://", "postgres://")
            pool = AsyncConnectionPool(conninfo=pg_url, max_size=10, open=False)
            await pool.open()
            saver = AsyncPostgresSaver(pool)
            await saver.setup()
            return saver
        except Exception as exc:
            logger.warning(f"Failed to initialize AsyncPostgresSaver ({exc}). Falling back to AsyncSqliteSaver.")

    try:
        from pathlib import Path
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        backend_dir = Path(__file__).resolve().parent.parent.parent
        sqlite_file = str(backend_dir / "vendorguard_checkpoints.db")
        conn = await aiosqlite.connect(sqlite_file)
        saver = AsyncSqliteSaver(conn)
        await saver.setup()
        return saver
    except Exception as exc:
        logger.warning(f"Failed to initialize AsyncSqliteSaver ({exc}). Falling back to MemorySaver.")
        return MemorySaver()


class VendorRiskWorkflowRunner:
    """
    LangGraph Multi-Agent Vendor Risk Intelligence Workflow Runner.
    Orchestrates DiscoveryAgent, PolicyAuditorAgent, RiskAuditorAgent, Approval Evaluator, and ExecutiveReportAgent
    with persistent PostgreSQL/SQLite checkpointing and Human-in-the-Loop (HITL) interrupt/resume gating.
    """

    def __init__(
        self,
        discovery_agent: Optional[DiscoveryAgent] = None,
        policy_auditor_agent: Optional[PolicyAuditorAgent] = None,
        risk_auditor_agent: Optional[RiskAuditorAgent] = None,
        executive_report_agent: Optional[ExecutiveReportAgent] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None
    ):
        self.discovery_agent = discovery_agent or DiscoveryAgent()
        self.policy_auditor_agent = policy_auditor_agent or PolicyAuditorAgent()
        self.risk_auditor_agent = risk_auditor_agent or RiskAuditorAgent()
        self.executive_report_agent = executive_report_agent or ExecutiveReportAgent()
        self._checkpointer = checkpointer

    async def _get_saver(self) -> BaseCheckpointSaver:
        if self._checkpointer is None:
            self._checkpointer = await get_checkpointer()
        return self._checkpointer

    async def save_workflow_state(self, workflow_id: str, state: VendorRiskState) -> None:
        saver = await self._get_saver()
        config = {"configurable": {"thread_id": workflow_id, "checkpoint_ns": ""}}
        now_ts = datetime.now(timezone.utc)
        checkpoint_id = f"{now_ts.strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:8]}"
        checkpoint = {
            "v": 1,
            "id": checkpoint_id,
            "ts": now_ts.isoformat(),
            "channel_values": dict(state),
            "channel_versions": {"state": 1},
            "versions_seen": {},
            "pending_sends": []
        }
        metadata = {"step": 1, "source": "input", "writes": {}, "parents": {}}
        new_versions = {"state": 1}
        await saver.aput(config, checkpoint, metadata, new_versions)

    async def get_workflow_state(self, workflow_id: str) -> Optional[VendorRiskState]:
        saver = await self._get_saver()
        config = {"configurable": {"thread_id": workflow_id, "checkpoint_ns": ""}}
        
        latest_tuple = None
        async for tuple_res in saver.alist(config, limit=1):
            latest_tuple = tuple_res
            break

        if latest_tuple and latest_tuple.checkpoint and "channel_values" in latest_tuple.checkpoint:
            val = latest_tuple.checkpoint["channel_values"]
            return VendorRiskState(**val)
        return None

    async def run_workflow(
        self,
        db: AsyncSession,
        vendor_id: str,
        mock_ai_result: Optional[AIAssessmentResultSchema] = None,
        mock_summary: Optional[str] = None
    ) -> VendorRiskState:
        workflow_id = str(uuid.uuid4())

        initial_state: VendorRiskState = {
            "workflow_id": workflow_id,
            "vendor_id": vendor_id,
            "vendor_name": "",
            "domain": "",
            "website_url": "",
            "current_step": "start",
            "status": "pending",
            "discovered_documents": [],
            "indexed_chunks_count": 0,
            "risk_assessment_id": None,
            "overall_score": 0.0,
            "risk_tier": "Low",
            "category_scores": {},
            "key_findings": [],
            "citations": [],
            "executive_summary": "",
            "requires_human_approval": False,
            "human_approved": None,
            "approval_notes": None,
            "alerts_created": [],
            "errors": [],
        }

        await self.save_workflow_state(workflow_id, initial_state)

        try:
            # 1. Node 1: Discovery Agent
            disc_res = await self.discovery_agent.run(initial_state, db)
            initial_state.update(disc_res)
            await self.save_workflow_state(workflow_id, initial_state)

            if initial_state.get("status") == "failed":
                return initial_state

            # 2. Node 2: Policy Auditor Agent
            audit_res = await self.policy_auditor_agent.run(initial_state, db)
            initial_state.update(audit_res)
            await self.save_workflow_state(workflow_id, initial_state)

            if initial_state.get("status") == "failed":
                return initial_state

            # 3. Node 3: Risk Auditor Agent (Orchestrates AIRiskEngine)
            risk_res = await self.risk_auditor_agent.run(initial_state, db, mock_ai_result=mock_ai_result)
            initial_state.update(risk_res)
            await self.save_workflow_state(workflow_id, initial_state)

            if initial_state.get("status") == "failed":
                return initial_state

            # 4. Node 4: Approval Evaluator (HITL Gate Check)
            overall_score = initial_state.get("overall_score", 0.0)
            risk_tier = initial_state.get("risk_tier", "Low")

            if risk_tier == "Critical" or overall_score >= 75.0:
                logger.info(
                    f"Workflow '{workflow_id}': Critical risk detected ({overall_score}, {risk_tier}). "
                    f"INTERRUPTING FOR HUMAN APPROVAL."
                )
                initial_state["requires_human_approval"] = True
                initial_state["current_step"] = "human_approval"
                initial_state["status"] = "awaiting_approval"
                await self.save_workflow_state(workflow_id, initial_state)
                return initial_state

            # 5. Node 5: Executive Report Agent (Automatic continuation for Low/Medium/High < 75)
            report_res = await self.executive_report_agent.run(initial_state, db, mock_summary=mock_summary)
            initial_state.update(report_res)
            await self.save_workflow_state(workflow_id, initial_state)

            return initial_state

        except Exception as exc:
            err = f"Workflow '{workflow_id}' failed: {str(exc)}"
            logger.error(err, exc_info=True)
            initial_state["status"] = "failed"
            errors = initial_state.get("errors", [])
            errors.append(err)
            initial_state["errors"] = errors
            await self.save_workflow_state(workflow_id, initial_state)
            return initial_state

    async def resume_approval(
        self,
        db: AsyncSession,
        workflow_id: str,
        approved: bool,
        notes: Optional[str] = None,
        mock_summary: Optional[str] = None
    ) -> VendorRiskState:
        state = await self.get_workflow_state(workflow_id)
        if not state:
            raise ValueError(f"Workflow with ID '{workflow_id}' not found.")

        if state.get("status") != "awaiting_approval":
            raise ValueError(f"Workflow '{workflow_id}' is not in 'awaiting_approval' status (current: {state.get('status')}).")

        state["human_approved"] = approved
        state["approval_notes"] = notes

        if not approved:
            logger.info(f"Workflow '{workflow_id}': Rejected by human analyst.")
            state["current_step"] = "human_approval"
            state["status"] = "rejected"
            await self.save_workflow_state(workflow_id, state)
            return state

        logger.info(f"Workflow '{workflow_id}': Approved by human analyst. Resuming executive reporting.")

        # Resume to Executive Report Agent
        report_res = await self.executive_report_agent.run(state, db, mock_summary=mock_summary)
        state.update(report_res)
        await self.save_workflow_state(workflow_id, state)
        return state


# Global Runner Instance
_global_runner: Optional[VendorRiskWorkflowRunner] = None


def get_workflow_runner() -> VendorRiskWorkflowRunner:
    global _global_runner
    if _global_runner is None:
        _global_runner = VendorRiskWorkflowRunner()
    return _global_runner
