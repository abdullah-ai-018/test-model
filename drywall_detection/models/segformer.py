"""
drywall_detection.models.segformer
==================================
SegFormer-B0 semantic segmentation architecture for architectural wall and
drywall detection.

Features:
- Hierarchical Mix Transformer (MiT-B0) encoder + all-MLP lightweight decoder.
- Total parameters: 3,715,172 (~3.72M) for 4-class segmentation.
- Dynamic bilinear interpolation layer restoring [B, 4, H, W] from [B, 4, H/4, W/4].
- Resilient offline initialization fallback when HuggingFace Hub is unreachable.
- Supports both standard Tensor returns [B, 4, H, W] and HF dict returns.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple, Union

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import SegformerConfig, SegformerForSemanticSegmentation

logger = logging.getLogger(__name__)

# Standard MiT-B0 configuration constants
MIT_B0_CONFIG = {
    "num_channels": 3,
    "image_size": 512,
    "patch_sizes": [7, 3, 3, 3],
    "strides": [4, 2, 2, 2],
    "hidden_sizes": [32, 64, 160, 256],
    "depths": [2, 2, 2, 2],
    "sr_ratios": [8, 4, 2, 1],
    "num_attention_heads": [1, 2, 5, 8],
    "mlp_ratios": [4, 4, 4, 4],
    "decoder_hidden_size": 256,
    "classifier_dropout_prob": 0.1,
}


class SegFormerB0(nn.Module):
    """
    SegFormer-B0 semantic segmentation network adapted for architectural drawings.

    Accepts input images of shape [B, 3, H, W] and outputs segmentation logits
    of shape [B, num_classes, H, W] (defaulting to 4 classes: Background, Drywall,
    Non-Drywall, Uncertain).
    """

    def __init__(
        self,
        num_classes: int = 4,
        in_channels: int = 3,
        pretrained: bool = False,
        hub_model_id: str = "nvidia/mit-b0",
        offline: bool = True,
        dropout_prob: float = 0.1,
    ) -> None:
        super().__init__()
        self.num_classes = num_classes
        self.in_channels = in_channels
        self.pretrained = pretrained
        self.hub_model_id = hub_model_id
        self.offline = offline

        self.config = SegformerConfig(
            num_labels=num_classes,
            num_channels=in_channels,
            image_size=512,
            patch_sizes=[7, 3, 3, 3],
            strides=[4, 2, 2, 2],
            hidden_sizes=[32, 64, 160, 256],
            decoder_hidden_size=256,
            depths=[2, 2, 2, 2],
            sr_ratios=[8, 4, 2, 1],
            num_attention_heads=[1, 2, 5, 8],
            mlp_ratios=[4, 4, 4, 4],
            classifier_dropout_prob=dropout_prob,
        )

        self.model = self._initialize_model()

    def _initialize_model(self) -> SegformerForSemanticSegmentation:
        """
        Initializes SegFormer with pretrained weights or offline random weights.
        Safely falls back to local configuration if hub download fails or offline is True.
        """
        if self.pretrained and not self.offline:
            try:
                logger.info("Attempting to load pretrained SegFormer from %s...", self.hub_model_id)
                model = SegformerForSemanticSegmentation.from_pretrained(
                    self.hub_model_id,
                    num_labels=self.num_classes,
                    ignore_mismatched_sizes=True,
                )
                logger.info("Successfully loaded pretrained SegFormer from %s.", self.hub_model_id)
                return model
            except Exception as exc:
                logger.warning(
                    "Could not load SegFormer weights from Hub (%s). "
                    "Falling back to local SegformerConfig offline initialization.",
                    exc,
                )

        logger.info("Instantiating SegFormer-B0 with offline random initialization.")
        return SegformerForSemanticSegmentation(self.config)

    def forward(
        self,
        pixel_values: torch.Tensor,
        return_dict: bool = False,
    ) -> Union[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Forward pass with automatic bilinear upsampling to input resolution.

        Args:
            pixel_values: [B, 3, H, W] float32 image tensor.
            return_dict: If True, returns dict with 'logits'. If False, returns raw logits tensor.

        Returns:
            logits: [B, num_classes, H, W] float32 tensor of unnormalized class logits.
        """
        B, C, H, W = pixel_values.shape
        raw_outputs = self.model(pixel_values=pixel_values)
        raw_logits = raw_outputs.logits  # Shape: [B, num_classes, H/4, W/4]

        # Bilinear interpolation to restore input spatial resolution [B, num_classes, H, W]
        upsampled_logits = F.interpolate(
            raw_logits,
            size=(H, W),
            mode="bilinear",
            align_corners=False,
        )

        if return_dict:
            return {"logits": upsampled_logits}
        return upsampled_logits

    def count_parameters(self) -> int:
        """Returns total number of trainable and non-trainable parameters."""
        return sum(p.numel() for p in self.parameters())

    def count_trainable_parameters(self) -> int:
        """Returns total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# Backward compatibility alias
SegFormerWallDetector = SegFormerB0


def build_segformer(
    num_classes: int = 4,
    pretrained: bool = False,
    in_channels: int = 3,
    offline: bool = True,
    **kwargs: Any,
) -> SegFormerB0:
    """
    Factory helper to construct SegFormerB0.
    """
    return SegFormerB0(
        num_classes=num_classes,
        in_channels=in_channels,
        pretrained=pretrained,
        offline=offline,
        **kwargs,
    )
