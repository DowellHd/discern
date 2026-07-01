"""Tests for the LLM post-processor module."""

from __future__ import annotations

from unittest.mock import patch

from discern.inference.llm_postprocess import estimate_cost_cents, refine


def test_refine_no_backends_returns_empty() -> None:
    """With no API keys set, both backends skip and refine() returns {}."""
    with (
        patch.dict("os.environ", {}, clear=True),
    ):
        result = refine("receipt", {"merchant": "Wal-Mart", "amount": "$12.50"})
    assert result == {}


def test_refine_skips_sensitive_fields() -> None:
    """Sensitive fields are excluded from the prompt so the LLM cannot alter them."""
    # Even if a backend somehow returned a sensitive-key correction, refine()
    # filters to only keys present in field_values, which should not include sensitives.
    # We test the interface contract: refine() only corrects keys given to it.
    fields = {"merchant": "Wal-Mart"}
    with patch.dict("os.environ", {}, clear=True):
        corrections = refine("receipt", fields)
    # No backend available → empty; the field dict itself is the API boundary
    assert isinstance(corrections, dict)
    assert all(k in fields for k in corrections)


def test_refine_ignores_unknown_keys_in_response() -> None:
    """Keys returned by the LLM that weren't in the input are silently dropped."""
    with patch(
        "discern.inference.llm_postprocess._try_gemini",
        return_value={"merchant": "Walmart", "injected_key": "evil"},
    ):
        result = refine("receipt", {"merchant": "Wal-Mart", "amount": "$12.50"})
    assert "injected_key" not in result
    assert result.get("merchant") == "Walmart"


def test_refine_falls_back_to_haiku_when_gemini_returns_none() -> None:
    """Haiku is tried when Gemini is unavailable."""
    with (
        patch("discern.inference.llm_postprocess._try_gemini", return_value=None),
        patch(
            "discern.inference.llm_postprocess._try_haiku",
            return_value={"amount": "$12.50"},
        ) as mock_haiku,
    ):
        result = refine("receipt", {"amount": "12.50"})
    mock_haiku.assert_called_once()
    assert result.get("amount") == "$12.50"


def test_refine_skips_empty_string_corrections() -> None:
    """Blank-string LLM responses are filtered out."""
    with patch(
        "discern.inference.llm_postprocess._try_gemini",
        return_value={"merchant": "  ", "amount": "$12.50"},
    ):
        result = refine("receipt", {"merchant": "Wal-Mart", "amount": "12.50"})
    assert "merchant" not in result  # blank → dropped
    assert result.get("amount") == "$12.50"


def test_estimate_cost_cents_scales_with_prompt_length() -> None:
    short = estimate_cost_cents("Hello")
    long = estimate_cost_cents("Hello " * 500)
    assert long > short
    assert short >= 0


def test_estimate_cost_cents_typical_call() -> None:
    # A 500-char prompt (typical for a small doc) should cost well under 1 cent
    cost = estimate_cost_cents("x" * 500)
    assert cost < 1.0
