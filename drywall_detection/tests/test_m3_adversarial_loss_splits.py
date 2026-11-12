"""
drywall_detection.tests.test_m3_adversarial_loss_splits
======================================================
Adversarial stress-test suite for Milestone M3:
1. Compound loss functions and numerical stability (losses.py)
2. Boundary IoU mathematical equivalence (PyTorch MaxPool vs OpenCV cv2.erode) (metrics.py)
3. Split isolation anti-leakage invariants and quarantine enforcement (trainer.py and metrics.py)
"""

import numpy as np
import pytest
import torch
import torch.nn.functional as F
import cv2

from drywall_detection.models.losses import (
    calculate_class_weights,
    MultiClassSoftDiceLoss,
    MultiClassFocalLoss,
    CompoundSegmentationLoss,
    SoftDiceLoss,
    FocalLoss,
    CompoundLoss,
)
from drywall_detection.models.metrics import (
    compute_tensor_boundary_mask,
    compute_boundary_iou,
    SegmentationMetrics,
    SegmentationMetricTracker,
    assert_zero_leakage_manifests,
)
from drywall_detection.models.trainer import verify_split_isolation


# =============================================================================
# Helper Mock DataLoader for verify_split_isolation
# =============================================================================

class MockTileDataset:
    def __init__(self, tiles):
        self.tiles = tiles


class MockTileDataLoader:
    def __init__(self, tiles):
        self.dataset = MockTileDataset(tiles)


# =============================================================================
# Task 1: Adversarial Loss Stress Tests
# =============================================================================

