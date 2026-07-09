"""FastAPI dependency providers: DB session and inference engine singleton."""

from __future__ import annotations

from collections.abc import Generator

import structlog
from sqlalchemy.orm import Session

from discern.config import settings
from discern.data.schema import DocumentSchema
from discern.db.session import SessionLocal
from discern.inference.engine import InferenceEngine

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Document schema singleton (parsed from YAML only — no torch/model load, so
# routes that only need field metadata, e.g. sensitivity, stay cheap).
# ---------------------------------------------------------------------------
_schema: DocumentSchema | None = None


def get_document_schema() -> DocumentSchema:
    global _schema
    if _schema is None:
        from discern.config import load_document_schema
        from discern.data.schema import parse_document_schema

        _schema = parse_document_schema(load_document_schema())
    return _schema


# ---------------------------------------------------------------------------
# Inference engine singleton (initialized once on first use)
# ---------------------------------------------------------------------------
_engine: InferenceEngine | None = None


def get_inference_engine() -> InferenceEngine:
    global _engine
    if _engine is None:
        ckpt = settings.checkpoints_dir / "best.pt"
        _engine = InferenceEngine(schema=get_document_schema(), checkpoint_path=ckpt)
    return _engine


def reset_inference_engine(engine: InferenceEngine | None = None) -> None:
    """Replace singleton — used in tests."""
    global _engine
    _engine = engine


# ---------------------------------------------------------------------------
# DB session dependency
# ---------------------------------------------------------------------------


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
