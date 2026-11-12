"""
drywall_detection.models.losses
===============================
Compound loss functions for multi-class architectural floor plan segmentation.

Implements:
- calculate_class_weights: Smoothed ENet inverse frequency formula.
- MultiClassSoftDiceLoss: Squared denominator Dice loss with epsilon smoothing.
- MultiClassFocalLoss: Normalized alpha-balanced focal loss suppressing easy pixels.
- CompoundSegmentationLoss: Tri-fold objective (Weighted CE + Soft Dice + Focal Loss).
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple, Union

import torch
import torch.nn as nn
import torch.nn.functional as F

# Default empirical class weights calibrated for 90:10 floor plan class imbalance:
# 0: Background (1.0), 1: Drywall (5.0), 2: Non-Drywall (15.0), 3: Uncertain (20.0)
DEFAULT_CLASS_WEIGHTS = torch.tensor([1.0, 5.0, 15.0, 20.0], dtype=torch.float32)


def calculate_class_weights(
    class_frequencies: Union[List[float], torch.Tensor],
    smooth: float = 1.02,
    normalize: bool = True,
) -> torch.Tensor:
    """
    Computes smoothed inverse class frequency weights using the ENet formulation:
        w_c = 1.0 / ln(smooth + p_c)

    As p_c -> 0, w_c -> 1.0 / ln(smooth) (strictly finite upper bound ~50.5 for smooth=1.02).

    Args:
        class_frequencies: Iterable or Tensor of class probabilities p_c in [0, 1].
        smooth: Smoothing constant strictly > 1.0 (default 1.02).
        normalize: If True, normalizes weights relative to background class (w[0] = 1.0).

    Returns:
        Tensor of float32 weights of length C.
    """
    if not isinstance(class_frequencies, torch.Tensor):
        freqs = torch.tensor(class_frequencies, dtype=torch.float32)
    else:
        freqs = class_frequencies.float()

    if smooth <= 1.0:
        raise ValueError(f"Smoothing parameter smooth must be > 1.0, got {smooth}")

    weights = 1.0 / torch.log(smooth + freqs)

    if normalize and len(weights) > 0 and weights[0] > 0:
        weights = weights / weights[0]

    return weights


class MultiClassSoftDiceLoss(nn.Module):
    """
    Multi-Class Soft Dice Loss with squared denominator (Milletari et al.).
    Computes macro-average over all classes, with numerical stability epsilon.
    """

    def __init__(
        self,
        num_classes: int = 4,
        smooth: float = 1e-6,
        ignore_index: Optional[int] = None,
    ) -> None:
        super().__init__()
        self.num_classes = num_classes
        self.smooth = smooth
        self.ignore_index = ignore_index

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            logits: [B, C, H, W] unnormalized model logits.
            targets: [B, H, W] ground truth class labels (0..C-1).

        Returns:
            Scalar Dice loss in [0, 1].
        """
        B, C, H, W = logits.shape
        probs = F.softmax(logits, dim=1)  # [B, C, H, W]

        # One-hot encode targets
        targets_onehot = F.one_hot(targets, num_classes=self.num_classes).permute(0, 3, 1, 2).float()

        dims = (0, 2, 3)  # Sum across batch, height, width
        intersection = torch.sum(probs * targets_onehot, dim=dims)
        cardinality = torch.sum(probs**2 + targets_onehot**2, dim=dims)

        dice_per_class = (2.0 * intersection + self.smooth) / (cardinality + self.smooth)

        if self.ignore_index is not None and 0 <= self.ignore_index < self.num_classes:
            valid_indices = [c for c in range(self.num_classes) if c != self.ignore_index]
            loss_dice = 1.0 - torch.mean(dice_per_class[valid_indices])
        else:
            loss_dice = 1.0 - torch.mean(dice_per_class)

        return loss_dice


