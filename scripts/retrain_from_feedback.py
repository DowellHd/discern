"""Fine-tune the checkpoint on user-corrected fields — run as `python -m scripts.retrain_from_feedback`.

Pulls corrected checkbox/enum field values (visit_type, interests, category,
contact_ok — the fields with a matching classification head) from the DB,
fine-tunes a copy of the base checkpoint on them with a low learning rate,
and writes the result to a *new* checkpoint file. It never overwrites
checkpoints/best.pt automatically — promoting a fine-tuned checkpoint to
production is a deliberate, reviewed step, not something this script does
on your behalf.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
import structlog
import torch
from torch.utils.data import DataLoader

from discern.config import settings
from discern.db.session import SessionLocal
from discern.models.extractor import FieldExtractor
from discern.training.feedback import (
    FeedbackDataset,
    collate_feedback_batch,
    compute_feedback_loss,
    load_feedback_samples,
)

log = structlog.get_logger()


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune on user-corrected feedback.")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=settings.checkpoints_dir / "best.pt",
        help="Base checkpoint to fine-tune from (default: checkpoints/best.pt)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=settings.checkpoints_dir / "finetuned.pt",
        help="Where to write the fine-tuned checkpoint (default: checkpoints/finetuned.pt)",
    )
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--limit", type=int, default=500, help="Max feedback samples to pull")
    parser.add_argument(
        "--min-samples",
        type=int,
        default=10,
        help="Skip fine-tuning if fewer than this many corrected samples are available",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default=None)
    args = parser.parse_args()

    _seed_everything(args.seed)
    device = torch.device(args.device or ("cuda" if torch.cuda.is_available() else "cpu"))

    db = SessionLocal()
    try:
        samples = load_feedback_samples(db, limit=args.limit)
    finally:
        db.close()

    if len(samples) < args.min_samples:
        print(
            f"Only {len(samples)} corrected feedback samples available "
            f"(need >= {args.min_samples}). Nothing to do."
        )
        return

    by_field: dict[str, int] = {}
    for s in samples:
        by_field[s.field_name] = by_field.get(s.field_name, 0) + 1
    print(f"Fine-tuning on {len(samples)} corrected samples: {by_field}")

    if not args.checkpoint.exists():
        raise SystemExit(f"Base checkpoint not found: {args.checkpoint}")
    ckpt = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    model = FieldExtractor(pretrained=False).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.train()

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    dataset = FeedbackDataset(samples)
    loader = DataLoader(
        dataset,
        batch_size=min(args.batch_size, len(samples)),
        shuffle=True,
        collate_fn=collate_feedback_batch,
    )

    for epoch in range(1, args.epochs + 1):
        total_loss = 0.0
        n_batches = 0
        for images, field_names, targets in loader:
            images = images.to(device)
            targets = {k: v.to(device) for k, v in targets.items()}

            logits = model(images)
            loss, _ = compute_feedback_loss(logits, targets, field_names)
            if loss is None:
                continue

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            n_batches += 1

        avg_loss = total_loss / n_batches if n_batches else 0.0
        log.info("feedback_epoch", epoch=epoch, avg_loss=round(avg_loss, 4))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "epoch": ckpt.get("epoch", 0),
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "val_loss": ckpt.get("val_loss"),
            "config": ckpt.get("config"),
            "finetuned_from": str(args.checkpoint),
            "n_feedback_samples": len(samples),
        },
        args.out,
    )
    print(f"Wrote fine-tuned checkpoint: {args.out}")
    print(
        "This checkpoint was NOT promoted to best.pt. Back up best.pt, copy "
        f"{args.out.name} over it, and re-run `python -m scripts.evaluate` to compare "
        "metrics before deploying it."
    )


if __name__ == "__main__":
    main()
