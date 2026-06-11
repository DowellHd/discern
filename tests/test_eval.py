"""Tests for Milestone 5: eval metrics and CER/WER helpers."""

from __future__ import annotations

import pytest

from discern.eval.metrics import (
    CaptureMetrics,
    EvalResult,
    _char_error_rate,
    _normalize_value,
    _predicted_matches_label,
    _word_error_rate,
    evaluate_checkpoint,
)
from discern.inference.engine import InferenceEngine

# ---------------------------------------------------------------------------
# CER / WER helpers
# ---------------------------------------------------------------------------


def test_cer_identical() -> None:
    assert _char_error_rate("hello", "hello") == 0.0


def test_cer_completely_wrong() -> None:
    assert _char_error_rate("xyz", "abc") == 1.0


def test_cer_partial() -> None:
    rate = _char_error_rate("hxllo", "hello")
    assert 0.0 < rate < 1.0


def test_cer_empty_ref() -> None:
    assert _char_error_rate("anything", "") == 0.0


def test_wer_identical() -> None:
    assert _word_error_rate("hello world", "hello world") == 0.0


def test_wer_one_wrong() -> None:
    rate = _word_error_rate("hello planet", "hello world")
    assert rate == pytest.approx(0.5)


def test_wer_empty_ref() -> None:
    assert _word_error_rate("hello", "") == 0.0


# ---------------------------------------------------------------------------
# Normalize + match helpers
# ---------------------------------------------------------------------------


def test_normalize_list() -> None:
    assert _normalize_value(["b", "a"], "multiselect") == "a, b"


def test_normalize_bool() -> None:
    assert _normalize_value(True, "bool") == "True"


def test_normalize_none() -> None:
    assert _normalize_value(None, "string") == ""


def test_match_enum_exact() -> None:
    assert _predicted_matches_label("first_time", "first_time", "enum") is True


def test_match_multiselect_order_independent() -> None:
    assert _predicted_matches_label("prayer, baptism", "baptism, prayer", "multiselect") is True


def test_match_wrong_value() -> None:
    assert _predicted_matches_label("returning", "first_time", "enum") is False


# ---------------------------------------------------------------------------
# CaptureMetrics aggregation
# ---------------------------------------------------------------------------


def test_capture_metrics_precision() -> None:
    cm = CaptureMetrics("checkbox", tp=8, fp=2, fn=0)
    assert cm.precision == pytest.approx(0.8)


def test_capture_metrics_f1() -> None:
    cm = CaptureMetrics("checkbox", tp=4, fp=1, fn=1)
    assert cm.f1 == pytest.approx(2 * 0.8 * 0.8 / (0.8 + 0.8))


def test_capture_metrics_p50_p95() -> None:
    cm = CaptureMetrics("checkbox", latencies_ms=list(range(100)))
    assert cm.p50_ms == 50
    assert cm.p95_ms == 95


def test_capture_metrics_to_dict_keys() -> None:
    cm = CaptureMetrics("handwritten")
    d = cm.to_dict()
    assert {"capture", "precision", "recall", "f1", "cer", "wer"} <= d.keys()


# ---------------------------------------------------------------------------
# Full evaluate_checkpoint smoke test
# ---------------------------------------------------------------------------


def test_evaluate_checkpoint_smoke(schema) -> None:
    engine = InferenceEngine(schema=schema, checkpoint_path=None)
    result = evaluate_checkpoint(engine, schema, n_samples=2, seed=777)

    assert isinstance(result, EvalResult)
    assert result.n_samples == 2 * len(schema.document_types)
    assert "checkbox" in result.by_capture
    assert "handwritten" in result.by_capture
    assert 0.0 <= result.overall.f1 <= 1.0


def test_evaluate_checkpoint_dict_structure(schema) -> None:
    engine = InferenceEngine(schema=schema, checkpoint_path=None)
    result = evaluate_checkpoint(engine, schema, n_samples=1, seed=888)
    d = result.to_dict()

    assert "n_samples" in d
    assert "overall" in d
    assert "by_capture" in d
    for cap_dict in d["by_capture"].values():
        assert "f1" in cap_dict
        assert "p50_latency_ms" in cap_dict
