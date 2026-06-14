"""add follow_up_status to documents and corrected to extraction_fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-14

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("follow_up_status", sa.String(32), nullable=True))
    op.add_column(
        "extraction_fields",
        sa.Column("corrected", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("extraction_fields", "corrected")
    op.drop_column("documents", "follow_up_status")
