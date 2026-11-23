"""Deterministic stand-ins for the model, OCR and LLM backends.

Everything is derived from the image content, so the same upload always yields the same result.
A bundled sample (see `samples`) is read back exactly. Any other image gets *illustrative*
values: plausible, schema-valid, but unrelated to what is actually on the page. They are given
deliberately middling confidences so they land in the review queue instead of passing as
accurate reads.
"""

from __future__ import annotations

import hashlib
import random
from functools import lru_cache

from PIL import Image

from discern.config import load_document_schema
from discern.data.schema import DocumentSchema, parse_document_schema
from discern.data.synthesizer import ValueSynthesizer
from discern.demo.realism import polish
from discern.demo.samples import display_value, recognize, thumbnail
from discern.inference.engine import FieldResult, InferenceResult


@lru_cache(maxsize=1)
def _schema() -> DocumentSchema:
    return parse_document_schema(load_document_schema())


def image_seed(image: Image.Image) -> int:
    """Stable integer derived from the image content."""
    digest = hashlib.sha256(thumbnail(image).tobytes()).digest()
    return int.from_bytes(digest[:8], "big")


def pick_doc_type(schema: DocumentSchema, seed: int) -> str:
    keys = sorted(schema.document_types)
    return keys[seed % len(keys)]


def illustrative_values(schema: DocumentSchema, doc_type: str, seed: int) -> dict[str, str | None]:
    """Schema-valid fake values for a document the demo does not know."""
    spec = schema.document_types[doc_type]
    labels = ValueSynthesizer(seed=seed % (2**31)).synthesize_document(spec.fields)
    labels = polish(doc_type, labels, random.Random(seed))
    return {f.name: display_value(labels.get(f.name)) for f in spec.fields}


def _confidence(rng: random.Random, capture: str, exact: bool) -> float:
    if exact:
        if capture == "handwritten" and rng.random() < 0.12:
            return round(rng.uniform(0.62, 0.74), 4)  # an occasional shaky read
        low, high = (0.80, 0.96) if capture == "handwritten" else (0.88, 0.99)
        return round(rng.uniform(low, high), 4)
    return round(rng.uniform(0.40, 0.78), 4)


def build_result(
    schema: DocumentSchema,
    doc_type: str,
    values: dict[str, str | None],
    *,
    seed: int,
    exact: bool,
    doc_type_confidence: float,
) -> InferenceResult:
    spec = schema.document_types[doc_type]
    rng = random.Random(seed ^ 0x5DEECE66D)
    fields: list[FieldResult] = []
    for f in spec.fields:
        value = values.get(f.name)
        conf = _confidence(rng, f.capture, exact) if value is not None else 0.0
        fields.append(
            FieldResult(
                name=f.name,
                value="[REDACTED]" if f.sensitive and value is not None else value,
                confidence=conf,
                capture=f.capture,
                sensitive=f.sensitive,
                raw_value=value,
            )
        )
    return InferenceResult(
        doc_type=doc_type, doc_type_confidence=round(doc_type_confidence, 4), fields=fields
    )


def mock_handwritten_fields(
    image: Image.Image, field_names: list[str], doc_type: str
) -> dict[str, tuple[str | None, float]]:
    """Stand-in for `inference.ocr.extract_handwritten_fields` (Tesseract/Ollama/Gemini/Anthropic).

    Same return shape; never opens a socket or runs an OCR binary.
    """
    known = recognize(image)
    seed = image_seed(image)
    exact = known is not None and known.doc_type == doc_type
    values = known.fields if exact and known else illustrative_values(_schema(), doc_type, seed)
    rng = random.Random(seed ^ 0xB5297A4D)
    out: dict[str, tuple[str | None, float]] = {}
    for name in field_names:
        value = values.get(name)
        out[name] = (value, _confidence(rng, "handwritten", exact) if value is not None else 0.0)
    return out
