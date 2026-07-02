"""Compute field-level P/R/F1, OCR CER/WER, and latency — broken down by capture type."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from discern.data.generator import DocumentGenerator
from discern.data.schema import DocumentSchema
from discern.inference.engine import InferenceEngine

log = structlog.get_logger()


@dataclass
class CaptureMetrics:
    capture: str
    total: int = 0
    tp: int = 0
    fp: int = 0
    fn: int = 0
    cer_sum: float = 0.0
    wer_sum: float = 0.0
    ocr_count: int = 0
    latencies_ms: list[float] = field(default_factory=list)

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def cer(self) -> float:
        return self.cer_sum / self.ocr_count if self.ocr_count > 0 else 0.0

    @property
    def wer(self) -> float:
        return self.wer_sum / self.ocr_count if self.ocr_count > 0 else 0.0

    @property
    def p50_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        return s[len(s) // 2]

    @property
    def p95_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        return s[int(len(s) * 0.95)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "capture": self.capture,
            "n_fields": self.total,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "cer": round(self.cer, 4),
            "wer": round(self.wer, 4),
            "p50_latency_ms": round(self.p50_ms, 1),
            "p95_latency_ms": round(self.p95_ms, 1),
        }


@dataclass
class EvalResult:
    n_samples: int
    by_capture: dict[str, CaptureMetrics]
    by_doc_type: dict[str, CaptureMetrics]
    overall: CaptureMetrics

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_samples": self.n_samples,
            "overall": self.overall.to_dict(),
            "by_capture": {k: v.to_dict() for k, v in self.by_capture.items()},
            "by_doc_type": {k: v.to_dict() for k, v in self.by_doc_type.items()},
        }


def _char_error_rate(pred: str, ref: str) -> float:
    """Levenshtein distance / len(ref). Returns 0 if ref is empty."""
    if not ref:
        return 0.0
    pred, ref = pred.lower(), ref.lower()
    m, n = len(ref), len(pred)
    dp = list(range(m + 1))
    for j in range(1, n + 1):
        prev = dp[0]
        dp[0] = j
        for i in range(1, m + 1):
            temp = dp[i]
            if ref[i - 1] == pred[j - 1]:
                dp[i] = prev
            else:
                dp[i] = 1 + min(prev, dp[i], dp[i - 1])
            prev = temp
    return dp[m] / m


def _word_error_rate(pred: str, ref: str) -> float:
    ref_words = ref.lower().split()
    pred_words = pred.lower().split()
    if not ref_words:
        return 0.0
    m, n = len(ref_words), len(pred_words)
    dp = list(range(m + 1))
    for j in range(1, n + 1):
        prev = dp[0]
        dp[0] = j
        for i in range(1, m + 1):
            temp = dp[i]
            dp[i] = (
                prev if ref_words[i - 1] == pred_words[j - 1] else 1 + min(prev, dp[i], dp[i - 1])
            )
            prev = temp
    return dp[m] / m


def _normalize_value(value: Any, value_type: str) -> str:
    """Normalize a label value to a comparable string."""
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(sorted(str(v) for v in value))
    if isinstance(value, bool):
        return str(value)
    return str(value).strip()


def _predicted_matches_label(predicted: str | None, label_str: str, value_type: str) -> bool:
    """Check if predicted value matches ground-truth label string."""
    if predicted is None:
        return not label_str
    pred_norm = predicted.strip().lower()
    label_norm = label_str.strip().lower()
    if value_type == "multiselect":
        pred_set = {s.strip() for s in pred_norm.split(",") if s.strip()}
        label_set = {s.strip() for s in label_norm.split(",") if s.strip()}
        return pred_set == label_set
    if value_type == "bool":
        return pred_norm.startswith(label_norm[0]) if label_norm else pred_norm == label_norm
    return pred_norm == label_norm


def evaluate_checkpoint(
    engine: InferenceEngine,
    schema: DocumentSchema,
    n_samples: int = 200,
    seed: int = 999,
) -> EvalResult:
    """Evaluate engine on n_samples synthetic images from each doc type."""
    gen = DocumentGenerator(schema.document_types, seed=seed)
    doc_types = list(schema.document_types.keys())

    by_capture: dict[str, CaptureMetrics] = {}
    by_doc_type: dict[str, CaptureMetrics] = {}
    overall = CaptureMetrics(capture="overall")

    for _ in range(n_samples):
        for doc_type in doc_types:
            sample = gen.generate(doc_type)
            spec = schema.document_types[doc_type]

            if doc_type not in by_doc_type:
                by_doc_type[doc_type] = CaptureMetrics(capture=doc_type)
            dt_cm = by_doc_type[doc_type]

            t0 = time.perf_counter()
            result = engine.predict(sample.image)
            latency_ms = (time.perf_counter() - t0) * 1000

            predicted_map = {f.name: f.value for f in result.fields}

            for field_spec in spec.fields:
                capture = field_spec.capture
                if capture not in by_capture:
                    by_capture[capture] = CaptureMetrics(capture=capture)
                cm = by_capture[capture]

                raw_label = sample.labels.get(field_spec.name)
                label_str = _normalize_value(raw_label, field_spec.value_type)
                pred_val = predicted_map.get(field_spec.name)
                # Sensitive fields may be redacted — skip
                if field_spec.sensitive and pred_val == "[REDACTED]":
                    continue

                pred_str = pred_val if pred_val is not None else ""
                correct = _predicted_matches_label(pred_str, label_str, field_spec.value_type)

                for bucket in (cm, dt_cm, overall):
                    bucket.total += 1
                    bucket.latencies_ms.append(latency_ms)
                    if correct:
                        bucket.tp += 1
                    else:
                        if pred_str:
                            bucket.fp += 1
                        if label_str:
                            bucket.fn += 1

                if field_spec.capture == "handwritten" and label_str:
                    cer = _char_error_rate(pred_str, label_str)
                    wer = _word_error_rate(pred_str, label_str)
                    for bucket in (cm, dt_cm, overall):
                        bucket.cer_sum += cer
                        bucket.wer_sum += wer
                        bucket.ocr_count += 1

    return EvalResult(
        n_samples=n_samples * len(doc_types),
        by_capture=by_capture,
        by_doc_type=by_doc_type,
        overall=overall,
    )
