"""Tests for the feedback-loop fine-tuning module (Phase 6)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
import torch

from discern.config import load_document_schema
from discern.data.generator import DocumentGenerator
from discern.data.schema import parse_document_schema
from discern.db.models import Document, ExtractionField
from discern.training.feedback import (
    FeedbackDataset,
    _parse_corrected_value,
    collate_feedback_batch,
    compute_feedback_loss,
    load_feedback_samples,
)


@pytest.fixture(scope="module")
def schema():
    return parse_document_schema(load_document_schema())


def _make_document(db_session, tmp_path, doc_type: str) -> Document:
    schema = parse_document_schema(load_document_schema())
    gen = DocumentGenerator(schema.document_types, seed=1)
    sample = gen.generate(doc_type)
    img_path = tmp_path / f"{uuid.uuid4()}.png"
    sample.image.save(img_path)

    doc = Document(
        id=str(uuid.uuid4()),
        original_filename="test.png",
        doc_type=doc_type,
        doc_type_confidence=0.9,
        image_path=str(img_path),
        overlay_path=str(img_path),
        created_at=datetime.now(UTC),
    )
    db_session.add(doc)
    db_session.flush()
    return doc


def _add_field(db_session, doc, field_name, value, corrected=True) -> ExtractionField:
    field = ExtractionField(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        field_name=field_name,
        field_value=value,
        confidence=0.9,
        capture_type="checkbox",
        corrected=corrected,
    )
    db_session.add(field)
    db_session.flush()
    return field


# ---------------------------------------------------------------------------
# _parse_corrected_value
# ---------------------------------------------------------------------------


def test_parse_interests_splits_on_comma() -> None:
    assert _parse_corrected_value("interests", "baptism, prayer") == ["baptism", "prayer"]


def test_parse_contact_ok_bool() -> None:
    assert _parse_corrected_value("contact_ok", "True") is True
    assert _parse_corrected_value("contact_ok", "false") is False


def test_parse_enum_value_passthrough() -> None:
    assert _parse_corrected_value("visit_type", "returning") == "returning"


# ---------------------------------------------------------------------------
# load_feedback_samples
# ---------------------------------------------------------------------------


def test_load_feedback_samples_picks_up_corrected_fields(db_session, tmp_path) -> None:
    doc = _make_document(db_session, tmp_path, "connection_card")
    _add_field(db_session, doc, "visit_type", "returning")

    samples = load_feedback_samples(db_session, limit=100)
    matches = [s for s in samples if s.document_id == doc.id]
    assert len(matches) == 1
    assert matches[0].field_name == "visit_type"
    assert matches[0].target_value == "returning"


def test_load_feedback_samples_ignores_uncorrected_fields(db_session, tmp_path) -> None:
    doc = _make_document(db_session, tmp_path, "connection_card")
    _add_field(db_session, doc, "visit_type", "returning", corrected=False)

    samples = load_feedback_samples(db_session, limit=100)
    assert not any(s.document_id == doc.id for s in samples)


def test_load_feedback_samples_ignores_fields_without_head(db_session, tmp_path) -> None:
    doc = _make_document(db_session, tmp_path, "connection_card")
    _add_field(db_session, doc, "full_name", "Jane Doe")

    samples = load_feedback_samples(db_session, limit=100)
    assert not any(s.document_id == doc.id for s in samples)


def test_load_feedback_samples_skips_mismatched_doc_type(db_session, tmp_path) -> None:
    doc = _make_document(db_session, tmp_path, "prayer_request")
    _add_field(db_session, doc, "visit_type", "returning")  # belongs to connection_card

    samples = load_feedback_samples(db_session, limit=100)
    assert not any(s.document_id == doc.id for s in samples)


def test_load_feedback_samples_skips_missing_image(db_session, tmp_path) -> None:
    doc = _make_document(db_session, tmp_path, "connection_card")
    doc.image_path = str(tmp_path / "does-not-exist.png")
    db_session.flush()
    _add_field(db_session, doc, "visit_type", "returning")

    samples = load_feedback_samples(db_session, limit=100)
    assert not any(s.document_id == doc.id for s in samples)


# ---------------------------------------------------------------------------
# FeedbackDataset
# ---------------------------------------------------------------------------


def test_feedback_dataset_item_shapes(db_session, tmp_path) -> None:
    doc = _make_document(db_session, tmp_path, "connection_card")
    _add_field(db_session, doc, "interests", "baptism, prayer")

    samples = load_feedback_samples(db_session, limit=100)
    ds = FeedbackDataset(samples)
    img, field_name, targets = ds[0]
    assert img.shape == (1, 224, 224)
    assert field_name == "interests"
    assert targets["interests"][0].item() == 1.0


def test_collate_feedback_batch(db_session, tmp_path) -> None:
    doc1 = _make_document(db_session, tmp_path, "connection_card")
    _add_field(db_session, doc1, "visit_type", "returning")
    doc2 = _make_document(db_session, tmp_path, "prayer_request")
    _add_field(db_session, doc2, "category", "healing")

    samples = load_feedback_samples(db_session, limit=100)
    ds = FeedbackDataset(samples)
    batch = [ds[i] for i in range(len(ds))]
    images, field_names, targets = collate_feedback_batch(batch)
    assert images.shape == (len(samples), 1, 224, 224)
    assert set(field_names) == {"visit_type", "category"}
    assert targets["doc_type"].shape == (len(samples),)


# ---------------------------------------------------------------------------
# compute_feedback_loss
# ---------------------------------------------------------------------------


def test_compute_feedback_loss_masks_to_corrected_field() -> None:
    from discern.models.extractor import FieldExtractor

    model = FieldExtractor(pretrained=False)
    images = torch.randn(2, 1, 224, 224)
    logits = model(images)
    targets = {
        "doc_type": torch.tensor([0, 1]),
        "visit_type": torch.tensor([1, 0]),
        "interests": torch.zeros(2, 5),
        "category": torch.tensor([0, 0]),
        "contact_ok": torch.zeros(2),
    }
    # Sample 0 was corrected on visit_type, sample 1 on category —
    # neither sample's "interests"/"contact_ok" heads should contribute.
    loss, per_task = compute_feedback_loss(logits, targets, ["visit_type", "category"])
    assert loss is not None
    assert set(per_task.keys()) == {"visit_type", "category"}


def test_compute_feedback_loss_returns_none_for_unmatched_fields() -> None:
    from discern.models.extractor import FieldExtractor

    model = FieldExtractor(pretrained=False)
    images = torch.randn(1, 1, 224, 224)
    logits = model(images)
    targets = {
        "doc_type": torch.tensor([0]),
        "visit_type": torch.tensor([0]),
        "interests": torch.zeros(1, 5),
        "category": torch.tensor([0]),
        "contact_ok": torch.zeros(1),
    }
    loss, per_task = compute_feedback_loss(logits, targets, ["unknown_field"])
    assert loss is None
    assert per_task == {}
