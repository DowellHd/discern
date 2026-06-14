"""InferenceEngine: loads a checkpoint, runs FieldExtractor, decodes structured output."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import structlog
import torch
import torch.nn.functional as F
import torchvision.transforms as T
from PIL import Image

from discern.data.preprocess import preprocess
from discern.data.schema import DocumentSchema
from discern.inference.ocr import extract_handwritten_fields
from discern.models.extractor import (
    CATEGORY_OPTIONS,
    DOC_TYPES,
    INTERESTS_OPTIONS,
    VISIT_TYPE_OPTIONS,
    FieldExtractor,
)

log = structlog.get_logger()

_IMG_SIZE = 224
_transform = T.Compose(
    [T.Resize((_IMG_SIZE, _IMG_SIZE)), T.ToTensor(), T.Normalize(mean=[0.5], std=[0.5])]
)

_ALLOWED_MIME = {"image/jpeg", "image/png", "image/tiff"}
_MAX_BYTES = 20 * 1024 * 1024  # 20 MB


@dataclass
class FieldResult:
    name: str
    value: str | None
    confidence: float
    capture: str
    sensitive: bool


@dataclass
class InferenceResult:
    doc_type: str
    doc_type_confidence: float
    fields: list[FieldResult]


class InferenceEngine:
    """Schema-aware inference: loads model, runs on a PIL image, decodes results."""

    def __init__(
        self,
        schema: DocumentSchema,
        checkpoint_path: Path | None = None,
        device: str | None = None,
    ) -> None:
        self.schema = schema
        self.device = torch.device(device or "cpu")
        self.model = FieldExtractor(pretrained=False).to(self.device)
        self._checkpoint_loaded = False

        if checkpoint_path and checkpoint_path.exists():
            ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
            self.model.load_state_dict(ckpt["model_state_dict"])
            self._checkpoint_loaded = True
            log.info("checkpoint_loaded", path=str(checkpoint_path))
        else:
            log.warning("no_checkpoint", checkpoint=str(checkpoint_path))

        self.model.eval()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    @torch.no_grad()
    def predict(self, image: Image.Image) -> InferenceResult:
        """Run inference on a PIL image; returns structured result."""
        clean = strip_exif(image)
        processed = preprocess(clean)
        tensor = _transform(processed).unsqueeze(0).to(self.device)
        logits = self.model(tensor)

        # Determine document type first so OCR targets only the relevant fields.
        dt_probs = F.softmax(logits["doc_type"], dim=-1)[0]
        dt_name = DOC_TYPES[int(dt_probs.argmax().item())]
        spec = self.schema.document_types.get(dt_name)
        hw_names = [f.name for f in spec.fields if f.capture == "handwritten"] if spec else []

        # Run Claude Vision OCR on the full-resolution image for handwritten fields.
        ocr: dict[str, tuple[str | None, float]] = (
            extract_handwritten_fields(clean, hw_names, dt_name) if hw_names else {}
        )

        return self._decode(logits, ocr)

    @staticmethod
    def validate_upload(data: bytes, content_type: str) -> None:
        """Raise ValueError if the upload is too large or the wrong type."""
        if len(data) > _MAX_BYTES:
            raise ValueError(f"File too large: {len(data) // 1024} KB (max 20 MB)")
        if content_type not in _ALLOWED_MIME:
            raise ValueError(f"Unsupported type {content_type!r}. Allowed: {sorted(_ALLOWED_MIME)}")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _decode(
        self,
        logits: dict[str, torch.Tensor],
        ocr: dict[str, tuple[str | None, float]] | None = None,
    ) -> InferenceResult:
        dt_probs = F.softmax(logits["doc_type"], dim=-1)[0]
        dt_idx = int(dt_probs.argmax().item())
        dt_name = DOC_TYPES[dt_idx]
        dt_conf = float(dt_probs[dt_idx].item())

        spec = self.schema.document_types.get(dt_name)
        if spec is None:
            return InferenceResult(doc_type=dt_name, doc_type_confidence=dt_conf, fields=[])

        fields: list[FieldResult] = []
        for field in spec.fields:
            value, confidence = self._decode_field(
                field.name, field.value_type, field.capture, logits, ocr or {}
            )
            display_value = "[REDACTED]" if field.sensitive and value is not None else value
            fields.append(
                FieldResult(
                    name=field.name,
                    value=display_value,
                    confidence=round(confidence, 4),
                    capture=field.capture,
                    sensitive=field.sensitive,
                )
            )
        return InferenceResult(
            doc_type=dt_name, doc_type_confidence=round(dt_conf, 4), fields=fields
        )

    @staticmethod
    def _decode_field(
        name: str,
        value_type: str,
        capture: str,
        logits: dict[str, torch.Tensor],
        ocr: dict[str, tuple[str | None, float]],
    ) -> tuple[str | None, float]:
        if capture != "checkbox":
            return ocr.get(name, (None, 0.0))

        if name == "visit_type":
            probs = F.softmax(logits["visit_type"][0], dim=-1)
            idx = int(probs.argmax().item())
            return VISIT_TYPE_OPTIONS[idx], float(probs[idx].item())

        if name == "interests":
            probs = torch.sigmoid(logits["interests"][0])
            selected = [INTERESTS_OPTIONS[i] for i, p in enumerate(probs) if p.item() > 0.5]
            conf = float(probs.max().item())
            return (", ".join(selected) if selected else "none"), conf

        if name == "category":
            probs = F.softmax(logits["category"][0], dim=-1)
            idx = int(probs.argmax().item())
            return CATEGORY_OPTIONS[idx], float(probs[idx].item())

        if name == "contact_ok":
            prob = float(torch.sigmoid(logits["contact_ok"][0]).item())
            return str(prob > 0.5), prob if prob > 0.5 else 1.0 - prob

        return None, 0.0


def strip_exif(image: Image.Image) -> Image.Image:
    """Return a copy of the image with EXIF metadata removed."""
    buf = io.BytesIO()
    fmt = image.format or "PNG"
    image.save(buf, format=fmt)
    buf.seek(0)
    clean = Image.open(buf)
    clean.load()
    return clean.copy()
