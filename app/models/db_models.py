"""
SQLAlchemy ORM model for the pending_approvals table.
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
    messages_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
