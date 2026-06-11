"""Training loop, dataset, config, and checkpointing."""

from discern.training.config import TrainingConfig
from discern.training.dataset import SyntheticDataset
from discern.training.train import Trainer

__all__ = ["Trainer", "TrainingConfig", "SyntheticDataset"]
