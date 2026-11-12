"""
drywall_detection.tests.test_models
===================================
Comprehensive unit, property, and integration tests for Milestone M3:
- Candidate semantic segmentation architectures (SegFormer-B0, ResNet18 U-Net).
- Parameter counts, tensor shapes, and forward/backward gradient propagation.
- Compound loss functions (Class-Weighted CE, Multi-Class Soft Dice, Focal Loss).
- ENet smoothed inverse frequency class weights and finite bound invariant.
- SegmentationMetrics suite (4x4 confusion matrix, Wall mIoU, Boundary IoU, zero-division safety).
- Split isolation guardrails and quarantine enforcement.
- Trainer engine with CPU optimization, gradient accumulation, and early stopping.
- Checkpoint persistence and standalone inferencer reload.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any, Dict

import numpy as np
from PIL import Image
import pytest
import torch
import torch.nn as nn

from drywall_detection.checkpoints.best_model.infer import (
    StandaloneInferencer,
    create_hann_window,
)
from drywall_detection.datasets.loader import (
    DrywallTileDataset,
    get_tile_dataloader,
)
from drywall_detection.models.losses import (
    calculate_class_weights,
    CompoundSegmentationLoss,
    MultiClassFocalLoss,
    MultiClassSoftDiceLoss,
)
from drywall_detection.models.metrics import (
    SegmentationMetrics,
)
from drywall_detection.models.segformer import (
    build_segformer,
    SegFormerB0,
    SegFormerWallDetector,
)
from drywall_detection.models.trainer import (
    Trainer,
    verify_split_isolation,
)
from drywall_detection.models.unet import (
    build_unet,
    UNetWallDetector,
    ResNet34UNet,
    LightweightUNet,
)
from drywall_detection.models import create_segmentation_model
from drywall_detection.models.losses import (
    SoftDiceLoss,
    FocalLoss,
    CompoundLoss,
)


# -------------------------------------------------------------------------
# Test Group 1: Model Architectures & Parameter Invariants
# -------------------------------------------------------------------------

def test_segformer_b0_architecture_and_parameters():
    """Verifies SegFormer-B0 parameter count (~3.72M) and forward shape [B, 4, H, W]."""
    model = build_segformer(num_classes=4, pretrained=False, offline=True)
    param_count = model.count_parameters()
    # SegFormer-B0 has 3,715,172 parameters for 4 classes
    assert 3_600_000 <= param_count <= 3_800_000, f"Unexpected SegFormer-B0 param count: {param_count}"

    # Forward pass with [2, 3, 512, 512]
    x = torch.randn(2, 3, 512, 512)
    model.eval()
    with torch.no_grad():
        out = model(x)

    assert isinstance(out, torch.Tensor)
    assert out.shape == (2, 4, 512, 512), f"Expected shape (2, 4, 512, 512), got {out.shape}"


def test_segformer_b0_return_dict():
    """Verifies SegFormer-B0 supports return_dict=True for HuggingFace compatibility."""
    model = build_segformer(num_classes=4, pretrained=False, offline=True)
    x = torch.randn(1, 3, 256, 256)
    model.eval()
    with torch.no_grad():
        out = model(x, return_dict=True)

    assert isinstance(out, dict)
    assert "logits" in out
    assert out["logits"].shape == (1, 4, 256, 256)


def test_unet_resnet18_architecture_and_parameters():
    """Verifies ResNet18 U-Net parameter count (~14.34M) and forward shape [B, 4, H, W]."""
    model = build_unet(num_classes=4, in_channels=3, pretrained=False)
    param_count = model.count_parameters()
    # ResNet18 U-Net has 14,343,524 parameters
    assert 14_000_000 <= param_count <= 14_800_000, f"Unexpected U-Net param count: {param_count}"

    x = torch.randn(2, 3, 512, 512)
    model.eval()
    with torch.no_grad():
        out = model(x)

    assert isinstance(out, torch.Tensor)
    assert out.shape == (2, 4, 512, 512), f"Expected shape (2, 4, 512, 512), got {out.shape}"


def test_resnet34_unet_architecture_and_parameters():
    """Verifies ResNet34 U-Net parameter count (~24.43M) and forward shape [B, 4, H, W]."""
    model = ResNet34UNet(num_classes=4, in_channels=3, pretrained=False)
    param_count = model.count_parameters()
    assert 24_000_000 <= param_count <= 25_000_000, f"Unexpected ResNet34 U-Net param count: {param_count}"

    x = torch.randn(2, 3, 256, 256)
    model.eval()
    with torch.no_grad():
        out = model(x)

    assert isinstance(out, torch.Tensor)
    assert out.shape == (2, 4, 256, 256), f"Expected shape (2, 4, 256, 256), got {out.shape}"


def test_lightweight_unet_architecture_and_parameters():
    """Verifies Lightweight U-Net parameter count (~7.76M) and forward shape [B, 4, H, W]."""
    model = LightweightUNet(num_classes=4, in_channels=3)
    param_count = model.count_parameters()
    assert 7_000_000 <= param_count <= 8_500_000, f"Unexpected Lightweight U-Net param count: {param_count}"

    x = torch.randn(2, 3, 256, 256)
    model.eval()
    with torch.no_grad():
        out = model(x)

    assert isinstance(out, torch.Tensor)
    assert out.shape == (2, 4, 256, 256), f"Expected shape (2, 4, 256, 256), got {out.shape}"


def test_create_segmentation_model_factory():
    """Tests create_segmentation_model factory across candidate architectures."""
    seg = create_segmentation_model("segformer_b0", num_classes=4)
    assert isinstance(seg, (SegFormerB0, SegFormerWallDetector))

    rn34 = create_segmentation_model("resnet34_unet", num_classes=4)
    assert isinstance(rn34, ResNet34UNet)

    light = create_segmentation_model("lightweight_unet", num_classes=4)
    assert isinstance(light, LightweightUNet)


def test_offline_instantiation_without_network():
    """Verifies all models instantiate 100% offline without remote CDN or weights."""
    seg = SegFormerB0(num_classes=4, offline=True, pretrained=False)
    assert seg.count_parameters() == 3_715_172

    rn34 = ResNet34UNet(num_classes=4, pretrained=False)
    assert rn34.count_parameters() > 24_000_000

    light = LightweightUNet(num_classes=4)
    assert light.count_parameters() > 7_000_000


def test_resnet34_backward_gradient_flow():
    """Verifies backpropagation gradient flow through ResNet34UNet."""
    x = torch.randn(2, 3, 128, 128)
    y = torch.randint(0, 4, (2, 128, 128))
    model = ResNet34UNet(num_classes=4, pretrained=False)
    out = model(x)
    loss = nn.CrossEntropyLoss()(out, y)
    loss.backward()
    has_grads = any(p.grad is not None and p.grad.abs().sum() > 0 for p in model.parameters())
    assert has_grads, "ResNet34UNet parameters received zero gradients!"


def test_model_backward_gradient_flow():
    """Verifies end-to-end autograd backward pass through both architectures."""
    x = torch.randn(2, 3, 128, 128, requires_grad=False)
    y = torch.randint(0, 4, (2, 128, 128), dtype=torch.long)
    criterion = nn.CrossEntropyLoss()

    # SegFormer backward
    seg = build_segformer(num_classes=4, pretrained=False, offline=True)
    out_seg = seg(x)
    loss_seg = criterion(out_seg, y)
    loss_seg.backward()
    has_grads = any(p.grad is not None and p.grad.abs().sum() > 0 for p in seg.parameters())
    assert has_grads, "SegFormer parameters received zero gradients!"

    # U-Net backward
    unet = build_unet(num_classes=4, in_channels=3, pretrained=False)
    out_unet = unet(x)
    loss_unet = criterion(out_unet, y)
    loss_unet.backward()
    has_grads_u = any(p.grad is not None and p.grad.abs().sum() > 0 for p in unet.parameters())
    assert has_grads_u, "U-Net parameters received zero gradients!"


# -------------------------------------------------------------------------
# Test Group 2: Compound Loss Function & Weight Invariants
# -------------------------------------------------------------------------

def test_calculate_class_weights_enet_formula():
    """Tests smoothed ENet inverse frequency weights and finite bound."""
    # Typical floor plan class distribution: 95% background, 3% drywall, 1.5% non-drywall, 0.5% uncertain
    freqs = [0.95, 0.03, 0.015, 0.005]
    weights = calculate_class_weights(freqs, smooth=1.02, normalize=True)

    assert isinstance(weights, torch.Tensor)
    assert len(weights) == 4
    # Background weight is normalized to 1.0
    assert torch.isclose(weights[0], torch.tensor(1.0), atol=1e-4)
    # Rare classes have higher weights
    assert weights[0] < weights[1] < weights[2] < weights[3]

    # Test finite upper bound as p_c -> 0
    zero_freqs = [0.999, 0.0, 0.0, 0.0]
    weights_zero = calculate_class_weights(zero_freqs, smooth=1.02, normalize=False)
    max_bound = 1.0 / np.log(1.02)  # ~50.498
    assert torch.all(weights_zero <= max_bound + 1e-3)
    assert not torch.any(torch.isinf(weights_zero))
    assert not torch.any(torch.isnan(weights_zero))


def test_soft_dice_loss_bounds_and_zero_division():
    """Verifies Soft Dice loss behavior on identical, inverse, and absent classes."""
    dice_loss = MultiClassSoftDiceLoss(num_classes=4)

    # Identical predictions (one-hot logits)
    targets = torch.tensor([[0, 1], [2, 3]], dtype=torch.long)
    # Create extreme logits matching targets
    logits = torch.full((1, 4, 2, 2), -100.0)
    for r in range(2):
        for c in range(2):
            logits[0, targets[r, c], r, c] = 100.0

    loss_perfect = dice_loss(logits, targets.unsqueeze(0))
    assert 0.0 <= loss_perfect.item() < 0.05, f"Perfect prediction should have near-zero Dice loss: {loss_perfect.item()}"

    # Absent class test: targets contain only class 0
    targets_bg_only = torch.zeros((1, 64, 64), dtype=torch.long)
    logits_random = torch.randn(1, 4, 64, 64)
    loss_absent = dice_loss(logits_random, targets_bg_only)
    assert torch.isfinite(loss_absent), "Dice loss on absent classes returned non-finite value"


def test_focal_loss_modulation():
    """Verifies that focal loss heavily discounts easy background pixels vs uncertain boundary pixels."""
    focal_loss = MultiClassFocalLoss(gamma=2.0, num_classes=4)

    # Pixel 1: High confidence prediction on true class 0 (easy pixel)
    logits_easy = torch.tensor([[[[10.0]], [[0.0]], [[0.0]], [[0.0]]]])  # p(0) ~ 0.9999
    target_easy = torch.tensor([[0]], dtype=torch.long)
    loss_easy = focal_loss(logits_easy, target_easy)

    # Pixel 2: Ambiguous prediction on true class 0 (hard pixel)
    logits_hard = torch.tensor([[[[0.1]], [[0.1]], [[0.1]], [[0.1]]]])   # p(0) ~ 0.25
    target_hard = torch.tensor([[0]], dtype=torch.long)
    loss_hard = focal_loss(logits_hard, target_hard)

    assert loss_easy.item() < loss_hard.item() * 0.01, (
        f"Focal loss failed to suppress easy pixel: easy={loss_easy.item()}, hard={loss_hard.item()}"
    )


def test_compound_segmentation_loss_combination():
    """Tests CompoundSegmentationLoss linear combination and component dictionary."""
    compound = CompoundSegmentationLoss(
        num_classes=4,
        ce_weight=0.4,
        dice_weight=0.4,
        focal_weight=0.2,
    )

    logits = torch.randn(2, 4, 32, 32, requires_grad=True)
    targets = torch.randint(0, 4, (2, 32, 32), dtype=torch.long)

    total_loss, components = compound(logits, targets)

    assert isinstance(total_loss, torch.Tensor)
    assert total_loss.requires_grad
    assert "loss_total" in components
    assert "loss_ce" in components
    assert "loss_dice" in components
    assert "loss_focal" in components

    expected_total = (
        0.4 * components["loss_ce"]
        + 0.4 * components["loss_dice"]
        + 0.2 * components["loss_focal"]
    )
    assert abs(components["loss_total"] - expected_total) < 1e-4

    # Autograd verification
    total_loss.backward()
    assert logits.grad is not None
    assert torch.all(torch.isfinite(logits.grad))


# -------------------------------------------------------------------------
# Test Group 3: SegmentationMetrics Suite & Boundary IoU
# -------------------------------------------------------------------------

def test_segmentation_metrics_confusion_matrix_accumulation():
    """Verifies 4x4 confusion matrix streaming updates and metric calculations."""
    metrics = SegmentationMetrics(num_classes=4)

    # Batch 1: Ground truth has 10 bg, 10 drywall; prediction has 9 bg correct, 1 drywall as bg, etc.
    targets = torch.tensor([
        [0, 0, 0, 0, 1],
        [1, 1, 2, 2, 3],
    ])
    preds = torch.tensor([
        [0, 0, 0, 1, 1],  # 1 false drywall
        [1, 1, 2, 3, 3],  # 1 non-drywall predicted as uncertain
    ])

    metrics.update(preds, targets)
    cm = metrics.get_confusion_matrix()

    assert cm.shape == (4, 4)
    # True positives: class 0 (3), class 1 (3), class 2 (1), class 3 (1)
    assert cm[0, 0] == 3
    assert cm[0, 1] == 1  # Target 0, Pred 1
    assert cm[1, 1] == 3
    assert cm[2, 2] == 1
    assert cm[2, 3] == 1  # Target 2, Pred 3
    assert cm[3, 3] == 1

    res = metrics.compute()
    assert "pixel_accuracy" in res
    assert "mean_iou_all" in res
    assert "wall_mean_iou_present" in res
    assert "per_class" in res

    # Pixel accuracy = (3 + 3 + 1 + 1) / 10 = 0.8
    assert abs(res["pixel_accuracy"] - 0.8) < 1e-3


def test_segmentation_metrics_zero_division_and_absent_class():
    """Verifies that classes completely absent from ground truth do not trigger NaN."""
    metrics = SegmentationMetrics(num_classes=4)

    # Ground truth contains only class 0 (Background) and class 1 (Drywall)
    # Class 2 (Non-Drywall) and Class 3 (Uncertain) are absent
    targets = torch.zeros((1, 50, 50), dtype=torch.long)
    targets[0, 0:10, 0:10] = 1

    # Model predicts only class 0 and class 1 accurately
    preds = targets.clone()

    metrics.update(preds, targets)
    res = metrics.compute()

    assert res["per_class"]["Non-Drywall"]["present_in_gt"] is False
    assert res["per_class"]["Uncertain"]["present_in_gt"] is False
    # Absent classes with 0 false alarms should report 1.0 trivial IoU
    assert res["per_class"]["Non-Drywall"]["iou"] == 1.0
    assert not np.isnan(res["mean_iou_all"])
    assert not np.isnan(res["wall_mean_iou_present"])


def test_boundary_iou_native_pytorch():
    """Verifies PyTorch morphological boundary extraction produces correct boundaries."""
    metrics = SegmentationMetrics(num_classes=4, boundary_radius=1)

    # 10x10 mask with a 4x4 square of class 1 in center
    mask = torch.zeros((1, 10, 10), dtype=torch.long)
    mask[0, 3:7, 3:7] = 1

    boundaries = metrics._extract_boundaries(mask)
    assert boundaries.shape == (1, 4, 10, 10)

    # Class 1 boundary should be non-zero at perimeter of the square
    b1 = boundaries[0, 1].numpy()
    assert b1.sum() > 0
    # Center pixel (4, 4) in radius 1 should be eroded away if square is large enough
    # For a 4x4 square with radius 1, all pixels are within 1 pixel of edge, so all 16 are boundary
    assert b1[3, 3] == 1.0


# -------------------------------------------------------------------------
# Test Group 4: Split Isolation Guardrails
# -------------------------------------------------------------------------

def test_split_isolation_verification_passes_on_valid_splits():
    """Verifies that the ground truth splits pass verify_split_isolation without errors."""
    splits_dir = Path("drywall_detection/data/processed/splits")
    if not (splits_dir / "train.json").exists() or not (splits_dir / "val.json").exists():
        pytest.skip("Splits directory not available for integration test.")

    train_loader = get_tile_dataloader(splits_dir / "train.json", is_train=False, batch_size=2)
    val_loader = get_tile_dataloader(splits_dir / "val.json", is_train=False, batch_size=2)
    test_loader = get_tile_dataloader(splits_dir / "test.json", is_train=False, batch_size=2)

    # Should execute cleanly without raising ValueError
    verify_split_isolation(train_loader, val_loader, test_loader)


def test_split_isolation_raises_on_leakage():
    """Verifies that verify_split_isolation raises ValueError when leakage is introduced."""
    class MockDataset:
        def __init__(self, tiles):
            self.tiles = tiles

    class MockLoader:
        def __init__(self, tiles):
            self.dataset = MockDataset(tiles)

    train_tiles = [{"sample_id": "s1", "project_id": "proj_A", "drawing_id": "d1", "quarantine": False}]
    leaked_val_tiles = [{"sample_id": "s2", "project_id": "proj_A", "drawing_id": "d2", "quarantine": False}]

    train_loader = MockLoader(train_tiles)
    val_loader = MockLoader(leaked_val_tiles)

    with pytest.raises(ValueError, match="Project leakage detected"):
        verify_split_isolation(train_loader, val_loader)


def test_split_isolation_raises_on_quarantine_in_val():
    """Verifies that quarantined tiles in val_loader raise ValueError."""
    class MockDataset:
        def __init__(self, tiles):
            self.tiles = tiles

    class MockLoader:
        def __init__(self, tiles):
            self.dataset = MockDataset(tiles)

    train_tiles = [{"sample_id": "s1", "project_id": "proj_A", "drawing_id": "d1", "quarantine": False}]
    quarantined_val = [{"sample_id": "s2", "project_id": "proj_B", "drawing_id": "d2", "quarantine": True}]

    with pytest.raises(ValueError, match="Quarantined sample"):
        verify_split_isolation(MockLoader(train_tiles), MockLoader(quarantined_val))


# -------------------------------------------------------------------------
# Test Group 5: Trainer Engine, Early Stopping & Checkpoint Contract
# -------------------------------------------------------------------------

def test_trainer_single_epoch_and_checkpoint_persistence():
    """Tests Trainer train_one_epoch, evaluate, and save_checkpoint."""
    splits_dir = Path("drywall_detection/data/processed/splits")
    if not (splits_dir / "train.json").exists():
        pytest.skip("train.json not found")

    train_loader = get_tile_dataloader(splits_dir / "train.json", is_train=True, batch_size=2)
    val_loader = get_tile_dataloader(splits_dir / "val.json", is_train=False, batch_size=2)

    model = build_segformer(num_classes=4, pretrained=False, offline=True)
    criterion = CompoundSegmentationLoss(num_classes=4)

    with tempfile.TemporaryDirectory() as tmpdir:
        trainer = Trainer(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            criterion=criterion,
            gradient_accumulation_steps=2,
            max_epochs=1,
            checkpoint_dir=tmpdir,
        )

        train_metrics = trainer.train_one_epoch(epoch=1)
        assert "train_loss" in train_metrics
        assert train_metrics["train_loss"] > 0.0

        val_metrics = trainer.evaluate(val_loader)
        assert "loss" in val_metrics
        assert "pixel_accuracy" in val_metrics

        # Save checkpoint
        saved_dir = trainer.save_checkpoint(checkpoint_dir=tmpdir, is_best=True, val_metrics=val_metrics)
        assert (Path(tmpdir) / "best_model.pt").exists()
        assert (Path(tmpdir) / "config.json").exists()
        assert (Path(tmpdir) / "class_mapping.json").exists()
        assert (Path(tmpdir) / "training_log.json").exists()
        assert (Path(tmpdir) / "metrics.json").exists()


# -------------------------------------------------------------------------
# Test Group 6: Standalone Inferencer & Hann Stitching
# -------------------------------------------------------------------------

def test_hann_window_generation():
    """Verifies 2D Hann window creation and symmetry."""
    hann = create_hann_window(512)
    assert hann.shape == (512, 512)
    assert hann[256, 256] > 0.95
    assert hann[0, 0] < 0.01
    assert np.all(hann >= 1e-4)


def test_standalone_inferencer_tile_and_sliding_window():
    """Tests StandaloneInferencer reload and inference on tile and high-res image."""
    ckpt_dir = Path("drywall_detection/checkpoints/best_model")
    if not (ckpt_dir / "best_model.pt").exists():
        pytest.skip("best_model checkpoint not yet created.")

    inferencer = StandaloneInferencer(checkpoint_dir=ckpt_dir, device="cpu")

    # 1. Single 512x512 tile
    test_tile = Image.new("RGB", (512, 512), color=(255, 255, 255))
    pred_tile = inferencer.predict_tile(test_tile)
    assert pred_tile.shape == (512, 512)
    assert pred_tile.dtype == np.uint8
    assert set(np.unique(pred_tile)).issubset({0, 1, 2, 3})

    # 2. High-res image (1024x768) sliding window
    large_img = Image.new("RGB", (1024, 768), color=(240, 240, 240))
    pred_large, probs = inferencer.predict_image_sliding_window(large_img, tile_size=512, overlap=0.2)
    assert pred_large.shape == (768, 1024)
    assert probs.shape == (768, 1024, 4)

    # 3. Render overlay
    overlay = inferencer.render_overlay(np.array(large_img), pred_large, alpha=0.45)
    assert overlay.shape == (768, 1024, 3)


def test_infer_cli_invocation(tmp_path):
    """
    Verifies that the standalone inference script (infer.py) can be invoked
    via subprocess CLI with --help and with an actual image input, producing
    valid exit code 0 and output files without NameError or crash.
    """
    import subprocess
    import sys

    ckpt_dir = Path("drywall_detection/checkpoints/best_model")
    infer_script = ckpt_dir / "infer.py"
    if not infer_script.exists():
        pytest.skip("infer.py not found")

    # 1. Test --help CLI invocation
    res_help = subprocess.run(
        [sys.executable, str(infer_script), "--help"],
        capture_output=True,
        text=True,
    )
    assert res_help.returncode == 0, f"--help failed: {res_help.stderr}"
    assert "Standalone offline inference CLI" in res_help.stdout
    assert "--input" in res_help.stdout or "--image" in res_help.stdout

    # 2. Test execution on a generated test image
    test_img_path = tmp_path / "test_input.png"
    out_img_path = tmp_path / "test_output.png"
    Image.new("RGB", (512, 512), color=(255, 255, 255)).save(test_img_path)

    res_infer = subprocess.run(
        [
            sys.executable,
            str(infer_script),
            "--input",
            str(test_img_path),
            "--output",
            str(out_img_path),
            "--device",
            "cpu",
        ],
        capture_output=True,
        text=True,
    )
    assert res_infer.returncode == 0, f"Inference execution failed:\nSTDOUT:\n{res_infer.stdout}\nSTDERR:\n{res_infer.stderr}"
    assert out_img_path.exists(), "Output annotated image was not created by CLI"
    assert out_img_path.stat().st_size > 0

    json_start = res_infer.stdout.find("{")
    assert json_start != -1, f"No JSON found in stdout:\n{res_infer.stdout}"
    summary = json.loads(res_infer.stdout[json_start:])
    assert summary["status"] == "success"
    assert summary["type"] == "image"
    assert summary["dimensions"] == [512, 512]
    assert "pixel_counts" in summary
    assert "elapsed_sec" in summary


def test_standalone_inferencer_small_canvas_guard():
    """Verifies predict_image_sliding_window gracefully handles canvases smaller than tile_size."""
    ckpt_dir = Path("drywall_detection/checkpoints/best_model")
    if not (ckpt_dir / "best_model.pt").exists():
        pytest.skip("best_model checkpoint not yet created.")

    inferencer = StandaloneInferencer(checkpoint_dir=ckpt_dir, device="cpu")

    # Image smaller in both dimensions (256x256 vs tile_size 512)
    small_img = Image.new("RGB", (256, 256), color=(255, 255, 255))
    mask_small, probs_small = inferencer.predict_image_sliding_window(small_img, tile_size=512)
    assert mask_small.shape == (256, 256)
    assert probs_small.shape == (256, 256, 4)

    # Image smaller in one dimension only (300x700)
    rect_img = Image.new("RGB", (300, 700), color=(255, 255, 255))
    mask_rect, probs_rect = inferencer.predict_image_sliding_window(rect_img, tile_size=512)
    assert mask_rect.shape == (700, 300)
    assert probs_rect.shape == (700, 300, 4)

