"""Model definitions: backbone, task heads, and the assembled FieldExtractor."""

from discern.models.extractor import (
    CATEGORY_OPTIONS,
    DOC_TYPES,
    INTERESTS_OPTIONS,
    VISIT_TYPE_OPTIONS,
    FieldExtractor,
)

__all__ = [
    "FieldExtractor",
    "DOC_TYPES",
    "VISIT_TYPE_OPTIONS",
    "INTERESTS_OPTIONS",
    "CATEGORY_OPTIONS",
]
