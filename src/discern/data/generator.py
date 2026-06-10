"""Renders synthetic document images from schema-driven field values."""

from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from discern.data.schema import DocTypeSpec, FieldSpec
from discern.data.synthesizer import ValueSynthesizer

_CARD_W = 760
_CARD_H = 520
_MARGIN = 40
_LABEL_W = 200
_LINE_H = 36
_CHECKBOX_SZ = 14

_FONT_PATHS = [
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Geneva.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


@dataclass
class SyntheticSample:
    doc_type: str
    image: Image.Image
    labels: dict[str, Any]


class DocumentGenerator:
    """Renders synthetic form images for a given document type."""

    def __init__(self, schema_fields: dict[str, DocTypeSpec], seed: int = 42) -> None:
        self._schema = schema_fields
        self._rng = random.Random(seed)
        np.random.seed(seed)
        self._synthesizer = ValueSynthesizer(seed=seed)
        self._font_title = _load_font(18)
        self._font_label = _load_font(13)
        self._font_value = _load_font(13)

    def generate(self, doc_type: str) -> SyntheticSample:
        if doc_type not in self._schema:
            raise ValueError(f"Unknown doc type: {doc_type!r}")
        spec = self._schema[doc_type]
        labels = self._synthesizer.synthesize_document(spec.fields)
        img = self._render(doc_type, spec, labels)
        img = self._augment(img)
        return SyntheticSample(doc_type=doc_type, image=img, labels=labels)

    def save(self, sample: SyntheticSample, output_dir: Path) -> tuple[Path, Path]:
        target = output_dir / sample.doc_type
        target.mkdir(parents=True, exist_ok=True)
        name = uuid.uuid4().hex
        img_path = target / f"{name}.png"
        lbl_path = target / f"{name}.json"
        sample.image.save(img_path)
        lbl_path.write_text(
            json.dumps(
                {"doc_type": sample.doc_type, "fields": sample.labels},
                indent=2,
                default=str,
            )
        )
        return img_path, lbl_path

    def _render(self, doc_type: str, spec: DocTypeSpec, labels: dict[str, Any]) -> Image.Image:
        img = Image.new("RGB", (_CARD_W, _CARD_H), color=(252, 252, 248))
        draw = ImageDraw.Draw(img)
        draw.rectangle(
            (_MARGIN // 2, _MARGIN // 2, _CARD_W - _MARGIN // 2, _CARD_H - _MARGIN // 2),
            outline=(180, 180, 180),
            width=2,
        )
        title = doc_type.replace("_", " ").upper()
        draw.text((_MARGIN, _MARGIN), title, fill=(40, 40, 40), font=self._font_title)
        y = _MARGIN + _LINE_H + 8
        for field in spec.fields:
            value = labels.get(field.name)
            y = self._render_field(draw, field, value, y)
            if y + _LINE_H > _CARD_H - _MARGIN:
                break
        return img

    def _render_field(self, draw: ImageDraw.ImageDraw, field: FieldSpec, value: Any, y: int) -> int:
        if field.capture == "checkbox":
            return self._render_checkbox_field(draw, field, value, y)
        label = field.name.replace("_", " ").title()
        draw.text((_MARGIN, y + 2), f"{label}:", fill=(80, 80, 80), font=self._font_label)
        line_y = y + _LINE_H - 4
        draw.line(
            [(_MARGIN + _LABEL_W, line_y), (_CARD_W - _MARGIN, line_y)],
            fill=(180, 180, 180),
            width=1,
        )
        if value is not None:
            jitter = self._rng.randint(-2, 2)
            draw.text(
                (_MARGIN + _LABEL_W + 4, y + jitter),
                str(value),
                fill=(20, 30, 80),
                font=self._font_value,
            )
        return y + _LINE_H + 4

    def _render_checkbox_field(
        self, draw: ImageDraw.ImageDraw, field: FieldSpec, value: Any, y: int
    ) -> int:
        label = field.name.replace("_", " ").title()
        draw.text((_MARGIN, y + 2), f"{label}:", fill=(80, 80, 80), font=self._font_label)
        y += _LINE_H

        options = field.options or []
        if field.value_type == "bool":
            options = ["Yes", "No"]
            selected: set[str] = {"Yes"} if value else {"No"}
        elif field.value_type == "multiselect":
            selected = set(value) if isinstance(value, list) else set()
        else:
            selected = {str(value)} if value is not None else set()

        x = _MARGIN + 8
        for opt in options:
            checked = opt in selected
            cb_x1, cb_y1 = x, y + 2
            cb_x2, cb_y2 = cb_x1 + _CHECKBOX_SZ, cb_y1 + _CHECKBOX_SZ
            draw.rectangle((cb_x1, cb_y1, cb_x2, cb_y2), outline=(60, 60, 60), width=1)
            if checked:
                draw.line(
                    [(cb_x1 + 2, cb_y1 + 2), (cb_x2 - 2, cb_y2 - 2)], fill=(20, 30, 80), width=2
                )
                draw.line(
                    [(cb_x2 - 2, cb_y1 + 2), (cb_x1 + 2, cb_y2 - 2)], fill=(20, 30, 80), width=2
                )
            opt_label = opt.replace("_", " ").title()
            draw.text((cb_x2 + 6, y + 2), opt_label, fill=(60, 60, 60), font=self._font_label)
            x += _CHECKBOX_SZ + 8 + _estimate_text_width(opt_label, 13) + 20
            if x > _CARD_W - _MARGIN - 100:
                x = _MARGIN + 8
                y += _LINE_H
        return y + _LINE_H + 4

    def _augment(self, img: Image.Image) -> Image.Image:
        angle = self._rng.uniform(-2.5, 2.5)
        img = img.rotate(angle, fillcolor=(252, 252, 248), expand=False)
        if self._rng.random() < 0.4:
            img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
        arr = np.array(img, dtype=np.float32)
        noise = np.random.normal(0, 3, arr.shape).astype(np.float32)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(arr)


def _estimate_text_width(text: str, font_size: int) -> int:
    return int(len(text) * font_size * 0.55)