class TestAdversarialLossStress:
    """Stress-tests compound loss functions under hostile inputs."""

    def test_class_weights_zero_frequency_upper_bound(self):
        """
        Zero-frequency classes (p_c = 0) in calculate_class_weights must produce
        weights strictly <= 50.5 (unnormalized) and no NaNs or Infs.
        """
        # Case A: One class is 0 frequency
        freqs_with_zero = [0.90, 0.10, 0.0, 0.0]
        w_unnorm = calculate_class_weights(freqs_with_zero, smooth=1.02, normalize=False)
        assert torch.all(torch.isfinite(w_unnorm)), "Unnormalized weights contain non-finite values"
        assert torch.all(w_unnorm <= 50.5), f"Unnormalized weights exceeded 50.5: {w_unnorm}"
        assert torch.all(w_unnorm > 0.0), f"Weights must be strictly positive: {w_unnorm}"

        # Bound check at exactly p_c = 0.0: 1 / ln(1.02) = 50.4967 < 50.5
        w_zero = calculate_class_weights([0.0], smooth=1.02, normalize=False)
        assert float(w_zero[0]) <= 50.5
        assert float(w_zero[0]) > 50.4

        # Case B: All classes zero frequency
        all_zeros = [0.0, 0.0, 0.0, 0.0]
        w_all_zeros_unnorm = calculate_class_weights(all_zeros, smooth=1.02, normalize=False)
        assert torch.all(torch.isfinite(w_all_zeros_unnorm))
        assert torch.all(w_all_zeros_unnorm <= 50.5)

        # Case C: Normalized weights with zero-frequency classes
        w_norm = calculate_class_weights(freqs_with_zero, smooth=1.02, normalize=True)
        assert torch.all(torch.isfinite(w_norm)), "Normalized weights contain non-finite values"
        assert float(w_norm[0]) == pytest.approx(1.0, abs=1e-5)

    def test_empty_targets_finite_scalar(self):
        """
        Empty targets (e.g. all pixels are Class 0) must produce finite scalar losses
        without NaNs across all loss implementations.
        """
        B, C, H, W = 2, 4, 64, 64
        torch.manual_seed(42)
        logits = torch.randn(B, C, H, W)
        targets_all_zero = torch.zeros((B, H, W), dtype=torch.long)

        # MultiClassSoftDiceLoss
        dice_loss_fn = MultiClassSoftDiceLoss(num_classes=C)
        loss_dice = dice_loss_fn(logits, targets_all_zero)
        assert torch.isfinite(loss_dice), f"MultiClassSoftDiceLoss produced non-finite: {loss_dice}"

        # MultiClassFocalLoss
        focal_loss_fn = MultiClassFocalLoss(num_classes=C)
        loss_focal = focal_loss_fn(logits, targets_all_zero)
        assert torch.isfinite(loss_focal), f"MultiClassFocalLoss produced non-finite: {loss_focal}"

        # CompoundSegmentationLoss
        compound_fn = CompoundSegmentationLoss(num_classes=C)
        loss_compound, components = compound_fn(logits, targets_all_zero)
        assert torch.isfinite(loss_compound), f"CompoundSegmentationLoss produced non-finite: {loss_compound}"
        for comp_name, comp_val in components.items():
            assert np.isfinite(comp_val), f"Component {comp_name} is non-finite: {comp_val}"

        # Legacy SoftDiceLoss & FocalLoss & CompoundLoss
        legacy_dice = SoftDiceLoss(num_classes=C)
        assert torch.isfinite(legacy_dice(logits, targets_all_zero))

        legacy_focal = FocalLoss()
        assert torch.isfinite(legacy_focal(logits, targets_all_zero))

        legacy_compound = CompoundLoss(num_classes=C)
        l_comp, _ = legacy_compound(logits, targets_all_zero)
        assert torch.isfinite(l_comp)

    def test_inverse_predictions_monotonicity_and_gradients(self):
        """
        Inverse predictions (predicting 100% Class 0 when target is 100% Class 1):
        verify loss increases monotonically as predictions diverge, and gradients remain non-zero and finite.
        """
        B, C, H, W = 1, 4, 16, 16
        targets_class1 = torch.ones((B, H, W), dtype=torch.long)  # All Class 1 (Drywall)

        compound_fn = CompoundSegmentationLoss(num_classes=C)

        losses = []
        confidences = [0.0, 2.0, 5.0, 10.0, 20.0]

        for conf in confidences:
            # Shift logits strongly towards Class 0 (inverse prediction)
            logits = torch.zeros(B, C, H, W, requires_grad=True)
            with torch.no_grad():
                logits[:, 0, :, :] = conf   # Predict background
                logits[:, 1, :, :] = -conf  # Suppress drywall
            logits.requires_grad_(True)

            loss, _ = compound_fn(logits, targets_class1)
            assert torch.isfinite(loss), f"Loss non-finite at conf={conf}: {loss}"
            losses.append(loss.item())

            loss.backward()
            assert logits.grad is not None, "Gradients are None"
            assert torch.all(torch.isfinite(logits.grad)), f"Gradients contain NaN/Inf at conf={conf}"
            grad_norm = logits.grad.norm().item()
            assert grad_norm > 0.0, f"Gradients vanished to 0 at conf={conf}"

        # Verify strict monotonic increase of loss as inverse confidence increases
        for i in range(len(losses) - 1):
            assert losses[i] < losses[i + 1], (
                f"Loss did not increase monotonically: conf {confidences[i]} ({losses[i]}) "
                f"vs conf {confidences[i+1]} ({losses[i+1]})"
            )

    def test_extreme_logits_numerical_stability(self):
        """
        Extreme logits (+/- 1000.0) must not cause NaNs or Infs due to log-sum-exp stabilization.
        """
        B, C, H, W = 2, 4, 32, 32
        targets = torch.randint(0, C, (B, H, W), dtype=torch.long)

        extreme_logit_scenarios = [
            torch.full((B, C, H, W), 1000.0),
            torch.full((B, C, H, W), -1000.0),
            torch.randn(B, C, H, W) * 1000.0,
        ]

        # Add alternating +1000 and -1000 channels
        alternating = torch.zeros(B, C, H, W)
        alternating[:, 0, :, :] = 1000.0
        alternating[:, 1, :, :] = -1000.0
        alternating[:, 2, :, :] = 500.0
        alternating[:, 3, :, :] = -500.0
        extreme_logit_scenarios.append(alternating)

        compound_fn = CompoundSegmentationLoss(num_classes=C)
        dice_fn = MultiClassSoftDiceLoss(num_classes=C)
        focal_fn = MultiClassFocalLoss(num_classes=C)

        for idx, logits in enumerate(extreme_logit_scenarios):
            l_comp, _ = compound_fn(logits, targets)
            assert torch.isfinite(l_comp), f"Scenario {idx}: CompoundSegmentationLoss is non-finite: {l_comp}"

            l_dice = dice_fn(logits, targets)
            assert torch.isfinite(l_dice), f"Scenario {idx}: MultiClassSoftDiceLoss is non-finite: {l_dice}"

            l_focal = focal_fn(logits, targets)
            assert torch.isfinite(l_focal), f"Scenario {idx}: MultiClassFocalLoss is non-finite: {l_focal}"


