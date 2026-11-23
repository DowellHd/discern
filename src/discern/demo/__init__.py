"""Offline demo: local stand-ins for every external service.

Enabled with DISCERN_OFFLINE_DEMO=true (see `main.py`). Nothing in here runs otherwise.

- `samples`   bundled synthetic documents with known ground truth (`demo-samples/`)
- `mock`      deterministic values + confidences for documents the demo does not know
- `engine`    `DemoInferenceEngine`, a drop-in for the model + OCR + LLM pipeline
- `seed`      builds the SQLite library the UI opens to
- `bootstrap` creates the tables and seeds them on first run
- `router`    `/demo/samples` so the UI can offer "try a sample"
"""
