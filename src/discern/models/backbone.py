"""ResNet-18 backbone adapted for single-channel (grayscale) document images."""

from __future__ import annotations

import torch
import torch.nn as nn
from torchvision.models import ResNet18_Weights, resnet18

FEATURE_DIM = 512


class DiscernBackbone(nn.Module):
    def __init__(self, pretrained: bool = True) -> None:
        super().__init__()
        weights = ResNet18_Weights.DEFAULT if pretrained else None
        base = resnet18(weights=weights)

        orig_conv = base.conv1
        adapted_conv = nn.Conv2d(
            1,
            orig_conv.out_channels,
            kernel_size=orig_conv.kernel_size,
            stride=orig_conv.stride,
            padding=orig_conv.padding,
            bias=False,
        )
        if pretrained:
            # collapse RGB weights → grayscale by averaging across channels
            adapted_conv.weight.data = orig_conv.weight.data.mean(dim=1, keepdim=True)
        base.conv1 = adapted_conv

        self.features = nn.Sequential(
            base.conv1,
            base.bn1,
            base.relu,
            base.maxpool,
            base.layer1,
            base.layer2,
            base.layer3,
            base.layer4,
        )
        self.pool = nn.AdaptiveAvgPool2d((1, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.pool(x)
        return x.flatten(1)  # (B, FEATURE_DIM)
