"""
Metrics Endpoint — Statistics Dashboard

GET /api/v1/metrics/summary

Returns aggregated KPIs and distributions computed from all messages
that have passed through the CRM pipeline.  No authentication is
required — the data is non-sensitive aggregate information.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.stats_store import get_metrics_summary
from app.models.schemas import MetricsSummary

router = APIRouter()


@router.get(
    "/summary",
    response_model=MetricsSummary,
    summary="Get aggregated CRM message statistics",
    description=(
        "Returns KPIs (total messages, escalation rate, SLA breach rate, "
        "approval rate) and full distributions by sentiment, intent, "
        "proposed action, and top-10 clients by volume."
    ),
)
@limiter.limit("60/minute")
async def get_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MetricsSummary:
    return await get_metrics_summary(db)
