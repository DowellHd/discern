"""add template_category to documents

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-26

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("template_category", sa.String(32), nullable=True))
    op.create_index("ix_docs_template_category", "documents", ["template_category"])


def downgrade() -> None:
    op.drop_index("ix_docs_template_category", table_name="documents")
    op.drop_column("documents", "template_category")