# =============================================================================
# Task 2: Boundary IoU Empirical Rigor (PyTorch MaxPool2D vs OpenCV cv2.erode)
# =============================================================================

class TestBoundaryIoUEmpiricalRigor:
    """Verifies mathematical equivalence between PyTorch MaxPool2D boundary erosion and OpenCV."""

    @pytest.mark.parametrize("radius", [1, 2, 3, 5])
    def test_pytorch_erosion_vs_opencv_erode(self, radius):
        """
        Compare native PyTorch MaxPool2D morphological erosion against OpenCV cv2.erode
        across 100 synthetic random binary masks of varying radii (1, 2, 3, 5).
        Assert zero pixel difference (sum |cv2 - torch| == 0).
        """
        np.random.seed(100 + radius)
        torch.manual_seed(100 + radius)
        H, W = 64, 64
        num_trials = 25  # 25 per radius * 4 radii = 100 trials total
        ksize = 2 * radius + 1
        cv2_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))

        for trial in range(num_trials):
            # Create synthetic random binary mask with wall-like linework & patches
            mask_np = (np.random.rand(H, W) > 0.7).astype(np.uint8)
            # Add some lines
            for _ in range(5):
                r0, c0 = np.random.randint(0, H), np.random.randint(0, W)
                r1, c1 = np.random.randint(0, H), np.random.randint(0, W)
                cv2.line(mask_np, (c0, r0), (c1, r1), 1, thickness=np.random.randint(1, 4))

            mask_t = torch.from_numpy(mask_np).float()

            # PyTorch MaxPool2D erosion formulation:
            # In compute_tensor_boundary_mask:
            #   inv = 1.0 - mask
            #   eroded = 1.0 - max_pool2d(inv, kernel_size=k, stride=1, padding=r)
            inv_t = 1.0 - mask_t.unsqueeze(0).unsqueeze(0)
            eroded_torch = 1.0 - F.max_pool2d(inv_t, kernel_size=ksize, stride=1, padding=radius)
            eroded_torch_np = eroded_torch.squeeze().numpy().astype(np.uint8)

            # OpenCV cv2.erode:
            # Note: PyTorch max_pool2d on inv with padding=radius pads inv with 0.
            # In terms of mask = 1 - inv, zero padding on inv corresponds to borderValue = 1 in mask erosion.
            eroded_cv2 = cv2.erode(mask_np, cv2_kernel, borderType=cv2.BORDER_CONSTANT, borderValue=1)

            pixel_diff = np.sum(np.abs(eroded_cv2.astype(np.int32) - eroded_torch_np.astype(np.int32)))
            assert pixel_diff == 0, (
                f"Radius {radius}, Trial {trial}: Non-zero pixel difference between OpenCV and PyTorch erosion! "
                f"Diff pixels: {pixel_diff}"
            )

    def test_boundary_mask_extraction_equivalence(self):
        """
        Verify that compute_tensor_boundary_mask produces identical boundary masks
        as OpenCV morphological gradient (mask - eroded_cv2).
        """
        np.random.seed(42)
        H, W = 64, 64
        for d in [1, 2, 3, 5]:
            ksize = 2 * d + 1
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))
            for _ in range(10):
                mask_np = (np.random.rand(H, W) > 0.8).astype(np.uint8)
                mask_t = torch.from_numpy(mask_np).float().unsqueeze(0).unsqueeze(0)

                torch_boundary = compute_tensor_boundary_mask(mask_t, d=d).squeeze().numpy()

                eroded_cv2 = cv2.erode(mask_np, kernel, borderType=cv2.BORDER_CONSTANT, borderValue=1)
                cv2_boundary = (mask_np.astype(np.float32) - eroded_cv2.astype(np.float32)).clip(min=0.0)

                assert np.sum(np.abs(torch_boundary - cv2_boundary)) == 0


