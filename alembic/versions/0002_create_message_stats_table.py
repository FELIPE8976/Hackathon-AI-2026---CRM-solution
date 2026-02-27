"""create message_stats table

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-27 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "message_stats",
        sa.Column("run_id", sa.VARCHAR(), nullable=False),
        sa.Column("client_id", sa.VARCHAR(), nullable=False),
        sa.Column("sentiment", sa.VARCHAR(), nullable=False),
        sa.Column("intent", sa.VARCHAR(), nullable=False),
        sa.Column("sla_breached", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("proposed_action", sa.VARCHAR(), nullable=False),
        sa.Column("final_status", sa.VARCHAR(), nullable=False),
        sa.Column("human_approved", sa.Boolean(), nullable=True),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_message_stats_client_id", "message_stats", ["client_id"])
    op.create_index("ix_message_stats_processed_at", "message_stats", ["processed_at"])


def downgrade() -> None:
    op.drop_index("ix_message_stats_processed_at", table_name="message_stats")
    op.drop_index("ix_message_stats_client_id", table_name="message_stats")
    op.drop_table("message_stats")
