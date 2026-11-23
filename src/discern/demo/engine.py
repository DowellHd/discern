"""DemoInferenceEngine: a drop-in for `InferenceEngine` that needs no torch, model or network."""

from __future__ import annotations

import structlog
from PIL import Image

from discern.data.schema import DocumentSchema
from discern.demo import mock
from discern.demo.samples import recognize
from discern.inference.engine import InferenceEngine, InferenceResult, strip_exif

log = structlog.get_logger()


class DemoInferenceEngine(InferenceEngine):
    """Recognises the bundled sample documents and returns plausible values for anything else.

    Subclasses the real engine so type checks and `validate_upload` behave identically, but
    skips its constructor: no torch import, no checkpoint, no OCR/LLM backends.
    """

    def __init__(self, schema: DocumentSchema) -> None:  # noqa: D107 - deliberately not calling super()
        self.schema = schema
        # Reported by /health as "model_loaded"; the demo has nothing to load, so it is ready.
        self._checkpoint_loaded = True

    def predict(self, image: Image.Image, doc_type_override: str | None = None) -> InferenceResult:
        clean = strip_exif(image)
        known = recognize(clean)
        seed = mock.image_seed(clean)

        if doc_type_override and doc_type_override in self.schema.document_types:
            doc_type, doc_conf = doc_type_override, 1.0
        elif known is not None:
            doc_type = known.doc_type
            doc_conf = 0.90 + (seed % 90) / 1000  # 0.900 - 0.989
        else:
            doc_type = mock.pick_doc_type(self.schema, seed)
            doc_conf = 0.52 + (seed % 260) / 1000  # 0.520 - 0.779: unsure, goes to review

        exact = known is not None and known.doc_type == doc_type
        values = (
            known.fields
            if exact and known
            else mock.illustrative_values(self.schema, doc_type, seed)
        )
        result = mock.build_result(
            self.schema, doc_type, values, seed=seed, exact=exact, doc_type_confidence=doc_conf
        )
        log.info(
            "demo_extract",
            doc_type=doc_type,
            recognised_sample=known.file if known else None,
            exact=exact,
        )
        return result
