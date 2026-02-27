"""add suggested_response to pending_approvals

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-27 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IF NOT EXISTS avoids failure if the column was already added manually.
    op.execute(
        "ALTER TABLE pending_approvals ADD COLUMN IF NOT EXISTS suggested_response TEXT"
    )


def downgrade() -> None:
    op.drop_column("pending_approvals", "suggested_response")
