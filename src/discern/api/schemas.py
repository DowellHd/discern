"""Pydantic request/response models for the API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

FollowUpStatus = Literal["pending", "contacted", "done"] | None


class FieldOut(BaseModel):
    name: str
    value: str | None
    confidence: float
    capture: str
    sensitive: bool
    corrected: bool = False


class ExtractionOut(BaseModel):
    id: str
    doc_type: str
    doc_type_confidence: float
    template_category: str | None = None
    fields: list[FieldOut]
    overlay_url: str
    created_at: datetime
    follow_up_status: FollowUpStatus = None
    llm_refined: bool = False

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    total: int
    results: list[ExtractionOut]


class BatchOut(BaseModel):
    results: list[ExtractionOut]
    errors: list[str]


class HealthOut(BaseModel):
    status: str
    model_loaded: bool


class FieldPatch(BaseModel):
    value: str | None


class StatusPatch(BaseModel):
    follow_up_status: FollowUpStatus


class StatsOut(BaseModel):
    total_documents: int
    by_doc_type: dict[str, int]
    avg_confidence: float
    review_queue: int


class TemplateFieldOut(BaseModel):
    name: str
    value_type: str
    capture: str
    options: list[str] | None = None
    required: bool = False
    nullable: bool = False
    sensitive: bool = False


class ExportHintsOut(BaseModel):
    format: str
    date_field: str | None = None
    amount_field: str | None = None
    title_field: str | None = None


class TemplateOut(BaseModel):
    key: str
    label: str
    category: str
    description: str
    fields: list[TemplateFieldOut]
    export_hints: ExportHintsOut | None = None


class TemplatesOut(BaseModel):
    templates: list[TemplateOut]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Phase 6: Training candidates
# ---------------------------------------------------------------------------


class TrainingCandidate(BaseModel):
    document_id: str
    doc_type: str
    field_name: str
    corrected_value: str | None


class TrainingCandidatesOut(BaseModel):
    total: int
    candidates: list[TrainingCandidate]
