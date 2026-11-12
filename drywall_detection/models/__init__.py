"""
drywall_detection.models
========================
Semantic segmentation models, compound loss functions, metrics, and training
infrastructure for architectural wall detection and drywall classification.
"""

from typing import Any
import torch.nn as nn

from drywall_detection.models.segformer import (
    SegFormerB0,
    SegFormerWallDetector,
    build_segformer,
)
from drywall_detection.models.unet import (
    ResNet34UNet,
    LightweightUNet,
    UNetWallDetector,
    build_unet,
)
from drywall_detection.models.losses import (
    calculate_class_weights,
    DEFAULT_CLASS_WEIGHTS,
    SoftDiceLoss,
    FocalLoss,
    CompoundLoss,
    MultiClassSoftDiceLoss,
    MultiClassFocalLoss,
    CompoundSegmentationLoss,
)
from drywall_detection.models.metrics import (
    ClassMetricResult,
    SegmentationEvaluationReport,
    SegmentationMetricTracker,
    SegmentationMetrics,
    compute_boundary_iou,
    compute_tensor_boundary_mask,
    assert_zero_leakage_manifests,
)
from drywall_detection.models.trainer import (
    Trainer,
    verify_split_isolation,
    configure_cpu_hardware,
)


def create_segmentation_model(
    arch_name: str,
    num_classes: int = 4,
    in_channels: int = 3,
    pretrained: bool = False,
    **kwargs: Any,
) -> nn.Module:
    """
    Unified segmentation model factory.
    Supports:
    - 'segformer_b0' / 'segformer' -> SegFormerB0
    - 'resnet34_unet' / 'resnet34' / 'unet' -> ResNet34UNet
    - 'resnet18_unet' / 'resnet18' -> UNetWallDetector
    - 'lightweight_unet' / 'lightweight' -> LightweightUNet
    """
    arch = arch_name.lower().replace("-", "_")
    if "segformer" in arch:
        return SegFormerB0(
            num_classes=num_classes,
            in_channels=in_channels,
            pretrained=pretrained,
            **kwargs,
        )
    elif "34" in arch:
        return ResNet34UNet(
            num_classes=num_classes,
            in_channels=in_channels,
            pretrained=pretrained,
        )
    elif "light" in arch:
        return LightweightUNet(
            num_classes=num_classes,
            in_channels=in_channels,
        )
    elif "18" in arch:
        return UNetWallDetector(
            num_classes=num_classes,
            in_channels=in_channels,
            pretrained=pretrained,
        )
    else:
        # Default unet is ResNet34UNet as candidate baseline
        return ResNet34UNet(
            num_classes=num_classes,
            in_channels=in_channels,
            pretrained=pretrained,
        )


__all__ = [
    "SegFormerB0",
    "SegFormerWallDetector",
    "build_segformer",
    "ResNet34UNet",
    "LightweightUNet",
    "UNetWallDetector",
    "build_unet",
    "create_segmentation_model",
    "calculate_class_weights",
    "DEFAULT_CLASS_WEIGHTS",
    "SoftDiceLoss",
    "FocalLoss",
    "CompoundLoss",
    "MultiClassSoftDiceLoss",
    "MultiClassFocalLoss",
    "CompoundSegmentationLoss",
    "ClassMetricResult",
    "SegmentationEvaluationReport",
    "SegmentationMetricTracker",
    "SegmentationMetrics",
    "compute_boundary_iou",
    "compute_tensor_boundary_mask",
    "assert_zero_leakage_manifests",
    "Trainer",
    "verify_split_isolation",
    "configure_cpu_hardware",
]
