"""Seed the demo library: ~30 synthetic documents across all nine templates.

Rendered with the repo's own `DocumentGenerator` (so the images are real renders of the values
stored beside them), then written through the same models the API uses. Deterministic for a
given seed apart from timestamps, which are spread over the last few weeks from "now".
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import structlog
from PIL import Image
from sqlalchemy.orm import Session

from discern.api.auth import _ensure_demo_user, encrypt_field
from discern.config import load_document_schema, settings
from discern.data.generator import DocumentGenerator
from discern.data.schema import DocumentSchema, parse_document_schema
from discern.db.models import Document, ExtractionField
from discern.demo import mock
from discern.demo.realism import polish
from discern.demo.samples import display_value
from discern.inference.engine import InferenceResult
from discern.inference.overlay import draw_overlay

log = structlog.get_logger()

SEED = 42
_NAMESPACE = uuid.UUID("6f1c2b5e-3d34-4d2c-9a55-0a8e1d6b7c11")

# (template, how many). Roughly what a person who scans receipts and cards weekly would have.
PLAN: list[tuple[str, int]] = [
    ("receipt", 6),
    ("business_card", 5),
    ("connection_card", 4),
    ("invoice", 4),
    ("prayer_request", 3),
    ("giving_envelope", 2),
    ("handwritten_note", 2),
    ("event_flyer", 2),
    ("generic_form", 2),
]
# Positions in the (shuffled) sequence that should read as "unsure" and land in the review queue.
_REVIEW_POSITIONS = {2, 9, 16, 23}
# Positions where the user has already fixed a field by hand.
_CORRECTED_POSITIONS = {1, 6, 12, 19, 27}
_FOLLOW_UP = ["pending", "contacted", "done", "pending"]


def _save_png(img: Image.Image, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, format="PNG")


def _store(value: str | None, sensitive: bool) -> str | None:
    """Sensitive values are never stored in plaintext (same rule as the API)."""
    if sensitive and value:
        return encrypt_field(value) if settings.field_encryption_key else "[REDACTED]"
    return value


def seed_demo_library(db: Session, schema: DocumentSchema | None = None) -> int:
    """Create the demo documents. Returns how many were added."""
    schema = schema or parse_document_schema(load_document_schema())
    user = _ensure_demo_user(db)
    gen = DocumentGenerator(schema.document_types, seed=SEED, label_hook=polish)
    rng = random.Random(SEED)

    sequence = [t for t, n in PLAN for _ in range(n)]
    rng.shuffle(sequence)
    now = datetime.now(UTC).replace(tzinfo=None)

    for i, doc_type in enumerate(sequence):
        sample = gen.generate(doc_type)
        spec = schema.document_types[doc_type]
        values = {f.name: display_value(sample.labels.get(f.name)) for f in spec.fields}
        unsure = i in _REVIEW_POSITIONS
        seed = SEED * 1000 + i
        doc_conf = (
            round(rng.uniform(0.52, 0.68), 4) if unsure else round(rng.uniform(0.90, 0.99), 4)
        )
        result: InferenceResult = mock.build_result(
            schema, doc_type, values, seed=seed, exact=not unsure, doc_type_confidence=doc_conf
        )

        doc_id = str(uuid.uuid5(_NAMESPACE, f"demo-{i}"))
        upload_dir = settings.data_dir / "uploads" / doc_id
        image = sample.image.convert("RGB")
        _save_png(image, upload_dir / "original.png")
        _save_png(draw_overlay(image, result), upload_dir / "overlay.png")

        age = timedelta(days=(i * 41) // len(sequence), hours=rng.randint(0, 20))
        doc = Document(
            id=doc_id,
            user_id=user.id,
            original_filename=f"{doc_type}_{i + 1:02d}.jpg",
            doc_type=doc_type,
            doc_type_confidence=result.doc_type_confidence,
            template_category=schema.category_for(doc_type),
            image_path=str(upload_dir / "original.png"),
            overlay_path=str(upload_dir / "overlay.png"),
            follow_up_status=(
                _FOLLOW_UP[i % len(_FOLLOW_UP)]
                if schema.category_for(doc_type) == "church"
                else None
            ),
            llm_refined=False,
            created_at=now - age,
        )

        # In some documents the user has already fixed one field by hand (stored value is the fix).
        to_correct = i in _CORRECTED_POSITIONS
        for fr in result.fields:
            stored = _store(fr.raw_value, fr.sensitive) if fr.sensitive else fr.value
            corrected = False
            if to_correct and fr.capture != "checkbox" and fr.raw_value and not fr.sensitive:
                corrected, to_correct = True, False
            doc.fields.append(
                ExtractionField(
                    document_id=doc_id,
                    field_name=fr.name,
                    field_value=stored,
                    confidence=fr.confidence,
                    capture_type=fr.capture,
                    corrected=corrected,
                )
            )
        db.add(doc)

    db.commit()
    log.info("demo_library_seeded", documents=len(sequence))
    return len(sequence)


def seed_if_empty(db: Session) -> int:
    if db.query(Document).count() > 0:
        return 0
    return seed_demo_library(db)
