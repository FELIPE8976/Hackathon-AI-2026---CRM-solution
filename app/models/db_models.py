"""
SQLAlchemy ORM models for the CRM Multi-Agent database tables.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PendingApproval(Base):
    __tablename__ = "pending_approvals"

    run_id: Mapped[str] = mapped_column(primary_key=True)
    client_id: Mapped[str] = mapped_column(nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[str] = mapped_column(nullable=False)
    sentiment: Mapped[str] = mapped_column(nullable=False)
    intent: Mapped[str] = mapped_column(nullable=False)
    sla_breached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    proposed_action: Mapped[str] = mapped_column(nullable=False)
    supervisor_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    messages_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class MessageStat(Base):
    """Immutable audit record created for every message that enters the pipeline.

    The row is written once when the message is processed, and the
    `final_status` / `human_approved` columns are updated later if a
    supervisor makes a decision on an escalated case.
    """

    __tablename__ = "message_stats"

    run_id: Mapped[str] = mapped_column(primary_key=True)
    client_id: Mapped[str] = mapped_column(nullable=False)
    sentiment: Mapped[str] = mapped_column(nullable=False)
    intent: Mapped[str] = mapped_column(nullable=False)
    sla_breached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    proposed_action: Mapped[str] = mapped_column(nullable=False)
    # Lifecycle status — updated when a supervisor decides on escalated cases
    final_status: Mapped[str] = mapped_column(nullable=False)
    # None  → not escalated; True/False → supervisor decision
    human_approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
