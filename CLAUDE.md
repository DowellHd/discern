# CLAUDE.md — Project Memory for Discern

This file is loaded every session. All rules here override default behavior.

---

## Commit / Push Rules (DO NOT VIOLATE)

- Do NOT mention Claude, AI, assistant, or automation in commit messages, PR titles, or trailers
- No Co-Authored-By trailers, and no "Generated with" attribution of any kind
- Small, logical commits (one fix or one unit of work per commit)
- Push only after the verification steps pass (see below)

---

## Verification Steps (must all pass before any push)

```
ruff check . && ruff format --check .
mypy src
pytest -q
python -m scripts.evaluate
```

- Backend imports/starts and frontend builds (`npm run build`)

---

## Data Privacy (DO NOT VIOLATE)

- Never commit real personal data. Training/eval/demo use synthetic generated samples only.
- `.gitignore` the `real-data/` and `uploads/` directories. Strip EXIF on ingest.
- Fields marked `sensitive: true` in the schema are masked in all logs and in the metrics report.

---

## Project Conventions

- **Language:** Python 3.11, PyTorch-first. **Frontend:** Next.js (TypeScript).
- Config-driven (pydantic-settings + YAML). Seed all RNGs for reproducibility.
- Modular: clear `src/` packages, functions/classes, no notebook-only logic.
- Structured logging, not prints. Type hints throughout.

---

## Architecture Overview

```
discern/
  src/discern/
    data/        # synthetic doc generator, ingest, preprocessing (deskew, denoise)
    models/      # layout/region detection + OCR; a small fine-tunable head
    training/    # train loop, config, checkpoints, experiment logging
    inference/   # load model, run on an image, return overlay + structured JSON
    eval/        # metrics: field-level P/R/F1, OCR CER/WER, latency
    api/         # FastAPI: /extract (upload image), /search, /health
    db/          # Postgres models + migrations
  scripts/       # generate_data.py, train.py, evaluate.py
  frontend/      # Next.js: drag-drop upload, overlay, editable fields, search
  tests/
  configs/       # documents.yaml (the schema) + run/training configs
  docker/        # Dockerfile(s) + docker-compose for api + db
  README.md
```

---

## Schema Contract

`configs/documents.yaml` is the **single source of truth** for document domains.
- The synthetic generator labels against it
- Model field classes derive from it
- Eval iterates its field list
- DB columns map to it
- UI renders from it

Swapping `configs/documents.yaml` is how the document domain is retargeted.

---

## Milestones

1. STEP 0: memory + repo scaffold + tooling + `configs/documents.yaml`
2. Synthetic data generator (driven by schema) + preprocessing + tests
3. Model + training loop + checkpointing on synthetic data
4. Inference module + FastAPI `/extract` and `/search` + Postgres storage
5. Eval harness + metrics report, broken down by capture type
6. Next.js UI (upload, overlay, edit, search)
7. Docker + README (full deployment steps for Vercel + Render + subdomain)

---

## Deployment Targets

- **Frontend:** Vercel (`discern.dowellstandley.com` subdomain)
- **API:** Render
- **No new domain purchase** — DNS record created by user on existing `dowellstandley.com`
