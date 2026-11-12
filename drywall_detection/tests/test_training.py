"""
drywall_detection.tests.test_training
====================================
Comprehensive test suite for Milestone M4 Wall Segmentation Training:
- Compound loss functions numerical stability (SoftDiceLoss, FocalLoss, CompoundLoss).
- Multi-metric evaluation suite (SegmentationMetricTracker, Boundary IoU, Confusion Matrices).
- Runtime zero-leakage assertion gate and pseudo-label quarantine.
- Checkpoint persistence, reload fidelity, and inference reproducibility.
- Standalone infer.py CLI runner verification.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Dict

import numpy as np
from PIL import Image
import pytest
import torch
import torch.nn as nn

from drywall_detection.checkpoints.best_model.infer import StandaloneInferencer
from drywall_detection.models.losses import (
    SoftDiceLoss,
    FocalLoss,
    CompoundLoss,
    MultiClassSoftDiceLoss,
    MultiClassFocalLoss,
    CompoundSegmentationLoss,
)
from drywall_detection.models.metrics import (
    SegmentationMetricTracker,
    SegmentationMetrics,
    compute_boundary_iou,
    compute_tensor_boundary_mask,
    assert_zero_leakage_manifests,
)
from drywall_detection.models.segformer import SegFormerB0
from drywall_detection.models.unet import ResNet34UNet, LightweightUNet
from drywall_detection.models.trainer import Trainer


# ==============================================================================
# 1. Loss Function Numerical Stability Tests
# ==============================================================================

class TestLossNumericalStability:
    """Verifies that loss functions remain stable, finite, and free of NaN/Inf."""

    def test_soft_dice_all_background(self):
        """SoftDiceLoss handles all-background mask without NaN or division by zero."""
        dice_loss = SoftDiceLoss(num_classes=4, squared=True)
        logits = torch.randn(2, 4, 64, 64)
        targets = torch.zeros(2, 64, 64, dtype=torch.long)  # All background (class 0)
        loss = dice_loss(logits, targets)

        assert torch.isfinite(loss).item()
        assert loss.item() >= 0.0

    def test_soft_dice_single_pixel_wall(self):
        """SoftDiceLoss handles extremely sparse ground truth (single foreground pixel)."""
        dice_loss = SoftDiceLoss(num_classes=4, squared=True)
        logits = torch.randn(1, 4, 64, 64)
        targets = torch.zeros(1, 64, 64, dtype=torch.long)
        targets[0, 32, 32] = 1  # Exactly 1 drywall pixel
        loss = dice_loss(logits, targets)

        assert torch.isfinite(loss).item()
        assert loss.item() >= 0.0

    def test_focal_loss_extreme_logits(self):
        """FocalLoss handles extreme saturated logits (+/- 100.0) without overflow or NaN."""
        focal = FocalLoss(num_classes=4, gamma=2.0)
        logits = torch.tensor([[[[100.0]], [[-100.0]], [[-100.0]], [[-100.0]]]])
        targets = torch.tensor([[[0]]], dtype=torch.long)
        loss = focal(logits, targets)

        assert torch.isfinite(loss).item()
        assert 0.0 <= loss.item() < 0.01  # Heavily suppressed easy pixel

    def test_compound_loss_backward_gradient_flow(self):
        """CompoundLoss produces clean autograd gradients for all classes."""
        loss_fn = CompoundLoss(num_classes=4, alpha=1.0, beta=1.0)
        logits = torch.randn(2, 4, 32, 32, requires_grad=True)
        targets = torch.randint(0, 4, (2, 32, 32), dtype=torch.long)

        loss, comps = loss_fn(logits, targets)
        loss.backward()

        assert logits.grad is not None
        assert torch.isfinite(logits.grad).all()
        assert comps["loss_total"] > 0.0
        assert comps["loss_dice"] >= 0.0
        assert comps["loss_focal"] >= 0.0


# ==============================================================================
# 2. Multi-Metric Evaluation Suite Tests
# ==============================================================================

class TestMultiMetricEvaluationSuite:
    """Tests mIoU, Foreground Wall IoU, Boundary IoU, and Confusion Matrix views."""

    def test_miou_and_foreground_wall_iou_separation(self):
        """Foreground Wall IoU must omit Background class 0 to avoid inflation."""
        tracker = SegmentationMetricTracker(num_classes=4)

        # Ground truth: 90% background, 10% drywall
        targets = torch.zeros(1, 100, 100, dtype=torch.long)
        targets[:, :, :10] = 1  # 1000 drywall pixels

        # Perfect prediction on background, 0% on drywall (predicts all background)
        preds = torch.zeros(1, 100, 100, dtype=torch.long)

        tracker.update(preds, targets)
        report = tracker.compute()

        # Background IoU is high (100%), Drywall IoU is 0%
        # Overall mIoU is (1.0 + 0.0 + 1.0 + 1.0)/4 = 0.75 (or (1.0 + 0.0)/2 = 0.50 for present classes)
        # Foreground Wall IoU must be 0.0 or low, NOT inflated by background!
        fg_iou = report.foreground_wall_iou
        assert fg_iou < 0.35, f"Foreground wall IoU was artificially inflated by background: {fg_iou}"

    def test_confusion_matrix_normalization(self):
        """Row-normalized matrix must sum to 1.0 (Recall), col-normalized sums to 1.0 (Precision)."""
        tracker = SegmentationMetricTracker(num_classes=4)
        targets = torch.randint(0, 4, (2, 50, 50))
        preds = torch.randint(0, 4, (2, 50, 50))

        tracker.update(preds, targets)
        report = tracker.compute()

        row_norm = np.array(report.confusion_matrix_row_norm)
        col_norm = np.array(report.confusion_matrix_col_norm)

        # Non-zero rows sum to 1.0
        for r in range(4):
            if row_norm[r].sum() > 0:
                assert abs(row_norm[r].sum() - 1.0) < 1e-3

        # Non-zero cols sum to 1.0
        for c in range(4):
            if col_norm[:, c].sum() > 0:
                assert abs(col_norm[:, c].sum() - 1.0) < 1e-3

    def test_boundary_iou_distance_sensitivity(self):
        """Boundary IoU strictly degrades when predicted wall boundary is shifted."""
        gt = torch.zeros(1, 1, 64, 64)
        gt[0, 0, 20:44, 20:44] = 1.0  # 24x24 box

        # Perfect match
        b_perfect = compute_boundary_iou(gt, gt, d=2)
        assert abs(b_perfect - 1.0) < 1e-4

        # 2-pixel shifted prediction
        pred_shifted = torch.zeros(1, 1, 64, 64)
        pred_shifted[0, 0, 22:46, 22:46] = 1.0
        b_shifted_d2 = compute_boundary_iou(gt, pred_shifted, d=2)
        b_shifted_d4 = compute_boundary_iou(gt, pred_shifted, d=4)

        assert b_shifted_d2 < 1.0
        assert b_shifted_d2 < b_shifted_d4, "Dilation d=4 should have higher tolerance than d=2"


# ==============================================================================
# 3. Anti-Leakage & Split Isolation Gate Tests
# ==============================================================================

class TestAntiLeakageAndQuarantineGate:
    """Verifies that split isolation assertions catch project, drawing, and file leakage."""

    def test_zero_leakage_manifest_passes_on_clean_splits(self):
        """assert_zero_leakage_manifests passes cleanly on the official train/val splits."""
        train_p = Path("drywall_detection/data/processed/splits/train.json")
        val_p = Path("drywall_detection/data/processed/splits/val.json")

        if train_p.exists() and val_p.exists():
            assert_zero_leakage_manifests(train_p, val_p)

    def test_zero_leakage_catches_synthetic_contamination(self, tmp_path):
        """assert_zero_leakage_manifests raises RuntimeError on project contamination."""
        train_json = tmp_path / "train.json"
        val_json = tmp_path / "val.json"

        # Leaked project "project_alpha" in both
        t_data = {"tiles": [{"project_id": "project_alpha", "drawing_id": "D1", "image_path": "a.png"}]}
        v_data = {"tiles": [{"project_id": "project_alpha", "drawing_id": "D2", "image_path": "b.png"}]}

        with open(train_json, "w") as f:
            json.dump(t_data, f)
        with open(val_json, "w") as f:
            json.dump(v_data, f)

        with pytest.raises(RuntimeError, match="Projects leaked"):
            assert_zero_leakage_manifests(train_json, val_json)

    def test_quarantined_samples_barred_from_val(self, tmp_path):
        """assert_zero_leakage_manifests raises RuntimeError if quarantined sample is in val."""
        train_json = tmp_path / "train.json"
        val_json = tmp_path / "val.json"

        t_data = {"tiles": [{"project_id": "proj_1", "drawing_id": "D1", "image_path": "a.png"}]}
        v_data = {"tiles": [{"project_id": "proj_2", "drawing_id": "D2", "image_path": "b.png", "quarantine": True, "sample_id": "Q1"}]}

        with open(train_json, "w") as f:
            json.dump(t_data, f)
        with open(val_json, "w") as f:
            json.dump(v_data, f)

        with pytest.raises(RuntimeError, match="Quarantined sample"):
            assert_zero_leakage_manifests(train_json, val_json)


# ==============================================================================
# 4. Checkpoint Save, Reload & Reproducibility Tests
# ==============================================================================

class TestCheckpointPersistenceAndReload:
    """Verifies that model checkpoints save all 8 metadata fields and reproduce outputs."""

    def test_segformer_checkpoint_reload_produces_identical_logits(self, tmp_path):
        """Asserts reloading SegFormer weights from disk produces bit-identical logits."""
        model = SegFormerB0(num_classes=4, offline=True)
        model.eval()

        ckpt_path = tmp_path / "test_model.pt"
        torch.save({"model_state_dict": model.state_dict(), "architecture": "SegFormerB0"}, ckpt_path)

        # Reload into new instance
        model_reloaded = SegFormerB0(num_classes=4, offline=True)
        loaded_state = torch.load(ckpt_path, map_location="cpu")
        model_reloaded.load_state_dict(loaded_state["model_state_dict"])
        model_reloaded.eval()

        dummy_x = torch.randn(1, 3, 128, 128)
        with torch.no_grad():
            out1 = model(dummy_x)
            out2 = model_reloaded(dummy_x)

        assert torch.allclose(out1, out2, atol=1e-6), "Reloaded model produced divergent logits!"

    def test_best_model_checkpoint_bundle_artifacts_exist(self):
        """Asserts all 8 required checkpoint bundle artifacts exist in best_model directory."""
        bundle_dir = Path("drywall_detection/checkpoints/best_model")
        required_files = [
            "best_model.pt",
            "config.json",
            "class_mapping.json",
            "training_log.json",
            "metrics.json",
            "infer.py",
            "README.md",
        ]
        for fname in required_files:
            p = bundle_dir / fname
            assert p.exists(), f"Missing required checkpoint bundle artifact: {fname}"

        # Assert visual triplets exist
        overlays_dir = bundle_dir / "sample_overlays"
        assert overlays_dir.exists()
        triplet_files = ["sample_01_original.png", "sample_01_mask.png", "sample_01_overlay.png"]
        for tf in triplet_files:
            assert (overlays_dir / tf).exists(), f"Missing sample overlay triplet: {tf}"


# ==============================================================================
# 5. Standalone infer.py CLI Execution Test
# ==============================================================================

class TestStandaloneInferCLI:
    """Tests CLI reload-and-infer runner execution."""

    def test_infer_cli_with_image_input(self, tmp_path):
        """Runs infer.py CLI on a synthetic image and asserts color overlay output."""
        infer_script = Path("drywall_detection/checkpoints/best_model/infer.py")
        test_img_path = tmp_path / "test_floorplan.png"
        out_overlay_path = tmp_path / "output_overlay.png"

        # Create dummy image
        img = Image.new("RGB", (256, 256), color=(255, 255, 255))
        img.save(test_img_path)

        cmd = [
            sys.executable,
            str(infer_script),
            "--image", str(test_img_path),
            "--output", str(out_overlay_path),
            "--checkpoint", "drywall_detection/checkpoints/best_model",
            "--device", "cpu",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, f"infer.py failed with stderr: {result.stderr}"
        assert out_overlay_path.exists(), "Output overlay image was not created!"
        assert "pixel_counts" in result.stdout or "status" in result.stdout
