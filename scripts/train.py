"""Train the FieldExtractor on synthetic document data."""

from __future__ import annotations

import argparse
from pathlib import Path

from discern.config import CONFIGS_DIR, load_document_schema
from discern.data.schema import parse_document_schema
from discern.training.config import TrainingConfig
from discern.training.train import Trainer


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Discern FieldExtractor.")
    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIGS_DIR / "train.yaml",
        help="Path to train.yaml (default: configs/train.yaml)",
    )
    parser.add_argument("--device", default=None, help="cuda / cpu (auto-detected if omitted)")
    parser.add_argument(
        "--resume",
        type=Path,
        default=None,
        help="Resume from a checkpoint .pt file",
    )
    args = parser.parse_args()

    schema = parse_document_schema(load_document_schema())
    cfg = TrainingConfig.from_yaml(args.config)

    if args.resume:
        trainer, start_epoch, val_loss = Trainer.load_checkpoint(
            args.resume, schema, device=args.device
        )
        print(f"Resuming from epoch {start_epoch}, best val_loss={val_loss:.4f}")
    else:
        trainer = Trainer(cfg, schema, device=args.device)

    trainer.fit()


if __name__ == "__main__":
    main()
