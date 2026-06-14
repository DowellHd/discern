"""Vision-based OCR for handwritten form fields using the Anthropic API.

Falls back gracefully (returning an empty dict) when the API key is absent
or the call fails, so the rest of the pipeline keeps working.
"""

from __future__ import annotations

import base64
import io
import json
import os
from typing import Any

import structlog
from PIL import Image

log = structlog.get_logger()

# Confidence reported when Claude successfully extracts a value
_CONF_HIT = 0.82
_CONF_MISS = 0.0


def extract_handwritten_fields(
    image: Image.Image,
    field_names: list[str],
    doc_type: str,
) -> dict[str, tuple[str | None, float]]:
    """Call Claude Vision to extract handwritten field values from a form image.

    Returns a dict mapping field_name -> (value, confidence).
    Returns an empty dict on any error, missing key, or when field_names is empty.
    """
    if not field_names:
        return {}

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning("handwritten_ocr_skipped", reason="ANTHROPIC_API_KEY not set")
        return {}

    try:
        import anthropic  # guarded import — not a hard dep at module load time
    except ImportError:
        log.warning("handwritten_ocr_skipped", reason="anthropic package not installed")
        return {}

    # Encode the full-resolution image as base64 PNG (not the 224×224 tensor crop)
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    image_b64 = base64.standard_b64encode(buf.getvalue()).decode()

    field_list = "\n".join(f"- {name}" for name in field_names)
    prompt = (
        f"This is a church {doc_type.replace('_', ' ')} form. "
        "Extract the handwritten or typed text for each field listed below.\n\n"
        f"{field_list}\n\n"
        "Return ONLY a JSON object. Keys must exactly match the field names above. "
        "Values are the extracted text (string), or null if the field is blank or illegible. "
        "No explanation, no markdown — only the JSON object.\n"
        'Example: {"full_name": "Marcus Bell", "email": "m@example.com", "notes": null}'
    )

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
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
    except Exception as exc:
        log.warning("handwritten_ocr_api_error", error=str(exc))
        return {}

    raw = message.content[0].text.strip()  # type: ignore[union-attr]

    # Strip markdown code fences if Claude wraps the JSON
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw

    try:
        extracted: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("handwritten_ocr_parse_error", raw=raw[:200], error=str(exc))
        return {}

    result: dict[str, tuple[str | None, float]] = {}
    for name in field_names:
        raw_val = extracted.get(name)
        if raw_val is not None and str(raw_val).strip():
            result[name] = (str(raw_val).strip(), _CONF_HIT)
        else:
            result[name] = (None, _CONF_MISS)

    log.info("handwritten_ocr_done", doc_type=doc_type, fields=list(result.keys()))
    return result
