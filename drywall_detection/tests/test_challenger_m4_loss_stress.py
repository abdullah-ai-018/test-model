"""
drywall_detection.tests.test_challenger_m4_loss_stress
======================================================
Adversarial Challenger Stress Harness for Milestone M4:
- Architectures: SegFormerB0, ResNet34UNet, LightweightUNet under degenerate inputs
  (singular batch B=1, non-square dimensions, all-zeros, all-ones, huge pixel values [-1000, 1000]).
- Resolution divisibility contract & odd dimension handling across models.
- Loss functions: SoftDiceLoss, FocalLoss, CompoundLoss, CompoundSegmentationLoss under
  extreme class imbalance (99.9% background, zero positive presence, empty masks, huge logits [-1000, 1000]).
- Boundary IoU: empty masks, 1-pixel walls, checkerboards, envelopes exceeding wall width.
- SegmentationMetricTracker under extreme class absence.
"""

from __future__ import annotations

import math
import numpy as np
import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F

from drywall_detection.models.segformer import SegFormerB0, build_segformer
from drywall_detection.models.unet import ResNet34UNet, LightweightUNet, UNetWallDetector, build_unet
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
    compute_boundary_iou,
    compute_tensor_boundary_mask,
    SegmentationMetricTracker,
    SegmentationMetrics,
)


# =============================================================================
# 1. Architecture Edge Cases & Stress Tests
# =============================================================================

