# Discern — Eval Report

**Samples evaluated:** 300

## Results by Capture Type

| Capture | Precision | Recall | F1 | CER | WER | p50 (ms) | p95 (ms) |
|---------|-----------|--------|----|-----|-----|----------|----------|
| handwritten | 1.000 | 0.009 | 0.018 | 1.000 | 1.000 | 573.9 | 741.4 |
| checkbox | 0.800 | 0.400 | 0.533 | 0.000 | 0.000 | 573.9 | 741.4 |
| **overall** | **0.807** | **0.139** | **0.238** | 1.000 | 1.000 | 573.9 | 741.4 |

> Handwritten field values are not extracted by the current model (OCR head not yet
> trained); CER/WER = 1.0 for handwritten fields reflects this gap.
