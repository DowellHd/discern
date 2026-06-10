"""Eval harness entry point — runs as `python -m scripts.evaluate`.

Milestone 1: smoke-test only. Loads the document schema and prints field counts.
Real metrics (P/R/F1, CER/WER, latency) are added in Milestone 5.
"""

from __future__ import annotations

from discern.config import load_document_schema


def main() -> None:
    schema = load_document_schema()

    doc_types = schema.get("document_types", {})
    region_types = schema.get("region_types", {})

    print("=== Discern — Evaluation Smoke Test ===")
    for doc_name, doc_cfg in doc_types.items():
        fields = doc_cfg.get("fields", [])
        print(f"  {doc_name}: {len(fields)} fields")
        for field in fields:
            flags = []
            if field.get("required"):
                flags.append("required")
            if field.get("sensitive"):
                flags.append("sensitive")
            if field.get("nullable"):
                flags.append("nullable")
            tag = f"  [{', '.join(flags)}]" if flags else ""
            print(f"    - {field['name']} ({field['value_type']}, {field['capture']}){tag}")

    for region_name, region_cfg in region_types.items():
        blocks = region_cfg.get("blocks", [])
        print(f"  {region_name}: {len(blocks)} block types")

    print("\nSmoke test passed. Full metrics active in Milestone 5.")


if __name__ == "__main__":
    main()
