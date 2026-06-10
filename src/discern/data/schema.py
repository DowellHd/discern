"""Pydantic models for the parsed document schema (configs/documents.yaml)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FieldSpec(BaseModel):
    name: str
    value_type: str
    capture: str
    options: list[str] | None = None
    required: bool = False
    nullable: bool = False
    sensitive: bool = False


class DocTypeSpec(BaseModel):
    description: str
    fields: list[FieldSpec] = Field(default_factory=list)


class RegionTypeSpec(BaseModel):
    description: str
    blocks: list[str] = Field(default_factory=list)


class DocumentSchema(BaseModel):
    document_types: dict[str, DocTypeSpec] = Field(default_factory=dict)
    region_types: dict[str, RegionTypeSpec] = Field(default_factory=dict)


def parse_document_schema(raw: dict[str, Any]) -> DocumentSchema:
    """Convert raw YAML dict to a typed DocumentSchema."""
    return DocumentSchema.model_validate(raw)
