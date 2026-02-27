"""ensure suggested_response column exists in pending_approvals

Uses IF NOT EXISTS so this is safe to run even if the column was already
added by a previous migration or manual DDL.

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE pending_approvals ADD COLUMN IF NOT EXISTS suggested_response TEXT"
    )


def downgrade() -> None:
    op.drop_column("pending_approvals", "suggested_response")
