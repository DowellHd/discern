"""Task-specific classification heads attached to the shared backbone."""

from __future__ import annotations

import torch
import torch.nn as nn


class ClassificationHead(nn.Module):
    """Single-label classification: returns raw logits for CrossEntropyLoss."""

    def __init__(self, in_features: int, num_classes: int, dropout: float = 0.3) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(in_features, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class MultiLabelHead(nn.Module):
    """Multi-label classification: returns raw logits for BCEWithLogitsLoss."""

    def __init__(self, in_features: int, num_labels: int, dropout: float = 0.3) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(in_features, num_labels),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
