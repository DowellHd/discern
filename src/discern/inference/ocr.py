"""Vision-based OCR for text and handwritten form fields.

Extraction backends tried in order:
  1. Tesseract   — local rule-based OCR; best for printed/typed text; zero dependencies at runtime
  2. Ollama      — local VLM, free, no external service; handles handwriting
  3. Gemini Flash — Google's free-tier cloud VLM (15 RPM / 1 M TPD, no cost)
  4. Anthropic   — fallback only; requires ANTHROPIC_API_KEY, incurs usage cost

Tesseract requires the `tesseract-ocr` system package.
  macOS:  brew install tesseract
  Ubuntu: apt-get install -y tesseract-ocr   (already present on Render/Heroku)
  Render: prefix your Build Command with: apt-get install -y tesseract-ocr &&

Environment variables:
  OLLAMA_URL      default http://localhost:11434
  OLLAMA_MODEL    default llava:7b
  OLLAMA_TIMEOUT  default 10 s (increase to 120 for CPU-only inference)
  GOOGLE_API_KEY  or GEMINI_API_KEY — free key from aistudio.google.com
  ANTHROPIC_API_KEY
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

import structlog
from PIL import Image

log = structlog.get_logger()

_CONF_HIT = 0.82
_CONF_MISS = 0.0

_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llava:7b")
_OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "10"))

_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
_GEMINI_TIMEOUT = 30

# Resize before sending to any VLM — keeps latency down without hurting OCR accuracy.
_VLM_MAX_DIM = 1024


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _build_prompt(field_names: list[str], doc_type: str) -> str:
    field_list = "\n".join(f"- {name}" for name in field_names)
    return (
        f"This is a church {doc_type.replace('_', ' ')} form. "
        "Extract the handwritten or typed text for each field listed below.\n\n"
        f"{field_list}\n\n"
        "Return ONLY a JSON object. Keys must exactly match the field names above. "
        "Values are the extracted text (string), or null if the field is blank or illegible. "
        "No explanation, no markdown — only the JSON object.\n"
        'Example: {"full_name": "Marcus Bell", "email": "m@example.com", "notes": null}'
    )


def _prepare_for_vlm(image: Image.Image) -> str:
    """Resize and base64-encode an image for VLM submission."""
    img = image.convert("RGB")
    w, h = img.size
    if max(w, h) > _VLM_MAX_DIM:
        scale = _VLM_MAX_DIM / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode()


def _parse_json(raw: str) -> dict[str, Any] | None:
    """Strip markdown fences and parse JSON; falls back to scanning for the first object."""
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1].lstrip("json").strip() if len(parts) > 1 else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return None


def _fields_from(
    extracted: dict[str, Any], field_names: list[str]
) -> dict[str, tuple[str | None, float]]:
    result: dict[str, tuple[str | None, float]] = {}
    for name in field_names:
        raw_val = extracted.get(name)
        if raw_val is not None and str(raw_val).strip():
            result[name] = (str(raw_val).strip(), _CONF_HIT)
        else:
            result[name] = (None, _CONF_MISS)
    return result


def _post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any] | None:
    """POST JSON and return the parsed response dict, or None on any error."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())  # type: ignore[return-value]
    except urllib.error.HTTPError as exc:
        # API returned an error (e.g. 400 invalid key, 403 quota exceeded)
        body = exc.read().decode(errors="replace")[:500]
        log.warning("http_api_error", status=exc.code, reason=exc.reason, body=body)
    except urllib.error.URLError as exc:
        # Connection-level failure — service not reachable (expected for Ollama on Render)
        log.debug("http_unavailable", url=url, error=str(exc))
    except Exception as exc:
        log.warning("http_error", url=url, error=str(exc))
    return None


# ---------------------------------------------------------------------------
# Backend 1: Tesseract (local, no API key, best for printed/typed text)
# ---------------------------------------------------------------------------

