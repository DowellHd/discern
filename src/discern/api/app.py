"""FastAPI application: /extract, /search, /health, and overlay endpoints."""

from __future__ import annotations

import io
import uuid
from pathlib import Path

import structlog
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from PIL import Image
from sqlalchemy.orm import Session

from discern.api.deps import get_db, get_inference_engine
from discern.api.schemas import ExtractionOut, FieldOut, HealthOut, SearchResponse
from discern.config import settings
from discern.db.models import Document, ExtractionField
from discern.inference.engine import InferenceEngine
from discern.inference.overlay import draw_overlay

log = structlog.get_logger()

app = FastAPI(
    title="Discern",
    description="Extracts structured data from paper church records.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _save_image(img: Image.Image, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, format="PNG")


def _doc_to_out(doc: Document, request_base: str = "") -> ExtractionOut:
    fields = [
        FieldOut(
            name=f.field_name,
            value=f.field_value,
            confidence=f.confidence,
            capture=f.capture_type,
            sensitive=False,
        )
        for f in doc.fields
    ]
    return ExtractionOut(
        id=doc.id,
        doc_type=doc.doc_type,
        doc_type_confidence=doc.doc_type_confidence,
        fields=fields,
        overlay_url=f"{request_base}/extractions/{doc.id}/overlay",
        created_at=doc.created_at,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthOut, tags=["meta"])
def health(engine: InferenceEngine = Depends(get_inference_engine)) -> HealthOut:
    return HealthOut(status="ok", model_loaded=engine._checkpoint_loaded)


@app.post("/extract", response_model=ExtractionOut, tags=["extraction"])
def extract(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    engine: InferenceEngine = Depends(get_inference_engine),
) -> ExtractionOut:
    raw = file.file.read()
    content_type = file.content_type or "application/octet-stream"

    try:
        engine.validate_upload(raw, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    image = Image.open(io.BytesIO(raw))

    result = engine.predict(image)
    log.info(
        "extract",
        doc_type=result.doc_type,
        confidence=result.doc_type_confidence,
        filename=file.filename,
    )

    doc_id = str(uuid.uuid4())
    upload_dir = settings.data_dir / "uploads" / doc_id

    orig_path = upload_dir / "original.png"
    overlay_path = upload_dir / "overlay.png"

    _save_image(image.convert("RGB"), orig_path)
    overlay_img = draw_overlay(image.convert("RGB"), result)
    _save_image(overlay_img, overlay_path)

    doc = Document(
        id=doc_id,
        original_filename=file.filename or "upload.png",
        doc_type=result.doc_type,
        doc_type_confidence=result.doc_type_confidence,
        image_path=str(orig_path),
        overlay_path=str(overlay_path),
    )
    for fr in result.fields:
        doc.fields.append(
            ExtractionField(
                document_id=doc_id,
                field_name=fr.name,
                field_value=fr.value,
                confidence=fr.confidence,
                capture_type=fr.capture,
            )
        )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    return _doc_to_out(doc)


@app.get("/extractions/{doc_id}/overlay", tags=["extraction"])
def get_overlay(doc_id: str, db: Session = Depends(get_db)) -> Response:
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Extraction not found")
    overlay_path = Path(doc.overlay_path)
    if not overlay_path.exists():
        raise HTTPException(status_code=404, detail="Overlay image not found on disk")
    return Response(content=overlay_path.read_bytes(), media_type="image/png")


@app.get("/search", response_model=SearchResponse, tags=["search"])
def search(
    q: str | None = Query(default=None, description="Full-text search over field values"),
    doc_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> SearchResponse:
    query = db.query(Document)

    if doc_type:
        query = query.filter(Document.doc_type == doc_type)

    if q:
        query = query.join(Document.fields).filter(ExtractionField.field_value.ilike(f"%{q}%"))

    total = query.count()
    docs = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
    return SearchResponse(total=total, results=[_doc_to_out(d) for d in docs])
