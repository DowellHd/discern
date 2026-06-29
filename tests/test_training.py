"""Tests for Milestone 3: dataset, trainer, and checkpointing."""

from __future__ import annotations

from pathlib import Path

import pytest
import torch

from discern.config import load_document_schema
from discern.data.schema import parse_document_schema
from discern.models.extractor import DOC_TYPES, INTERESTS_OPTIONS
from discern.training.config import TrainingConfig
from discern.training.dataset import SyntheticDataset, _encode_targets
from discern.training.train import Trainer


@pytest.fixture(scope="module")
def schema():
    return parse_document_schema(load_document_schema())


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


def test_dataset_length(schema) -> None:
    ds = SyntheticDataset(schema, size=10, seed=0)
    assert len(ds) == 10


def test_dataset_item_shapes(schema) -> None:
    ds = SyntheticDataset(schema, size=4, seed=0)
    img, targets = ds[0]
    assert img.shape == (1, 224, 224)
    assert targets["doc_type"].dtype == torch.long
    assert targets["interests"].shape == (len(INTERESTS_OPTIONS),)


def test_dataset_doc_types_cycle(schema) -> None:
    n = len(DOC_TYPES)
    ds = SyntheticDataset(schema, size=n, seed=0)
    types = [ds[i][1]["doc_type"].item() for i in range(n)]
    assert types == list(range(n))


def test_encode_targets_connection_card() -> None:
    labels = {"visit_type": "returning", "interests": ["baptism", "prayer"], "contact_ok": True}
    targets = _encode_targets("connection_card", labels)
    assert targets["doc_type"].item() == DOC_TYPES.index("connection_card")
    assert targets["visit_type"].item() == 1  # "returning" is index 1
    assert targets["interests"][0].item() == 1.0  # baptism present
    assert targets["interests"][1].item() == 0.0  # community_group absent


def test_encode_targets_prayer_request() -> None:
    labels = {"category": "healing", "contact_ok": True}
    targets = _encode_targets("prayer_request", labels)
    assert targets["doc_type"].item() == DOC_TYPES.index("prayer_request")
    assert targets["category"].item() == 0  # "healing" is index 0
    assert targets["contact_ok"].item() == 1.0


def test_encode_targets_missing_optional_fields() -> None:
    targets = _encode_targets("connection_card", {})
    assert targets["visit_type"].item() == 0
    assert targets["interests"].sum().item() == 0.0


# ---------------------------------------------------------------------------
# Trainer – smoke tests (no full training)
# ---------------------------------------------------------------------------


@pytest.fixture()
def tiny_cfg(tmp_path: Path) -> TrainingConfig:
    return TrainingConfig(
        epochs=1,
        batch_size=2,
        train_size=4,
        val_size=4,
        pretrained=False,
        checkpoint_dir=tmp_path / "ckpts",
    )


def test_trainer_one_epoch(tiny_cfg: TrainingConfig, schema) -> None:
    trainer = Trainer(tiny_cfg, schema, device="cpu")
    train_loss, task_losses = trainer._run_epoch(train=True)
    assert isinstance(train_loss, float)
    assert train_loss > 0
    assert "doc_type" in task_losses


def test_trainer_val_epoch(tiny_cfg: TrainingConfig, schema) -> None:
    trainer = Trainer(tiny_cfg, schema, device="cpu")
    val_loss, _ = trainer._run_epoch(train=False)
    assert isinstance(val_loss, float)


def test_trainer_fit_completes(tiny_cfg: TrainingConfig, schema) -> None:
    trainer = Trainer(tiny_cfg, schema, device="cpu")
    trainer.fit()
    assert (tiny_cfg.checkpoint_dir / "best.pt").exists()
    assert (tiny_cfg.checkpoint_dir / "last.pt").exists()


# ---------------------------------------------------------------------------
# Checkpoint round-trip
# ---------------------------------------------------------------------------


def test_checkpoint_save_load(tiny_cfg: TrainingConfig, schema, tmp_path: Path) -> None:
    trainer = Trainer(tiny_cfg, schema, device="cpu")
    ckpt_path = tmp_path / "test.pt"
    trainer.save_checkpoint(ckpt_path, epoch=1, val_loss=1.23)

    loaded, epoch, val_loss = Trainer.load_checkpoint(ckpt_path, schema, device="cpu")
    assert epoch == 1
    assert abs(val_loss - 1.23) < 1e-5
    assert isinstance(loaded.model.backbone, type(trainer.model.backbone))


def test_checkpoint_model_weights_preserved(
    tiny_cfg: TrainingConfig, schema, tmp_path: Path
) -> None:
    trainer = Trainer(tiny_cfg, schema, device="cpu")
    ckpt_path = tmp_path / "weights.pt"
    trainer.save_checkpoint(ckpt_path, epoch=2, val_loss=0.5)

    loaded, _, _ = Trainer.load_checkpoint(ckpt_path, schema, device="cpu")
    for (n1, p1), (n2, p2) in zip(
        trainer.model.named_parameters(), loaded.model.named_parameters(), strict=True
    ):
        assert n1 == n2
        assert torch.allclose(p1, p2), f"Weight mismatch at {n1}"


def test_training_config_from_yaml(tmp_path: Path) -> None:
    cfg_file = tmp_path / "t.yaml"
    cfg_file.write_text("epochs: 5\nbatch_size: 8\nlr: 0.0005\n")
    cfg = TrainingConfig.from_yaml(cfg_file)
    assert cfg.epochs == 5
    assert cfg.batch_size == 8
    assert cfg.lr == 0.0005
