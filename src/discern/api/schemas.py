"""Pydantic request/response models for the API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FieldOut(BaseModel):
    name: str
    value: str | None
    confidence: float
    capture: str
    sensitive: bool


class ExtractionOut(BaseModel):
    id: str
    doc_type: str
    doc_type_confidence: float
    fields: list[FieldOut]
    overlay_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    total: int
    results: list[ExtractionOut]


class HealthOut(BaseModel):
    status: str
    model_loaded: bool
