"""Tests for Milestone 4: InferenceEngine and overlay rendering."""

from __future__ import annotations

import pytest
from PIL import Image

from discern.data.generator import DocumentGenerator
from discern.inference.engine import InferenceEngine, strip_exif
from discern.inference.overlay import draw_overlay


@pytest.fixture(scope="module")
def engine(schema):
    return InferenceEngine(schema=schema, checkpoint_path=None)


@pytest.fixture(scope="module")
def sample_image(schema):
    gen = DocumentGenerator(schema.document_types, seed=99)
    return gen.generate("connection_card").image


# ---------------------------------------------------------------------------
# Engine basics
# ---------------------------------------------------------------------------


def test_engine_creates_without_checkpoint(schema) -> None:
    eng = InferenceEngine(schema=schema, checkpoint_path=None)
    assert eng.model is not None
    assert eng._checkpoint_loaded is False


def test_predict_returns_inference_result(engine, sample_image, schema) -> None:
    result = engine.predict(sample_image)
    assert result.doc_type in schema.document_types
    assert 0.0 <= result.doc_type_confidence <= 1.0


def test_predict_fields_match_schema(engine, sample_image, schema) -> None:
    result = engine.predict(sample_image)
    spec = schema.document_types[result.doc_type]
    schema_names = {f.name for f in spec.fields}
    result_names = {f.name for f in result.fields}
    assert result_names == schema_names


def test_predict_field_confidence_range(engine, sample_image) -> None:
    result = engine.predict(sample_image)
    for f in result.fields:
        assert 0.0 <= f.confidence <= 1.0, f"Bad confidence for {f.name}"


def test_predict_sensitive_field_masked(engine, schema) -> None:
    gen = DocumentGenerator(schema.document_types, seed=77)
    img = gen.generate("prayer_request").image
    result = engine.predict(img)
    sensitive = [f for f in result.fields if f.sensitive]
    for f in sensitive:
        assert f.value in (None, "[REDACTED]"), f"Sensitive field {f.name} not masked"


def test_handwritten_fields_have_no_value(engine, sample_image) -> None:
    result = engine.predict(sample_image)
    hw = [f for f in result.fields if f.capture == "handwritten"]
    for f in hw:
        assert f.value is None
        assert f.confidence == 0.0


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_validate_upload_rejects_large_file(engine) -> None:
    with pytest.raises(ValueError, match="too large"):
        engine.validate_upload(b"x" * (21 * 1024 * 1024), "image/png")


def test_validate_upload_rejects_bad_type(engine) -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        engine.validate_upload(b"data", "application/zip")


def test_validate_upload_accepts_valid(engine) -> None:
    engine.validate_upload(b"x" * 1000, "image/jpeg")  # no exception


# ---------------------------------------------------------------------------
# EXIF stripping
# ---------------------------------------------------------------------------


def test_strip_exif_returns_image() -> None:
    img = Image.new("RGB", (50, 50), color=(128, 128, 128))
    result = strip_exif(img)
    assert isinstance(result, Image.Image)
    assert result.size == (50, 50)


# ---------------------------------------------------------------------------
# Overlay
# ---------------------------------------------------------------------------


def test_overlay_wider_than_original(engine, sample_image) -> None:
    result = engine.predict(sample_image)
    overlay = draw_overlay(sample_image, result)
    assert overlay.width > sample_image.width


def test_overlay_is_rgb(engine, sample_image) -> None:
    result = engine.predict(sample_image)
    overlay = draw_overlay(sample_image, result)
    assert overlay.mode == "RGB"
