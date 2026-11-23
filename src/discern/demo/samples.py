"""Bundled demo documents and recognition of them.

`demo-samples/` holds synthetic documents rendered by `DocumentGenerator` plus an `index.json`
of their ground-truth field values. When one of them is uploaded, the demo engine recognises
it by image similarity and returns the true values — so the demo reads those documents
correctly without any model or OCR. Everything is synthetic; no real personal data.

Regenerate with `python -m discern.demo.samples` (deterministic for a given seed).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import structlog
from PIL import Image

from discern.config import DEMO_SAMPLES_DIR, load_document_schema
from discern.data.generator import DocumentGenerator
from discern.data.schema import DocumentSchema, parse_document_schema
from discern.demo.realism import polish

log = structlog.get_logger()

SAMPLE_SEED = 7
SAMPLES_PER_TYPE = 2
_THUMB = 96
# Mean absolute pixel difference (0-255) below which two thumbnails are the same document.
# Measured on the bundled set: the same document recompressed (JPEG q40-95) or resized differs
# by < 0.5; the closest pair of *different* samples differs by 1.6. The threshold sits between.
_MATCH_MAX_MAD = 1.0

INDEX_NAME = "index.json"


@dataclass(frozen=True)
class Sample:
    file: str
    doc_type: str
    fields: dict[str, str | None]
    label: str


def display_value(value: Any) -> str | None:
    """Render a ground-truth label the way the real engine reports field values."""
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else "none"
    if isinstance(value, bool):
        return str(value)
    return str(value)


def thumbnail(image: Image.Image) -> np.ndarray:
    """Small grayscale fingerprint used to recognise a bundled sample."""
    gray = image.convert("L").resize((_THUMB, _THUMB), Image.Resampling.LANCZOS)
    return np.asarray(gray, dtype=np.float32)


def _schema() -> DocumentSchema:
    return parse_document_schema(load_document_schema())


def generate_samples(
    out_dir: Path = DEMO_SAMPLES_DIR, per_type: int = SAMPLES_PER_TYPE, seed: int = SAMPLE_SEED
) -> list[Sample]:
    """Render the bundled sample documents and write `index.json`."""
    schema = _schema()
    gen = DocumentGenerator(schema.document_types, seed=seed, label_hook=polish)
    out_dir.mkdir(parents=True, exist_ok=True)
    samples: list[Sample] = []
    for doc_type, spec in schema.document_types.items():
        for n in range(1, per_type + 1):
            sample = gen.generate(doc_type)
            fname = f"{doc_type}_{n}.jpg"
            sample.image.convert("RGB").save(out_dir / fname, format="JPEG", quality=88)
            fields = {f.name: display_value(sample.labels.get(f.name)) for f in spec.fields}
            samples.append(
                Sample(
                    file=fname,
                    doc_type=doc_type,
                    fields=fields,
                    label=f"{spec.label} {n}" if spec.label else f"{doc_type} {n}",
                )
            )
    index = [
        {"file": s.file, "doc_type": s.doc_type, "label": s.label, "fields": s.fields}
        for s in samples
    ]
    (out_dir / INDEX_NAME).write_text(json.dumps(index, indent=2) + "\n")
    log.info("demo_samples_generated", count=len(samples), directory=str(out_dir))
    _load.cache_clear()
    return samples


@lru_cache(maxsize=1)
def _load() -> tuple[list[Sample], list[np.ndarray]]:
    index_path = DEMO_SAMPLES_DIR / INDEX_NAME
    if not index_path.exists():
        return [], []
    samples: list[Sample] = []
    thumbs: list[np.ndarray] = []
    for row in json.loads(index_path.read_text()):
        path = DEMO_SAMPLES_DIR / row["file"]
        if not path.exists():
            continue
        samples.append(Sample(row["file"], row["doc_type"], row["fields"], row["label"]))
        with Image.open(path) as im:
            thumbs.append(thumbnail(im))
    return samples, thumbs


def list_samples() -> list[Sample]:
    return list(_load()[0])


def sample_path(name: str) -> Path | None:
    """Path of a bundled sample by file name (no directory traversal)."""
    if name != Path(name).name:
        return None
    path = DEMO_SAMPLES_DIR / name
    return path if path.exists() and any(s.file == name for s in list_samples()) else None


def recognize(image: Image.Image) -> Sample | None:
    """Return the bundled sample this image is (a copy of), or None."""
    samples, thumbs = _load()
    if not samples:
        return None
    probe = thumbnail(image)
    dists = [float(np.abs(probe - t).mean()) for t in thumbs]
    best = int(np.argmin(dists))
    return samples[best] if dists[best] <= _MATCH_MAX_MAD else None


if __name__ == "__main__":
    made = generate_samples()
    print(f"Wrote {len(made)} sample documents to {DEMO_SAMPLES_DIR}")
