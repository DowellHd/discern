# CLAUDE.md — Project Memory for Discern

This file is loaded every session. All rules here override default behavior.

---

## Product North Star

Discern is a **general-purpose personal document-intelligence app**. Goal: a tool a person opens weekly — snap or upload any document, get clean structured + searchable data back, find it again later.

**Lead use cases (most universally daily):** receipts → expense log; business cards → contacts; forms / handwritten notes / whiteboard photos → searchable text.

The existing church connection/prayer card schema is one built-in template category (`church`) among many, not the whole app. Generalize additively — never break the working church templates.

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
    api/         # FastAPI: /extract, /templates, /search, /health, stats, export
    db/          # Postgres models + migrations
  scripts/       # generate_data.py, train.py, evaluate.py
  frontend/      # Next.js: drag-drop upload, overlay, editable fields, search
  tests/
  configs/       # documents.yaml (template registry) + run/training configs
  docker/        # Dockerfile(s) + docker-compose for api + db
  README.md
```

---

## Schema Contract

`configs/documents.yaml` is the **single source of truth** for all document templates.
- Each template has: `key` (the dict key), `label`, `category`, `description`, `fields`, optional `export_hints`
- Categories: `church` | `personal` | `business`
- The synthetic generator labels against it
- Model field classes derive from it
- Eval iterates its field list
- DB `doc_type` column stores the template key; `template_category` stores the category
- UI renders template options from the `/templates` API endpoint (not hardcoded)

Swapping `configs/documents.yaml` is how the document domain is retargeted.

---

## Phase Plan

Audited against actual code 2026-07-08 (commit history didn't follow phase order, and this
checklist had gone stale — trust this over old memory of "Phase 0 done, 1-6 pending").

- **Phase 0** — Vision + foundations: expanded template registry, document_type plumbing end-to-end, CLAUDE.md updated. ✅
- **Phase 1** — Visual + UX overhaul: design system, upload states, cold-start UX, PWA, a11y. ✅
  Real gap: results panel has no distinct "hero" reveal treatment (it's a well-built panel, just not a hero moment).
- **Phase 2** — Generalize document types: synthetic data for all 9 templates, classifier, model extension. ✅
  `POST /extract/batch` exists alongside a frontend client-side loop over single `/extract` calls — this is
  intentional, not dead code: the client-side loop gives live per-file progress (added deliberately in
  "Batch: per-file live progress"), which a single batched request/response can't provide. The batch endpoint
  remains for programmatic/API consumers. Fixed 2026-07-08: added test coverage for `/extract/batch`
  (`tests/test_api.py`) since it had none before.
- **Phase 3** — Daily-use features: library/search, type-aware exports (vCard/iCal/expense CSV), review queue. ✅
  Folders were never built (not necessarily needed — reconsider before building).
- **Phase 4** — Intelligence layer: optional LLM post-processor, feature-flagged, cost-aware. ✅ fully done as scoped.
- **Phase 5** — Accounts + privacy: lightweight auth, no-signup demo mode. ✅
  Fixed 2026-07-08: "encryption at rest" was dead code — sensitive fields were replaced with `"[REDACTED]"`
  in `inference/engine.py` *before* `encrypt_field` ran in `api/app.py`, so real values were never encrypted,
  and `decrypt_field` was never called anywhere. Now the true value is encrypted when
  `DISCERN_FIELD_ENCRYPTION_KEY` is set, and falls back to storing `"[REDACTED]"` (never plaintext) when no
  key is set. `/training-candidates` and `PATCH /fields/{name}` mask/encrypt consistently with every other
  read path.
- **Phase 6** — MLOps + evals: per-type metrics, labeled benchmark, model card, feedback loop, README results table.
  Real gaps (biggest remaining chunk of work):
  - Per-doc-type P/R/F1 breakdown is implemented in `eval/metrics.py` but `reports/eval.json`/`eval.md`/README
    were never regenerated after the 9-type expansion — still showing old capture-type-only numbers. Local OCR
    (Ollama) was found hung/memory-starved during the regen attempt; rerunning against the Anthropic OCR
    fallback instead.
  - Fixed 2026-07-08: `scripts/retrain_from_feedback.py` + `src/discern/training/feedback.py` fine-tune the
    classification heads (visit_type, interests, category, contact_ok — the only fields with a matching model
    head) on corrected values pulled from the DB, masked per-sample to just the corrected field since a
    correction only gives ground truth for one field per document. Writes to `checkpoints/finetuned.pt`,
    never auto-promotes to `best.pt` — that stays a manual, reviewed step. Handwritten/freetext corrections
    aren't usable here (that's OCR output, not something this classifier predicts).
  - No model card exists.
  - "Benchmark" is reproducible seeded synthetic eval, not a persisted labeled dataset — fine as-is unless a
    real held-out benchmark is wanted.

**GLOBAL RULES (apply every phase):**
- NEVER push or deploy. Make changes, run the gate, show diff + local preview, then STOP. User pushes.
- Work one phase at a time. Within a phase, small milestones, summarize, wait for go-ahead.
- Don't break /extract and /search. Generalize additively; keep church templates.

---

## Deployment Targets

- **Frontend:** Vercel (`discern.dowellstandley.com` subdomain)
- **API:** Render
- **No new domain purchase** — DNS record created by user on existing `dowellstandley.com`
