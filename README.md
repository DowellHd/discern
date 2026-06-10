# Discern

> Computer vision that turns paper records into structured, searchable data.

Discern is a document-intelligence pipeline that processes photos and scans of paper church records — connection cards, prayer request cards, and weekly bulletins — and extracts structured, searchable data. The document domain is fully swappable via a single YAML config.

---

## Architecture

```
src/discern/
  data/        synthetic generator, ingest, preprocessing (deskew, denoise)
  models/      layout/region detection + OCR; fine-tunable field-type head
  training/    train loop, checkpointing, experiment logging
  inference/   load model, run on image, return overlay + structured JSON
  eval/        field-level P/R/F1 · OCR CER/WER · latency by capture type
  api/         FastAPI: /extract · /search · /health
  db/          Postgres models + Alembic migrations
scripts/       generate_data.py · train.py · evaluate.py
frontend/      Next.js: drag-drop upload · overlay · editable fields · search
configs/       documents.yaml (schema contract) · run configs
docker/        Dockerfile(s) · docker-compose (api + db)
```

The file `configs/documents.yaml` is the **single source of truth**. The synthetic generator, model field classes, eval harness, DB columns, and UI all derive from it. Retargeting to a new document domain means swapping that one file.

---

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
make verify          # lint + typecheck + tests + eval smoke test
```

---

## Verification Steps

These must all pass before any push:

```bash
ruff check . && ruff format --check .   # formatting / lint
mypy src                                # type check
pytest -q                               # tests
python -m scripts.evaluate             # eval smoke test / metrics
```

---

## Performance Notes

- **Image preprocessing** (deskew, denoise) is the dominant CPU cost at ingest; batching and async I/O are used in the API.
- **Batch inference** via `torch.no_grad()` + DataLoader with `num_workers` for throughput.
- Preprocessing runs on separate threads from the model forward pass.

## Security Notes

- Upload endpoint validates file type (allowlist: JPEG, PNG, TIFF, PDF) and enforces a size limit (default 20 MB).
- EXIF data is stripped on ingest — no GPS or device metadata is stored.
- Fields marked `sensitive: true` in `configs/documents.yaml` are masked in all logs and the metrics report.
- No PII is ever committed to the repo; all training/eval data is synthetic.

---

## Deployment

### Prerequisites

- A Vercel account (frontend)
- A Render account (API + Postgres)
- DNS access to `dowellstandley.com` — you will add one CNAME record

### Frontend → Vercel

1. Push the repo to GitHub.
2. In Vercel, click **Add New Project** → import this repo.
3. Set **Root Directory** to `frontend`.
4. Add env vars: `NEXT_PUBLIC_API_URL=https://<your-render-service>.onrender.com`.
5. Deploy. Vercel gives you a `*.vercel.app` URL.
6. In Vercel **Domains**, add `discern.dowellstandley.com`.
7. In your DNS provider for `dowellstandley.com`, add:
   ```
   CNAME  discern  cname.vercel-dns.com.
   ```

### API → Render

1. In Render, click **New Web Service** → connect this repo.
2. Set **Root Directory** to `.` (repo root).
3. **Build command:** `pip install -e .`
4. **Start command:** `uvicorn discern.api.main:app --host 0.0.0.0 --port $PORT`
5. Add a **Postgres** database on Render; copy the internal `DATABASE_URL`.
6. Set env vars on the web service:
   ```
   DISCERN_DATABASE_URL=<internal postgres url>
   DISCERN_LOG_LEVEL=INFO
   ```
7. Deploy. Render provides the URL you paste into the Vercel env var above.

### Local with Docker

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml up --build
```

API available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

---

## Milestones

| # | Milestone | Status |
|---|-----------|--------|
| 1 | Scaffold + tooling + schema | ✅ |
| 2 | Synthetic data generator + preprocessing | ⬜ |
| 3 | Model + training loop + checkpoints | ⬜ |
| 4 | Inference + FastAPI + Postgres | ⬜ |
| 5 | Eval harness + metrics report | ⬜ |
| 6 | Next.js UI | ⬜ |
| 7 | Docker + full deployment docs | ⬜ |

---

## Eval Results

*(Populated in Milestone 5)*

| Capture type | Precision | Recall | F1 | CER | WER | p50 latency | p95 latency |
|---|---|---|---|---|---|---|---|
| handwritten | — | — | — | — | — | — | — |
| checkbox | — | — | — | — | — | — | — |
