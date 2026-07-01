"""Tests for config loading and document schema."""

from __future__ import annotations

from discern.config import load_document_schema, settings


def test_settings_defaults() -> None:
    assert settings.app_name == "discern"
    assert settings.seed == 42


def test_schema_loads() -> None:
    schema = load_document_schema()
    assert "document_types" in schema
    assert "region_types" in schema


def test_connection_card_required_fields() -> None:
    schema = load_document_schema()
    fields = {f["name"]: f for f in schema["document_types"]["connection_card"]["fields"]}
    assert fields["full_name"]["required"] is True
    assert fields["visit_type"]["required"] is True


def test_sensitive_field_flagged() -> None:
    schema = load_document_schema()
    fields = {f["name"]: f for f in schema["document_types"]["prayer_request"]["fields"]}
    assert fields["request_text"].get("sensitive") is True


def test_bulletin_blocks_present() -> None:
    schema = load_document_schema()
    blocks = schema["region_types"]["bulletin"]["blocks"]
    assert "header" in blocks
    assert "service_date" in blocks


def test_llm_postprocess_default_off() -> None:
    assert settings.llm_postprocess is False


def test_llm_postprocess_budget_default() -> None:
    assert settings.llm_postprocess_budget_cents == 1.0
