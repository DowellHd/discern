"""FastAPI application: /extract, /search, /health, stats, export, and review endpoints."""

from __future__ import annotations

import csv
import io
import uuid
from pathlib import Path

import structlog
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from PIL import Image
from sqlalchemy import func
from sqlalchemy.orm import Session

from discern.api.deps import get_db, get_inference_engine
from discern.api.schemas import (
    BatchOut,
    ExtractionOut,
    FieldOut,
    FieldPatch,
    HealthOut,
    SearchResponse,
    StatsOut,
    StatusPatch,
)
from discern.config import settings
from discern.db.models import Document, ExtractionField
from discern.inference.engine import InferenceEngine, pdf_first_page
from discern.inference.overlay import draw_overlay

log = structlog.get_logger()

_REVIEW_THRESHOLD = 0.70  # doc_type_confidence below this → review queue

app = FastAPI(
    title="Discern",
    description="Extracts structured data from paper church records.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
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
            corrected=f.corrected,
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
        follow_up_status=doc.follow_up_status,
    )


def _process_upload(
    raw: bytes,
    content_type: str,
    filename: str,
    engine: InferenceEngine,
    db: Session,
    doc_type_override: str | None = None,
) -> ExtractionOut:
    """Validate, extract, persist, and return one upload."""
    engine.validate_upload(raw, content_type)

    if content_type == "application/pdf":
        image = pdf_first_page(raw)
    else:
        image = Image.open(io.BytesIO(raw))

    result = engine.predict(image, doc_type_override=doc_type_override)

    doc_id = str(uuid.uuid4())
    upload_dir = settings.data_dir / "uploads" / doc_id
    orig_path = upload_dir / "original.png"
    overlay_path = upload_dir / "overlay.png"

    _save_image(image.convert("RGB"), orig_path)
    _save_image(draw_overlay(image.convert("RGB"), result), overlay_path)

    doc = Document(
        id=doc_id,
        original_filename=filename,
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

    log.info(
        "extract",
        doc_type=result.doc_type,
        confidence=result.doc_type_confidence,
        filename=filename,
    )
    return _doc_to_out(doc)


# ---------------------------------------------------------------------------
# Routes — meta
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthOut, tags=["meta"])
def health(engine: InferenceEngine = Depends(get_inference_engine)) -> HealthOut:
    return HealthOut(status="ok", model_loaded=engine._checkpoint_loaded)


@app.get("/stats", response_model=StatsOut, tags=["meta"])
def stats(db: Session = Depends(get_db)) -> StatsOut:
    total = db.query(func.count(Document.id)).scalar() or 0
    by_type_rows = (
        db.query(Document.doc_type, func.count(Document.id)).group_by(Document.doc_type).all()
    )
    by_doc_type = {row[0]: row[1] for row in by_type_rows}
    avg_conf = db.query(func.avg(Document.doc_type_confidence)).scalar() or 0.0
    review_queue = (
        db.query(func.count(Document.id))
        .filter(Document.doc_type_confidence < _REVIEW_THRESHOLD)
        .scalar()
        or 0
    )
    return StatsOut(
        total_documents=total,
        by_doc_type=by_doc_type,
        avg_confidence=round(float(avg_conf), 4),
        review_queue=review_queue,
    )


# ---------------------------------------------------------------------------
# Routes — extraction
# ---------------------------------------------------------------------------


