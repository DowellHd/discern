"""PyTorch Dataset that generates synthetic document samples on the fly."""

from __future__ import annotations

import torch
import torchvision.transforms as T
from torch.utils.data import Dataset

from discern.data.generator import DocumentGenerator
from discern.data.preprocess import preprocess
from discern.data.schema import DocumentSchema
from discern.models.extractor import (
    CATEGORY_OPTIONS,
    DOC_TYPES,
    INTERESTS_OPTIONS,
    VISIT_TYPE_OPTIONS,
)

_IMG_SIZE = 224

_transform = T.Compose(
    [
        T.Resize((_IMG_SIZE, _IMG_SIZE)),
        T.ToTensor(),
        T.Normalize(mean=[0.5], std=[0.5]),
    ]
)


class SyntheticDataset(Dataset[tuple[torch.Tensor, dict[str, torch.Tensor]]]):
    """Generates (image_tensor, targets) pairs from the document schema.

    Each call to __getitem__ produces a fresh synthetic image, so the
    effective training set grows with epochs. The generator is seeded for
    reproducibility of the starting state.
    """

    def __init__(self, schema: DocumentSchema, size: int = 1000, seed: int = 42) -> None:
        self._generator = DocumentGenerator(schema.document_types, seed=seed)
        self._size = size
        self._doc_type_keys = DOC_TYPES  # fixed order matches head label indices

    def __len__(self) -> int:
        return self._size

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        doc_type = self._doc_type_keys[idx % len(self._doc_type_keys)]
        sample = self._generator.generate(doc_type)
        img = preprocess(sample.image)  # L-mode PIL image
        tensor = _transform(img)  # (1, 224, 224)
        targets = _encode_targets(doc_type, sample.labels)
        return tensor, targets


def _encode_targets(doc_type: str, labels: dict) -> dict[str, torch.Tensor]:
    dt_idx = DOC_TYPES.index(doc_type)

    vt_raw = labels.get("visit_type", VISIT_TYPE_OPTIONS[0])
    vt_idx = VISIT_TYPE_OPTIONS.index(vt_raw) if vt_raw in VISIT_TYPE_OPTIONS else 0

    interests_raw = labels.get("interests") or []
    interests_multihot = [1.0 if opt in interests_raw else 0.0 for opt in INTERESTS_OPTIONS]

    cat_raw = labels.get("category", CATEGORY_OPTIONS[0])
    cat_idx = CATEGORY_OPTIONS.index(cat_raw) if cat_raw in CATEGORY_OPTIONS else 0

    contact_val = float(bool(labels.get("contact_ok", False)))

    return {
        "doc_type": torch.tensor(dt_idx, dtype=torch.long),
        "visit_type": torch.tensor(vt_idx, dtype=torch.long),
        "interests": torch.tensor(interests_multihot, dtype=torch.float),
        "category": torch.tensor(cat_idx, dtype=torch.long),
        "contact_ok": torch.tensor(contact_val, dtype=torch.float),
    }