# Maps schema field names → possible label text that appears on real forms.
# "full_name" might appear as "Name:" or "Full Name:" on the physical card.
_FIELD_LABELS: dict[str, list[str]] = {
    "full_name": ["full name", "name"],
    "email": ["email", "e-mail", "email address"],
    "phone": ["phone", "phone number", "cell", "telephone"],
    "service_date": ["date", "service date"],
    "notes": ["notes", "comments", "additional notes"],
    "invited_by": ["invited by"],
    "requester_name": ["name", "your name", "requester"],
    "request_text": ["prayer request", "request", "message"],
    "donor_name": ["donor name", "name", "donor"],
    "envelope_date": ["date", "envelope date"],
    "amount": ["amount", "gift amount", "offering"],
    "memo": ["memo", "note", "notes"],
}


def _extract_by_label(field_name: str, text: str) -> str | None:
    """Pull a field value from raw OCR text using form-label heuristics."""
    # Regex patterns for well-structured fields.
    if field_name in ("email",):
        m = re.search(r"[\w.+\-]+@[\w.\-]+\.\w{2,}", text)
        return m.group(0) if m else None
    if field_name in ("phone",):
        m = re.search(r"\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}", text)
        return m.group(0) if m else None
    if field_name in ("service_date", "envelope_date"):
        m = re.search(r"\d{1,2}[\s/\-]\d{1,2}[\s/\-]\d{2,4}", text)
        return m.group(0) if m else None

    aliases = _FIELD_LABELS.get(field_name, [field_name.replace("_", " ")])
    for alias in aliases:
        # Look for "Label: value" or "Label  value" on a single line
        pattern = rf"(?i)\b{re.escape(alias)}\s*[:\-]?\s*(.+?)(?:\n|$)"
        m = re.search(pattern, text)
        if m:
            val = m.group(1).strip().rstrip(",;")
            # Skip blank hits, all-caps headings, and values that look like another label
            if val and len(val) > 1 and not re.fullmatch(r"[A-Z\s/]+", val):
                return val
    return None


def _try_tesseract(
    image: Image.Image,
    field_names: list[str],
    doc_type: str,
) -> dict[str, tuple[str | None, float]] | None:
    try:
        import pytesseract
    except ImportError:
        log.debug("tesseract_skipped", reason="pytesseract not installed")
        return None

    try:
        text = pytesseract.image_to_string(image, config="--psm 6")
    except Exception as exc:
        log.warning("tesseract_error", error=str(exc))
        return None

    if not text.strip():
        log.warning("tesseract_empty")
        return None

    result: dict[str, tuple[str | None, float]] = {}
    found = 0
    for name in field_names:
        val = _extract_by_label(name, text)
        if val:
            result[name] = (val, 0.72)
            found += 1
        else:
            result[name] = (None, 0.0)

    if found == 0:
        log.warning("tesseract_no_fields_found", doc_type=doc_type)
        return None  # let next backend try

    log.info("ocr_done", backend="tesseract", doc_type=doc_type, fields_found=found)
    return result


# ---------------------------------------------------------------------------
# Backend 3: Ollama (local VLM)
# ---------------------------------------------------------------------------


def _try_ollama(
    image: Image.Image,
    field_names: list[str],
    doc_type: str,
) -> dict[str, tuple[str | None, float]] | None:
    data = _post_json(
        f"{_OLLAMA_URL}/api/chat",
        {
            "model": _OLLAMA_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": _build_prompt(field_names, doc_type),
                    "images": [_prepare_for_vlm(image)],
                }
            ],
            "stream": False,
            "options": {"temperature": 0},
        },
        timeout=_OLLAMA_TIMEOUT,
    )
    if data is None:
        return None

    raw = data.get("message", {}).get("content", "").strip()
    extracted = _parse_json(raw)
    if extracted is None:
        log.warning("ollama_parse_error", model=_OLLAMA_MODEL, raw=raw[:200])
        return None

    log.info("ocr_done", backend="ollama", model=_OLLAMA_MODEL, doc_type=doc_type)
    return _fields_from(extracted, field_names)


