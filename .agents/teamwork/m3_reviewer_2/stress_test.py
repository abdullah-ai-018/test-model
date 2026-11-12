"""
Independent Stress-Testing and Verification Script for Milestone M3
Author: m3_reviewer_2
"""
import json
from pathlib import Path
import sys

# Ensure workspace root is on sys.path
workspace_root = str(Path(__file__).resolve().parents[3])
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

import numpy as np
import torch
import torch.nn.functional as F

from drywall_detection.models.losses import (
    calculate_class_weights,
    MultiClassSoftDiceLoss,
    MultiClassFocalLoss,
    CompoundSegmentationLoss,
)
from drywall_detection.models.metrics import (
    SegmentationMetrics,
    compute_boundary_iou,
    compute_tensor_boundary_mask,
    assert_zero_leakage_manifests,
)
from drywall_detection.models.trainer import (
    configure_cpu_hardware,
    verify_split_isolation,
)

def test_class_weights():
    print("=== Testing calculate_class_weights ===")
    # 1. Normalization w[0] == 1.0
    freqs = [0.95, 0.03, 0.015, 0.005]
    w = calculate_class_weights(freqs, smooth=1.02, normalize=True)
    assert abs(w[0].item() - 1.0) < 1e-5, f"w[0] not 1.0: {w[0]}"
    print(f"Calibrated weights: {w.tolist()}")

    # 2. Finite supremum as p -> 0
    zero_freqs = [1.0, 0.0, 0.0, 0.0]
    w_unnorm = calculate_class_weights(zero_freqs, smooth=1.02, normalize=False)
    supremum = 1.0 / np.log(1.02) # ~50.4984
    print(f"Zero freq unnormalized: {w_unnorm.tolist()}, supremum: {supremum:.4f}")
    assert (w_unnorm <= supremum + 1e-4).all(), f"Weights exceed supremum: {w_unnorm}"
    assert torch.isfinite(w_unnorm).all()

    # 3. Invalid smooth <= 1.0
    try:
        calculate_class_weights(freqs, smooth=1.0)
        assert False, "Should have raised ValueError for smooth=1.0"
    except ValueError:
        pass
    print("Class weights tests PASSED.")

def test_soft_dice_loss():
    print("=== Testing MultiClassSoftDiceLoss ===")
    loss_fn = MultiClassSoftDiceLoss(num_classes=4, smooth=1e-6)

    # 1. Identical prediction
    targets = torch.tensor([[[0, 1, 2, 3]]], dtype=torch.long) # [1, 1, 4]
    logits = torch.full((1, 4, 1, 4), -50.0)
    for i in range(4):
        logits[0, i, 0, i] = 50.0
    l_perf = loss_fn(logits, targets)
    assert l_perf.item() < 0.01, f"Loss not near 0: {l_perf.item()}"
    print(f"Perfect match loss: {l_perf.item():.6f}")

    # 2. Empty classes in target
    bg_targets = torch.zeros((2, 64, 64), dtype=torch.long)
    rand_logits = torch.randn(2, 4, 64, 64, requires_grad=True)
    l_empty = loss_fn(rand_logits, bg_targets)
    assert torch.isfinite(l_empty), "Loss non-finite on empty classes"
    l_empty.backward()
    assert rand_logits.grad is not None
    assert torch.isfinite(rand_logits.grad).all()
    print(f"Empty classes loss: {l_empty.item():.6f}, grad finite: True")

    # 3. Extreme logits (+/- 1000)
    extreme_logits = torch.clamp(rand_logits * 100.0, -1000.0, 1000.0)
    l_extreme = loss_fn(extreme_logits, bg_targets)
    assert torch.isfinite(l_extreme), f"Extreme logits loss non-finite: {l_extreme}"
    print(f"Extreme logits loss: {l_extreme.item():.6f}")
    print("Soft Dice tests PASSED.")

