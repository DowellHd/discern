"""Create and seed the offline demo database."""

from __future__ import annotations

import shutil

import structlog

from discern.config import DEMO_DATA_DIR, settings
from discern.db.models import Base
from discern.db.session import SessionLocal, get_default_engine

log = structlog.get_logger()


def init_demo() -> None:
    """Create the SQLite tables and seed the library if it is empty (idempotent)."""
    from discern.demo.seed import seed_if_empty

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(get_default_engine())
    with SessionLocal() as db:
        added = seed_if_empty(db)
    # Create the engine now so /health reports it ready from the first request.
    from discern.api.deps import get_inference_engine

    get_inference_engine()
    log.info("demo_ready", seeded_documents=added, database=settings.database_url)


def reset_demo_data() -> None:
    """Delete the demo database and uploads so the next start reseeds from scratch.

    Refuses to touch anything outside `data/demo` — it must never reach real data.
    """
    if not settings.offline_demo or settings.data_dir != DEMO_DATA_DIR:
        raise RuntimeError("reset_demo_data only runs in offline demo mode")
    get_default_engine().dispose()
    if DEMO_DATA_DIR.exists():
        shutil.rmtree(DEMO_DATA_DIR)
    log.info("demo_data_reset", path=str(DEMO_DATA_DIR))
