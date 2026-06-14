"""Vision-based OCR for handwritten form fields.

Extraction backends tried in order:
  1. Ollama (local VLM — free, no external service)
  2. Anthropic Claude Vision (requires ANTHROPIC_API_KEY, has usage cost)

Set OLLAMA_URL / OLLAMA_MODEL env vars to point at a non-default Ollama
instance or a different model.  A vision-capable model must be pulled, e.g.:
  ollama pull llava:7b          # popular, fast, 4.7 GB
  ollama pull qwen2-vl:7b      # better at structured forms, 4.4 GB
"""

from __future__ import annotations

import base64
import io
import json
import os
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

# Resize images to this max dimension before sending to any VLM.
# Keeps latency reasonable without sacrificing OCR accuracy.
_VLM_MAX_DIM = 1024


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
    """Parse JSON from a VLM response; strips markdown fences and locates embedded objects."""
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1].lstrip("json").strip() if len(parts) > 1 else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to pull out the first complete JSON object (handles preamble/postamble)
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


# ---------------------------------------------------------------------------
# Backend: Ollama
# ---------------------------------------------------------------------------


def _try_ollama(
    image: Image.Image,
    field_names: list[str],
    doc_type: str,
) -> dict[str, tuple[str | None, float]] | None:
    """Send the image to a local Ollama vision model.  Returns None if unavailable."""
    image_b64 = _prepare_for_vlm(image)
    payload = json.dumps(
        {
            "model": _OLLAMA_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": _build_prompt(field_names, doc_type),
                    "images": [image_b64],
                }
            ],
            "stream": False,
            "options": {"temperature": 0},
        }
    ).encode()

    req = urllib.request.Request(
        f"{_OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_OLLAMA_TIMEOUT) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as exc:
        log.debug("ollama_unavailable", error=str(exc))
        return None
    except Exception as exc:
        log.warning("ollama_ocr_error", error=str(exc))
        return None

    raw = data.get("message", {}).get("content", "").strip()
    extracted = _parse_json(raw)
    if extracted is None:
        log.warning("ollama_parse_error", model=_OLLAMA_MODEL, raw=raw[:200])
        return None

    log.info("ocr_done", backend="ollama", model=_OLLAMA_MODEL, doc_type=doc_type)
    return _fields_from(extracted, field_names)


# ---------------------------------------------------------------------------
# Backend: Anthropic (fallback — incurs API cost)
# ---------------------------------------------------------------------------


def _try_anthropic(
    image: Image.Image,
    field_names: list[str],
    doc_type: str,
) -> dict[str, tuple[str | None, float]] | None:
    """Call Claude Vision.  Returns None when the key is absent or the call fails."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        log.warning("anthropic_package_missing")
        return None

    image_b64 = _prepare_for_vlm(image)
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
                                "data": image_b64,
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

    Tries Ollama (local, free) first; falls back to Anthropic if an API key is
    configured.  Returns an empty dict when no backend succeeds.

    Returns a dict mapping field_name -> (value, confidence).
    """
    if not field_names:
        return {}

    result = _try_ollama(image, field_names, doc_type)
    if result is not None:
        return result

    result = _try_anthropic(image, field_names, doc_type)
    if result is not None:
        return result

    log.warning(
        "ocr_skipped", reason="no backend available — install Ollama or set ANTHROPIC_API_KEY"
    )
    return {}
