"""
Supervisor Endpoint — Human-in-the-Loop

GET  /api/v1/supervisor/pending   → list all messages waiting for a decision
POST /api/v1/supervisor/decide    → approve or reject a pending action

When approved, the Executor agent is called directly with the stored state
so that the automated response is finally sent to the client.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.executor import run_executor
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import get_current_supervisor
from app.core.store import delete_pending, get_pending, list_pending
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
@limiter.limit("60/minute")
async def get_pending_approvals(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_supervisor),
) -> List[PendingApprovalItem]:
    items = await list_pending(db)
    result: List[PendingApprovalItem] = []
    for run_id, state in items:
        result.append(
            PendingApprovalItem(
                run_id=run_id,
                client_id=state["client_id"],
                message=state["messages"][-1]["content"],
                sentiment=state["sentiment"],
                sla_breached=state["sla_breached"],
                proposed_action=state["proposed_action"],
                supervisor_note=state.get("supervisor_note"),
                suggested_response=state.get("suggested_response"),
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
@limiter.limit("30/minute")
async def decide_action(
    request: Request,
    decision: SupervisorDecision,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_supervisor),
) -> ProcessingResponse:
    state = await get_pending(decision.run_id, db)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"run_id '{decision.run_id}' not found in pending approvals. "
                "It may have already been decided or never existed."
            ),
        )

    # Remove from the pending queue regardless of the decision
    await delete_pending(decision.run_id, db)

    # ------------------------------------------------------------------ #
    # Approved → use manual response, suggested response, or run executor #
    # ------------------------------------------------------------------ #
    if decision.approved:
        state["human_approved"] = True

        if decision.manual_response and decision.manual_response.strip():
            # Supervisor wrote a custom response — use it verbatim
            execution_result = decision.manual_response.strip()
        elif state.get("suggested_response"):
            # Supervisor accepted the system's suggestion
            execution_result = state["suggested_response"]
        else:
            # Fallback: generate a response with the executor
            executor_update = run_executor(state)
            execution_result = executor_update.get("execution_result")

        state["execution_result"] = execution_result

        return ProcessingResponse(
            run_id=decision.run_id,
            status="approved_and_executed",
            sentiment=state["sentiment"],
            sla_breached=state["sla_breached"],
            proposed_action=state["proposed_action"],
            supervisor_note=state.get("supervisor_note"),
            execution_result=execution_result,
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
