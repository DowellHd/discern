.PHONY: install lint fmt typecheck test eval verify generate train up down build-frontend migrate

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

install:
	pip install -e ".[dev]"
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

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

build-frontend:
	cd frontend && npm run build

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

up:
	docker compose -f docker/docker-compose.yml up --build -d

down:
	docker compose -f docker/docker-compose.yml down
