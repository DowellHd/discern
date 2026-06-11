"""Evaluation harness: field-level P/R/F1, OCR CER/WER, and latency by capture type."""

from discern.eval.metrics import EvalResult, evaluate_checkpoint

__all__ = ["EvalResult", "evaluate_checkpoint"]
