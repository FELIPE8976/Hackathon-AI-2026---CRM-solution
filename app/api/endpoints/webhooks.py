"""
Webhook Endpoint — Message Ingestion

POST /api/v1/webhook/messages

Receives a simulated CRM message, runs it through the LangGraph pipeline
(Analyst → Triage → Executor or pause), and returns the outcome.

If the Triage agent decides to escalate (negative sentiment or SLA breach),
the state is persisted to PostgreSQL and the caller receives a
`pending_approval` status with the `run_id` needed to decide later.
"""

import asyncio
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import crm_graph
from app.agents.state import AgentState
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import verify_api_key
from app.core.store import save_pending
from app.models.schemas import ProcessingResponse, WebhookPayload

router = APIRouter()


@router.post(
    "/messages",
    response_model=ProcessingResponse,
    summary="Receive an incoming CRM message",
    description=(
        "Triggers the full multi-agent pipeline. "
        "Returns immediately with either 'processed' or 'pending_approval'."
    ),
)
@limiter.limit("30/minute")
async def receive_message(
    request: Request,
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
) -> ProcessingResponse:
    run_id = str(uuid.uuid4())

    # Build the initial state that enters the graph
    initial_state: AgentState = {
        "client_id": payload.client_id,
        "messages": [{"role": "user", "content": payload.message}],
        "timestamp": payload.timestamp.isoformat(),
        # Defaults — will be overwritten by agent nodes
        "sentiment": "neutral",
        "intent": "general_inquiry",
        "sla_breached": False,
        "proposed_action": "",
        "supervisor_note": None,
        "human_approved": None,
        "execution_result": None,
    }

    # Run the synchronous LangGraph graph in a thread to avoid blocking the event loop
    final_state: AgentState = await asyncio.to_thread(crm_graph.invoke, initial_state)

    # ------------------------------------------------------------------ #
    # Branch: graph paused — supervisor must approve before proceeding     #
    # ------------------------------------------------------------------ #
    if final_state.get("proposed_action") == "escalate_to_human":
        await save_pending(run_id, final_state, db)
        return ProcessingResponse(
            run_id=run_id,
            status="pending_approval",
            sentiment=final_state["sentiment"],
            sla_breached=final_state["sla_breached"],
            proposed_action=final_state["proposed_action"],
            supervisor_note=final_state.get("supervisor_note"),
            execution_result=None,
            message=(
                f"Message from client '{payload.client_id}' requires human approval "
                f"before any action is taken. Use run_id to decide via "
                f"POST /api/v1/supervisor/decide."
            ),
        )

    # ------------------------------------------------------------------ #
    # Branch: graph completed automatically                                #
    # ------------------------------------------------------------------ #
    return ProcessingResponse(
        run_id=run_id,
        status="processed",
        sentiment=final_state["sentiment"],
        sla_breached=final_state["sla_breached"],
        proposed_action=final_state["proposed_action"],
        supervisor_note=None,
        execution_result=final_state.get("execution_result"),
        message=(
            f"Message from client '{payload.client_id}' processed automatically. "
            f"Action executed: {final_state['proposed_action']}."
        ),
    )
