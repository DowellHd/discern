"""Tests for Milestone 3: model architecture and loss computation."""

from __future__ import annotations

import pytest
import torch

from discern.models.backbone import FEATURE_DIM, DiscernBackbone
from discern.models.extractor import (
    CATEGORY_OPTIONS,
    DOC_TYPES,
    INTERESTS_OPTIONS,
    VISIT_TYPE_OPTIONS,
    FieldExtractor,
)
from discern.models.heads import ClassificationHead, MultiLabelHead

# ---------------------------------------------------------------------------
# Backbone
# ---------------------------------------------------------------------------


def test_backbone_output_shape() -> None:
    model = DiscernBackbone(pretrained=False)
    x = torch.randn(2, 1, 224, 224)
    out = model(x)
    assert out.shape == (2, FEATURE_DIM)


def test_backbone_first_conv_is_single_channel() -> None:
    model = DiscernBackbone(pretrained=False)
    assert model.features[0].in_channels == 1


# ---------------------------------------------------------------------------
# Heads
# ---------------------------------------------------------------------------


def test_classification_head_shape() -> None:
    head = ClassificationHead(FEATURE_DIM, 3)
    x = torch.randn(4, FEATURE_DIM)
    assert head(x).shape == (4, 3)


def test_multilabel_head_shape() -> None:
    head = MultiLabelHead(FEATURE_DIM, 5)
    x = torch.randn(4, FEATURE_DIM)
    assert head(x).shape == (4, 5)


# ---------------------------------------------------------------------------
# FieldExtractor – forward
# ---------------------------------------------------------------------------


@pytest.fixture()
def extractor() -> FieldExtractor:
    return FieldExtractor(pretrained=False)


def test_extractor_forward_keys(extractor: FieldExtractor) -> None:
    x = torch.randn(2, 1, 224, 224)
    out = extractor(x)
    assert set(out.keys()) == {"doc_type", "visit_type", "interests", "category", "contact_ok"}


def test_extractor_doc_type_shape(extractor: FieldExtractor) -> None:
    x = torch.randn(2, 1, 224, 224)
    out = extractor(x)
    assert out["doc_type"].shape == (2, len(DOC_TYPES))


def test_extractor_doc_type_covers_all_templates(extractor: FieldExtractor) -> None:
    expected = {
        "connection_card",
        "prayer_request",
        "giving_envelope",
        "receipt",
        "business_card",
        "handwritten_note",
        "generic_form",
        "invoice",
        "event_flyer",
    }
    assert set(DOC_TYPES) == expected
    assert len(DOC_TYPES) == 9


def test_extractor_visit_type_shape(extractor: FieldExtractor) -> None:
    x = torch.randn(2, 1, 224, 224)
    out = extractor(x)
    assert out["visit_type"].shape == (2, len(VISIT_TYPE_OPTIONS))


def test_extractor_interests_shape(extractor: FieldExtractor) -> None:
    x = torch.randn(2, 1, 224, 224)
    out = extractor(x)
    assert out["interests"].shape == (2, len(INTERESTS_OPTIONS))


def test_extractor_category_shape(extractor: FieldExtractor) -> None:
    x = torch.randn(2, 1, 224, 224)
    out = extractor(x)
    assert out["category"].shape == (2, len(CATEGORY_OPTIONS))


def test_extractor_contact_ok_shape(extractor: FieldExtractor) -> None:
    x = torch.randn(2, 1, 224, 224)
    out = extractor(x)
    assert out["contact_ok"].shape == (2,)


# ---------------------------------------------------------------------------
# FieldExtractor – loss
# ---------------------------------------------------------------------------


def _make_targets(batch_size: int, doc_type_idx: int) -> dict[str, torch.Tensor]:
    return {
        "doc_type": torch.full((batch_size,), doc_type_idx, dtype=torch.long),
        "visit_type": torch.zeros(batch_size, dtype=torch.long),
        "interests": torch.zeros(batch_size, len(INTERESTS_OPTIONS)),
        "category": torch.zeros(batch_size, dtype=torch.long),
        "contact_ok": torch.zeros(batch_size),
    }


def test_loss_connection_card_is_scalar(extractor: FieldExtractor) -> None:
    x = torch.randn(4, 1, 224, 224)
    logits = extractor(x)
    targets = _make_targets(4, doc_type_idx=0)  # connection_card
    total, task_losses = extractor.compute_loss(logits, targets)
    assert total.ndim == 0
    assert "doc_type" in task_losses
    assert "visit_type" in task_losses
    assert "interests" in task_losses
    assert "category" not in task_losses
    assert "contact_ok" not in task_losses


def test_loss_prayer_request_is_scalar(extractor: FieldExtractor) -> None:
    x = torch.randn(4, 1, 224, 224)
    logits = extractor(x)
    targets = _make_targets(4, doc_type_idx=1)  # prayer_request
    total, task_losses = extractor.compute_loss(logits, targets)
    assert total.ndim == 0
    assert "doc_type" in task_losses
    assert "category" in task_losses
    assert "contact_ok" in task_losses
    assert "visit_type" not in task_losses
    assert "interests" not in task_losses


def test_loss_mixed_batch(extractor: FieldExtractor) -> None:
    x = torch.randn(4, 1, 224, 224)
    logits = extractor(x)
    targets = _make_targets(4, doc_type_idx=0)
    targets["doc_type"] = torch.tensor([0, 0, 1, 1], dtype=torch.long)
    total, task_losses = extractor.compute_loss(logits, targets)
    assert total.ndim == 0
    assert "visit_type" in task_losses
    assert "interests" in task_losses
    assert "category" in task_losses
    assert "contact_ok" in task_losses


def test_loss_backward(extractor: FieldExtractor) -> None:
    x = torch.randn(2, 1, 224, 224)
    logits = extractor(x)
    targets = _make_targets(2, doc_type_idx=0)
    total, _ = extractor.compute_loss(logits, targets)
    total.backward()
    grads = [p.grad for p in extractor.parameters() if p.grad is not None]
    assert len(grads) > 0
