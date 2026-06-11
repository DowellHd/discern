"""Draw an annotated overlay image showing extracted fields and confidence scores."""

from __future__ import annotations

import textwrap

from PIL import Image, ImageDraw, ImageFont

from discern.inference.engine import InferenceResult

_FONT_PATHS = [
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Geneva.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
_PANEL_W = 320
_ROW_H = 40
_PADDING = 12
_HDR_H = 48

_CONF_HIGH = (72, 199, 116)  # green
_CONF_MED = (245, 166, 35)  # amber
_CONF_LOW = (220, 80, 80)  # red
_PANEL_BG = (245, 247, 250)
_HDR_BG = (30, 50, 90)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in _FONT_PATHS:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _conf_color(conf: float) -> tuple[int, int, int]:
    if conf >= 0.75:
        return _CONF_HIGH
    if conf >= 0.45:
        return _CONF_MED
    return _CONF_LOW


def draw_overlay(image: Image.Image, result: InferenceResult) -> Image.Image:
    """Compose original image + annotated fields panel side-by-side."""
    orig_w, orig_h = image.size
    panel_h = _HDR_H + len(result.fields) * _ROW_H + _PADDING * 2
    canvas_h = max(orig_h, panel_h)
    canvas_w = orig_w + _PANEL_W

    canvas = Image.new("RGB", (canvas_w, canvas_h), _PANEL_BG)
    canvas.paste(image, (0, (canvas_h - orig_h) // 2))

    draw = ImageDraw.Draw(canvas)
    px = orig_w  # panel x-start

    # Header
    draw.rectangle([px, 0, canvas_w, _HDR_H], fill=_HDR_BG)
    f_hdr = _load_font(14)
    doc_label = result.doc_type.replace("_", " ").title()
    draw.text(
        (px + _PADDING, _PADDING),
        f"{doc_label}  {result.doc_type_confidence:.0%}",
        fill=(255, 255, 255),
        font=f_hdr,
    )

    # Field rows
    f_label = _load_font(11)
    f_val = _load_font(12)
    y = _HDR_H + _PADDING
    for field in result.fields:
        color = _conf_color(field.confidence)

        # Confidence bar (left 4 px strip)
        draw.rectangle([px, y, px + 4, y + _ROW_H - 4], fill=color)

        # Field name
        label = field.name.replace("_", " ").title()
        draw.text((px + 10, y + 2), label, fill=(80, 90, 110), font=f_label)

        # Field value (truncate long values)
        raw_val = field.value or "—"
        if field.sensitive and field.value == "[REDACTED]":
            display = "••••••"
        else:
            display = textwrap.shorten(raw_val, width=28, placeholder="…")

        draw.text((px + 10, y + 16), display, fill=(20, 30, 50), font=f_val)

        # Confidence pct (right-aligned)
        conf_txt = f"{field.confidence:.0%}"
        draw.text((canvas_w - _PADDING - 36, y + 10), conf_txt, fill=color, font=f_label)

        y += _ROW_H

    return canvas
