"""Training hyperparameters loaded from configs/train.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class TrainingConfig(BaseModel):
    epochs: int = 20
    batch_size: int = 16
    lr: float = 1e-3
    weight_decay: float = 1e-4
    train_size: int = 2000
    val_size: int = 400
    seed: int = 42
    checkpoint_dir: Path = Path("checkpoints")
    pretrained: bool = True
    dropout: float = 0.3
    num_workers: int = 0  # 0 keeps on-the-fly generation deterministic

    @classmethod
    def from_yaml(cls, path: Path) -> TrainingConfig:
        with path.open() as fh:
            return cls(**yaml.safe_load(fh))