def test_focal_loss():
    print("=== Testing MultiClassFocalLoss ===")
    alpha = torch.tensor([1.0, 5.0, 15.0, 20.0])
    focal_fn = MultiClassFocalLoss(gamma=2.0, alpha=alpha, num_classes=4)

    # 1. Gradient flow check
    logits = torch.randn(2, 4, 32, 32, requires_grad=True)
    targets = torch.randint(0, 4, (2, 32, 32), dtype=torch.long)
    loss = focal_fn(logits, targets)
    assert torch.isfinite(loss), "Focal loss non-finite"
    loss.backward()
    assert logits.grad is not None
    assert torch.isfinite(logits.grad).all()
    print(f"Focal loss value: {loss.item():.6f}, grad finite: True")

    # 2. Easy vs hard pixel ratio
    easy_logits = torch.tensor([[[[20.0]], [[-20.0]], [[-20.0]], [[-20.0]]]]) # p(0) ~ 1.0
    hard_logits = torch.tensor([[[[0.0]], [[0.0]], [[0.0]], [[0.0]]]])         # p(0) = 0.25
    t = torch.tensor([[0]], dtype=torch.long)
    l_easy = focal_fn(easy_logits, t)
    l_hard = focal_fn(hard_logits, t)
    print(f"Easy pixel loss: {l_easy.item():.8f}, Hard pixel loss: {l_hard.item():.6f}")
    assert l_easy.item() < l_hard.item() * 1e-3, "Focal modulation factor failed"
    print("Focal Loss tests PASSED.")

def test_compound_loss():
    print("=== Testing CompoundSegmentationLoss ===")
    loss_fn = CompoundSegmentationLoss(
        num_classes=4,
        ce_weight=0.4,
        dice_weight=0.4,
        focal_weight=0.2,
    )
    logits = torch.randn(2, 4, 32, 32, requires_grad=True)
    targets = torch.randint(0, 4, (2, 32, 32), dtype=torch.long)

    total_loss, comps = loss_fn(logits, targets)
    print(f"Compound components: {comps}")
    reconstructed = 0.4 * comps["loss_ce"] + 0.4 * comps["loss_dice"] + 0.2 * comps["loss_focal"]
    assert abs(comps["loss_total"] - reconstructed) < 1e-4, f"Sum mismatch: {comps['loss_total']} vs {reconstructed}"
    total_loss.backward()
    assert torch.isfinite(logits.grad).all()
    print("Compound Loss tests PASSED.")

def test_metrics():
    print("=== Testing SegmentationMetrics ===")
    metrics = SegmentationMetrics(num_classes=4)

    # All 4 classes present
    targets = torch.tensor([
        [0, 1],
        [2, 3],
    ])
    preds = torch.tensor([
        [0, 1],
        [2, 0], # class 3 misclassified as 0
    ])
    metrics.update(preds, targets)
    res = metrics.compute()
    cm = np.array(res["confusion_matrix"])
    print(f"Confusion matrix:\n{cm}")
    assert cm.shape == (4, 4)
    assert cm[0, 0] == 1 # TP 0
    assert cm[1, 1] == 1 # TP 1
    assert cm[2, 2] == 1 # TP 2
    assert cm[3, 0] == 1 # FN 3, FP 0
    assert res["per_class"]["Background"]["gt_pixels"] == 1
    assert res["per_class"]["Drywall"]["iou"] == 1.0
    assert res["per_class"]["Non-Drywall"]["iou"] == 1.0
    assert res["per_class"]["Uncertain"]["iou"] == 0.0

    # Wall mIoU macro average check:
    # classes: Drywall (1.0), Non-Drywall (1.0), Uncertain (0.0) -> mean = (1.0 + 1.0 + 0.0) / 3 = 0.6667
    assert abs(res["wall_mean_iou_present"] - 0.6667) < 1e-3, f"Wall mIoU mismatch: {res['wall_mean_iou_present']}"
    print(f"Wall mIoU present: {res['wall_mean_iou_present']}")
    print("Metrics tests PASSED.")

