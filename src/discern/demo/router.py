"""Demo-only routes: let the UI offer the bundled sample documents ("try a sample")."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from discern.demo.samples import list_samples, sample_path

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/samples")
def samples() -> list[dict[str, str]]:
    """The bundled synthetic documents. Uploading one returns its exact ground-truth fields."""
    return [
        {
            "file": s.file,
            "label": s.label,
            "doc_type": s.doc_type,
            "url": f"/demo/samples/{s.file}",
        }
        for s in list_samples()
    ]


@router.get("/samples/{name}")
def sample_image(name: str) -> FileResponse:
    path = sample_path(name)
    if path is None:
        raise HTTPException(status_code=404, detail="Sample not found")
    return FileResponse(path, media_type="image/jpeg")
