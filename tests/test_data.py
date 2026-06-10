"""Tests for Milestone 2: schema parsing, value synthesis, image generation, preprocessing."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from discern.config import load_document_schema
from discern.data.generator import DocumentGenerator
from discern.data.preprocess import denoise, deskew, normalize, preprocess
from discern.data.schema import FieldSpec, parse_document_schema
from discern.data.synthesizer import ValueSynthesizer

# ---------------------------------------------------------------------------
# Schema parsing
# ---------------------------------------------------------------------------


def test_parse_document_schema_types() -> None:
    raw = load_document_schema()
    schema = parse_document_schema(raw)
    assert "connection_card" in schema.document_types
    assert "prayer_request" in schema.document_types
    assert "bulletin" in schema.region_types


def test_field_spec_required_flag() -> None:
    raw = load_document_schema()
    schema = parse_document_schema(raw)
    fields = {f.name: f for f in schema.document_types["connection_card"].fields}
    assert fields["full_name"].required is True
    assert fields["notes"].required is False


def test_field_spec_sensitive_flag() -> None:
    raw = load_document_schema()
    schema = parse_document_schema(raw)
    fields = {f.name: f for f in schema.document_types["prayer_request"].fields}
    assert fields["request_text"].sensitive is True


def test_region_blocks_parsed() -> None:
    raw = load_document_schema()
    schema = parse_document_schema(raw)
    blocks = schema.region_types["bulletin"].blocks
    assert "header" in blocks
    assert len(blocks) == 6


def test_field_spec_options_preserved() -> None:
    raw = load_document_schema()
    schema = parse_document_schema(raw)
    fields = {f.name: f for f in schema.document_types["connection_card"].fields}
    assert fields["visit_type"].options == ["first_time", "returning", "regular"]


# ---------------------------------------------------------------------------
# Value synthesizer
# ---------------------------------------------------------------------------


@pytest.fixture()
def synth() -> ValueSynthesizer:
    return ValueSynthesizer(seed=0)


def test_synthesize_string(synth: ValueSynthesizer) -> None:
    f = FieldSpec(name="x", value_type="string", capture="handwritten")
    val = synth.synthesize(f)
    assert isinstance(val, str) and len(val) > 0


def test_synthesize_email(synth: ValueSynthesizer) -> None:
    f = FieldSpec(name="x", value_type="email", capture="handwritten")
    val = synth.synthesize(f)
    assert isinstance(val, str) and "@" in val


def test_synthesize_phone(synth: ValueSynthesizer) -> None:
    f = FieldSpec(name="x", value_type="phone", capture="handwritten")
    val = synth.synthesize(f)
    assert isinstance(val, str) and len(val) >= 10


def test_synthesize_date(synth: ValueSynthesizer) -> None:
    f = FieldSpec(name="x", value_type="date", capture="handwritten")
    val = synth.synthesize(f)
    assert isinstance(val, str) and "/" in val


def test_synthesize_enum(synth: ValueSynthesizer) -> None:
    opts = ["a", "b", "c"]
    f = FieldSpec(name="x", value_type="enum", capture="checkbox", options=opts)
    val = synth.synthesize(f)
    assert val in opts


def test_synthesize_multiselect(synth: ValueSynthesizer) -> None:
    opts = ["a", "b", "c", "d"]
    f = FieldSpec(name="x", value_type="multiselect", capture="checkbox", options=opts)
    val = synth.synthesize(f)
    assert isinstance(val, list) and len(val) >= 1
    assert all(v in opts for v in val)


def test_synthesize_bool(synth: ValueSynthesizer) -> None:
    f = FieldSpec(name="x", value_type="bool", capture="checkbox")
    val = synth.synthesize(f)
    assert isinstance(val, bool)


def test_synthesize_freetext(synth: ValueSynthesizer) -> None:
    f = FieldSpec(name="x", value_type="freetext", capture="handwritten")
    val = synth.synthesize(f)
    assert isinstance(val, str) and len(val.split()) >= 5


def test_nullable_can_return_none() -> None:
    f = FieldSpec(name="x", value_type="string", capture="handwritten", nullable=True)
    results = [ValueSynthesizer(seed=i).synthesize(f) for i in range(50)]
    assert any(v is None for v in results), "Expected at least one None for nullable field"


def test_synthesize_document_has_all_fields(synth: ValueSynthesizer) -> None:
    raw = load_document_schema()
    schema = parse_document_schema(raw)
    fields = schema.document_types["connection_card"].fields
    doc = synth.synthesize_document(fields)
    for field in fields:
        assert field.name in doc


def test_synthesis_is_reproducible() -> None:
    raw = load_document_schema()
    schema = parse_document_schema(raw)
    fields = schema.document_types["connection_card"].fields
    doc_a = ValueSynthesizer(seed=7).synthesize_document(fields)
    doc_b = ValueSynthesizer(seed=7).synthesize_document(fields)
    assert doc_a == doc_b


# ---------------------------------------------------------------------------
# Image generator
# ---------------------------------------------------------------------------


@pytest.fixture()
def gen() -> DocumentGenerator:
    raw = load_document_schema()
    schema = parse_document_schema(raw)
    return DocumentGenerator(schema.document_types, seed=42)


def test_generate_connection_card(gen: DocumentGenerator) -> None:
    sample = gen.generate("connection_card")
    assert sample.doc_type == "connection_card"
    assert isinstance(sample.image, Image.Image)
    assert sample.image.width > 0 and sample.image.height > 0


def test_generate_prayer_request(gen: DocumentGenerator) -> None:
    sample = gen.generate("prayer_request")
    assert isinstance(sample.image, Image.Image)
    assert sample.doc_type == "prayer_request"


def test_generate_unknown_type_raises(gen: DocumentGenerator) -> None:
    with pytest.raises(ValueError, match="Unknown doc type"):
        gen.generate("nonexistent_type")


def test_labels_contain_all_fields(gen: DocumentGenerator) -> None:
    raw = load_document_schema()
    schema = parse_document_schema(raw)
    field_names = {f.name for f in schema.document_types["connection_card"].fields}
    sample = gen.generate("connection_card")
    assert field_names == set(sample.labels.keys())


def test_save_writes_png_and_json(gen: DocumentGenerator, tmp_path: Path) -> None:
    sample = gen.generate("connection_card")
    img_path, lbl_path = gen.save(sample, tmp_path)
    assert img_path.exists() and img_path.suffix == ".png"
    assert lbl_path.exists() and lbl_path.suffix == ".json"
    data = json.loads(lbl_path.read_text())
    assert data["doc_type"] == "connection_card"
    assert "fields" in data


def test_save_creates_doc_type_subdirectory(gen: DocumentGenerator, tmp_path: Path) -> None:
    sample = gen.generate("prayer_request")
    img_path, _ = gen.save(sample, tmp_path)
    assert img_path.parent.name == "prayer_request"


def test_generated_image_is_rgb(gen: DocumentGenerator) -> None:
    sample = gen.generate("connection_card")
    assert sample.image.mode == "RGB"


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------


@pytest.fixture()
def blank_img() -> Image.Image:
    return Image.new("RGB", (400, 300), color=(240, 240, 240))


def test_deskew_returns_same_size(blank_img: Image.Image) -> None:
    result = deskew(blank_img)
    assert isinstance(result, Image.Image)
    assert result.size == blank_img.size


def test_denoise_returns_image(blank_img: Image.Image) -> None:
    result = denoise(blank_img)
    assert isinstance(result, Image.Image)
    assert result.size == blank_img.size


def test_normalize_returns_grayscale(blank_img: Image.Image) -> None:
    result = normalize(blank_img)
    assert isinstance(result, Image.Image)
    assert result.mode == "L"


def test_preprocess_pipeline(blank_img: Image.Image) -> None:
    result = preprocess(blank_img)
    assert isinstance(result, Image.Image)
    assert result.mode == "L"


def test_preprocess_on_generated_image(gen: DocumentGenerator) -> None:
    sample = gen.generate("connection_card")
    processed = preprocess(sample.image)
    assert isinstance(processed, Image.Image)
    arr = np.array(processed)
    assert arr.ndim == 2
    assert arr.shape[0] > 0 and arr.shape[1] > 0


def test_preprocess_pixel_range(blank_img: Image.Image) -> None:
    result = preprocess(blank_img)
    arr = np.array(result)
    assert arr.min() >= 0 and arr.max() <= 255
