# Discern

> Computer vision that turns paper records into structured, searchable data.

Discern is a document-intelligence pipeline that processes photos and scans of paper church records — connection cards, prayer request cards, and weekly bulletins — and extracts structured, searchable data. The document domain is fully swappable via a single YAML config.

## Demo

**[▶ Watch Demo Video](#)** <!-- TODO: replace # with the demo video URL -->

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?logo=sqlalchemy&logoColor=white)
![SQLite](https://img.shields.io/badge/Demo_DB-SQLite-003B57?logo=sqlite&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)

The whole app runs locally with **no Postgres, no API keys, and no network**. In offline demo mode
SQLite replaces Postgres, a mock engine replaces the model and the OCR/LLM backends (Tesseract,
Ollama, Gemini, Anthropic), and the library opens pre-filled with 30 synthetic documents.

### Run the demo

```bash
# 1. Clone
git clone https://github.com/DowellHd/discern.git && cd discern

# 2. Install the API (Python 3.11+; no torch needed)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-demo.txt

# 3. Run it
python main.py                  # API + docs → http://localhost:8000/docs
```

In a second terminal, start the UI (Node 20+):

```bash
cd frontend
cp .env.demo .env.local && npm install && npm run dev     # → http://localhost:3000
```

`make demo` and `make demo-frontend` do the same. Open <http://localhost:3000>, click a sample under
**Try a sample document**, then explore the **Library** and **Stats** tabs.

**What you get**

- A library of 30 documents across all nine templates (receipts, business cards, invoices,
  connection and prayer cards, giving envelopes, notes, flyers, forms) with confidence scores,
  follow-up statuses, hand-corrected fields, and a review queue
- One-click extraction of 18 bundled sample documents (also in `demo-samples/`), shown with the
  annotated overlay, editable fields, and vCard / iCal / expense-CSV exports
- Search, filters, stats, and CSV export, all backed by the real API code

**What demo mode is, and isn't**

- Every document is synthetic. Nothing real is stored, and sensitive fields stay masked.
- The bundled samples are recognised by image similarity and read back **exactly**. Any other file
  you upload gets **illustrative** values: plausible and schema-valid, but unrelated to what is on
  the page. They are given low confidence on purpose, so they land in the review queue.
- The mock engine does not run the model. To run the real classifier locally (needs
  `poetry install` for torch), set `DISCERN_OFFLINE_DEMO_REAL_MODEL=true`. OCR and LLM calls stay
  mocked, so nothing leaves your machine either way.
- Demo data lives in `data/demo/` (git-ignored). `python main.py --reset` rebuilds it.

**Switching back to the real services**

Run `python main.py --real`, or set `DISCERN_OFFLINE_DEMO=false`, or just use `make serve`. No code
changes are needed; the real database, model, and OCR code are untouched and only bypassed while
the demo flag is on. For the UI, delete `frontend/.env.local`.

| Variable | Where | Meaning |
|---|---|---|
| `DISCERN_OFFLINE_DEMO` | API | Local mocks instead of Postgres, the model, OCR and LLMs. **Off by default** |
| `DISCERN_DEMO_MODE` | API | Skip login and use a shared demo user (separate; defaults to on) |
| `NEXT_PUBLIC_OFFLINE_DEMO` | UI | Show the "Try a sample document" row |
| `NEXT_PUBLIC_DEMO_MODE` | UI | Hide the sign-in UI |
| `NEXT_PUBLIC_BACK_SOON` | UI | `false` shows the app; the default shows the "Back Soon" page |

---

## Screenshots

| Upload & Extract | Search Records |
|:-:|:-:|
| ![Upload zone](frontend/public/screenshots/home.png) | ![Search panel](frontend/public/screenshots/upload.png) |

---

## What it does

1. **Upload** a photo of a paper form (JPEG / PNG / TIFF, max 20 MB).
2. **Extract** — a ResNet-18 backbone with multi-task heads classifies the document type and decodes checkbox fields; the full overlay image annotates each field with its confidence score.
3. **Store** — results land in Postgres (SQLAlchemy + Alembic) for search.
4. **Search** — query field values or filter by document type via `GET /search`.
5. **Edit** — the Next.js UI lets you correct extracted values before saving.

---

## Architecture

```
discern/
  src/discern/
    data/        synthetic generator · preprocessing (deskew, denoise, CLAHE)
    models/      ResNet-18 backbone · multi-task heads (doc-type, checkbox fields)
    training/    Trainer · OneCycleLR · checkpoint save/load · structlog logging
    inference/   InferenceEngine · EXIF strip · overlay renderer
    eval/        field-level P/R/F1 · CER/WER · p50/p95 latency by capture type
    api/         FastAPI: POST /extract · GET /search · GET /health
    db/          SQLAlchemy ORM · Alembic migrations (documents + extraction_fields)
  scripts/       generate_data.py · train.py · evaluate.py
  frontend/      Next.js 16: drag-drop upload · overlay · editable fields · search
  configs/       documents.yaml (schema contract) · train.yaml
  docker/        Dockerfile.api · Dockerfile.frontend · docker-compose.yml
  reports/       eval.json · eval.md (generated by scripts/evaluate)
```

`configs/documents.yaml` is the **single source of truth**. Swap it to retarget the whole pipeline to a different document domain.

---

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install poetry
POETRY_VIRTUALENVS_CREATE=false poetry install
pre-commit install
make verify          # lint + typecheck + tests + eval
```

---

## Verification Gate

```bash
ruff check . && ruff format --check .   # lint / format
mypy src                                 # type check
pytest -q                               # 109 tests
python -m scripts.evaluate             # metrics report
```

---

## Running Locally

### Python API

```bash
# 1. Start Postgres (Docker)
docker compose -f docker/docker-compose.yml up db -d

# 2. Apply migrations
make migrate

# 3. Serve
make serve
# → http://localhost:8000/docs
```

### Next.js Frontend

```bash
cd frontend
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
# → http://localhost:3000
```

### Everything via Docker

```bash
make up          # builds api + db, starts both
# API → http://localhost:8000
```

---

## Training

```bash
make train       # uses configs/train.yaml (10 epochs, 1000 synthetic samples)
make eval        # writes reports/eval.json + reports/eval.md
```

---

## Eval Results

Evaluated on 300 held-out synthetic samples (150 per doc type, seed=999).
Handwritten field values are **not extracted** by the current model (OCR head not implemented); CER/WER = 1.0 reflects this gap. Checkbox classification achieves F1 = 1.000 after 10 training epochs.

| Capture type | Precision | Recall | F1 | CER | WER | p50 latency | p95 latency |
|---|---|---|---|---|---|---|---|
| handwritten | 1.000 | 0.009 | 0.018 | 1.000 | 1.000 | 301 ms | 353 ms |
| checkbox | 1.000 | 1.000 | 1.000 | — | — | 301 ms | 359 ms |
| **overall** | **1.000** | **0.339** | **0.507** | 1.000 | 1.000 | 301 ms | 353 ms |

> Latency is CPU inference on an M-series Mac. GPU inference would be ~10× faster.

---

## Security

- Upload endpoint validates MIME type (JPEG/PNG/TIFF only) and enforces a 20 MB size limit.
- EXIF data is stripped on ingest — no GPS or device metadata is stored.
- Fields marked `sensitive: true` in `configs/documents.yaml` are masked (`[REDACTED]`) in all API responses and logs.
- No PII is ever committed to the repo; all training/eval data is synthetic.
- `torch.load` is used only for trusted internal checkpoints (`weights_only=False` is documented inline).

---

## Deployment

### Prerequisites

- A Vercel account (frontend)
- A Render account (API + Postgres)
- DNS access to `dowellstandley.com` — you will add one CNAME record

### Frontend → Vercel

1. Push the repo to GitHub.
2. In Vercel: **Add New Project** → import this repo.
3. Set **Root Directory** to `frontend`.
4. Add env var: `NEXT_PUBLIC_API_URL=https://<your-render-service>.onrender.com`
5. Deploy. Vercel gives you a `*.vercel.app` URL.
6. In Vercel **Domains**, add `discern.dowellstandley.com`.
7. In your DNS provider for `dowellstandley.com`, add:
   ```
   CNAME  discern  cname.vercel-dns.com.
   ```

### API → Render

1. In Render: **New Web Service** → connect this repo.
2. Set **Root Directory** to `.` (repo root).
3. **Build command:** `pip install poetry && POETRY_VIRTUALENVS_CREATE=false poetry install --only main`
4. **Start command:** `uvicorn discern.api.app:app --host 0.0.0.0 --port $PORT`
5. Add a **Postgres** database on Render; copy the internal `DATABASE_URL`.
6. Set env vars on the web service:
   ```
   DISCERN_DATABASE_URL=<internal postgres url>
   DISCERN_LOG_LEVEL=INFO
   ```
7. Migrate: set `DISCERN_DATABASE_URL` and run `alembic upgrade head` via the Render shell.
8. Deploy. Paste the Render URL into the Vercel env var from step 4.

---

## Schema Contract

`configs/documents.yaml` drives the entire pipeline:

```yaml
document_types:
  connection_card:
    fields:
      - name: full_name
        value_type: string
        capture: handwritten     # "handwritten" | "checkbox"
        required: true
      - name: visit_type
        value_type: enum
        options: [first_time, returning, regular]
        capture: checkbox
      - name: interests
        value_type: multiselect
        options: [baptism, community_group, volunteering, prayer, membership]
        capture: checkbox
      # … more fields
  prayer_request:
    fields:
      - name: request_text
        value_type: freetext
        capture: handwritten
        sensitive: true          # masked in logs + API responses
```

Swap this file to retarget to any other paper form domain.

---

## Milestones

| # | Milestone | Status |
|---|-----------|--------|
| 1 | Scaffold + tooling + schema | ✅ |
| 2 | Synthetic data generator + preprocessing | ✅ |
| 3 | Model + training loop + checkpoints | ✅ |
| 4 | Inference + FastAPI + Postgres | ✅ |
| 5 | Eval harness + metrics report | ✅ |
| 6 | Next.js UI | ✅ |
| 7 | Docker + full deployment docs | ✅ |