# =============================================================================
# Task 3: Split Isolation & Quarantine Adversarial Attacks
# =============================================================================

class TestSplitIsolationAdversarialAttacks:
    """Stress-tests split isolation against deliberate data leakage and quarantine bypass."""

    def test_attack_1_project_id_overlap_train_val(self):
        """Construct hostile split with Project ID overlap between train and val."""
        train_tiles = [
            {"sample_id": "t1", "project_id": "proj_shared", "drawing_id": "draw_train", "quarantine": False}
        ]
        val_tiles = [
            {"sample_id": "v1", "project_id": "proj_shared", "drawing_id": "draw_val", "quarantine": False}
        ]
        test_tiles = [
            {"sample_id": "te1", "project_id": "proj_test", "drawing_id": "draw_test", "quarantine": False}
        ]

        with pytest.raises(ValueError, match="Project leakage"):
            verify_split_isolation(
                MockTileDataLoader(train_tiles),
                MockTileDataLoader(val_tiles),
                MockTileDataLoader(test_tiles),
            )

    def test_attack_2_drawing_id_overlap_train_test(self):
        """
        Construct hostile split with Drawing ID overlap between train and test.
        Projects are distinct, but drawing_id is leaked.
        """
        train_tiles = [
            {"sample_id": "t1", "project_id": "proj_train", "drawing_id": "draw_LEAKED_01", "quarantine": False}
        ]
        val_tiles = [
            {"sample_id": "v1", "project_id": "proj_val", "drawing_id": "draw_val_ok", "quarantine": False}
        ]
        test_tiles = [
            {"sample_id": "te1", "project_id": "proj_test", "drawing_id": "draw_LEAKED_01", "quarantine": False}
        ]

        with pytest.raises(ValueError, match="Drawing leakage"):
            verify_split_isolation(
                MockTileDataLoader(train_tiles),
                MockTileDataLoader(val_tiles),
                MockTileDataLoader(test_tiles),
            )

    def test_attack_3_quarantined_tile_injected_into_val(self):
        """Construct hostile split with quarantined tile (quarantine=True) injected into val split."""
        train_tiles = [
            {"sample_id": "t1", "project_id": "proj_train", "drawing_id": "draw_train", "quarantine": False}
        ]
        val_tiles = [
            {"sample_id": "v1", "project_id": "proj_val", "drawing_id": "draw_val", "quarantine": True}
        ]
        test_tiles = [
            {"sample_id": "te1", "project_id": "proj_test", "drawing_id": "draw_test", "quarantine": False}
        ]

        with pytest.raises(ValueError, match="Quarantined sample"):
            verify_split_isolation(
                MockTileDataLoader(train_tiles),
                MockTileDataLoader(val_tiles),
                MockTileDataLoader(test_tiles),
            )

    def test_attack_4_pseudo_labeled_tile_injected_into_test(self):
        """Construct hostile split with pseudo-labeled tile (is_pseudo_label=True) injected into test split."""
        train_tiles = [
            {"sample_id": "t1", "project_id": "proj_train", "drawing_id": "draw_train", "quarantine": False}
        ]
        val_tiles = [
            {"sample_id": "v1", "project_id": "proj_val", "drawing_id": "draw_val", "quarantine": False}
        ]
        test_tiles = [
            {"sample_id": "te1", "project_id": "proj_test", "drawing_id": "draw_test", "is_pseudo_label": True}
        ]

        with pytest.raises(ValueError, match="Pseudo-labeled sample"):
            verify_split_isolation(
                MockTileDataLoader(train_tiles),
                MockTileDataLoader(val_tiles),
                MockTileDataLoader(test_tiles),
            )

    def test_attack_5_project_id_overlap_train_test(self):
        """Construct hostile split with Project ID overlap between train and test."""
        train_tiles = [
            {"sample_id": "t1", "project_id": "proj_train_test_leak", "drawing_id": "draw_train", "quarantine": False}
        ]
        val_tiles = [
            {"sample_id": "v1", "project_id": "proj_val", "drawing_id": "draw_val", "quarantine": False}
        ]
        test_tiles = [
            {"sample_id": "te1", "project_id": "proj_train_test_leak", "drawing_id": "draw_test", "quarantine": False}
        ]

        with pytest.raises(ValueError, match="Project leakage"):
            verify_split_isolation(
                MockTileDataLoader(train_tiles),
                MockTileDataLoader(val_tiles),
                MockTileDataLoader(test_tiles),
            )

    def test_attack_6_quarantined_tile_injected_into_test(self):
        """Construct hostile split with quarantined tile injected into test split."""
        train_tiles = [
            {"sample_id": "t1", "project_id": "proj_train", "drawing_id": "draw_train", "quarantine": False}
        ]
        val_tiles = [
            {"sample_id": "v1", "project_id": "proj_val", "drawing_id": "draw_val", "quarantine": False}
        ]
        test_tiles = [
            {"sample_id": "te1", "project_id": "proj_test", "drawing_id": "draw_test", "quarantine": True}
        ]

        with pytest.raises(ValueError, match="Quarantined sample"):
            verify_split_isolation(
                MockTileDataLoader(train_tiles),
                MockTileDataLoader(val_tiles),
                MockTileDataLoader(test_tiles),
            )

    def test_attack_7_drawing_id_overlap_val_test(self):
        """Construct hostile split with Drawing ID overlap between val and test."""
        train_tiles = [
            {"sample_id": "t1", "project_id": "proj_train", "drawing_id": "draw_train", "quarantine": False}
        ]
        val_tiles = [
            {"sample_id": "v1", "project_id": "proj_val", "drawing_id": "draw_val_test_leak", "quarantine": False}
        ]
        test_tiles = [
            {"sample_id": "te1", "project_id": "proj_test", "drawing_id": "draw_val_test_leak", "quarantine": False}
        ]

        with pytest.raises(ValueError, match="Drawing leakage"):
            verify_split_isolation(
                MockTileDataLoader(train_tiles),
                MockTileDataLoader(val_tiles),
                MockTileDataLoader(test_tiles),
            )


