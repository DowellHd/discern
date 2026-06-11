"""Shared test fixtures: in-memory SQLite DB, TestClient, and mocked engine."""

from __future__ import annotations

import io
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from discern.api.app import app
from discern.api.deps import get_db, get_inference_engine
from discern.config import load_document_schema, settings
from discern.data.schema import parse_document_schema
from discern.db.models import Base
from discern.inference.engine import FieldResult, InferenceResult

# ---------------------------------------------------------------------------
# In-memory SQLite DB
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def sqlite_engine():
    # StaticPool ensures all connections share the same in-memory SQLite database
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(sqlite_engine):
    SessionLocal = sessionmaker(bind=sqlite_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


# ---------------------------------------------------------------------------
# Mocked inference engine
# ---------------------------------------------------------------------------


def _dummy_result() -> InferenceResult:
    return InferenceResult(
        doc_type="connection_card",
        doc_type_confidence=0.92,
        fields=[
            FieldResult("full_name", None, 0.0, "handwritten", False),
            FieldResult("visit_type", "first_time", 0.88, "checkbox", False),
            FieldResult("email", None, 0.0, "handwritten", False),
            FieldResult("phone", None, 0.0, "handwritten", False),
            FieldResult("service_date", None, 0.0, "handwritten", False),
            FieldResult("interests", "baptism, prayer", 0.71, "checkbox", False),
            FieldResult("notes", None, 0.0, "handwritten", False),
        ],
    )


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine._checkpoint_loaded = False
    engine.predict.return_value = _dummy_result()
    engine.validate_upload = MagicMock()
    return engine


# ---------------------------------------------------------------------------
# TestClient with dependency overrides
# ---------------------------------------------------------------------------


@pytest.fixture
def client(db_session, mock_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    def override_db():
        yield db_session

    def override_engine():
        return mock_engine

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_inference_engine] = override_engine

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def schema():
    return parse_document_schema(load_document_schema())


def make_png_bytes(width: int = 100, height: int = 100) -> bytes:
    """Create a minimal PNG in memory."""
    img = Image.new("RGB", (width, height), color=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
