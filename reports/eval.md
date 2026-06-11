# Discern — Eval Report

**Samples evaluated:** 300

## Results by Capture Type

| Capture | Precision | Recall | F1 | CER | WER | p50 (ms) | p95 (ms) |
|---------|-----------|--------|----|-----|-----|----------|----------|
| handwritten | 1.000 | 0.009 | 0.018 | 1.000 | 1.000 | 2156.9 | 5867.1 |
| checkbox | 0.963 | 0.963 | 0.963 | 0.000 | 0.000 | 2156.9 | 5885.7 |
| **overall** | **0.964** | **0.327** | **0.489** | 1.000 | 1.000 | 2156.9 | 5867.1 |

> Handwritten field values are not extracted by the current model (OCR head not yet
> trained); CER/WER = 1.0 for handwritten fields reflects this gap.
