"""(absorbed) add suggested_response — already applied by revision 0002

This migration is intentionally a no-op.  The suggested_response column was
added to pending_approvals in revision 0002.  This file exists only to keep
the linear revision chain intact after a branch merge.

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Column already added in 0002 — nothing to do.
    pass


def downgrade() -> None:
    pass
