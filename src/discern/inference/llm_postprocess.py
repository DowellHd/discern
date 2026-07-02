"""Optional LLM post-processor: normalizes and corrects extracted field values.

Backends tried in cost order:
  1. Gemini Flash — free tier (15 RPM / 1 M TPD)
  2. Haiku        — paid but cheap (~0.03 ¢/call); skipped if estimated cost > budget

Both backends receive a text-only prompt (no image) since OCR already ran.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

import structlog

log = structlog.get_logger()

# Haiku 4.5 pricing ($ per million tokens)
_HAIKU_INPUT_CPM = 0.80
_HAIKU_OUTPUT_CPM = 4.00
# Conservative upper bound on output size for cost estimation
_ESTIMATED_OUTPUT_CHARS = 200

_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
_GEMINI_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


def _build_prompt(doc_type: str, field_values: dict[str, str | None]) -> str:
    return (
        f"Document type: {doc_type}\n"
        "Extracted field values (may contain OCR errors):\n"
        f"{json.dumps(field_values, indent=2)}\n\n"
        "Return a JSON object with ONLY the fields that need correction or normalization.\n"
        "Rules:\n"
        '- Fix OCR typos (e.g. "0regon" → "Oregon", "Jannuary" → "January")\n'
        "- Normalize dates to MM/DD/YYYY\n"
        "- Normalize phone numbers to (XXX) XXX-XXXX\n"
        "- Normalize currency amounts to $X.XX\n"
        "- Do NOT invent values for null or blank fields\n"
        "- Return {} if nothing needs changing\n"
        "Output ONLY valid JSON, no explanation."
    )


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


def estimate_cost_cents(prompt: str) -> float:
    """Rough per-call cost estimate in US cents for Haiku."""
    input_tokens = len(prompt) / 4
    output_tokens = _ESTIMATED_OUTPUT_CHARS / 4
    return (input_tokens * _HAIKU_INPUT_CPM + output_tokens * _HAIKU_OUTPUT_CPM) / 1_000_000 * 100


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _parse_json(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1].lstrip("json").strip() if len(parts) > 1 else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return None


def _post_json(
    url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int
) -> dict[str, Any] | None:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())  # type: ignore[return-value]
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:300]
        log.warning("llm_postprocess_http_error", status=exc.code, body=body)
    except urllib.error.URLError as exc:
        log.debug("llm_postprocess_unavailable", url=url, error=str(exc))
    except Exception as exc:
        log.warning("llm_postprocess_error", url=url, error=str(exc))
    return None


# ---------------------------------------------------------------------------
# Backend 1: Gemini Flash (free tier)
# ---------------------------------------------------------------------------


def _try_gemini(prompt: str) -> dict[str, Any] | None:
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    is_oauth = api_key.startswith("ya29.")
    base = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:generateContent"
    )
    url = base if is_oauth else f"{base}?key={api_key}"
    headers = {"Authorization": f"Bearer {api_key}"} if is_oauth else {}

    data = _post_json(
        url,
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 256},
        },
        headers,
        _GEMINI_TIMEOUT,
    )
    if data is None:
        return None

    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as exc:
        log.warning("llm_postprocess_gemini_response_error", error=str(exc))
        return None

    result = _parse_json(raw)
    if result is None:
        log.warning("llm_postprocess_gemini_parse_error", raw=raw[:200])
        return None

    log.info("llm_postprocess_done", backend="gemini", model=_GEMINI_MODEL)
    return result


# ---------------------------------------------------------------------------
# Backend 2: Anthropic Haiku (paid, cheap)
# ---------------------------------------------------------------------------


def _try_haiku(prompt: str, budget_cents: float) -> dict[str, Any] | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    cost = estimate_cost_cents(prompt)
    if cost > budget_cents:
        log.warning(
            "llm_postprocess_budget_exceeded",
            estimated_cents=round(cost, 4),
            budget_cents=budget_cents,
        )
        return None

    try:
        import anthropic
    except ImportError:
        log.warning("llm_postprocess_anthropic_missing")
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()  # type: ignore[union-attr]
    except Exception as exc:
        log.warning("llm_postprocess_haiku_error", error=str(exc))
        return None

    result = _parse_json(raw)
    if result is None:
        log.warning("llm_postprocess_haiku_parse_error", raw=raw[:200])
        return None

    log.info("llm_postprocess_done", backend="haiku", estimated_cents=round(cost, 4))
    return result


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def refine(
    doc_type: str,
    field_values: dict[str, str | None],
    budget_cents: float = 1.0,
) -> dict[str, str]:
    """Return a dict of corrected field values (only changed keys).

    Tries Gemini Flash (free) first, then Haiku (cost-checked).
    Returns {} when no backend is available or nothing needs correcting.
    """
    if not field_values:
        return {}

    prompt = _build_prompt(doc_type, field_values)

    corrections = _try_gemini(prompt)
    if corrections is None:
        corrections = _try_haiku(prompt, budget_cents)

    if not corrections:
        return {}

    # Return only valid string corrections for known fields
    return {
        k: str(v).strip()
        for k, v in corrections.items()
        if k in field_values and isinstance(v, str) and str(v).strip()
    }