class MultiClassFocalLoss(nn.Module):
    """
    Multi-Class Focal Loss with normalized alpha class weighting and focusing exponent gamma.
    Suppresses gradient contribution from easy background pixels.
    """

    def __init__(
        self,
        gamma: float = 2.0,
        alpha: Optional[torch.Tensor] = None,
        num_classes: int = 4,
    ) -> None:
        super().__init__()
        self.gamma = gamma
        self.num_classes = num_classes
        if alpha is not None:
            self.register_buffer("alpha", alpha.float())
        else:
            self.register_buffer("alpha", torch.ones(num_classes, dtype=torch.float32))

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            logits: [B, C, H, W] unnormalized logits.
            targets: [B, H, W] ground truth class labels (0..C-1).

        Returns:
            Scalar normalized focal loss.
        """
        B, C, H, W = logits.shape
        if targets.shape != (B, H, W):
            targets = targets.view(B, H, W)

        log_p = F.log_softmax(logits, dim=1)  # [B, C, H, W]
        p = torch.exp(log_p)

        # Gather target probabilities
        log_pt = log_p.gather(1, targets.unsqueeze(1)).squeeze(1)  # [B, H, W]
        pt = p.gather(1, targets.unsqueeze(1)).squeeze(1)          # [B, H, W]

        # Focal modulating factor
        focal_weight = (1.0 - pt) ** self.gamma

        # Alpha class weighting
        alpha_t = self.alpha.gather(0, targets.view(-1)).view(targets.shape)

        # Normalized focal loss
        loss = -(alpha_t * focal_weight * log_pt).sum() / torch.clamp(alpha_t.sum(), min=1e-6)
        return loss


class LossTuple(tuple):
    """2-tuple (total_loss, components) that also delegates attribute access to total_loss."""
    def __new__(cls, total_loss: torch.Tensor, components: Dict[str, float]):
        return super().__new__(cls, (total_loss, components))

    def __getattr__(self, name: str) -> Any:
        return getattr(self[0], name)

    def item(self) -> float:
        return self[0].item()

    def backward(self, *args: Any, **kwargs: Any) -> Any:
        return self[0].backward(*args, **kwargs)


class CompoundSegmentationLoss(nn.Module):
    """
    Tri-fold compound objective combining:
    1. Class-Weighted Cross-Entropy Loss (lambda_ce)
    2. Multi-Class Soft Dice Loss (lambda_dice)
    3. Multi-Class Focal Loss (lambda_focal)
    """

    def __init__(
        self,
        num_classes: int = 4,
        weights: Optional[torch.Tensor] = None,
        ce_weight: float = 0.4,
        dice_weight: float = 0.4,
        focal_weight: float = 0.2,
        gamma: float = 2.0,
        smooth: float = 1e-6,
        class_weights: Optional[torch.Tensor] = None,
    ) -> None:
        super().__init__()
        self.num_classes = num_classes
        self.ce_weight = ce_weight
        self.dice_weight = dice_weight
        self.focal_weight = focal_weight
        self.gamma = gamma
        self.smooth = smooth

        eff_weights = weights if weights is not None else class_weights
        weights_tensor = eff_weights if eff_weights is not None else DEFAULT_CLASS_WEIGHTS.clone()
        self.register_buffer("weights", weights_tensor.float())

        self.dice_loss = MultiClassSoftDiceLoss(num_classes=num_classes, smooth=smooth)
        self.focal_loss = MultiClassFocalLoss(gamma=gamma, alpha=self.weights, num_classes=num_classes)

    def forward(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
    ) -> LossTuple:
        """
        Computes weighted combination of CE, Dice, and Focal loss.

        Args:
            logits: [B, C, H, W] float32 tensor of class logits.
            targets: [B, H, W] int64 tensor of class labels.

        Returns:
            LossTuple: (total_loss, components) with scalar tensor delegation.
        """
        B, C, H, W = logits.shape
        if C != self.num_classes:
            raise ValueError(f"Logits channels ({C}) must match num_classes ({self.num_classes})")
        if targets.shape != (B, H, W):
            raise ValueError(f"Targets shape {targets.shape} must match (B, H, W) = {(B, H, W)}")

        # 1. Weighted Cross-Entropy Loss
        loss_ce = F.cross_entropy(logits, targets, weight=self.weights, reduction="mean")

        # 2. Multi-Class Soft Dice Loss
        loss_dice = self.dice_loss(logits, targets)

        # 3. Multi-Class Focal Loss
        loss_focal = self.focal_loss(logits, targets)

        # Total Compound Loss
        total_loss = (
            self.ce_weight * loss_ce
            + self.dice_weight * loss_dice
            + self.focal_weight * loss_focal
        )

        components = {
            "loss_total": float(total_loss.item()),
            "loss_ce": float(loss_ce.item()),
            "loss_dice": float(loss_dice.item()),
            "loss_focal": float(loss_focal.item()),
        }

        return LossTuple(total_loss, components)


class SoftDiceLoss(nn.Module):
    """
    Soft Dice Loss for multi-class or binary segmentation.
    Uses squared denominator (Milletari et al.) for stronger gradients on thin walls.
    Supports class weighting and spatial batch aggregation.
    """

    def __init__(
        self,
        num_classes: int = 4,
        weights: Optional[Sequence[float]] = None,
        eps: float = 1e-6,
        squared: bool = True,
        ignore_index: Optional[int] = None,
    ) -> None:
        super().__init__()
        self.num_classes = num_classes
        self.eps = eps
        self.squared = squared
        self.ignore_index = ignore_index

        if weights is not None:
            self.register_buffer("weights", torch.tensor(weights, dtype=torch.float32))
        else:
            self.weights = None

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            logits: [B, C, H, W] raw model output logits.
            targets: [B, H, W] ground truth class indices (LongTensor).
        Returns:
            Scalar loss tensor.
        """
        B, C, H, W = logits.shape
        if targets.ndim != 3 or targets.shape != (B, H, W):
            targets = targets.view(B, H, W)
        num_classes = logits.shape[1]
        probs = F.softmax(logits, dim=1)  # [B, C, H, W]

        # Convert targets to one-hot: [B, H, W] -> [B, C, H, W]
        targets_clamped = torch.clamp(targets, 0, num_classes - 1)
        targets_1hot = F.one_hot(targets_clamped, num_classes=num_classes)
        targets_1hot = targets_1hot.permute(0, 3, 1, 2).to(dtype=logits.dtype)

        # Batch-level spatial aggregation: sum over (B, H, W)
        dims = (0, 2, 3)
        intersection = torch.sum(probs * targets_1hot, dim=dims)

        if self.squared:
            cardinality = torch.sum(probs ** 2 + targets_1hot ** 2, dim=dims)
        else:
            cardinality = torch.sum(probs + targets_1hot, dim=dims)

        dice = (2.0 * intersection + self.eps) / (cardinality + self.eps)
        per_class_loss = 1.0 - dice  # [C]

        if self.weights is not None:
            w = self.weights.to(logits.device)
            if self.ignore_index is not None and 0 <= self.ignore_index < num_classes:
                w = w.clone()
                w[self.ignore_index] = 0.0
            total_loss = (per_class_loss * w).sum() / (w.sum() + self.eps)
        else:
            if self.ignore_index is not None and 0 <= self.ignore_index < num_classes:
                valid_mask = torch.ones(num_classes, device=logits.device, dtype=torch.bool)
                valid_mask[self.ignore_index] = False
                total_loss = per_class_loss[valid_mask].mean()
            else:
                total_loss = per_class_loss.mean()

        return total_loss


