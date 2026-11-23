"""Offline demo mode: isolation, seeding, recognition, the mock engine, and no-network guarantees."""

from __future__ import annotations

import io
import random
import socket
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from discern.api.deps import get_inference_engine
from discern.config import (
    DEMO_DATA_DIR,
    DEMO_SAMPLES_DIR,
    Settings,
    load_document_schema,
    settings,
)
from discern.data.schema import parse_document_schema
from discern.db.models import Base, Document
from discern.demo import mock
from discern.demo.bootstrap import reset_demo_data
from discern.demo.engine import DemoInferenceEngine
from discern.demo.realism import polish
from discern.demo.router import router as demo_router
from discern.demo.samples import list_samples, recognize
from discern.demo.seed import PLAN, seed_demo_library, seed_if_empty


@pytest.fixture(scope="module")
def schema():
    return parse_document_schema(load_document_schema())


@pytest.fixture
def demo_on(monkeypatch, tmp_path):
    """Offline demo on, with uploads redirected to a temp directory."""
    monkeypatch.setattr(settings, "offline_demo", True)
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "llm_postprocess", False)


@pytest.fixture
def fresh_db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def _sample_image(name: str) -> Image.Image:
    return Image.open(DEMO_SAMPLES_DIR / name)


# ---------------------------------------------------------------------------
# Settings: the demo must never reach real data or a real database
# ---------------------------------------------------------------------------


def test_offline_demo_is_off_by_default(monkeypatch):
    monkeypatch.delenv("DISCERN_OFFLINE_DEMO", raising=False)
    assert Settings(_env_file=None).offline_demo is False


def test_offline_demo_overrides_database_and_data_dir(monkeypatch):
    monkeypatch.setenv("DISCERN_OFFLINE_DEMO", "true")
    # Even an inherited production URL must not be used: seeding writes to the database.
    monkeypatch.setenv("DISCERN_DATABASE_URL", "postgresql://prod:secret@db.example.com/prod")
    s = Settings(_env_file=None)
    assert s.database_url.startswith("sqlite:///")
    assert "postgresql" not in s.database_url
    assert s.data_dir == DEMO_DATA_DIR


def test_reset_refuses_outside_offline_demo(monkeypatch):
    monkeypatch.setattr(settings, "offline_demo", False)
    with pytest.raises(RuntimeError):
        reset_demo_data()


# ---------------------------------------------------------------------------
# Bundled samples and recognition
# ---------------------------------------------------------------------------


def test_every_template_has_bundled_samples(schema):
    by_type: dict[str, int] = {}
    for s in list_samples():
        by_type[s.doc_type] = by_type.get(s.doc_type, 0) + 1
    assert set(by_type) == set(schema.document_types)
    assert all(n >= 2 for n in by_type.values())


def test_samples_are_recognised_as_themselves():
    for s in list_samples():
        found = recognize(_sample_image(s.file))
        assert found is not None and found.file == s.file


