from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.agentic import (
    WorkflowRunRequest,
    WorkflowApprovalRequest,
    WorkflowStatusResponse,
)
from app.services.agents import get_workflow_runner
from app.services.vendor_service import get_vendor_by_id

router = APIRouter()


@router.post("/workflow/run", response_model=WorkflowStatusResponse, status_code=status.HTTP_200_OK)
async def run_workflow(
    payload: WorkflowRunRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers the LangGraph Multi-Agent Vendor Risk Intelligence Workflow for a vendor:
    Discovery Agent -> Policy Auditor Agent -> Risk Auditor Agent -> HITL Approval Evaluator -> Executive Report Agent.
    """
    vendor = await get_vendor_by_id(db=db, vendor_id=payload.vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID '{payload.vendor_id}' not found."
        )

    try:
        runner = get_workflow_runner()
        state = await runner.run_workflow(db=db, vendor_id=payload.vendor_id)
        
        return WorkflowStatusResponse(
            workflow_id=state["workflow_id"],
            vendor_id=state["vendor_id"],
            vendor_name=state.get("vendor_name", vendor.name),
            domain=state.get("domain", vendor.domain),
            status=state["status"],
            current_step=state["current_step"],
            overall_score=state.get("overall_score", 0.0),
            risk_tier=state.get("risk_tier", "Low"),
            requires_human_approval=state.get("requires_human_approval", False),
            human_approved=state.get("human_approved"),
            approval_notes=state.get("approval_notes"),
            executive_summary=state.get("executive_summary", ""),
            indexed_chunks_count=state.get("indexed_chunks_count", 0),
            errors=state.get("errors", [])
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(exc)}"
        )


@router.get("/workflow/status/{workflow_id}", response_model=WorkflowStatusResponse, status_code=status.HTTP_200_OK)
async def get_workflow_status(workflow_id: str):
    """
    Retrieves the state and execution progress of a multi-agent workflow.
    """
    runner = get_workflow_runner()
    state = await runner.get_workflow_state(workflow_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID '{workflow_id}' not found."
        )

    return WorkflowStatusResponse(
        workflow_id=state["workflow_id"],
        vendor_id=state["vendor_id"],
        vendor_name=state.get("vendor_name", ""),
        domain=state.get("domain", ""),
        status=state["status"],
        current_step=state["current_step"],
        overall_score=state.get("overall_score", 0.0),
        risk_tier=state.get("risk_tier", "Low"),
        requires_human_approval=state.get("requires_human_approval", False),
        human_approved=state.get("human_approved"),
        approval_notes=state.get("approval_notes"),
        executive_summary=state.get("executive_summary", ""),
        indexed_chunks_count=state.get("indexed_chunks_count", 0),
        errors=state.get("errors", [])
    )


@router.post("/workflow/approve/{workflow_id}", response_model=WorkflowStatusResponse, status_code=status.HTTP_200_OK)
async def approve_workflow(
    workflow_id: str,
    payload: WorkflowApprovalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submits a human approval or rejection decision for a workflow paused at the HITL approval gate.
    """
    try:
        runner = get_workflow_runner()
        state = await runner.resume_approval(
            db=db,
            workflow_id=workflow_id,
            approved=payload.approved,
            notes=payload.notes
        )

        return WorkflowStatusResponse(
            workflow_id=state["workflow_id"],
            vendor_id=state["vendor_id"],
            vendor_name=state.get("vendor_name", ""),
            domain=state.get("domain", ""),
            status=state["status"],
            current_step=state["current_step"],
            overall_score=state.get("overall_score", 0.0),
            risk_tier=state.get("risk_tier", "Low"),
            requires_human_approval=state.get("requires_human_approval", False),
            human_approved=state.get("human_approved"),
            approval_notes=state.get("approval_notes"),
            executive_summary=state.get("executive_summary", ""),
            indexed_chunks_count=state.get("indexed_chunks_count", 0),
            errors=state.get("errors", [])
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Approval submission failed: {str(exc)}"
        )
