"""create pending_approvals table

Revision ID: 0001
Revises:
Create Date: 2026-02-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_approvals",
        sa.Column("run_id", sa.VARCHAR(), nullable=False),
        sa.Column("client_id", sa.VARCHAR(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.VARCHAR(), nullable=False),
        sa.Column("sentiment", sa.VARCHAR(), nullable=False),
        sa.Column("intent", sa.VARCHAR(), nullable=False),
        sa.Column("sla_breached", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("proposed_action", sa.VARCHAR(), nullable=False),
        sa.Column("supervisor_note", sa.Text(), nullable=True),
        sa.Column("messages_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("run_id"),
    )


def downgrade() -> None:
    op.drop_table("pending_approvals")
