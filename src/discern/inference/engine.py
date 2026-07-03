"""InferenceEngine: loads a checkpoint, runs FieldExtractor, decodes structured output."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import structlog
from PIL import Image

from discern.config import settings
from discern.data.preprocess import preprocess, preprocess_for_ocr
from discern.data.schema import DocumentSchema
from discern.inference import llm_postprocess
from discern.inference.ocr import extract_handwritten_fields

log = structlog.get_logger()

_IMG_SIZE = 224
_ALLOWED_MIME = {"image/jpeg", "image/png", "image/tiff", "application/pdf"}
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
    llm_refined: bool = False


class InferenceEngine:
    """Schema-aware inference: loads model, runs on a PIL image, decodes results."""

    def __init__(
        self,
        schema: DocumentSchema,
        checkpoint_path: Path | None = None,
        device: str | None = None,
    ) -> None:
        # Torch is imported here (not at module level) to defer its ~150 MB footprint
        # until the first request, keeping startup memory under Render's 512 MB limit.
        import gc

        import torch
        import torch.nn.functional as F
        import torchvision.transforms as T
        from discern.models.extractor import (
            CATEGORY_OPTIONS,
            DOC_TYPES,
            INTERESTS_OPTIONS,
            VISIT_TYPE_OPTIONS,
            FieldExtractor,
        )

        self._torch = torch
        self._F = F
        self._DOC_TYPES = DOC_TYPES
        self._VISIT_TYPE_OPTIONS = VISIT_TYPE_OPTIONS
        self._INTERESTS_OPTIONS = INTERESTS_OPTIONS
        self._CATEGORY_OPTIONS = CATEGORY_OPTIONS

        self.schema = schema
        self.device = torch.device(device or "cpu")
        self._transform = T.Compose(
            [T.Resize((_IMG_SIZE, _IMG_SIZE)), T.ToTensor(), T.Normalize(mean=[0.5], std=[0.5])]
        )
        self.model = FieldExtractor(pretrained=False).to(self.device)
        self._checkpoint_loaded = False

        if checkpoint_path and checkpoint_path.exists():
            ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
            self.model.load_state_dict(ckpt["model_state_dict"])
            del ckpt
            gc.collect()
            self._checkpoint_loaded = True
            log.info("checkpoint_loaded", path=str(checkpoint_path))
        else:
            log.warning("no_checkpoint", checkpoint=str(checkpoint_path))

        self.model.eval()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def predict(self, image: Image.Image, doc_type_override: str | None = None) -> InferenceResult:
        """Run inference on a PIL image; returns structured result."""
        torch = self._torch
        clean = strip_exif(image)
        processed = preprocess(clean)
        tensor = self._transform(processed).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)

        if doc_type_override and doc_type_override in self.schema.document_types:
            dt_name = doc_type_override
        else:
            dt_probs = self._F.softmax(logits["doc_type"], dim=-1)[0]
            dt_name = self._DOC_TYPES[int(dt_probs.argmax().item())]

        spec = self.schema.document_types.get(dt_name)
        hw_names = [f.name for f in spec.fields if f.capture == "handwritten"] if spec else []

        ocr_image = preprocess_for_ocr(clean) if hw_names else None
        ocr: dict[str, tuple[str | None, float]] = (
            extract_handwritten_fields(ocr_image, hw_names, dt_name)
            if ocr_image is not None
            else {}
        )

        result = self._decode(logits, ocr, doc_type_name=dt_name)

        if settings.llm_postprocess:
            non_sensitive = {f.name: f.value for f in result.fields if not f.sensitive}
            corrections = llm_postprocess.refine(
                result.doc_type, non_sensitive, settings.llm_postprocess_budget_cents
            )
            if corrections:
                result = self._apply_corrections(result, corrections)

        return result

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
        logits: dict,
        ocr: dict[str, tuple[str | None, float]] | None = None,
        doc_type_name: str | None = None,
    ) -> InferenceResult:
        F = self._F
        dt_probs = F.softmax(logits["doc_type"], dim=-1)[0]
        dt_idx = int(dt_probs.argmax().item())
        model_dt_name = self._DOC_TYPES[dt_idx]
        model_dt_conf = float(dt_probs[dt_idx].item())

        if doc_type_name is not None:
            dt_name = doc_type_name
            dt_conf = model_dt_conf if dt_name == model_dt_name else 1.0
        else:
            dt_name = model_dt_name
            dt_conf = model_dt_conf

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
    def _apply_corrections(result: InferenceResult, corrections: dict[str, str]) -> InferenceResult:
        refined: list[FieldResult] = []
        for f in result.fields:
            if f.name in corrections:
                refined.append(
                    FieldResult(
                        name=f.name,
                        value=corrections[f.name],
                        confidence=max(f.confidence, 0.85),
                        capture=f.capture,
                        sensitive=f.sensitive,
                    )
                )
            else:
                refined.append(f)
        return InferenceResult(
            doc_type=result.doc_type,
            doc_type_confidence=result.doc_type_confidence,
            fields=refined,
            llm_refined=True,
        )

    def _decode_field(
        self,
        name: str,
        value_type: str,
        capture: str,
        logits: dict,
        ocr: dict[str, tuple[str | None, float]],
    ) -> tuple[str | None, float]:
        torch = self._torch
        F = self._F

        if capture != "checkbox":
            return ocr.get(name, (None, 0.0))

        if name == "visit_type":
            probs = F.softmax(logits["visit_type"][0], dim=-1)
            idx = int(probs.argmax().item())
            return self._VISIT_TYPE_OPTIONS[idx], float(probs[idx].item())

        if name == "interests":
            probs = torch.sigmoid(logits["interests"][0])
            selected = [self._INTERESTS_OPTIONS[i] for i, p in enumerate(probs) if p.item() > 0.5]
            conf = float(probs.max().item())
            return (", ".join(selected) if selected else "none"), conf

        if name == "category":
            probs = F.softmax(logits["category"][0], dim=-1)
            idx = int(probs.argmax().item())
            return self._CATEGORY_OPTIONS[idx], float(probs[idx].item())

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


def pdf_first_page(data: bytes) -> Image.Image:
    """Render the first page of a PDF at 2× resolution and return a PIL Image."""
    import fitz  # PyMuPDF — guarded import so the package is only required at runtime

    doc = fitz.open(stream=data, filetype="pdf")
    page = doc[0]
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
