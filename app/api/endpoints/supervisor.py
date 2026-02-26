"""
Supervisor Endpoint — Human-in-the-Loop

GET  /api/v1/supervisor/pending   → list all messages waiting for a decision
POST /api/v1/supervisor/decide    → approve or reject a pending action

When approved, the Executor agent is called directly with the stored state
so that the automated response is finally sent to the client.
"""

from typing import List

from fastapi import APIRouter, HTTPException

from app.agents.executor import run_executor
from app.core.store import pending_approvals
from app.models.schemas import PendingApprovalItem, ProcessingResponse, SupervisorDecision

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /pending
# ---------------------------------------------------------------------------

@router.get(
    "/pending",
    response_model=List[PendingApprovalItem],
    summary="List actions pending human approval",
    description="Returns all messages that were escalated and are waiting for a supervisor decision.",
)
async def get_pending_approvals() -> List[PendingApprovalItem]:
    result: List[PendingApprovalItem] = []
    for run_id, state in pending_approvals.items():
        result.append(
            PendingApprovalItem(
                run_id=run_id,
                client_id=state["client_id"],
                message=state["messages"][-1]["content"],
                sentiment=state["sentiment"],
                sla_breached=state["sla_breached"],
                proposed_action=state["proposed_action"],
                supervisor_note=state.get("supervisor_note"),
                timestamp=state["timestamp"],
            )
        )
    return result


# ---------------------------------------------------------------------------
# POST /decide
# ---------------------------------------------------------------------------

@router.post(
    "/decide",
    response_model=ProcessingResponse,
    summary="Approve or reject a pending action",
    description=(
        "Submit a supervisor decision for a message that was escalated. "
        "If approved, the Executor agent will be called immediately."
    ),
)
async def decide_action(decision: SupervisorDecision) -> ProcessingResponse:
    state = pending_approvals.get(decision.run_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"run_id '{decision.run_id}' not found in pending approvals. "
                "It may have already been decided or never existed."
            ),
        )

    # Remove from the pending queue regardless of the decision
    del pending_approvals[decision.run_id]

    # ------------------------------------------------------------------ #
    # Approved → run executor and return result                            #
    # ------------------------------------------------------------------ #
    if decision.approved:
        state["human_approved"] = True
        executor_update = run_executor(state)
        state.update(executor_update)

        return ProcessingResponse(
            run_id=decision.run_id,
            status="approved_and_executed",
            sentiment=state["sentiment"],
            sla_breached=state["sla_breached"],
            proposed_action=state["proposed_action"],
            supervisor_note=state.get("supervisor_note"),
            execution_result=state.get("execution_result"),
            message=(
                f"Action approved and executed for client '{state['client_id']}'. "
                + (f"Supervisor note: {decision.reason}" if decision.reason else "")
            ),
        )

    # ------------------------------------------------------------------ #
    # Rejected → log and return without executing                          #
    # ------------------------------------------------------------------ #
    state["human_approved"] = False
    return ProcessingResponse(
        run_id=decision.run_id,
        status="rejected",
        sentiment=state["sentiment"],
        sla_breached=state["sla_breached"],
        proposed_action=state["proposed_action"],
        supervisor_note=state.get("supervisor_note"),
        execution_result=None,
        message=(
            f"Action rejected by supervisor for client '{state['client_id']}'. "
            + (f"Reason: {decision.reason}" if decision.reason else "No reason provided.")
        ),
    )
