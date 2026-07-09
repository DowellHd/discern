"""Tests for Milestone 4: FastAPI endpoints."""

from __future__ import annotations

from tests.conftest import make_png_bytes

# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


def test_health_ok(client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "model_loaded" in body


# ---------------------------------------------------------------------------
# POST /extract
# ---------------------------------------------------------------------------


def test_extract_returns_200(client) -> None:
    png = make_png_bytes()
    resp = client.post("/extract", files={"file": ("card.png", png, "image/png")})
    assert resp.status_code == 200


def test_extract_response_schema(client) -> None:
    png = make_png_bytes()
    resp = client.post("/extract", files={"file": ("card.png", png, "image/png")})
    body = resp.json()
    assert "id" in body
    assert "doc_type" in body
    assert "doc_type_confidence" in body
    assert "fields" in body
    assert "overlay_url" in body
    assert "created_at" in body
    assert "llm_refined" in body


def test_extract_llm_refined_false_by_default(client) -> None:
    png = make_png_bytes()
    resp = client.post("/extract", files={"file": ("card.png", png, "image/png")})
    assert resp.json()["llm_refined"] is False


def test_extract_fields_list(client) -> None:
    png = make_png_bytes()
    resp = client.post("/extract", files={"file": ("card.png", png, "image/png")})
    fields = resp.json()["fields"]
    assert isinstance(fields, list)
    assert len(fields) > 0
    for f in fields:
        assert "name" in f
        assert "confidence" in f
        assert "capture" in f


def test_extract_rejects_oversized(client, mock_engine) -> None:
    from discern.inference.engine import _MAX_BYTES

    mock_engine.validate_upload.side_effect = ValueError("File too large")
    big = b"x" * (_MAX_BYTES + 1)
    resp = client.post("/extract", files={"file": ("big.png", big, "image/png")})
    assert resp.status_code == 422
    mock_engine.validate_upload.side_effect = None


def test_extract_rejects_bad_mimetype(client, mock_engine) -> None:
    mock_engine.validate_upload.side_effect = ValueError("Unsupported type")
    resp = client.post("/extract", files={"file": ("doc.pdf", b"data", "application/pdf")})
    assert resp.status_code == 422
    mock_engine.validate_upload.side_effect = None


# ---------------------------------------------------------------------------
# GET /extractions/{id}/overlay
# ---------------------------------------------------------------------------


def test_overlay_returns_png(client, tmp_path) -> None:
    png = make_png_bytes()
    resp = client.post("/extract", files={"file": ("card.png", png, "image/png")})
    doc_id = resp.json()["id"]

    overlay_resp = client.get(f"/extractions/{doc_id}/overlay")
    assert overlay_resp.status_code == 200
    assert overlay_resp.headers["content-type"] == "image/png"


def test_overlay_404_for_missing(client) -> None:
    resp = client.get("/extractions/does-not-exist/overlay")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /search
# ---------------------------------------------------------------------------


def test_search_returns_results(client) -> None:
    png = make_png_bytes()
    client.post("/extract", files={"file": ("card.png", png, "image/png")})
    resp = client.get("/search")
    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body
    assert "results" in body
    assert body["total"] >= 1


def test_search_filter_by_doc_type(client) -> None:
    resp = client.get("/search", params={"doc_type": "connection_card"})
    assert resp.status_code == 200
    for doc in resp.json()["results"]:
        assert doc["doc_type"] == "connection_card"


def test_search_query_param(client) -> None:
    resp = client.get("/search", params={"q": "first_time"})
    assert resp.status_code == 200
    assert "total" in resp.json()


def test_search_pagination(client) -> None:
    resp = client.get("/search", params={"limit": 1, "offset": 0})
    assert resp.status_code == 200
    assert len(resp.json()["results"]) <= 1


# ---------------------------------------------------------------------------
# Type-aware exports
# ---------------------------------------------------------------------------


def test_export_vcard_wrong_type(client) -> None:
    png = make_png_bytes()
    resp = client.post("/extract", files={"file": ("card.png", png, "image/png")})
    doc_id = resp.json()["id"]
    # The mock returns connection_card, not business_card
    r = client.get(f"/extractions/{doc_id}/export.vcf")
    assert r.status_code == 422


def test_export_ical_wrong_type(client) -> None:
    png = make_png_bytes()
    resp = client.post("/extract", files={"file": ("card.png", png, "image/png")})
    doc_id = resp.json()["id"]
    r = client.get(f"/extractions/{doc_id}/export.ics")
    assert r.status_code == 422


def test_export_expense_wrong_type(client) -> None:
    png = make_png_bytes()
    resp = client.post("/extract", files={"file": ("card.png", png, "image/png")})
    doc_id = resp.json()["id"]
    r = client.get(f"/extractions/{doc_id}/export-expense.csv")
    assert r.status_code == 422


def test_export_vcard_404(client) -> None:
    r = client.get("/extractions/does-not-exist/export.vcf")
    assert r.status_code == 404


def test_export_ical_404(client) -> None:
    r = client.get("/extractions/does-not-exist/export.ics")
    assert r.status_code == 404


def test_export_expense_404(client) -> None:
    r = client.get("/extractions/does-not-exist/export-expense.csv")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Auth endpoints (Phase 5)
# ---------------------------------------------------------------------------


def test_register_creates_account(client, monkeypatch) -> None:
    from discern.config import settings
    from tests.conftest import _TEST_JWT_SECRET

    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "jwt_secret", _TEST_JWT_SECRET)
    resp = client.post("/auth/register", json={"email": "alice@test.com", "password": "password123"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_register_duplicate_returns_409(client, monkeypatch) -> None:
    from discern.config import settings
    from tests.conftest import _TEST_JWT_SECRET

    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "jwt_secret", _TEST_JWT_SECRET)
    client.post("/auth/register", json={"email": "bob@test.com", "password": "password123"})
    resp = client.post("/auth/register", json={"email": "bob@test.com", "password": "password123"})
    assert resp.status_code == 409


def test_login_returns_token(client, monkeypatch) -> None:
    from discern.config import settings
    from tests.conftest import _TEST_JWT_SECRET

    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "jwt_secret", _TEST_JWT_SECRET)
    client.post("/auth/register", json={"email": "carol@test.com", "password": "securepass"})
    resp = client.post("/auth/login", json={"email": "carol@test.com", "password": "securepass"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password_returns_401(client, monkeypatch) -> None:
    from discern.config import settings
    from tests.conftest import _TEST_JWT_SECRET

    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "jwt_secret", _TEST_JWT_SECRET)
    client.post("/auth/register", json={"email": "dave@test.com", "password": "rightpass"})
    resp = client.post("/auth/login", json={"email": "dave@test.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_me_in_demo_mode(client) -> None:
    resp = client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "demo@discern.local"


# ---------------------------------------------------------------------------
# Training candidates (Phase 6)
# ---------------------------------------------------------------------------


def test_training_candidates_empty(client) -> None:
    resp = client.get("/training-candidates")
    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body
    assert "candidates" in body
    assert body["total"] == 0


# ---------------------------------------------------------------------------
# Sensitive field encryption at rest (Phase 5)
# ---------------------------------------------------------------------------


def _prayer_request_result(request_text_raw: str = "please pray for my mother"):
    from discern.inference.engine import FieldResult, InferenceResult

    return InferenceResult(
        doc_type="prayer_request",
        doc_type_confidence=0.95,
        fields=[
            FieldResult(
                "requester_name", "Jane Doe", 0.9, "handwritten", False, raw_value="Jane Doe"
            ),
            FieldResult("service_date", None, 0.0, "handwritten", False),
            FieldResult("category", "healing", 0.9, "checkbox", False),
            FieldResult(
                "request_text",
                "[REDACTED]",
                0.8,
                "handwritten",
                True,
                raw_value=request_text_raw,
            ),
            FieldResult("contact_ok", "True", 0.9, "checkbox", False),
        ],
    )


def _reset_fernet_cache() -> None:
    from discern.api import auth

    auth._fernet_checked = False
    auth._fernet_instance = None


def test_sensitive_field_masked_in_response(client, mock_engine) -> None:
    mock_engine.predict.return_value = _prayer_request_result()
    resp = client.post("/extract", files={"file": ("card.png", make_png_bytes(), "image/png")})
    field = next(f for f in resp.json()["fields"] if f["name"] == "request_text")
    assert field["value"] == "[REDACTED]"
    assert field["sensitive"] is True


def test_sensitive_field_encrypted_at_rest_with_key(
    client, mock_engine, db_session, monkeypatch
) -> None:
    from cryptography.fernet import Fernet

    from discern.api import auth
    from discern.config import settings
    from discern.db.models import ExtractionField

    monkeypatch.setattr(settings, "field_encryption_key", Fernet.generate_key().decode())
    _reset_fernet_cache()

    mock_engine.predict.return_value = _prayer_request_result()
    resp = client.post("/extract", files={"file": ("card.png", make_png_bytes(), "image/png")})
    doc_id = resp.json()["id"]

    stored = (
        db_session.query(ExtractionField)
        .filter_by(document_id=doc_id, field_name="request_text")
        .one()
    )
    assert stored.field_value != "please pray for my mother"
    assert auth.decrypt_field(stored.field_value) == "please pray for my mother"


def test_sensitive_field_not_persisted_as_plaintext_without_key(
    client, mock_engine, db_session, monkeypatch
) -> None:
    from discern.config import settings
    from discern.db.models import ExtractionField

    monkeypatch.setattr(settings, "field_encryption_key", "")
    _reset_fernet_cache()

    mock_engine.predict.return_value = _prayer_request_result()
    resp = client.post("/extract", files={"file": ("card.png", make_png_bytes(), "image/png")})
    doc_id = resp.json()["id"]

    stored = (
        db_session.query(ExtractionField)
        .filter_by(document_id=doc_id, field_name="request_text")
        .one()
    )
    assert stored.field_value == "[REDACTED]"


def test_patch_sensitive_field_is_encrypted(client, mock_engine, db_session, monkeypatch) -> None:
    from cryptography.fernet import Fernet

    from discern.api import auth
    from discern.config import settings
    from discern.db.models import ExtractionField

    monkeypatch.setattr(settings, "field_encryption_key", Fernet.generate_key().decode())
    _reset_fernet_cache()

    mock_engine.predict.return_value = _prayer_request_result()
    resp = client.post("/extract", files={"file": ("card.png", make_png_bytes(), "image/png")})
    doc_id = resp.json()["id"]

    patch_resp = client.patch(
        f"/extractions/{doc_id}/fields/request_text", json={"value": "please pray harder"}
    )
    assert patch_resp.status_code == 200
    field = next(f for f in patch_resp.json()["fields"] if f["name"] == "request_text")
    assert field["value"] == "[REDACTED]"

    stored = (
        db_session.query(ExtractionField)
        .filter_by(document_id=doc_id, field_name="request_text")
        .one()
    )
    assert stored.field_value != "please pray harder"
    assert auth.decrypt_field(stored.field_value) == "please pray harder"


def test_training_candidates_excludes_sensitive_fields(client, mock_engine) -> None:
    mock_engine.predict.return_value = _prayer_request_result()
    resp = client.post("/extract", files={"file": ("card.png", make_png_bytes(), "image/png")})
    doc_id = resp.json()["id"]

    client.patch(f"/extractions/{doc_id}/fields/requester_name", json={"value": "Janet Doe"})
    client.patch(f"/extractions/{doc_id}/fields/request_text", json={"value": "please pray harder"})

    tc_resp = client.get("/training-candidates")
    names = {c["field_name"] for c in tc_resp.json()["candidates"]}
    assert "requester_name" in names
    assert "request_text" not in names