@app.post("/extract", response_model=ExtractionOut, tags=["extraction"])
def extract(
    file: UploadFile = File(...),
    doc_type: str | None = Form(None),
    db: Session = Depends(get_db),
    engine: InferenceEngine = Depends(get_inference_engine),
) -> ExtractionOut:
    raw = file.file.read()
    content_type = file.content_type or "application/octet-stream"
    try:
        return _process_upload(
            raw,
            content_type,
            file.filename or "upload",
            engine,
            db,
            doc_type_override=doc_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/extract/batch", response_model=BatchOut, tags=["extraction"])
def extract_batch(
    files: list[UploadFile] = File(...),
    doc_type: str | None = Form(None),
    db: Session = Depends(get_db),
    engine: InferenceEngine = Depends(get_inference_engine),
) -> BatchOut:
    results: list[ExtractionOut] = []
    errors: list[str] = []
    for f in files:
        raw = f.file.read()
        content_type = f.content_type or "application/octet-stream"
        try:
            results.append(
                _process_upload(
                    raw,
                    content_type,
                    f.filename or "upload",
                    engine,
                    db,
                    doc_type_override=doc_type,
                )
            )
        except Exception as exc:
            errors.append(f"{f.filename}: {exc}")
    return BatchOut(results=results, errors=errors)


@app.get("/extractions/{doc_id}/overlay", tags=["extraction"])
def get_overlay(doc_id: str, db: Session = Depends(get_db)) -> Response:
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Extraction not found")
    overlay_path = Path(doc.overlay_path)
    if not overlay_path.exists():
        raise HTTPException(status_code=404, detail="Overlay image not found on disk")
    return Response(content=overlay_path.read_bytes(), media_type="image/png")


@app.patch(
    "/extractions/{doc_id}/fields/{field_name}", response_model=ExtractionOut, tags=["extraction"]
)
def patch_field(
    doc_id: str,
    field_name: str,
    body: FieldPatch,
    db: Session = Depends(get_db),
) -> ExtractionOut:
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Extraction not found")
    field = next((f for f in doc.fields if f.field_name == field_name), None)
    if field is None:
        raise HTTPException(status_code=404, detail=f"Field {field_name!r} not found")
    field.field_value = body.value
    field.corrected = True
    db.commit()
    db.refresh(doc)
    return _doc_to_out(doc)


@app.patch("/extractions/{doc_id}/status", response_model=ExtractionOut, tags=["extraction"])
def patch_status(
    doc_id: str,
    body: StatusPatch,
    db: Session = Depends(get_db),
) -> ExtractionOut:
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Extraction not found")
    doc.follow_up_status = body.follow_up_status
    db.commit()
    db.refresh(doc)
    return _doc_to_out(doc)


@app.delete("/extractions/{doc_id}", status_code=204, tags=["extraction"])
def delete_extraction(doc_id: str, db: Session = Depends(get_db)) -> None:
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Extraction not found")
    db.delete(doc)
    db.commit()


# ---------------------------------------------------------------------------
# Routes — search, review, export
# ---------------------------------------------------------------------------


@app.get("/search", response_model=SearchResponse, tags=["search"])
def search(
    q: str | None = Query(default=None, description="Full-text search over field values"),
    doc_type: str | None = Query(default=None),
    follow_up_status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> SearchResponse:
    query = db.query(Document)
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    if follow_up_status:
        query = query.filter(Document.follow_up_status == follow_up_status)
    if q:
        query = query.join(Document.fields).filter(ExtractionField.field_value.ilike(f"%{q}%"))
    total = query.count()
    docs = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
    return SearchResponse(total=total, results=[_doc_to_out(d) for d in docs])


@app.get("/review", response_model=SearchResponse, tags=["search"])
def review_queue(
    threshold: float = Query(default=_REVIEW_THRESHOLD, ge=0.0, le=1.0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Return extractions whose doc-type confidence falls below the review threshold."""
    query = db.query(Document).filter(Document.doc_type_confidence < threshold)
    total = query.count()
    docs = query.order_by(Document.doc_type_confidence.asc()).offset(offset).limit(limit).all()
    return SearchResponse(total=total, results=[_doc_to_out(d) for d in docs])


@app.get("/export.csv", tags=["export"])
def export_csv(
    doc_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream all extractions as a CSV file."""
    query = db.query(Document)
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    docs = query.order_by(Document.created_at.desc()).all()

    def _generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        # Collect all unique field names across results for consistent columns
        all_field_names: list[str] = []
        seen: set[str] = set()
        for doc in docs:
            for f in doc.fields:
                if f.field_name not in seen:
                    all_field_names.append(f.field_name)
                    seen.add(f.field_name)

        writer.writerow(
            ["id", "doc_type", "doc_type_confidence", "follow_up_status", "created_at"]
            + all_field_names
        )
        buf.seek(0)
        yield buf.read()

        for doc in docs:
            buf = io.StringIO()
            writer = csv.writer(buf)
            field_map = {f.field_name: f.field_value for f in doc.fields}
            writer.writerow(
                [
                    doc.id,
                    doc.doc_type,
                    round(doc.doc_type_confidence, 4),
                    doc.follow_up_status or "",
                    doc.created_at.isoformat(),
                ]
                + [field_map.get(name, "") for name in all_field_names]
            )
            buf.seek(0)
            yield buf.read()

    filename = f"discern-export{'-' + doc_type if doc_type else ''}.csv"
    return StreamingResponse(
        _generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
