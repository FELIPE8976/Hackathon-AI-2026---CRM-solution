"""
PostgreSQL-backed async store for pending human-approval requests.

Replaces the previous in-memory dict so that state survives server restarts.
All functions require an AsyncSession injected via FastAPI's Depends(get_db).
"""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import PendingApproval


async def save_pending(run_id: str, state: dict[str, Any], db: AsyncSession) -> None:
    """Persist a new escalated state to the database."""
    row = PendingApproval(
        run_id=run_id,
        client_id=state["client_id"],
        message=state["messages"][-1]["content"],
        timestamp=state["timestamp"],
        sentiment=state["sentiment"],
        intent=state["intent"],
        sla_breached=state["sla_breached"],
        proposed_action=state["proposed_action"],
        supervisor_note=state.get("supervisor_note"),
        messages_json=state["messages"],
    )
    db.add(row)
    await db.commit()


async def get_pending(run_id: str, db: AsyncSession) -> dict[str, Any] | None:
    """Return the AgentState dict for run_id, or None if not found."""
    result = await db.execute(
        select(PendingApproval).where(PendingApproval.run_id == run_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _row_to_state(row)


async def delete_pending(run_id: str, db: AsyncSession) -> None:
    """Remove a pending approval row by run_id."""
    await db.execute(
        delete(PendingApproval).where(PendingApproval.run_id == run_id)
    )
    await db.commit()


async def list_pending(db: AsyncSession) -> list[tuple[str, dict[str, Any]]]:
    """Return all pending approvals as (run_id, AgentState) tuples."""
    result = await db.execute(select(PendingApproval).order_by(PendingApproval.created_at))
    rows = result.scalars().all()
    return [(row.run_id, _row_to_state(row)) for row in rows]


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _row_to_state(row: PendingApproval) -> dict[str, Any]:
    return {
        "client_id": row.client_id,
        "messages": row.messages_json,
        "timestamp": row.timestamp,
        "sentiment": row.sentiment,
        "intent": row.intent,
        "sla_breached": row.sla_breached,
        "proposed_action": row.proposed_action,
        "supervisor_note": row.supervisor_note,
        "human_approved": None,
        "execution_result": None,
    }