class TestArchitectureStress:
    """Stress tests segmentation architectures with extreme and degenerate inputs."""

    @pytest.mark.parametrize("model_cls,model_name", [
        (SegFormerB0, "SegFormerB0"),
        (ResNet34UNet, "ResNet34UNet"),
        (LightweightUNet, "LightweightUNet"),
    ])
    def test_singular_batch_eval_and_train(self, model_cls, model_name):
        """
        Singular batch size (B=1) must execute without error in both eval()
        and train() modes, and backward pass must produce finite gradients.
        """
        model = model_cls(num_classes=4)
        
        # 1. Eval mode B=1
        model.eval()
        x_eval = torch.randn(1, 3, 128, 128)
        with torch.no_grad():
            out_eval = model(x_eval)
        assert out_eval.shape == (1, 4, 128, 128), f"{model_name} eval B=1 failed shape check: {out_eval.shape}"
        assert torch.all(torch.isfinite(out_eval)), f"{model_name} eval B=1 produced non-finite output"

        # 2. Train mode B=1 (tests BatchNorm behavior when B=1 across spatial pixels)
        model.train()
        x_train = torch.randn(1, 3, 128, 128, requires_grad=True)
        out_train = model(x_train)
        assert out_train.shape == (1, 4, 128, 128), f"{model_name} train B=1 failed shape check: {out_train.shape}"
        assert torch.all(torch.isfinite(out_train)), f"{model_name} train B=1 produced non-finite output"

        loss = out_train.sum()
        loss.backward()
        assert x_train.grad is not None, f"{model_name} gradient is None"
        assert torch.all(torch.isfinite(x_train.grad)), f"{model_name} gradient contains NaN or Inf"
        assert x_train.grad.norm().item() > 0.0, f"{model_name} gradient is all zero"

    @pytest.mark.parametrize("h,w", [
        (256, 512),
        (512, 256),
        (384, 288),  # 384 = 12*32, 288 = 9*32
    ])
    def test_non_square_dimensions_multiples_of_32(self, h, w):
        """
        All architectures must seamlessly process non-square dimensions
        that are multiples of 32 (standard patch tiling contract).
        """
        for model_cls, name in [(SegFormerB0, "SegFormerB0"), (ResNet34UNet, "ResNet34UNet"), (LightweightUNet, "LightweightUNet")]:
            model = model_cls(num_classes=4)
            model.eval()
            x = torch.randn(1, 3, h, w)
            with torch.no_grad():
                out = model(x)
            assert out.shape == (1, 4, h, w), f"{name} failed on non-square ({h}, {w}): got {out.shape}"
            assert torch.all(torch.isfinite(out)), f"{name} produced non-finite on ({h}, {w})"

    def test_arbitrary_odd_resolutions_segformer_and_lightweight(self):
        """
        SegFormerB0 (via bilinear interpolation) and LightweightUNet (via 4 padded DecoderBlocks)
        must support arbitrary odd/non-multiple-of-32 spatial resolutions.
        """
        odd_sizes = [(255, 255), (127, 129), (250, 250)]
        for h, w in odd_sizes:
            # SegFormerB0
            sf = SegFormerB0(num_classes=4)
            sf.eval()
            out_sf = sf(torch.randn(1, 3, h, w))
            assert out_sf.shape == (1, 4, h, w), f"SegFormerB0 failed on ({h}, {w})"

            # LightweightUNet
            lw = LightweightUNet(num_classes=4)
            lw.eval()
            out_lw = lw(torch.randn(1, 3, h, w))
            assert out_lw.shape == (1, 4, h, w), f"LightweightUNet failed on ({h}, {w})"

    def test_resnet34_divisibility_contract_and_failure_mode(self):
        """
        ResNet34UNet strictly requires spatial dimensions to be multiples of 32
        due to unpadded dec1 skip-concatenation. Tests and asserts this architectural
        boundary constraint empirically.
        """
        model = ResNet34UNet(num_classes=4)
        model.eval()

        # Multiples of 32 pass cleanly
        x_valid = torch.randn(1, 3, 256, 256)
        out_valid = model(x_valid)
        assert out_valid.shape == (1, 4, 256, 256)

        # Non-multiples of 32 (like 250x250) trigger shape mismatch in dec1
        x_invalid = torch.randn(1, 3, 250, 250)
        with pytest.raises(RuntimeError, match="Sizes of tensors must match except in dimension 1"):
            model(x_invalid)

    @pytest.mark.parametrize("model_cls,model_name", [
        (SegFormerB0, "SegFormerB0"),
        (ResNet34UNet, "ResNet34UNet"),
        (LightweightUNet, "LightweightUNet"),
    ])
    def test_all_zeros_and_all_ones_degenerate_inputs(self, model_cls, model_name):
        """
        Degenerate inputs: all-zeros and all-ones (representing pure blank or white pages)
        must not cause NaN, Inf, zero-division, or crash.
        """
        model = model_cls(num_classes=4)
        model.eval()

        # 1. All-zeros (pure black)
        zeros = torch.zeros(1, 3, 128, 128)
        out_zero = model(zeros)
        assert torch.all(torch.isfinite(out_zero)), f"{model_name} failed on all zeros"

        # 2. All-ones (normalized white)
        ones = torch.ones(1, 3, 128, 128)
        out_ones = model(ones)
        assert torch.all(torch.isfinite(out_ones)), f"{model_name} failed on all ones"

        # 3. Extreme value (raw 255.0 or 1000.0)
        extreme = torch.full((1, 3, 128, 128), 1000.0)
        out_extreme = model(extreme)
        assert torch.all(torch.isfinite(out_extreme)), f"{model_name} failed on extreme 1000.0"

    def test_model_trainable_parameters_receive_gradients(self):
        """
        Verifies that every single trainable parameter in SegFormerB0, ResNet34UNet,
        and LightweightUNet receives a non-None, finite gradient during training.
        """
        for model_cls, name in [(SegFormerB0, "SegFormerB0"), (ResNet34UNet, "ResNet34UNet"), (LightweightUNet, "LightweightUNet")]:
            model = model_cls(num_classes=4)
            model.train()
            x = torch.randn(2, 3, 128, 128)
            targets = torch.randint(0, 4, (2, 128, 128))
            criterion = CompoundLoss(num_classes=4)

            logits = model(x)
            loss, _ = criterion(logits, targets)
            loss.backward()

            unupdated = []
            for pname, param in model.named_parameters():
                if param.requires_grad:
                    if param.grad is None:
                        unupdated.append(f"{pname} (grad is None)")
                    elif not torch.all(torch.isfinite(param.grad)):
                        unupdated.append(f"{pname} (grad has NaN/Inf)")
            assert len(unupdated) == 0, f"{name} had parameters without valid gradients: {unupdated[:5]}"


