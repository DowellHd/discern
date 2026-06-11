"""create documents and extraction_fields tables

Revision ID: 0001
Revises:
Create Date: 2026-06-11

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("doc_type_confidence", sa.Float, nullable=False),
        sa.Column("image_path", sa.String(512), nullable=False),
        sa.Column("overlay_path", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "extraction_fields",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(64), nullable=False),
        sa.Column("field_value", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("capture_type", sa.String(32), nullable=False),
    )
    op.create_index("ix_docs_doc_type", "documents", ["doc_type"])
    op.create_index("ix_fields_document_id", "extraction_fields", ["document_id"])
    op.create_index("ix_fields_field_name", "extraction_fields", ["field_name"])


def downgrade() -> None:
    op.drop_table("extraction_fields")
    op.drop_table("documents")
