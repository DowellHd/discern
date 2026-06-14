# Discern — Eval Report

**Samples evaluated:** 300

## Results by Capture Type

| Capture | Precision | Recall | F1 | CER | WER | p50 (ms) | p95 (ms) |
|---------|-----------|--------|----|-----|-----|----------|----------|
| handwritten | 1.000 | 0.009 | 0.018 | 1.000 | 1.000 | 499.1 | 680.0 |
| checkbox | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 499.2 | 680.0 |
| **overall** | **1.000** | **0.339** | **0.507** | 1.000 | 1.000 | 499.1 | 680.0 |

> Handwritten field values are not extracted by the current model (OCR head not yet
> trained); CER/WER = 1.0 for handwritten fields reflects this gap.
