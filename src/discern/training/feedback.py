"""Fine-tune the classification heads on user-corrected field values.

Only fields with a matching classification head can be learned from here:
visit_type / interests (connection_card) and category / contact_ok
(prayer_request). Handwritten/freetext fields are OCR output, not something
this model predicts, so corrections to them aren't usable as training signal.

Each correction only tells us the true value of *one* field on a document —
we don't have full ground truth for the rest of that document's fields — so
the loss for a feedback sample is masked down to just the corrected field,
unlike the full multi-task loss used for synthetic data in `FieldExtractor`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import structlog
import torch
import torch.nn as nn
import torchvision.transforms as T
from PIL import Image
from sqlalchemy.orm import Session
from torch.utils.data import Dataset

from discern.data.preprocess import preprocess
from discern.db.models import Document, ExtractionField
from discern.training.dataset import _encode_targets

log = structlog.get_logger()

_IMG_SIZE = 224
_transform = T.Compose(
    [
        T.Resize((_IMG_SIZE, _IMG_SIZE)),
        T.ToTensor(),
        T.Normalize(mean=[0.5], std=[0.5]),
    ]
)

# field_name -> doc_type it belongs to (mirrors FieldExtractor's masked heads)
FEEDBACK_FIELD_DOC_TYPES = {
    "visit_type": "connection_card",
    "interests": "connection_card",
    "category": "prayer_request",
    "contact_ok": "prayer_request",
}


def _parse_corrected_value(field_name: str, raw: str) -> object:
    if field_name == "interests":
        return [v.strip() for v in raw.split(",") if v.strip()]
    if field_name == "contact_ok":
        return raw.strip().lower() in {"true", "1", "yes"}
    return raw.strip()


@dataclass
class FeedbackSample:
    document_id: str
    doc_type: str
    field_name: str
    image_path: Path
    target_value: object


def load_feedback_samples(db: Session, limit: int = 500) -> list[FeedbackSample]:
    """Pull corrected fields with a matching classification head from the DB.

    Skips fields with no matching head (handwritten/freetext), sensitive
    fields (excluded from training data on principle, matching the
    /training-candidates API), and documents whose image no longer exists
    on disk.
    """
    field_names = list(FEEDBACK_FIELD_DOC_TYPES)
    rows = (
        db.query(ExtractionField, Document.doc_type, Document.image_path)
        .join(Document, ExtractionField.document_id == Document.id)
        .filter(ExtractionField.corrected == True)  # noqa: E712
        .filter(ExtractionField.field_name.in_(field_names))
        .limit(limit)
        .all()
    )

    samples: list[FeedbackSample] = []
    for ef, doc_type, image_path in rows:
        if doc_type != FEEDBACK_FIELD_DOC_TYPES[ef.field_name]:
            continue  # correction doesn't match the doc type the head expects
        if ef.field_value is None:
            continue
        path = Path(image_path)
        if not path.exists():
            log.warning("feedback_image_missing", document_id=ef.document_id, path=str(path))
            continue
        samples.append(
            FeedbackSample(
                document_id=ef.document_id,
                doc_type=doc_type,
                field_name=ef.field_name,
                image_path=path,
                target_value=_parse_corrected_value(ef.field_name, ef.field_value),
            )
        )
    return samples


class FeedbackDataset(Dataset[tuple[torch.Tensor, str, dict[str, torch.Tensor]]]):
    def __init__(self, samples: list[FeedbackSample]) -> None:
        self._samples = samples

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, str, dict[str, torch.Tensor]]:
        s = self._samples[idx]
        img = preprocess(Image.open(s.image_path))
        tensor = _transform(img)
        targets = _encode_targets(s.doc_type, {s.field_name: s.target_value})
        return tensor, s.field_name, targets


def collate_feedback_batch(
    batch: list[tuple[torch.Tensor, str, dict[str, torch.Tensor]]],
) -> tuple[torch.Tensor, list[str], dict[str, torch.Tensor]]:
    images = torch.stack([b[0] for b in batch])
    field_names = [b[1] for b in batch]
    keys = batch[0][2].keys()
    targets = {k: torch.stack([b[2][k] for b in batch]) for k in keys}
    return images, field_names, targets


def compute_feedback_loss(
    logits: dict[str, torch.Tensor],
    targets: dict[str, torch.Tensor],
    field_names: list[str],
) -> tuple[torch.Tensor | None, dict[str, torch.Tensor]]:
    """Like FieldExtractor.compute_loss, but masked per-sample to the single
    field that sample was corrected on — sibling heads for the same doc type
    get no gradient from a sample unless that specific field was corrected.
    """
    ce = nn.CrossEntropyLoss()
    bce = nn.BCEWithLogitsLoss()
    device = logits["doc_type"].device
    losses: dict[str, torch.Tensor] = {}

    def mask_for(name: str) -> torch.Tensor:
        return torch.tensor([f == name for f in field_names], device=device)

    vt_mask = mask_for("visit_type")
    if vt_mask.any():
        losses["visit_type"] = ce(logits["visit_type"][vt_mask], targets["visit_type"][vt_mask])

    it_mask = mask_for("interests")
    if it_mask.any():
        losses["interests"] = bce(
            logits["interests"][it_mask], targets["interests"][it_mask].float()
        )

    cat_mask = mask_for("category")
    if cat_mask.any():
        losses["category"] = ce(logits["category"][cat_mask], targets["category"][cat_mask])

    co_mask = mask_for("contact_ok")
    if co_mask.any():
        losses["contact_ok"] = bce(
            logits["contact_ok"][co_mask], targets["contact_ok"][co_mask].float()
        )

    if not losses:
        return None, {}
    total: torch.Tensor = sum(losses.values())  # type: ignore[assignment]
    return total, losses


__all__ = [
    "FEEDBACK_FIELD_DOC_TYPES",
    "FeedbackSample",
    "FeedbackDataset",
    "load_feedback_samples",
    "compute_feedback_loss",
    "collate_feedback_batch",
]
