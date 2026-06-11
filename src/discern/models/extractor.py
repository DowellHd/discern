"""FieldExtractor: backbone + multi-task heads for document field extraction."""

from __future__ import annotations

import torch
import torch.nn as nn

from discern.models.backbone import FEATURE_DIM, DiscernBackbone
from discern.models.heads import ClassificationHead, MultiLabelHead

# Ordered lists define label→index mapping for each head.
DOC_TYPES = ["connection_card", "prayer_request"]
VISIT_TYPE_OPTIONS = ["first_time", "returning", "regular"]
INTERESTS_OPTIONS = ["baptism", "community_group", "volunteering", "prayer", "membership"]
CATEGORY_OPTIONS = ["healing", "family", "guidance", "thanksgiving", "other"]


class FieldExtractor(nn.Module):
    """Multi-task model for document type classification and field extraction.

    Heads are masking-aware: doc-type-specific heads receive gradient only
    from samples of the matching document type.
    """

    def __init__(self, pretrained: bool = True, dropout: float = 0.3) -> None:
        super().__init__()
        self.backbone = DiscernBackbone(pretrained=pretrained)
        self.doc_type_head = ClassificationHead(FEATURE_DIM, len(DOC_TYPES), dropout)
        # connection_card-specific
        self.visit_type_head = ClassificationHead(FEATURE_DIM, len(VISIT_TYPE_OPTIONS), dropout)
        self.interests_head = MultiLabelHead(FEATURE_DIM, len(INTERESTS_OPTIONS), dropout)
        # prayer_request-specific
        self.category_head = ClassificationHead(FEATURE_DIM, len(CATEGORY_OPTIONS), dropout)
        self.contact_ok_head = ClassificationHead(FEATURE_DIM, 1, dropout)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        features = self.backbone(x)
        return {
            "doc_type": self.doc_type_head(features),
            "visit_type": self.visit_type_head(features),
            "interests": self.interests_head(features),
            "category": self.category_head(features),
            "contact_ok": self.contact_ok_head(features).squeeze(1),
        }

    def compute_loss(
        self,
        logits: dict[str, torch.Tensor],
        targets: dict[str, torch.Tensor],
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        """Return (total_loss, per_task_loss_dict). Doc-type-specific heads are masked."""
        losses: dict[str, torch.Tensor] = {}
        ce = nn.CrossEntropyLoss()
        bce = nn.BCEWithLogitsLoss()

        losses["doc_type"] = ce(logits["doc_type"], targets["doc_type"])

        cc_mask = targets["doc_type"] == DOC_TYPES.index("connection_card")
        if cc_mask.any():
            losses["visit_type"] = ce(logits["visit_type"][cc_mask], targets["visit_type"][cc_mask])
            losses["interests"] = bce(
                logits["interests"][cc_mask], targets["interests"][cc_mask].float()
            )

        pr_mask = targets["doc_type"] == DOC_TYPES.index("prayer_request")
        if pr_mask.any():
            losses["category"] = ce(logits["category"][pr_mask], targets["category"][pr_mask])
            losses["contact_ok"] = bce(
                logits["contact_ok"][pr_mask], targets["contact_ok"][pr_mask].float()
            )

        total: torch.Tensor = sum(losses.values())  # type: ignore[assignment]
        return total, losses