# ---------------------------------------------------------------------------
# Backend 4: Google Gemini Flash (free tier)
# ---------------------------------------------------------------------------


def _try_gemini(
    image: Image.Image,
    field_names: list[str],
    doc_type: str,
) -> dict[str, tuple[str | None, float]] | None:
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log.warning("gemini_skipped", reason="GOOGLE_API_KEY / GEMINI_API_KEY not set")
        return None

    # Google OAuth access tokens start with "ya29."; everything else is an API key.
    is_oauth = api_key.startswith("ya29.")
    log.info(
        "gemini_attempt",
        model=_GEMINI_MODEL,
        key_prefix=api_key[:10],
        auth="bearer" if is_oauth else "apikey",
    )

    base_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:generateContent"
    )
    url = base_url if is_oauth else f"{base_url}?key={api_key}"

    payload: dict[str, Any] = {
        "contents": [
            {
                "parts": [
                    {"inlineData": {"mimeType": "image/png", "data": _prepare_for_vlm(image)}},
                    {"text": _build_prompt(field_names, doc_type)},
                ]
            }
        ],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 512},
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if is_oauth else {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_GEMINI_TIMEOUT) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:500]
        log.warning("gemini_http_error", status=exc.code, reason=exc.reason, body=body)
        return None
    except urllib.error.URLError as exc:
        log.warning("gemini_connection_error", error=str(exc))
        return None
    except Exception as exc:
        log.warning("gemini_error", error=str(exc))
        return None

    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as exc:
        log.warning("gemini_response_error", error=str(exc), data=str(data)[:200])
        return None

    extracted = _parse_json(raw)
    if extracted is None:
        log.warning("gemini_parse_error", raw=raw[:200])
        return None

    log.info("ocr_done", backend="gemini", model=_GEMINI_MODEL, doc_type=doc_type)
    return _fields_from(extracted, field_names)


# ---------------------------------------------------------------------------
# Backend 5: Anthropic (fallback — incurs API cost)
# ---------------------------------------------------------------------------


def _try_anthropic(
    image: Image.Image,
    field_names: list[str],
    doc_type: str,
) -> dict[str, tuple[str | None, float]] | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        log.warning("anthropic_package_missing")
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": _prepare_for_vlm(image),
                            },
                        },
                        {"type": "text", "text": _build_prompt(field_names, doc_type)},
                    ],
                }
            ],
        )
    except Exception as exc:
        log.warning("anthropic_ocr_error", error=str(exc))
        return None

    raw = message.content[0].text.strip()  # type: ignore[union-attr]
    extracted = _parse_json(raw)
    if extracted is None:
        log.warning("anthropic_parse_error", raw=raw[:200])
        return None

    log.info("ocr_done", backend="anthropic", doc_type=doc_type)
    return _fields_from(extracted, field_names)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def extract_handwritten_fields(
    image: Image.Image,
    field_names: list[str],
    doc_type: str,
) -> dict[str, tuple[str | None, float]]:
    """Extract handwritten field values from a form image.

    Priority: Ollama (local) → Gemini Flash (free cloud) → Anthropic (paid cloud).
    Returns an empty dict when no backend succeeds.
    """
    if not field_names:
        return {}

    result = _try_tesseract(image, field_names, doc_type)
    if result is not None:
        return result

    result = _try_ollama(image, field_names, doc_type)
    if result is not None:
        return result

    result = _try_gemini(image, field_names, doc_type)
    if result is not None:
        return result

    result = _try_anthropic(image, field_names, doc_type)
    if result is not None:
        return result

    log.warning(
        "ocr_skipped",
        reason="no backend available — install tesseract-ocr, Ollama, or set GOOGLE_API_KEY",
    )
    return {}