# =============================================================================
# 2. Loss Functions Under Extreme Class Imbalance & Numerical Stress
# =============================================================================

class TestLossImbalanceAndExtremeStress:
    """Stress tests SoftDiceLoss, FocalLoss, and Compound losses under hostile conditions."""

    def test_extreme_class_imbalance_999_background(self):
        """
        Extreme class imbalance (99.9% background, only 0.1% foreground).
        In a 64x64 batch (8192 total pixels across B=2), exactly 1 pixel is foreground class 1.
        All loss functions must produce finite loss and finite non-vanishing gradients.
        """
        B, C, H, W = 2, 4, 64, 64
        torch.manual_seed(123)

        logits = torch.randn(B, C, H, W, requires_grad=True)
        targets = torch.zeros((B, H, W), dtype=torch.long)
        targets[0, 0, 0] = 1  # 1 pixel out of 8192 = 99.988% background

        # 1. SoftDiceLoss
        dice_fn = SoftDiceLoss(num_classes=C)
        l_dice = dice_fn(logits, targets)
        assert torch.isfinite(l_dice)
        assert 0.0 <= l_dice.item() <= 1.0

        # 2. FocalLoss
        focal_fn = FocalLoss(num_classes=C)
        l_focal = focal_fn(logits, targets)
        assert torch.isfinite(l_focal)
        assert l_focal.item() >= 0.0

        # 3. CompoundLoss
        comp_fn = CompoundLoss(num_classes=C)
        l_comp, metrics = comp_fn(logits, targets)
        assert torch.isfinite(l_comp)
        assert metrics["loss_total"] > 0.0

        # 4. Backward gradient check
        l_comp.backward()
        assert torch.all(torch.isfinite(logits.grad))
        assert logits.grad.norm().item() > 0.0

    def test_zero_positive_presence_in_batch(self):
        """
        Zero positive class presence for classes 1, 2, 3 (100% background batch).
        Must not divide by zero or yield NaN.
        """
        B, C, H, W = 2, 4, 32, 32
        logits = torch.randn(B, C, H, W, requires_grad=True)
        targets_all_bg = torch.zeros((B, H, W), dtype=torch.long)

        dice_fn = SoftDiceLoss(num_classes=C)
        focal_fn = FocalLoss(num_classes=C)
        comp_fn = CompoundLoss(num_classes=C)
        comp_seg_fn = CompoundSegmentationLoss(num_classes=C)

        l_d = dice_fn(logits, targets_all_bg)
        l_f = focal_fn(logits, targets_all_bg)
        l_c, _ = comp_fn(logits, targets_all_bg)
        l_cs, _ = comp_seg_fn(logits, targets_all_bg)

        for name, val in [("Dice", l_d), ("Focal", l_f), ("Compound", l_c), ("CompoundSeg", l_cs)]:
            assert torch.isfinite(val), f"{name} produced non-finite on 100% background: {val}"

        l_c.backward()
        assert torch.all(torch.isfinite(logits.grad)), "Gradients non-finite on 100% background"

    def test_all_foreground_targets_100_percent(self):
        """
        100% foreground batch (e.g. all pixels are drywall class 1, or non-drywall class 2).
        Must produce finite loss and valid gradients.
        """
        B, C, H, W = 2, 4, 32, 32
        for fg_class in [1, 2, 3]:
            logits = torch.randn(B, C, H, W, requires_grad=True)
            targets_fg = torch.full((B, H, W), fg_class, dtype=torch.long)

            comp_fn = CompoundLoss(num_classes=C)
            l_c, _ = comp_fn(logits, targets_fg)
            assert torch.isfinite(l_c)

            l_c.backward()
            assert torch.all(torch.isfinite(logits.grad))

    @pytest.mark.parametrize("pred_type", ["correct", "wrong", "uniform_zero", "uniform_huge_pos", "uniform_huge_neg"])
    def test_huge_logits_range_minus_1000_to_plus_1000(self, pred_type):
        """
        Logits with extreme values in [-1000, 1000].
        Must not cause overflow (Inf), NaN, or NaN gradients.
        """
        B, C, H, W = 2, 4, 32, 32
        targets = torch.zeros((B, H, W), dtype=torch.long)  # All class 0
        logits = torch.zeros((B, C, H, W), requires_grad=True)

        with torch.no_grad():
            if pred_type == "correct":
                logits[:, :, :, :] = -1000.0
                logits[:, 0, :, :] = 1000.0  # Confident correct
            elif pred_type == "wrong":
                logits[:, :, :, :] = -1000.0
                logits[:, 1, :, :] = 1000.0  # Confident wrong
            elif pred_type == "uniform_zero":
                logits[:, :, :, :] = 0.0
            elif pred_type == "uniform_huge_pos":
                logits[:, :, :, :] = 1000.0
            elif pred_type == "uniform_huge_neg":
                logits[:, :, :, :] = -1000.0

        dice_fn = SoftDiceLoss(num_classes=C)
        focal_fn = FocalLoss(num_classes=C)
        comp_fn = CompoundLoss(num_classes=C)

        l_d = dice_fn(logits, targets)
        l_f = focal_fn(logits, targets)
        l_c, _ = comp_fn(logits, targets)

        assert torch.isfinite(l_d), f"Dice failed on {pred_type}: {l_d}"
        assert torch.isfinite(l_f), f"Focal failed on {pred_type}: {l_f}"
        assert torch.isfinite(l_c), f"Compound failed on {pred_type}: {l_c}"

        if pred_type == "correct":
            assert l_d.item() < 0.01, f"Dice loss should be near 0 on perfect prediction, got {l_d.item()}"
            assert l_f.item() < 0.01, f"Focal loss should be near 0 on perfect prediction, got {l_f.item()}"

        l_c.backward()
        assert torch.all(torch.isfinite(logits.grad)), f"Grad failed on {pred_type}"

    def test_out_of_range_labels_clamping_safety(self):
        """
        SoftDiceLoss and FocalLoss clamp out-of-range labels [0, num_classes-1]
        preventing CUDA/CPU index out-of-bounds segfaults.
        """
        B, C, H, W = 2, 4, 16, 16
        logits = torch.randn(B, C, H, W)
        targets_corrupt = torch.tensor([[-5, 0], [4, 255]]).repeat(B, H // 2, W // 2)

        dice_fn = SoftDiceLoss(num_classes=C)
        focal_fn = FocalLoss(num_classes=C)

        l_d = dice_fn(logits, targets_corrupt)
        l_f = focal_fn(logits, targets_corrupt)

        assert torch.isfinite(l_d)
        assert torch.isfinite(l_f)

    def test_calculate_class_weights_extreme_frequencies(self):
        """
        ENet class weight formula w_c = 1.0 / ln(smooth + p_c).
        Tests zero frequencies, near-zero frequencies (1e-8), and validates
        the strict finite upper bound 1.0 / ln(1.02) <= 50.5.
        """
        # Exact zero frequency
        w_zero = calculate_class_weights([0.0], smooth=1.02, normalize=False)
        assert torch.all(torch.isfinite(w_zero))
        assert float(w_zero[0]) <= 50.5
        assert float(w_zero[0]) > 50.4

        # Highly unbalanced distribution
        freqs = [0.9999, 0.0001, 0.0, 0.0]
        w_unnorm = calculate_class_weights(freqs, smooth=1.02, normalize=False)
        assert torch.all(torch.isfinite(w_unnorm))
        assert torch.all(w_unnorm <= 50.5)
        assert torch.all(w_unnorm > 0.0)

        # Normalized distribution (w[0] == 1.0)
        w_norm = calculate_class_weights(freqs, smooth=1.02, normalize=True)
        assert float(w_norm[0]) == pytest.approx(1.0, abs=1e-5)
        assert float(w_norm[1]) > float(w_norm[0])


# =============================================================================
# 3. Boundary IoU Stress Testing
# =============================================================================

class TestBoundaryIoUStress:
    """Stress tests Boundary IoU (Cheng et al., CVPR 2021) under boundary cases."""

    def test_both_masks_empty(self):
        """
        When both ground truth and prediction have zero wall pixels,
        Boundary IoU must return exactly 1.0 (empty set agreement).
        """
        H, W = 64, 64
        gt_empty = torch.zeros((1, H, W))
        pred_empty = torch.zeros((1, H, W))
        for d in [1, 2, 4]:
            val = compute_boundary_iou(gt_empty, pred_empty, d=d)
            assert val == 1.0, f"Both empty should be 1.0, got {val} at d={d}"

    def test_one_mask_empty_other_non_empty(self):
        """
        When ground truth is empty and prediction is non-empty (or vice-versa),
        Boundary IoU must evaluate to approximately 0.0 (< 1e-6).
        """
        H, W = 64, 64
        gt_empty = torch.zeros((1, H, W))
        pred_non_empty = torch.zeros((1, H, W))
        pred_non_empty[0, 20:30, 20:30] = 1.0

        val_fp = compute_boundary_iou(gt_empty, pred_non_empty, d=2)
        val_fn = compute_boundary_iou(pred_non_empty, gt_empty, d=2)

        assert 0.0 <= val_fp < 1e-5, f"False positive boundary IoU should be ~0.0, got {val_fp}"
        assert 0.0 <= val_fn < 1e-5, f"False negative boundary IoU should be ~0.0, got {val_fn}"

    def test_single_pixel_wall_exact_and_shifted(self):
        """
        Single-pixel wide wall:
        1. Exact match must yield Boundary IoU = 1.0.
        2. Shifted by 1 pixel (completely disjoint) must yield Boundary IoU ~ 0.0.
        """
        H, W = 64, 64
        gt_1px = torch.zeros((1, H, W))
        gt_1px[0, 32, :] = 1.0  # 1-pixel horizontal wall line

        # 1. Exact match
        val_exact = compute_boundary_iou(gt_1px, gt_1px, d=2)
        assert val_exact == 1.0, f"1-pixel exact match must be 1.0, got {val_exact}"

        # 2. Shifted by 1 pixel (row 33)
        pred_shift = torch.zeros((1, H, W))
        pred_shift[0, 33, :] = 1.0
        val_shift_d2 = compute_boundary_iou(gt_1px, pred_shift, d=2)
        val_shift_d4 = compute_boundary_iou(gt_1px, pred_shift, d=4)

        assert val_shift_d2 < 1e-5, f"Disjoint 1px wall should be ~0.0, got {val_shift_d2}"
        assert val_shift_d4 < 1e-5, f"Disjoint 1px wall should be ~0.0, got {val_shift_d4}"

    def test_checkerboard_adversarial_pattern(self):
        """
        Adversarial checkerboard pattern: every single pixel is a boundary edge.
        1. Self-match must equal 1.0.
        2. Inverted checkerboard must equal ~0.0.
        """
        H, W = 64, 64
        cb = torch.zeros((1, H, W))
        cb[0, ::2, ::2] = 1.0
        cb[0, 1::2, 1::2] = 1.0

        val_self = compute_boundary_iou(cb, cb, d=2)
        assert val_self == 1.0, f"Checkerboard self-match must be 1.0, got {val_self}"

        cb_inv = 1.0 - cb
        val_inv = compute_boundary_iou(cb, cb_inv, d=2)
        assert val_inv < 1e-5, f"Inverted checkerboard must be ~0.0, got {val_inv}"

    def test_boundary_envelope_larger_than_wall_width(self):
        r"""
        When dilation distance d exceeds wall half-width (e.g. d=4 on a 1px or 3px wall),
        the inner erosion is completely empty (G \ominus d = \emptyset), so G_d = G.
        Boundary IoU for identical masks must still equal exactly 1.0.
        """
        H, W = 64, 64
        wall_3px = torch.zeros((1, H, W))
        wall_3px[0, 30:33, :] = 1.0

        for d in [2, 4, 8, 16]:
            b_mask = compute_tensor_boundary_mask(wall_3px, d=d)
            assert b_mask.shape == (1, 1, H, W)
            assert torch.all(torch.isfinite(b_mask))
            val = compute_boundary_iou(wall_3px, wall_3px, d=d)
            assert val == 1.0, f"Envelope d={d} self-match failed: {val}"

    def test_extreme_dilation_distance_larger_than_image(self):
        """
        Extreme dilation distance d=100 on 32x32 image.
        Must not crash or change spatial tensor dimensions.
        """
        H, W = 32, 32
        mask = torch.zeros((1, H, W))
        mask[0, 10:20, 10:20] = 1.0

        b_mask = compute_tensor_boundary_mask(mask, d=100)
        assert b_mask.shape == (1, 1, H, W)
        assert torch.all(torch.isfinite(b_mask))
        val = compute_boundary_iou(mask, mask, d=100)
        assert val == 1.0


# =============================================================================
# 4. Metric Tracker Imbalance Stress
# =============================================================================

class TestMetricTrackerImbalanceStress:
    """Stress tests SegmentationMetricTracker under streaming extreme imbalance."""

    def test_tracker_streaming_all_background(self):
        """
        Streaming batches of 100% background data:
        - Global accuracy must be 1.0.
        - Foreground Wall IoU must be 0.0 (no foreground walls present).
        - No NaN or division-by-zero exceptions in per-class metrics.
        """
        tracker = SegmentationMetricTracker(num_classes=4)
        B, H, W = 2, 64, 64

        for _ in range(5):
            preds = torch.zeros((B, H, W), dtype=torch.long)
            targets = torch.zeros((B, H, W), dtype=torch.long)
            tracker.update(preds, targets)

        report = tracker.compute()
        assert report.global_accuracy == 1.0
        assert report.foreground_wall_iou == 0.0
        assert report.total_pixels == 5 * B * H * W
        assert not math.isnan(report.mean_dice)
        assert not math.isnan(report.mean_precision)
        assert not math.isnan(report.mean_recall)

        # Background class is perfectly 1.0
        bg_result = report.per_class_metrics["Background"]
        assert bg_result.iou == 1.0
        assert bg_result.dice == 1.0
        assert bg_result.precision == 1.0
        assert bg_result.recall == 1.0

        # Drywall has 0 pixels, IoU/Dice default safely to 1.0 (empty set agreement)
        # and precision/recall to 0.0
        dw_result = report.per_class_metrics["Drywall"]
        assert not math.isnan(dw_result.iou)
        assert not math.isnan(dw_result.precision)

    def test_tracker_streaming_extreme_single_class_collapse(self):
        """
        Model collapses and predicts only Background (0) for everything,
        while targets have a tiny fraction of Drywall (1).
        Verifies confusion matrix correctly reflects precision=0, recall=0 for Drywall.
        """
        tracker = SegmentationMetricTracker(num_classes=4)
        B, H, W = 2, 64, 64

        preds = torch.zeros((B, H, W), dtype=torch.long)
        targets = torch.zeros((B, H, W), dtype=torch.long)
        targets[:, 10:15, 10:15] = 1  # 2 * 25 = 50 drywall pixels

        tracker.update(preds, targets)
        report = tracker.compute()

        dw_result = report.per_class_metrics["Drywall"]
        assert dw_result.tp == 0
        assert dw_result.fn == 50
        assert dw_result.fp == 0
        assert dw_result.recall == 0.0
        assert dw_result.precision == 0.0
        assert dw_result.iou == 0.0
        assert not math.isnan(report.miou_all_classes)
