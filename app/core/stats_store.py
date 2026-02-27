"""
PostgreSQL-backed async store for aggregated message statistics.

Responsibilities:
- Record a stat row for every message that enters the pipeline.
- Update the row when a supervisor makes a decision on an escalated case.
- Query and aggregate stats for the metrics dashboard.
"""

import logging
from typing import Any

from sqlalchemy import Boolean, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import MessageStat
from app.models.schemas import (
    ActionCount,
    ClientStat,
    IntentCount,
    MetricsSummary,
    SentimentCount,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------


async def record_message_stat(
    run_id: str,
    state: dict[str, Any],
    final_status: str,
    db: AsyncSession,
) -> None:
    """Persist a new stat row at the moment a message finishes processing.

    Args:
        run_id: UUID identifying this pipeline run.
        state: Final AgentState dict produced by the pipeline.
        final_status: One of ``processed`` | ``pending_approval``.
        db: Async SQLAlchemy session.
    """
    row = MessageStat(
        run_id=run_id,
        client_id=state["client_id"],
        sentiment=state["sentiment"],
        intent=state["intent"],
        sla_breached=state["sla_breached"],
        proposed_action=state["proposed_action"],
        final_status=final_status,
        human_approved=None,
    )
    db.add(row)
    await db.commit()


async def update_stat_decision(
    run_id: str,
    approved: bool,
    db: AsyncSession,
) -> None:
    """Update an existing stat row with the supervisor's decision.

    Args:
        run_id: UUID of the escalated run to update.
        approved: True if the supervisor approved the action.
        db: Async SQLAlchemy session.
    """
    new_status = "approved_and_executed" if approved else "rejected"
    await db.execute(
        update(MessageStat)
        .where(MessageStat.run_id == run_id)
        .values(final_status=new_status, human_approved=approved)
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Read / aggregation
# ---------------------------------------------------------------------------


async def get_metrics_summary(db: AsyncSession) -> MetricsSummary:
    """Return fully aggregated metrics computed from all ``message_stats`` rows.

    All counts are computed in a single round-trip per dimension to keep
    the number of DB queries small and predictable.
    """
    total = await _count_total(db)
    if total == 0:
        return _empty_summary()

    escalated = await _count_where(db, MessageStat.proposed_action == "escalate_to_human")
    sla_breached_count = await _count_where(db, MessageStat.sla_breached == True)  # noqa: E712
    approved_count = await _count_where(db, MessageStat.human_approved == True)  # noqa: E712
    pending_count = await _count_where(db, MessageStat.final_status == "pending_approval")

    sentiment_dist = await _sentiment_distribution(db, total)
    intent_dist = await _intent_distribution(db, total)
    action_dist = await _action_distribution(db, total)
    top_clients = await _top_clients(db)

    return MetricsSummary(
        total_messages=total,
        escalation_rate=_pct(escalated, total),
        sla_breach_rate=_pct(sla_breached_count, total),
        approval_rate=_pct(approved_count, escalated),
        pending_approvals=pending_count,
        sentiment_distribution=sentiment_dist,
        intent_distribution=intent_dist,
        action_distribution=action_dist,
        top_clients=top_clients,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


async def _count_total(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(MessageStat))
    return result.scalar_one() or 0


async def _count_where(db: AsyncSession, condition) -> int:
    result = await db.execute(
        select(func.count()).select_from(MessageStat).where(condition)
    )
    return result.scalar_one() or 0


async def _sentiment_distribution(db: AsyncSession, total: int) -> list[SentimentCount]:
    result = await db.execute(
        select(MessageStat.sentiment, func.count().label("count"))
        .group_by(MessageStat.sentiment)
        .order_by(func.count().desc())
    )
    return [
        SentimentCount(
            sentiment=row.sentiment,
            count=row.count,
            percentage=_pct(row.count, total),
        )
        for row in result.all()
    ]


async def _intent_distribution(db: AsyncSession, total: int) -> list[IntentCount]:
    result = await db.execute(
        select(MessageStat.intent, func.count().label("count"))
        .group_by(MessageStat.intent)
        .order_by(func.count().desc())
    )
    return [
        IntentCount(
            intent=row.intent,
            count=row.count,
            percentage=_pct(row.count, total),
        )
        for row in result.all()
    ]


async def _action_distribution(db: AsyncSession, total: int) -> list[ActionCount]:
    result = await db.execute(
        select(MessageStat.proposed_action, func.count().label("count"))
        .group_by(MessageStat.proposed_action)
        .order_by(func.count().desc())
    )
    return [
        ActionCount(
            action=row.proposed_action,
            count=row.count,
            percentage=_pct(row.count, total),
        )
        for row in result.all()
    ]


async def _top_clients(db: AsyncSession) -> list[ClientStat]:
    result = await db.execute(
        select(
            MessageStat.client_id,
            func.count().label("total"),
            func.sum(
                case((MessageStat.sentiment == "negative", 1), else_=0)
            ).label("negative_count"),
            func.sum(
                case((MessageStat.sla_breached == True, 1), else_=0)  # noqa: E712
            ).label("sla_breached_count"),
        )
        .group_by(MessageStat.client_id)
        .order_by(func.count().desc())
        .limit(10)
    )
    return [
        ClientStat(
            client_id=row.client_id,
            total=row.total,
            negative_count=int(row.negative_count or 0),
            sla_breached_count=int(row.sla_breached_count or 0),
        )
        for row in result.all()
    ]


def _pct(part: int, total: int) -> float:
    """Return percentage rounded to one decimal, or 0.0 if total is zero."""
    if total == 0:
        return 0.0
    return round(part / total * 100, 1)


def _empty_summary() -> MetricsSummary:
    return MetricsSummary(
        total_messages=0,
        escalation_rate=0.0,
        sla_breach_rate=0.0,
        approval_rate=0.0,
        pending_approvals=0,
        sentiment_distribution=[],
        intent_distribution=[],
        action_distribution=[],
        top_clients=[],
    )
