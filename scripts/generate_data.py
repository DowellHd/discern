"""Generates synthetic training images driven by configs/documents.yaml."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from discern.config import load_document_schema, settings
from discern.data.generator import DocumentGenerator
from discern.data.schema import parse_document_schema

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic document images.")
    parser.add_argument("--n", type=int, default=10, help="Samples per document type")
    parser.add_argument("--doc-type", default=None, help="Limit to one document type")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=settings.data_dir / "synthetic",
        help="Output directory (default: data/synthetic/)",
    )
    parser.add_argument("--seed", type=int, default=settings.seed)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    raw = load_document_schema()
    schema = parse_document_schema(raw)
    gen = DocumentGenerator(schema.document_types, seed=args.seed)

    doc_types = [args.doc_type] if args.doc_type else list(schema.document_types.keys())

    for doc_type in doc_types:
        if doc_type not in schema.document_types:
            log.error("Unknown doc type %r — skipping", doc_type)
            continue
        for i in range(args.n):
            sample = gen.generate(doc_type)
            img_path, _ = gen.save(sample, args.output_dir)
            if i == 0:
                log.info("Writing %s → %s", doc_type, img_path.parent)
        log.info("%s: %d samples written", doc_type, args.n)

    log.info("Done. Output: %s", args.output_dir)


if __name__ == "__main__":
    sys.exit(main())