# =============================================================================
# Task 3B: Manifest Pre-Evaluation Assertions (metrics.py)
# =============================================================================

class TestAssertZeroLeakageManifestsAdversarial:
    """Stress-tests assert_zero_leakage_manifests under adversarial JSON manifests."""

    def test_drawing_overlap_train_test_manifests(self, tmp_path):
        """Hostile test manifest sharing drawing_id with train manifest."""
        import json
        t_path = tmp_path / "train.json"
        v_path = tmp_path / "val.json"
        te_path = tmp_path / "test.json"

        t_path.write_text(json.dumps({
            "tiles": [{"sample_id": "t1", "project_id": "p_train", "drawing_id": "draw_SHARED", "tile_path": "a.png"}]
        }))
        v_path.write_text(json.dumps({
            "tiles": [{"sample_id": "v1", "project_id": "p_val", "drawing_id": "draw_v", "tile_path": "b.png"}]
        }))
        te_path.write_text(json.dumps({
            "tiles": [{"sample_id": "te1", "project_id": "p_test", "drawing_id": "draw_SHARED", "tile_path": "c.png"}]
        }))

        with pytest.raises(RuntimeError, match="Drawings leaked"):
            assert_zero_leakage_manifests(t_path, v_path, te_path)

    def test_quarantined_tile_in_test_manifest(self, tmp_path):
        """Hostile test manifest containing a quarantined tile."""
        import json
        t_path = tmp_path / "train.json"
        v_path = tmp_path / "val.json"
        te_path = tmp_path / "test.json"

        t_path.write_text(json.dumps({
            "tiles": [{"sample_id": "t1", "project_id": "p_train", "drawing_id": "d1", "tile_path": "a.png"}]
        }))
        v_path.write_text(json.dumps({
            "tiles": [{"sample_id": "v1", "project_id": "p_val", "drawing_id": "d2", "tile_path": "b.png"}]
        }))
        te_path.write_text(json.dumps({
            "tiles": [{"sample_id": "te1", "project_id": "p_test", "drawing_id": "d3", "tile_path": "c.png", "quarantine": True}]
        }))

        with pytest.raises(RuntimeError, match="Quarantined sample"):
            assert_zero_leakage_manifests(t_path, v_path, te_path)
