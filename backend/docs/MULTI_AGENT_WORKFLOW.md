# VendorGuard AI — Phase 6.3 LangGraph Multi-Agent Workflow Documentation

## Overview

Phase 6.3 introduces an autonomous **LangGraph Multi-Agent Vendor Risk Intelligence Workflow** into VendorGuard AI. The system orchestrates specialized agents and core services into a stateful, resilient workflow with persistent database-backed checkpointing and Human-in-the-Loop (HITL) approval gates for critical risk assessments.

---

## Architecture Diagram

```text
               ┌───────────────────────────────┐
               │         START WORKFLOW        │
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │    1. Discovery Agent         │
               │   (VendorCrawlerService)      │
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │    2. RAG Indexing Node       │
               │        (RAGIndexer)           │
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │    3. Policy Auditor Agent    │
               │       (RAGRetriever)          │
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │    4. Risk Auditor Agent      │
               │       (AIRiskEngine)          │
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │ 5. Approval Evaluator (Branch)│
               └───────┬───────────────┬───────┘
                       │               │
      RiskTier == Critical             │ RiskTier < Critical
      OR score >= 75.0                 │
                       │               │
                       ▼               │
         ┌───────────────────────────┐ │
         │ 6. Human Approval Gate    │ │
         │  (Interrupt & Resume API) │ │
         └─────────────┬─────────────┘ │
                       │ (Approved)    │
                       └───────┬───────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │  7. Executive Report Agent    │
               │   (Summary, Alerts, Audits)   │
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │          END WORKFLOW         │
               └───────────────┬───────────────┘
```

---

## Specialized Agent Responsibilities

### 1. Discovery Agent (`app.services.agents.discovery_agent.DiscoveryAgent`)
* **Role**: Normalizes vendor domain and website URL, triggers web crawl via `VendorCrawlerService`, discovers policy pages (Privacy, Terms, Security, Compliance), and persists `Document` + `PolicyVersion` records. Handles crawl timeouts and network errors gracefully.

### 2. Policy Auditor Agent (`app.services.agents.policy_auditor_agent.PolicyAuditorAgent`)
* **Role**: Uses `RAGIndexer` to chunk and embed policy documents. Uses `RAGRetriever` to extract vendor-isolated policy evidence across Privacy, Security, Compliance, and Legal categories. Identifies missing or insufficient policy evidence prior to risk scoring.

### 3. Risk Auditor Agent (`app.services.agents.risk_auditor_agent.RiskAuditorAgent`)
* **Role**: Orchestrates `AIRiskEngine.analyze_vendor`. Preserves all deterministic category score formulas, severity penalties, and evidence quote verification without duplicating formulas or executing LLM score math. Prepares verified risk assessment data for approval evaluation.

### 4. Executive Report Agent (`app.services.agents.executive_report_agent.ExecutiveReportAgent`)
* **Role**: Synthesizes an executive-level summary and actionable recommendations. Reuses existing `Alert` and `AuditLog` infrastructure to record risk updates without duplicating alerts.

---

## State Schema (`app.services.agents.state.VendorRiskState`)

```python
class VendorRiskState(TypedDict, total=False):
    workflow_id: str
    vendor_id: str
    vendor_name: str
    domain: str
    website_url: str
    current_step: str
    status: str  # pending, crawling, indexing, auditing, awaiting_approval, completed, rejected, failed
    discovered_documents: List[Dict[str, Any]]
    indexed_chunks_count: int
    risk_assessment_id: Optional[str]
    overall_score: float
    risk_tier: str
    category_scores: Dict[str, float]
    key_findings: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    executive_summary: str
    requires_human_approval: bool
    human_approved: Optional[bool]
    approval_notes: Optional[str]
    alerts_created: List[Dict[str, Any]]
    errors: List[str]
```

---

## Persistent Checkpoint Architecture & Thread ID Mapping

* **Checkpointer Selection**: Checkpointing uses `AsyncPostgresSaver` in production environments when `POSTGRES_USER` or `CHECKPOINT_DATABASE_URL` / `DATABASE_URL` points to PostgreSQL. For SQLite or local development environments, `AsyncSqliteSaver` persists workflow state to `vendorguard_checkpoints.db`.
* **Thread ID Mapping**: Each workflow instance maps its unique `workflow_id` directly to the LangGraph `thread_id` (`config = {"configurable": {"thread_id": workflow_id}}`).
* **Backend Restart Recovery**: State is restored directly from PostgreSQL/SQLite checkpoints via `thread_id`. If a process or server restarts while a workflow is paused in `awaiting_approval`, the workflow state is reloaded from the database upon status query or approval request.

---

## Human-in-the-Loop (HITL) Gate & Persistence

When an assessment evaluates to `RiskTier == "Critical"` or `overall_score >= 75.0`:
1. The approval evaluator node sets `requires_human_approval = True` and transitions workflow status to `"awaiting_approval"`.
2. The workflow state snapshot is written to PostgreSQL/SQLite checkpoint storage.
3. Execution pauses until an analyst submits an approval or rejection payload via `POST /api/v1/agentic/workflow/approve/{workflow_id}`:
   * If `approved = True`: Execution resumes from the checkpointer snapshot to the Executive Report Agent (`status = "completed"`).
   * If `approved = False`: Execution updates status to `"rejected"` and saves final state.

---

## API Endpoints

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/v1/agentic/workflow/run` | Initiates the multi-agent workflow for a vendor. |
| `GET` | `/api/v1/agentic/workflow/status/{workflow_id}` | Retrieves current state and step progress for a workflow from persistent checkpointer. |
| `POST` | `/api/v1/agentic/workflow/approve/{workflow_id}` | Submits human approval/rejection decision to resume a thread. |

---

## Environment Variables & Local Development Setup

### Environment Variables
```env
# Database Settings
DATABASE_URL=postgresql+asyncpg://vendorguard:vendorguard123@localhost:5432/vendorguard_db
CHECKPOINT_DATABASE_URL=postgresql://vendorguard:vendorguard123@localhost:5432/vendorguard_db

# Local SQLite Fallback
# DATABASE_URL=sqlite+aiosqlite:///./vendorguard.db
```

### Local Commands
```powershell
# Run backend test suite
.\venv\Scripts\python -m pytest

# Start backend server
.\venv\Scripts\uvicorn app.main:app --reload --port 8000
```

---

## Production Considerations

* **PostgreSQL Checkpoint Persistence**: Production setups use `AsyncPostgresSaver` backed by PostgreSQL (`psycopg_pool.AsyncConnectionPool`) for high-availability multi-node backend clusters.
* **Database Connection Pooling**: Connection pool sizes (`max_size=10`) are tuned for concurrent workflow executions across worker threads.