def test_recognition_survives_recompression_and_resizing():
    for s in list_samples():
        im = _sample_image(s.file)
        buf = io.BytesIO()
        im.resize((im.width // 2, im.height // 2)).save(buf, format="JPEG", quality=40)
        buf.seek(0)
        found = recognize(Image.open(buf))
        assert found is not None and found.file == s.file


def test_other_images_are_not_recognised():
    assert recognize(Image.new("RGB", (640, 480), (235, 230, 220))) is None


# ---------------------------------------------------------------------------
# Mock engine
# ---------------------------------------------------------------------------


def test_known_sample_returns_ground_truth(schema):
    engine = DemoInferenceEngine(schema)
    for s in list_samples():
        result = engine.predict(_sample_image(s.file))
        assert result.doc_type == s.doc_type
        assert result.doc_type_confidence >= 0.9
        for f in result.fields:
            if not f.sensitive:
                assert f.value == s.fields[f.name]


def test_unknown_image_is_deterministic_and_low_confidence(schema):
    engine = DemoInferenceEngine(schema)
    img = Image.new("RGB", (640, 480), (200, 190, 180))
    a, b = engine.predict(img), engine.predict(img)
    assert [(f.name, f.value, f.confidence) for f in a.fields] == [
        (f.name, f.value, f.confidence) for f in b.fields
    ]
    # Illustrative values must not pass as accurate reads.
    assert a.doc_type_confidence < 0.8
    assert all(f.confidence < 0.8 for f in a.fields)


def test_doc_type_override_is_respected(schema):
    engine = DemoInferenceEngine(schema)
    result = engine.predict(Image.new("RGB", (300, 200)), doc_type_override="receipt")
    assert result.doc_type == "receipt"
    assert {f.name for f in result.fields} == {
        f.name for f in schema.document_types["receipt"].fields
    }


def test_sensitive_fields_are_masked_but_keep_the_raw_value(schema):
    engine = DemoInferenceEngine(schema)
    sample = next(s for s in list_samples() if s.doc_type == "prayer_request")
    result = engine.predict(_sample_image(sample.file))
    field = next(f for f in result.fields if f.name == "request_text")
    assert field.sensitive and field.value == "[REDACTED]"
    assert field.raw_value == sample.fields["request_text"]


def test_health_reports_ready(schema):
    assert DemoInferenceEngine(schema)._checkpoint_loaded is True


# ---------------------------------------------------------------------------
# Coherent values
# ---------------------------------------------------------------------------


def _amount(s: str) -> float:
    return float(s.replace("$", "").replace(",", ""))


def test_polished_values_add_up():
    rng = random.Random(1)
    for _ in range(50):
        r = polish("receipt", {}, rng)
        assert 0 < _amount(r["tax_amount"]) < _amount(r["total_amount"])
        inv = polish("invoice", {"invoice_date": "03/10/2026"}, rng)
        assert _amount(inv["total_due"]) == pytest.approx(
            _amount(inv["subtotal"]) + _amount(inv["tax_amount"]), abs=0.011
        )
        issued = datetime.strptime("03/10/2026", "%m/%d/%Y")
        assert datetime.strptime(inv["due_date"], "%m/%d/%Y") >= issued


# ---------------------------------------------------------------------------
# Seeded library
# ---------------------------------------------------------------------------


def test_seed_builds_a_realistic_library(demo_on, fresh_db, tmp_path, schema):
    assert seed_demo_library(fresh_db, schema) == sum(n for _, n in PLAN)
    docs = fresh_db.query(Document).all()
    assert {d.doc_type for d in docs} == set(schema.document_types)
    assert 3 <= sum(d.doc_type_confidence < 0.70 for d in docs) <= 6  # review queue
    assert any(f.corrected for d in docs for f in d.fields)
    assert {d.follow_up_status for d in docs if d.template_category == "church"} >= {
        "pending",
        "contacted",
        "done",
    }
    # Spread over weeks, not all created at the same instant.
    assert (max(d.created_at for d in docs) - min(d.created_at for d in docs)).days >= 20
    for d in docs:
        assert (tmp_path / "uploads" / d.id / "original.png").exists()
        assert (tmp_path / "uploads" / d.id / "overlay.png").exists()


def test_seed_never_stores_sensitive_plaintext(demo_on, fresh_db, schema, monkeypatch):
    monkeypatch.setattr(settings, "field_encryption_key", "")
    seed_demo_library(fresh_db, schema)
    prayers = [d for d in fresh_db.query(Document).all() if d.doc_type == "prayer_request"]
    values = [f.field_value for d in prayers for f in d.fields if f.field_name == "request_text"]
    assert values and all(v == "[REDACTED]" for v in values)


def test_seed_is_idempotent(demo_on, fresh_db):
    assert seed_if_empty(fresh_db) > 0
    assert seed_if_empty(fresh_db) == 0


# ---------------------------------------------------------------------------
# API with the demo engine, and the demo router
# ---------------------------------------------------------------------------


def test_extract_via_api_returns_ground_truth(client, schema):
    from discern.api.app import app

    app.dependency_overrides[get_inference_engine] = lambda: DemoInferenceEngine(schema)
    sample = next(s for s in list_samples() if s.doc_type == "invoice")
    data = (DEMO_SAMPLES_DIR / sample.file).read_bytes()
    resp = client.post("/extract", files={"file": (sample.file, data, "image/jpeg")})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["doc_type"] == "invoice"
    assert {f["name"]: f["value"] for f in body["fields"]} == sample.fields


def test_demo_router_lists_and_serves_samples():
    app = FastAPI()
    app.include_router(demo_router)
    client = TestClient(app)
    listing = client.get("/demo/samples").json()
    assert len(listing) == len(list_samples())
    first = client.get(listing[0]["url"])
    assert first.status_code == 200 and first.headers["content-type"] == "image/jpeg"
    assert client.get("/demo/samples/nope.jpg").status_code == 404
    assert client.get("/demo/samples/..%2Findex.json").status_code in (404, 422)


# ---------------------------------------------------------------------------
# Nothing leaves the machine
# ---------------------------------------------------------------------------


@pytest.fixture
def no_network(monkeypatch):
    def refuse(*_a, **_k):
        raise AssertionError("network access attempted in offline demo")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


def test_mock_ocr_and_llm_make_no_network_calls(demo_on, no_network, monkeypatch):
    from discern.inference import llm_postprocess
    from discern.inference.ocr import extract_handwritten_fields

    # Keys present in the environment must not matter.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-never-be-used")
    monkeypatch.setenv("GOOGLE_API_KEY", "should-never-be-used")
    out = extract_handwritten_fields(
        Image.new("RGB", (300, 200), (220, 220, 220)), ["full_name", "email"], "connection_card"
    )
    assert set(out) == {"full_name", "email"}
    assert llm_postprocess.refine("receipt", {"merchant_name": "x"}) == {}


def test_demo_engine_makes_no_network_calls(demo_on, no_network, schema):
    engine = DemoInferenceEngine(schema)
    for s in list_samples()[:4]:
        engine.predict(_sample_image(s.file))


def test_real_model_with_mock_ocr_makes_no_network_calls(demo_on, no_network, schema, monkeypatch):
    """The optional real classifier still runs offline: OCR and LLM stay mocked."""
    pytest.importorskip("torch")
    from discern.inference.engine import InferenceEngine

    ckpt = settings.checkpoints_dir / "best.pt"
    if not ckpt.exists():
        pytest.skip("no checkpoint")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-never-be-used")
    engine = InferenceEngine(schema=schema, checkpoint_path=ckpt)
    sample = next(s for s in list_samples() if s.doc_type == "connection_card")
    result = engine.predict(_sample_image(sample.file))
    assert result.fields  # classifier ran, mock OCR filled the handwritten fields
    assert mock.image_seed(_sample_image(sample.file)) > 0
