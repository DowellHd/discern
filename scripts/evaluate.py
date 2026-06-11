"""Eval harness — run as `python -m scripts.evaluate`.

Evaluates the best checkpoint on a held-out synthetic split. Writes
reports/eval.json and reports/eval.md. Falls back to schema smoke-test
when no checkpoint is available.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))  # noqa: E402

from discern.config import load_document_schema, settings  # noqa: E402
from discern.data.schema import parse_document_schema  # noqa: E402


def _smoke_test(schema_raw: dict) -> None:
    doc_types = schema_raw.get("document_types", {})
    region_types = schema_raw.get("region_types", {})
    print("=== Discern — Schema Smoke Test ===")
    for name, cfg in doc_types.items():
        fields = cfg.get("fields", [])
        print(f"  {name}: {len(fields)} fields")
    for name, cfg in region_types.items():
        print(f"  {name}: {len(cfg.get('blocks', []))} blocks")
    print("\nSmoke test passed.")


def _run_full_eval(schema, ckpt_path: Path) -> dict:
    from discern.eval.metrics import evaluate_checkpoint
    from discern.inference.engine import InferenceEngine

    print(f"Loading checkpoint: {ckpt_path}")
    engine = InferenceEngine(schema=schema, checkpoint_path=ckpt_path)

    print("Evaluating on 150 synthetic held-out samples per doc type…")
    result = evaluate_checkpoint(engine, schema, n_samples=150, seed=999)
    return result.to_dict()


def _write_report(data: dict, reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = reports_dir / "eval.json"
    json_path.write_text(json.dumps(data, indent=2))
    print(f"JSON report: {json_path}")

    md_path = reports_dir / "eval.md"
    lines = [
        "# Discern — Eval Report",
        "",
        f"**Samples evaluated:** {data['n_samples']}",
        "",
        "## Results by Capture Type",
        "",
        "| Capture | Precision | Recall | F1 | CER | WER | p50 (ms) | p95 (ms) |",
        "|---------|-----------|--------|----|-----|-----|----------|----------|",
    ]
    for cap_data in data["by_capture"].values():
        lines.append(
            f"| {cap_data['capture']} "
            f"| {cap_data['precision']:.3f} "
            f"| {cap_data['recall']:.3f} "
            f"| {cap_data['f1']:.3f} "
            f"| {cap_data['cer']:.3f} "
            f"| {cap_data['wer']:.3f} "
            f"| {cap_data['p50_latency_ms']:.1f} "
            f"| {cap_data['p95_latency_ms']:.1f} |"
        )
    ov = data["overall"]
    lines += [
        f"| **overall** "
        f"| **{ov['precision']:.3f}** "
        f"| **{ov['recall']:.3f}** "
        f"| **{ov['f1']:.3f}** "
        f"| {ov['cer']:.3f} "
        f"| {ov['wer']:.3f} "
        f"| {ov['p50_latency_ms']:.1f} "
        f"| {ov['p95_latency_ms']:.1f} |",
        "",
        "> Handwritten field values are not extracted by the current model (OCR head not yet",
        "> trained); CER/WER = 1.0 for handwritten fields reflects this gap.",
    ]
    md_path.write_text("\n".join(lines) + "\n")
    print(f"Markdown report: {md_path}")


def _print_table(data: dict) -> None:
    print("\n=== Discern Eval Results ===")
    print(
        f"{'Capture':<12} {'P':>6} {'R':>6} {'F1':>6} {'CER':>6} {'WER':>6} {'p50ms':>7} {'p95ms':>7}"
    )
    print("-" * 62)
    for cap_data in data["by_capture"].values():
        print(
            f"{cap_data['capture']:<12} "
            f"{cap_data['precision']:>6.3f} "
            f"{cap_data['recall']:>6.3f} "
            f"{cap_data['f1']:>6.3f} "
            f"{cap_data['cer']:>6.3f} "
            f"{cap_data['wer']:>6.3f} "
            f"{cap_data['p50_latency_ms']:>7.1f} "
            f"{cap_data['p95_latency_ms']:>7.1f}"
        )
    ov = data["overall"]
    print("-" * 62)
    print(
        f"{'overall':<12} "
        f"{ov['precision']:>6.3f} "
        f"{ov['recall']:>6.3f} "
        f"{ov['f1']:>6.3f} "
        f"{ov['cer']:>6.3f} "
        f"{ov['wer']:>6.3f} "
        f"{ov['p50_latency_ms']:>7.1f} "
        f"{ov['p95_latency_ms']:>7.1f}"
    )


def main() -> None:
    raw = load_document_schema()
    schema = parse_document_schema(raw)

    ckpt_path = settings.checkpoints_dir / "best.pt"
    if not ckpt_path.exists():
        _smoke_test(raw)
        return

    data = _run_full_eval(schema, ckpt_path)
    _print_table(data)
    _write_report(data, REPO_ROOT / "reports")
    print("\nEval complete.")


if __name__ == "__main__":
    main()
