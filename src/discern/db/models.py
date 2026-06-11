"""SQLAlchemy ORM models for documents and extracted fields."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    doc_type_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    overlay_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    fields: Mapped[list[ExtractionField]] = relationship(
        "ExtractionField", back_populates="document", cascade="all, delete-orphan"
    )


class ExtractionField(Base):
    __tablename__ = "extraction_fields"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    field_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    capture_type: Mapped[str] = mapped_column(String(32), nullable=False)

    document: Mapped[Document] = relationship("Document", back_populates="fields")
