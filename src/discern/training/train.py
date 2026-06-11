"""Trainer: fit loop, val loop, checkpointing, and structured experiment logging."""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import structlog
import torch
from torch.utils.data import DataLoader

from discern.data.schema import DocumentSchema
from discern.models.extractor import FieldExtractor
from discern.training.config import TrainingConfig
from discern.training.dataset import SyntheticDataset

log = structlog.get_logger()


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class Trainer:
    def __init__(
        self,
        config: TrainingConfig,
        schema: DocumentSchema,
        device: str | None = None,
    ) -> None:
        _seed_everything(config.seed)
        self.cfg = config
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))

        self.model = FieldExtractor(pretrained=config.pretrained, dropout=config.dropout).to(
            self.device
        )

        self.optimizer = torch.optim.Adam(
            self.model.parameters(), lr=config.lr, weight_decay=config.weight_decay
        )

        train_ds = SyntheticDataset(schema, size=config.train_size, seed=config.seed)
        val_ds = SyntheticDataset(schema, size=config.val_size, seed=config.seed + 1)

        self.train_loader = DataLoader(
            train_ds,
            batch_size=config.batch_size,
            shuffle=True,
            num_workers=config.num_workers,
        )
        self.val_loader = DataLoader(
            val_ds,
            batch_size=config.batch_size,
            shuffle=False,
            num_workers=config.num_workers,
        )

        self.scheduler = torch.optim.lr_scheduler.OneCycleLR(
            self.optimizer,
            max_lr=config.lr,
            steps_per_epoch=len(self.train_loader),
            epochs=config.epochs,
        )

        self.best_val_loss = float("inf")
        config.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self) -> None:
        log.info("training_start", epochs=self.cfg.epochs, device=str(self.device))
        for epoch in range(1, self.cfg.epochs + 1):
            train_loss, train_task_losses = self._run_epoch(train=True)
            val_loss, val_task_losses = self._run_epoch(train=False)
            log.info(
                "epoch",
                epoch=epoch,
                train_loss=round(train_loss, 4),
                val_loss=round(val_loss, 4),
                **{f"train_{k}": round(v, 4) for k, v in train_task_losses.items()},
                **{f"val_{k}": round(v, 4) for k, v in val_task_losses.items()},
            )
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.save_checkpoint(self.cfg.checkpoint_dir / "best.pt", epoch, val_loss)
        self.save_checkpoint(self.cfg.checkpoint_dir / "last.pt", self.cfg.epochs, val_loss)
        log.info("training_complete", best_val_loss=round(self.best_val_loss, 4))

    def save_checkpoint(self, path: Path, epoch: int, val_loss: float) -> None:
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "val_loss": val_loss,
                "config": self.cfg.model_dump(),
            },
            path,
        )
        log.info("checkpoint_saved", path=str(path), epoch=epoch, val_loss=round(val_loss, 4))

    @classmethod
    def load_checkpoint(
        cls,
        path: Path,
        schema: DocumentSchema,
        device: str | None = None,
    ) -> tuple[Trainer, int, float]:
        # weights_only=False is intentional: checkpoint includes optimizer state
        # and config dict. Only load checkpoints from trusted sources.
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        cfg = TrainingConfig(**ckpt["config"])
        trainer = cls(cfg, schema, device=device)
        trainer.model.load_state_dict(ckpt["model_state_dict"])
        trainer.optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        trainer.best_val_loss = ckpt.get("val_loss", float("inf"))
        return trainer, ckpt["epoch"], ckpt["val_loss"]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_epoch(self, train: bool) -> tuple[float, dict[str, float]]:
        self.model.train(train)
        loader = self.train_loader if train else self.val_loader
        total_loss = 0.0
        accumulated_task: dict[str, float] = {}

        with torch.set_grad_enabled(train):
            for images, targets in loader:
                images = images.to(self.device)
                targets = {k: v.to(self.device) for k, v in targets.items()}

                logits = self.model(images)
                loss, task_losses = self.model.compute_loss(logits, targets)

                if train:
                    self.optimizer.zero_grad()
                    loss.backward()
                    self.optimizer.step()
                    self.scheduler.step()

                total_loss += loss.item()
                for k, v in task_losses.items():
                    accumulated_task[k] = accumulated_task.get(k, 0.0) + v.item()

        n = len(loader)
        return total_loss / n, {k: v / n for k, v in accumulated_task.items()}