def test_split_isolation():
    print("=== Testing Split Isolation & Manifest Integrity ===")
    splits_dir = Path("drywall_detection/data/processed/splits")
    train_p = splits_dir / "train.json"
    val_p = splits_dir / "val.json"
    test_p = splits_dir / "test.json"
    quarantine_p = splits_dir / "quarantine.json"

    assert train_p.exists() and val_p.exists() and test_p.exists() and quarantine_p.exists()

    with open(train_p, "r", encoding="utf-8") as f:
        t_data = json.load(f)["tiles"]
    with open(val_p, "r", encoding="utf-8") as f:
        v_data = json.load(f)["tiles"]
    with open(test_p, "r", encoding="utf-8") as f:
        te_data = json.load(f)["tiles"]
    with open(quarantine_p, "r", encoding="utf-8") as f:
        q_data = json.load(f)["tiles"]

    t_projs = {t.get("project_id") for t in t_data}
    v_projs = {t.get("project_id") for t in v_data}
    te_projs = {t.get("project_id") for t in te_data}
    q_projs = {t.get("project_id") for t in q_data}

    print(f"Train projects ({len(t_projs)}): {t_projs}")
    print(f"Val projects ({len(v_projs)}): {v_projs}")
    print(f"Test projects ({len(te_projs)}): {te_projs}")
    print(f"Quarantine projects ({len(q_projs)}): {q_projs}")

    # Project disjointness
    assert len(t_projs & v_projs) == 0, f"Leakage train & val: {t_projs & v_projs}"
    assert len(t_projs & te_projs) == 0, f"Leakage train & test: {t_projs & te_projs}"
    assert len(v_projs & te_projs) == 0, f"Leakage val & test: {v_projs & te_projs}"

    # Drawing disjointness
    t_draws = {t.get("drawing_id") for t in t_data if t.get("drawing_id")}
    v_draws = {t.get("drawing_id") for t in v_data if t.get("drawing_id")}
    te_draws = {t.get("drawing_id") for t in te_data if t.get("drawing_id")}
    print(f"Train drawings ({len(t_draws)}): {t_draws}")
    print(f"Val drawings ({len(v_draws)}): {v_draws}")
    print(f"Test drawings ({len(te_draws)}): {te_draws}")

    assert len(t_draws & v_draws) == 0, f"Drawing leakage train & val: {t_draws & v_draws}"
    assert len(t_draws & te_draws) == 0, f"Drawing leakage train & test: {t_draws & te_draws}"
    assert len(v_draws & te_draws) == 0, f"Drawing leakage val & test: {v_draws & te_draws}"

    # File path disjointness
    t_imgs = {t.get("image_path") for t in t_data}
    v_imgs = {t.get("image_path") for t in v_data}
    te_imgs = {t.get("image_path") for t in te_data}
    assert len(t_imgs & v_imgs) == 0, f"Image path leakage train & val: {t_imgs & v_imgs}"
    assert len(t_imgs & te_imgs) == 0, f"Image path leakage train & test: {t_imgs & te_imgs}"
    assert len(v_imgs & te_imgs) == 0, f"Image path leakage val & test: {v_imgs & te_imgs}"

    # Quarantine and pseudo label absence in val and test
    for t in v_data:
        assert not t.get("quarantine", False), f"Quarantined tile in val: {t}"
        assert not t.get("is_pseudo_label", False), f"Pseudo-label tile in val: {t}"

    for t in te_data:
        assert not t.get("quarantine", False), f"Quarantined tile in test: {t}"
        assert not t.get("is_pseudo_label", False), f"Pseudo-label tile in test: {t}"

    print("Split isolation verification PASSED.")

def test_checkpoint_bundle():
    print("=== Testing Checkpoint Bundle ===")
    ckpt_dir = Path("drywall_detection/checkpoints/best_model")
    pt_p = ckpt_dir / "best_model.pt"
    assert pt_p.exists(), f"Missing {pt_p}"
    ckpt = torch.load(pt_p, map_location="cpu")
    print(f"Checkpoint keys: {list(ckpt.keys())}")
    assert "model_state_dict" in ckpt
    assert "best_metric" in ckpt
    print(f"Architecture in ckpt: {ckpt.get('architecture')}, best metric: {ckpt.get('best_metric')}")
    print("Checkpoint bundle test PASSED.")

if __name__ == "__main__":
    test_class_weights()
    test_soft_dice_loss()
    test_focal_loss()
    test_compound_loss()
    test_metrics()
    test_split_isolation()
    test_checkpoint_bundle()
    print("ALL STRESS TESTS COMPLETED SUCCESSFULLY!")
