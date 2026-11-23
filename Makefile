.PHONY: install lint fmt typecheck test eval verify generate train up down build-frontend migrate demo demo-frontend demo-samples

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

install:
	POETRY_VIRTUALENVS_CREATE=false poetry install
	pre-commit install

lint:
	ruff check .

fmt:
	ruff format .

typecheck:
	mypy src

test:
	pytest -q

eval:
	python -m scripts.evaluate

verify: lint typecheck test eval
	@echo "All verification steps passed."

# ---------------------------------------------------------------------------
# Data / training
# ---------------------------------------------------------------------------

generate:
	python scripts/generate_data.py

train:
	python scripts/train.py

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

migrate:
	alembic upgrade head

serve:
	uvicorn discern.api.app:app --reload --host 0.0.0.0 --port 8000

# Offline demo: API on :8000 with no Postgres, keys or network (see README).
demo:
	python main.py

demo-samples:
	python -m discern.demo.samples

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

build-frontend:
	cd frontend && npm run build

# Offline demo UI on :3000 (run `make demo` in another terminal first).
demo-frontend:
	cp -n frontend/.env.demo frontend/.env.local || true
	cd frontend && npm run dev

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

up:
	docker compose -f docker/docker-compose.yml up --build -d

down:
	docker compose -f docker/docker-compose.yml down
