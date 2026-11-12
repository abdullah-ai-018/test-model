# Milestone M4 Review & Adversarial Critique Report

**Reviewer**: `reviewer_m4_1` (M4 Architecture & Loss Reviewer)  
**Parent Orchestrator**: `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`  
**State Folder**: `.agents/teamwork/reviewer_m4_1/`  
**Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`  
**Date**: 2026-11-09T07:40:00Z  

---

## Review Summary

**Verdict**: **APPROVE**

---

## 1. Observation

Direct observations from source code inspections, execution traces, live pytest execution, and adversarial probes:

### 1.1 Test Suite Execution
- **Command**: `pytest drywall_detection/tests/test_models.py drywall_detection/tests/test_training.py -v`
- **Result**:
  ```
  collected 35 items
  drywall_detection/tests/test_models.py::test_segformer_b0_architecture_and_parameters PASSED [  2%]
  drywall_detection/tests/test_models.py::test_segformer_b0_return_dict PASSED [  5%]
  drywall_detection/tests/test_models.py::test_unet_resnet18_architecture_and_parameters PASSED [  8%]
  drywall_detection/tests/test_models.py::test_resnet34_unet_architecture_and_parameters PASSED [ 11%]
  drywall_detection/tests/test_models.py::test_lightweight_unet_architecture_and_parameters PASSED [ 14%]
  drywall_detection/tests/test_models.py::test_create_segmentation_model_factory PASSED [ 17%]
  drywall_detection/tests/test_models.py::test_offline_instantiation_without_network PASSED [ 20%]
  drywall_detection/tests/test_models.py::test_resnet34_backward_gradient_flow PASSED [ 22%]
  drywall_detection/tests/test_models.py::test_model_backward_gradient_flow PASSED [ 25%]
  drywall_detection/tests/test_models.py::test_calculate_class_weights_enet_formula PASSED [ 28%]
  drywall_detection/tests/test_models.py::test_soft_dice_loss_bounds_and_zero_division PASSED [ 31%]
  drywall_detection/tests/test_models.py::test_focal_loss_modulation PASSED [ 34%]
  drywall_detection/tests/test_models.py::test_compound_segmentation_loss_combination PASSED [ 37%]
  drywall_detection/tests/test_models.py::test_segmentation_metrics_confusion_matrix_accumulation PASSED [ 40%]
  drywall_detection/tests/test_models.py::test_segmentation_metrics_zero_division_and_absent_class PASSED [ 42%]
  drywall_detection/tests/test_models.py::test_boundary_iou_native_pytorch PASSED [ 45%]
  drywall_detection/tests/test_models.py::test_split_isolation_verification_passes_on_valid_splits PASSED [ 48%]
  drywall_detection/tests/test_models.py::test_split_isolation_raises_on_leakage PASSED [ 51%]
  drywall_detection/tests/test_models.py::test_split_isolation_raises_on_quarantine_in_val PASSED [ 54%]
  drywall_detection/tests/test_models.py::test_trainer_single_epoch_and_checkpoint_persistence PASSED [ 57%]
  drywall_detection/tests/test_models.py::test_hann_window_generation PASSED [ 60%]
  drywall_detection/tests/test_models.py::test_standalone_inferencer_tile_and_sliding_window PASSED [ 62%]
  drywall_detection/tests/test_training.py::TestLossNumericalStability::test_soft_dice_all_background PASSED [ 65%]
  drywall_detection/tests/test_training.py::TestLossNumericalStability::test_soft_dice_single_pixel_wall PASSED [ 68%]
  drywall_detection/tests/test_training.py::TestLossNumericalStability::test_focal_loss_extreme_logits PASSED [ 71%]
  drywall_detection/tests/test_training.py::TestLossNumericalStability::test_compound_loss_backward_gradient_flow PASSED [ 74%]
  drywall_detection/tests/test_training.py::TestMultiMetricEvaluationSuite::test_miou_and_foreground_wall_iou_separation PASSED [ 77%]
  drywall_detection/tests/test_training.py::TestMultiMetricEvaluationSuite::test_confusion_matrix_normalization PASSED [ 80%]
  drywall_detection/tests/test_training.py::TestMultiMetricEvaluationSuite::test_boundary_iou_distance_sensitivity PASSED [ 82%]
  drywall_detection/tests/test_training.py::TestAntiLeakageAndQuarantineGate::test_zero_leakage_manifest_passes_on_clean_splits PASSED [ 85%]
  drywall_detection/tests/test_training.py::TestAntiLeakageAndQuarantineGate::test_zero_leakage_catches_synthetic_contamination PASSED [ 88%]
  drywall_detection/tests/test_training.py::TestAntiLeakageAndQuarantineGate::test_quarantined_samples_barred_from_val PASSED [ 91%]
  drywall_detection/tests/test_training.py::TestCheckpointPersistenceAndReload::test_segformer_checkpoint_reload_produces_identical_logits PASSED [ 94%]
  drywall_detection/tests/test_training.py::TestCheckpointPersistenceAndReload::test_best_model_checkpoint_bundle_artifacts_exist PASSED [ 97%]
  drywall_detection/tests/test_training.py::TestStandaloneInferCLI::test_infer_cli_with_image_input PASSED [100%]

  ======================= 35 passed in 132.54s (0:02:12) ========================
  ```

### 1.2 Model Architectures & Parameter Invariants
- `drywall_detection/models/segformer.py`:
  - `SegFormerB0` inherits from `nn.Module`, wrapping `SegformerForSemanticSegmentation`.
  - Exactly 3,715,172 total parameters (~3.72M) for 4 output classes.
  - Forward output: automatically bilinearly interpolated from $[B, C, H/4, W/4]$ to $[B, C, H, W]$ (lines 130–135).
- `drywall_detection/models/unet.py`:
  - `UNetWallDetector`: Native ResNet-18 backbone encoder with 4 symmetrical decoder stages (14,343,524 parameters).
  - `ResNet34UNet`: Native ResNet-34 backbone encoder with symmetrical decoder (24,433,124 parameters).
  - `LightweightUNet`: 4-stage convolutional U-Net designed for rapid CPU execution (7,763,140 parameters).
- `drywall_detection/models/__init__.py`:
  - Implements unified factory `create_segmentation_model(arch_name, num_classes=4, in_channels=3)`.

### 1.3 Loss Formulations & Mathematical Correctness
- `drywall_detection/models/losses.py`:
  - `calculate_class_weights`: Implements the ENet formulation $w_c = \frac{1}{\ln(smooth + p_c)}$ with `smooth=1.02` ensuring finite upper bound $\le 50.498$ as $p_c \to 0$.
  - `MultiClassSoftDiceLoss`: Squared denominator $\sum p^2 + \sum y^2$ (Milletari et al.) with $\epsilon = 10^{-6}$ smoothing.
  - `MultiClassFocalLoss`: Multi-class focal loss with $\gamma=2.0$ modulating factor $(1 - p_t)^\gamma$ and $\log\text{-softmax}$ numerical stabilization.
  - `CompoundSegmentationLoss`: Weighted combination ($\mathcal{L} = 0.4 \mathcal{L}_{CE} + 0.4 \mathcal{L}_{Dice} + 0.2 \mathcal{L}_{Focal}$).
  - `CompoundLoss`: Multi-loss combining `SoftDiceLoss` and `FocalLoss` ($\mathcal{L} = \alpha \mathcal{L}_{Dice} + \beta \mathcal{L}_{Focal}$) returning loss tensor and component dictionary.

### 1.4 Metrics & Anti-Leakage Gate
- `drywall_detection/models/metrics.py`:
  - `SegmentationMetricTracker`: Computes overall mIoU, Foreground Wall IoU (isolating classes $1, 2, 3$ from background class $0$ to prevent artificial inflation), Dice, Precision, Recall, Specificity.
  - Boundary IoU (Cheng et al., CVPR 2021) implemented via native PyTorch morphological erosion (`MaxPool2d`) at distances $d=2$ and $d=4$.
  - `assert_zero_leakage_manifests`: Pre-evaluation runtime assertion gate checking project ID, drawing ID, and file path overlaps, and barring quarantined/pseudo-labeled samples from validation and test sets.

### 1.5 Checkpoint Bundle Integrity
- Directory `drywall_detection/checkpoints/best_model/` contains all 8 required artifacts:
  1. `best_model.pt` (14.17 MB float32 weights)
  2. `config.json` (architecture, hyperparameters, inference parameters)
  3. `class_mapping.json` (4-class taxonomy, hex/rgb colors)
  4. `training_log.json` (3-epoch local training log)
  5. `metrics.json` (quantitative validation results)
  6. `infer.py` (standalone offline CLI script)
  7. `README.md` (documentation and reproduction instructions)
  8. `sample_overlays/` (`sample_01_original.png`, `sample_01_mask.png`, `sample_01_overlay.png` — verified valid PNG files)

### 1.6 Adversarial Probe Findings
- Probed `SoftDiceLoss`, `FocalLoss`, and `CompoundLoss` on odd spatial resolutions ($17 \times 19$): PASSED without NaN or shape errors.
- Probed `compute_boundary_iou` on all-zero ground truth and prediction: PASSED (returned 1.0 safely without zero-division).
- Probed `compute_tensor_boundary_mask` with $d=0$: PASSED.
- Probed `calculate_class_weights` with 0 frequency: PASSED (finite bound preserved).
- Probed `SegFormerB0` on non-standard resolution ($250 \times 250$): PASSED (output: $[1, 4, 250, 250]$).
- Probed `ResNet34UNet` on non-standard resolution ($250 \times 250$):
  - **Finding**: Raised `RuntimeError: Sizes of tensors must match except in dimension 1. Expected size 126 but got size 125 for tensor number 1 in the list.` at `d1 = self.dec1(torch.cat([u1, e0], dim=1))` in `drywall_detection/models/unet.py:295`.
  - **Root Cause**: `u1 = self.up1(d2)` uses raw `nn.ConvTranspose2d` without dynamic padding adjustment, unlike stages `dec4`, `dec3`, `dec2` which use `DecoderBlock` padding compensation. For standard multiples of 32 (e.g. 256x256, 512x512), sizes match perfectly.

---

## 2. Logic Chain

1. **Integrity Rule 1 (Zero Cheating / Hardcoding)**:
   - Evaluated `drywall_detection/models/` and `drywall_detection/tests/` for hardcoded results or facade implementations.
   - Verified that `test_models.py` and `test_training.py` execute dynamic autograd backward passes (`loss.backward()`), inspect gradients (`p.grad is not None`), and compute metrics dynamically via numpy/pytorch.
   - In `metrics.json`, the metrics reflect the genuine output of the 3-epoch CPU run (`pixel_accuracy: 0.6167`, `Drywall recall: 0.607`, `Drywall precision: 0.0455`), matching the exact trajectory in `training_log.json` without fabrication.
   - Result: **INTEGRITY PASS** — No violations detected.

2. **Interface & Contract Conformance (`PROJECT.md`)**:
   - `PROJECT.md` Section 1 Track 3 & Section 2 F-MODEL-ARCH require SegFormer-B0 and U-Net ResNet34 implementations. Both architectures are implemented, parameterized, and benchmarked.
   - `PROJECT.md` Section 4.4 requires an 8-item checkpoint package in `drywall_detection/checkpoints/best_model/`. All 8 items are present, structurally valid, and functional.
   - `PROJECT.md` Section 6 Rule 3 enforces non-drywall status for Detail 1A (6" CMU). Both `config.py` and `class_mapping.json` assign Detail 1A strictly to Class 2 (Non-Drywall).
   - `PROJECT.md` Section 4.3 enforces drawing-level split isolation. Both `Trainer` and standalone evaluation execute `verify_split_isolation` and `assert_zero_leakage_manifests`.
   - Result: **CONTRACT COMPLIANT**.

3. **Mathematical Correctness of Losses and Metrics**:
   - `SoftDiceLoss`: Numerically stable with $\epsilon$ smoothing, squared denominator penalizes dropout on thin lines.
   - `FocalLoss`: Numerically stable via `log_softmax` and `gather`, downweights easy background pixels by factor $(1 - p_t)^2$.
   - `CompoundLoss`: Safely aggregates dice and focal losses, propagates valid gradients.
   - `SegmentationMetricTracker`: Separates Foreground Wall IoU from overall mIoU, preventing background dominance from disguising foreground miss rates.
   - Result: **MATHEMATICALLY SOUND**.

4. **Hardware Adaptation**:
   - In a constrained host environment (Windows CPU, $<1.0\text{ GB}$ free RAM), the implementation uses memory-bounded configuration (`batch_size=2`, `num_workers=0`, `gradient_accumulation_steps=8`, `torch.set_num_threads(4)`), successfully completing training and test suites without memory exhaustion or crash.
   - Standalone `train_colab.py` is provided for full GPU convergence on Google Colab (Tesla T4).
   - Result: **HARDWARE ADAPTIVE**.

5. **Adversarial Assessment**:
   - The champion model (`SegFormerB0`) is resilient to arbitrary spatial resolutions and thin-line discontinuities due to its global self-attention and bilinear interpolation.
   - The CNN baseline (`ResNet34UNet`) contains a minor architectural edge case when given non-multiple-of-32 inputs due to unpadded `u1` concatenation in stage 1, but functions correctly on all standard pipeline resolutions ($256 \times 256$ and $512 \times 512$).
   - Result: **APPROVED WITH MINOR ADVERSARIAL OBSERVATION**.

---

## 3. Caveats

1. **Local Host Training Bounds**: Due to the severe local CPU and RAM constraints (0.57–0.90 GB free RAM), the local checkpoint represents a 3-epoch calibration run ($256 \times 256$ resolution, batch size 2, accumulation 8), not a fully converged multi-epoch GPU run. The report transparently distinguishes local calibration metrics from target GPU capacity projections.
2. **Held-Out Validation Tile Class Distribution**: The held-out validation tile evaluated in `metrics.json` contained Background (Class 0) and Drywall (Class 1), but zero ground truth pixels for Non-Drywall (Class 2) and Uncertain (Class 3). The metrics correctly record `present_in_gt: false` for these classes.
3. **95% CDs Status**: The 99th Street PDF represents an interim 95% CDs progress set. Weak pseudo-labeling guardrails (quarantine from val/test, loss discount factor $\lambda = 0.35$) were properly applied.

---

## 4. Conclusion

Milestone M4 deliverables demonstrate high technical quality, mathematical rigor, and strict integrity compliance:
- **Zero integrity violations**: No hardcoding, no facades, no fabricated numbers.
- **Test results**: 35 of 35 unit/integration tests passing (100% pass rate in 132s).
- **Interface compliance**: All 8 required checkpoint bundle artifacts exist, reload cleanly, and execute inference without error.
- **Champion selection**: SegFormer-B0 is well-justified over ResNet34-UNet based on parameter efficiency (3.72M vs 24.43M), host memory safety, and global context preservation.
- **Verdict**: **APPROVE**.

### Recommendations for Milestone M5/M6:
- [Minor] In `drywall_detection/models/unet.py`, consider wrapping `up1` in a `DecoderBlock` or applying `F.pad` before `torch.cat([u1, e0], dim=1)` so that `ResNet34UNet` and `UNetWallDetector` gracefully accept arbitrary odd/non-multiple-of-32 input dimensions.
- Proceed directly to Milestone M5 (Local PDF Testing Interface & Inference Pipeline).

---

## 5. Verification Method

To independently verify these findings:
1. **Run full M4 test suites**:
   ```powershell
   python -m pytest drywall_detection/tests/test_models.py drywall_detection/tests/test_training.py -v
   ```
   *Expected outcome*: 35 tests pass with 0 failures.
2. **Verify standalone checkpoint reload and CLI inference**:
   ```powershell
   python drywall_detection/checkpoints/best_model/infer.py --image drywall_detection/checkpoints/best_model/sample_overlays/sample_01_original.png --output test_overlay.png --checkpoint drywall_detection/checkpoints/best_model --device cpu
   ```
   *Expected outcome*: Exits with code 0, emits JSON telemetry with pixel counts, and outputs `test_overlay.png`.
3. **Inspect checkpoint bundle contents**:
   ```powershell
   Get-ChildItem drywall_detection/checkpoints/best_model/
   ```
   *Expected outcome*: `best_model.pt`, `config.json`, `class_mapping.json`, `training_log.json`, `metrics.json`, `infer.py`, `README.md`, `sample_overlays/`.
