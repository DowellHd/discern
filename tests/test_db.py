"""Tests for Milestone 4: SQLAlchemy ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from discern.db.models import Document, ExtractionField


@pytest.fixture
def doc(db_session) -> Document:
    d = Document(
        id=str(uuid.uuid4()),
        original_filename="test.png",
        doc_type="connection_card",
        doc_type_confidence=0.9,
        image_path="/tmp/img.png",
        overlay_path="/tmp/overlay.png",
        created_at=datetime.now(UTC),
    )
    db_session.add(d)
    db_session.flush()
    return d


def test_document_persists(db_session, doc) -> None:
    fetched = db_session.get(Document, doc.id)
    assert fetched is not None
    assert fetched.doc_type == "connection_card"


def test_document_has_uuid_id(doc) -> None:
    assert len(doc.id) == 36
    uuid.UUID(doc.id)  # raises if invalid


def test_extraction_field_persists(db_session, doc) -> None:
    field = ExtractionField(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        field_name="visit_type",
        field_value="first_time",
        confidence=0.88,
        capture_type="checkbox",
    )
    db_session.add(field)
    db_session.flush()

    fetched = db_session.get(ExtractionField, field.id)
    assert fetched is not None
    assert fetched.field_value == "first_time"


def test_document_fields_relationship(db_session, doc) -> None:
    for i in range(3):
        f = ExtractionField(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            field_name=f"field_{i}",
            field_value=str(i),
            confidence=0.5,
            capture_type="handwritten",
        )
        db_session.add(f)
    db_session.flush()
    db_session.refresh(doc)
    assert len(doc.fields) == 3


def test_cascade_delete(db_session, doc) -> None:
    field = ExtractionField(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        field_name="x",
        field_value="y",
        confidence=0.5,
        capture_type="checkbox",
    )
    db_session.add(field)
    db_session.flush()
    field_id = field.id

    db_session.delete(doc)
    db_session.flush()

    assert db_session.get(ExtractionField, field_id) is None


def test_document_query_by_doc_type(db_session) -> None:
    for dt in ("connection_card", "prayer_request"):
        d = Document(
            id=str(uuid.uuid4()),
            original_filename="f.png",
            doc_type=dt,
            doc_type_confidence=0.8,
            image_path="/tmp/i.png",
            overlay_path="/tmp/o.png",
            created_at=datetime.now(UTC),
        )
        db_session.add(d)
    db_session.flush()

    results = db_session.query(Document).filter(Document.doc_type == "prayer_request").all()
    assert all(d.doc_type == "prayer_request" for d in results)