class FocalLoss(nn.Module):
    """
    Multi-class Focal Loss with numerical log-softmax stabilization.
    Downweights easy background pixels and focuses on hard wall boundaries.
    """

    def __init__(
        self,
        alpha: Optional[Union[float, Sequence[float], torch.Tensor]] = None,
        gamma: float = 2.0,
        reduction: str = "mean",
        ignore_index: int = -100,
        num_classes: Optional[int] = None,
    ) -> None:
        super().__init__()
        self.gamma = gamma
        self.reduction = reduction
        self.ignore_index = ignore_index
        self.num_classes = num_classes

        if alpha is not None:
            if isinstance(alpha, (list, tuple)):
                self.register_buffer("alpha", torch.tensor(alpha, dtype=torch.float32))
            elif isinstance(alpha, torch.Tensor):
                self.register_buffer("alpha", alpha.float())
            else:
                self.alpha = float(alpha)
        elif num_classes is not None:
            self.register_buffer("alpha", torch.ones(num_classes, dtype=torch.float32))
        else:
            self.alpha = None

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            logits: [B, C, H, W] raw model output logits.
            targets: [B, H, W] ground truth class indices.
        Returns:
            Scalar loss tensor.
        """
        B, C, H, W = logits.shape
        if targets.ndim != 3 or targets.shape != (B, H, W):
            targets = targets.view(B, H, W)
        num_classes = logits.shape[1]
        log_p = F.log_softmax(logits, dim=1)  # [B, C, H, W]
        p = torch.exp(log_p)

        targets_clamped = torch.clamp(targets, 0, num_classes - 1)
        targets_unsqueezed = targets_clamped.unsqueeze(1)  # [B, 1, H, W]

        # Gather probability corresponding to ground truth class
        log_pt = log_p.gather(1, targets_unsqueezed).squeeze(1)  # [B, H, W]
        pt = p.gather(1, targets_unsqueezed).squeeze(1)          # [B, H, W]

        # Focal modulating factor: (1 - pt)^gamma
        focal_weight = (1.0 - pt) ** self.gamma
        loss = -focal_weight * log_pt

        # Apply alpha weighting
        if self.alpha is not None:
            if isinstance(self.alpha, torch.Tensor):
                a = self.alpha.to(logits.device)
                alpha_t = a.gather(0, targets_clamped.flatten()).view_as(targets_clamped)
                loss = alpha_t * loss
            else:
                loss = self.alpha * loss

        # Handle ignore_index
        if self.ignore_index >= 0:
            valid_mask = (targets != self.ignore_index)
            loss = loss * valid_mask.float()
            if self.reduction == "mean":
                return loss.sum() / (valid_mask.sum().float() + 1e-6)
            elif self.reduction == "sum":
                return loss.sum()

        if self.reduction == "mean":
            return loss.mean()
        elif self.reduction == "sum":
            return loss.sum()
        return loss


class CompoundLoss(nn.Module):
    """
    Compound Loss combining Soft Dice Loss and Focal Loss.
    L = alpha * L_dice + beta * L_focal
    Default alpha=1.0, beta=1.0.
    """

    def __init__(
        self,
        num_classes: int = 4,
        alpha: float = 1.0,
        beta: float = 1.0,
        dice_weights: Optional[Sequence[float]] = (0.2, 1.0, 1.0, 1.0),
        focal_alpha: Optional[Sequence[float]] = (0.1, 1.0, 1.0, 1.0),
        focal_gamma: float = 2.0,
        eps: float = 1e-6,
    ) -> None:
        super().__init__()
        self.alpha = alpha
        self.beta = beta
        self.num_classes = num_classes
        self.dice_loss = SoftDiceLoss(num_classes=num_classes, weights=dice_weights, eps=eps)
        self.focal_loss = FocalLoss(alpha=focal_alpha, gamma=focal_gamma, reduction="mean")

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, float]]:
        l_dice = self.dice_loss(logits, targets)
        l_focal = self.focal_loss(logits, targets)
        total_loss = self.alpha * l_dice + self.beta * l_focal

        metrics = {
            "loss_total": float(total_loss.item()),
            "loss_dice": float(l_dice.item()),
            "loss_focal": float(l_focal.item()),
        }
        return total_loss, metrics
