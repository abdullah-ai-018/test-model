# Milestone M3 Loss, Boundary IoU & Split Isolation Challenger Handoff Report

**Agent**: `m3_challenger_2` (Loss & Split Isolation Challenger)  
**Recipient**: `parent` (Milestone M3 Orchestrator / Project Team)  
**Date**: 2026-11-08T20:21:00Z  
**Type**: Hard Handoff (Adversarial Stress Testing Complete)  
**Verdict**: **REQUEST_CHANGES**  

---

## Challenge Summary

**Overall Risk Assessment**: **CRITICAL**

While the numerical stability of compound loss functions, class weight bounds, and the mathematical equivalence of native PyTorch Boundary IoU morphological erosion to OpenCV are robustly verified, empirical stress-testing revealed **two critical data leakage blindspots**:
1. `drywall_detection/models/trainer.py` (`verify_split_isolation`): Drawing-level leakage between the training split and the held-out test split (and between validation and test) silently passes without raising a `ValueError`.
2. `drywall_detection/models/metrics.py` (`assert_zero_leakage_manifests`): Drawing-level leakage and quarantined/pseudo-labeled tile exclusion checks on the test manifest are completely omitted.

---

## 1. Observation

Direct empirical observations, verbatim file paths, line numbers, and tool outputs:

### 1.1 Empirical Test Suite Execution
An adversarial test suite was authored and executed at `drywall_detection/tests/test_m3_adversarial_loss_splits.py`:
- Command: `python -m pytest drywall_detection/tests/test_m3_adversarial_loss_splits.py -v`
- Results across the full suite:
  - `test_class_weights_zero_frequency_upper_bound`: **PASSED**
  - `test_empty_targets_finite_scalar`: **PASSED**
  - `test_inverse_predictions_monotonicity_and_gradients`: **PASSED**
  - `test_extreme_logits_numerical_stability`: **PASSED**
  - `test_pytorch_erosion_vs_opencv_erode[1]`: **PASSED**
  - `test_pytorch_erosion_vs_opencv_erode[2]`: **PASSED**
  - `test_pytorch_erosion_vs_opencv_erode[3]`: **PASSED**
  - `test_pytorch_erosion_vs_opencv_erode[5]`: **PASSED**
  - `test_boundary_mask_extraction_equivalence`: **PASSED**
  - `test_attack_1_project_id_overlap_train_val`: **PASSED**
  - `test_attack_2_drawing_id_overlap_train_test`: **FAILED** (`Failed: DID NOT RAISE ValueError`)
  - `test_attack_3_quarantined_tile_injected_into_val`: **PASSED**
  - `test_attack_4_pseudo_labeled_tile_injected_into_test`: **PASSED**
  - `test_attack_5_project_id_overlap_train_test`: **PASSED**
  - `test_attack_6_quarantined_tile_injected_into_test`: **PASSED**
  - `test_attack_7_drawing_id_overlap_val_test`: **FAILED** (`Failed: DID NOT RAISE ValueError`)
  - `test_drawing_overlap_train_test_manifests`: **FAILED** (`Failed: DID NOT RAISE RuntimeError`)
  - `test_quarantined_tile_in_test_manifest`: **FAILED** (`Failed: DID NOT RAISE RuntimeError`)

### 1.2 Inspection of `drywall_detection/models/trainer.py`
In `drywall_detection/models/trainer.py` (lines 93–101):
```python
    # Drawing-level isolation check
    train_drawings = {t["drawing_id"] for t in train_tiles if "drawing_id" in t}
    val_drawings = {t["drawing_id"] for t in val_tiles if "drawing_id" in t}
    test_drawings = {t["drawing_id"] for t in test_tiles if "drawing_id" in t}

    draw_train_val = train_drawings.intersection(val_drawings)
    if draw_train_val:
        raise ValueError(f"Drawing leakage detected between Train and Val: {draw_train_val}")
```
- Direct Observation: `test_drawings` is defined on line 96, but is **never evaluated** in any intersection operation.
- No `train_drawings.intersection(test_drawings)` check exists.
- No `val_drawings.intersection(test_drawings)` check exists.

### 1.3 Inspection of `drywall_detection/models/metrics.py`
In `drywall_detection/models/metrics.py` (lines 336–352):
```python
    if test_manifest_path is not None:
        with open(test_manifest_path, "r", encoding="utf-8") as f:
            te_data = json.load(f)
        te_tiles = te_data.get("tiles") or te_data.get("samples") or []
        te_projs = {t.get("project_id") for t in te_tiles if t.get("project_id")}
        if t_projs & te_projs:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Projects leaked between train and test: {t_projs & te_projs}")
        if v_projs & te_projs:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Projects leaked between val and test: {v_projs & te_projs}")

    for name, tiles in [("validation", v_tiles)]:
        for t in tiles:
            if t.get("quarantine", False):
                raise RuntimeError(f"[QUARANTINE LEAKAGE] Quarantined sample {t.get('sample_id')} found in {name} split!")
            if t.get("is_pseudo_label", False):
                raise RuntimeError(f"[QUARANTINE LEAKAGE] Pseudo-labeled sample {t.get('sample_id')} found in {name} split!")
```
- Direct Observation: `te_draws` is never computed; drawing leakage between train and test splits is ignored.
- Direct Observation: Line 346 only iterates over `("validation", v_tiles)`; any `quarantine: True` or `is_pseudo_label: True` tile inside `te_tiles` (test split) is not checked.

---

## 2. Challenges & Findings

### [Critical] Challenge 1: Drawing Leakage Bypasses `trainer.py:verify_split_isolation`
- **Assumption challenged**: `verify_split_isolation` in `trainer.py` enforces drawing-level isolation across all three loaders (train, val, test).
- **Attack scenario**: Inject a tile into `test_loader` that shares a `drawing_id` with a tile in `train_loader` (while having distinct `project_id`).
- **Blast radius**: The training engine fails to catch drawing-level leakage between training and testing data, directly violating `PROJECT.md` Section 4.3 and Acceptance Criteria ("Train, validation, and test splits are strictly separated at drawing level with zero project overlap"). Models could inadvertently evaluate on tiles from the same physical architectural drawing sheet seen during training.
- **Empirical proof**: `test_attack_2_drawing_id_overlap_train_test` and `test_attack_7_drawing_id_overlap_val_test` failed with `DID NOT RAISE ValueError`.
- **Mitigation**:
  In `drywall_detection/models/trainer.py` around line 101, add:
  ```python
  if test_drawings:
      draw_train_test = train_drawings.intersection(test_drawings)
      if draw_train_test:
          raise ValueError(f"Drawing leakage detected between Train and Test: {draw_train_test}")
      draw_val_test = val_drawings.intersection(test_drawings)
      if draw_val_test:
          raise ValueError(f"Drawing leakage detected between Val and Test: {draw_val_test}")
  ```

### [High] Challenge 2: Test Manifest Blindspot in `metrics.py:assert_zero_leakage_manifests`
- **Assumption challenged**: Pre-evaluation assertion gate in `metrics.py` ensures strict zero leakage and quarantine compliance before metrics are computed.
- **Attack scenario**: Inject a drawing collision between train and test manifests, or inject a quarantined tile into `test.json`.
- **Blast radius**: `evaluate.py` or any evaluation script relying on `assert_zero_leakage_manifests` will compute benchmark numbers on contaminated test sets without triggering an abort.
- **Empirical proof**: `test_drawing_overlap_train_test_manifests` and `test_quarantined_tile_in_test_manifest` failed with `DID NOT RAISE RuntimeError`.
- **Mitigation**:
  In `drywall_detection/models/metrics.py`:
  1. Extract `te_draws = {t.get("drawing_id") for t in te_tiles if t.get("drawing_id")}` and assert `t_draws & te_draws == set()` and `v_draws & te_draws == set()`.
  2. In the quarantine check loop, iterate over both `("validation", v_tiles)` and `("test", te_tiles)`.

---

## 3. Stress Test Results

| Test ID | Stress Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|:---:|
| **LOSS-01** | Zero-frequency class ($p_c = 0$) in `calculate_class_weights` | Finite weight strictly $\le 50.5$, no NaNs | $1.0 / \ln(1.02) = 50.4967$, finite scalar | **PASS** |
| **LOSS-02** | Empty targets (100% background, zero foreground) | Finite scalar losses across CE, Dice, Focal | All losses returned finite scalars ($L \approx 1.0$) | **PASS** |
| **LOSS-03** | Inverse predictions ($P(\text{bg}) \to 1.0$ when $Y = \text{drywall}$) | Strictly monotonic loss growth & non-zero gradients | Loss monotonically rose: $0.811 \to 10.342$; $\|\nabla\| > 0$ | **PASS** |
| **LOSS-04** | Extreme logits ($\pm 1000.0$) | Log-sum-exp stabilization, zero NaNs/Infs | Evaluated without overflow or underflow | **PASS** |
| **BIOU-01** | PyTorch MaxPool2D erosion vs OpenCV `cv2.erode` (100 trials, $r \in \{1, 2, 3, 5\}$) | $\sum \|cv2 - torch\| == 0$ | 0 pixel difference across all 100 random masks | **PASS** |
| **BIOU-02** | `compute_tensor_boundary_mask` vs OpenCV gradient | $\sum \|\text{torch} - \text{cv2}\| == 0$ | 0 pixel difference across all radii | **PASS** |
| **SPLIT-01** | Project ID overlap train vs val | Raises `ValueError` | Intercepted with `ValueError` | **PASS** |
| **SPLIT-02** | Drawing ID overlap train vs test | Raises `ValueError` | Silently passed (no exception) | **FAIL** |
| **SPLIT-03** | Quarantined tile in val split | Raises `ValueError` | Intercepted with `ValueError` | **PASS** |
| **SPLIT-04** | Pseudo-labeled tile in test split | Raises `ValueError` | Intercepted with `ValueError` | **PASS** |
| **SPLIT-05** | Project ID overlap train vs test | Raises `ValueError` | Intercepted with `ValueError` | **PASS** |
| **SPLIT-06** | Quarantined tile in test split | Raises `ValueError` | Intercepted with `ValueError` | **PASS** |
| **SPLIT-07** | Drawing ID overlap val vs test | Raises `ValueError` | Silently passed (no exception) | **FAIL** |
| **MANIF-01** | Drawing ID overlap train vs test manifest | Raises `RuntimeError` | Silently passed (no exception) | **FAIL** |
| **MANIF-02** | Quarantined tile in test manifest | Raises `RuntimeError` | Silently passed (no exception) | **FAIL** |

---

## 4. Unchallenged Areas

- **Distributed Data Parallel (DDP)**: Multi-node GPU synchronization of metrics and losses was not challenged, as the workspace is configured for Tier 5 local CPU training and single-GPU Colab execution.
- **Non-square MaxPool structuring elements**: MaxPool2D uses symmetric $(2d+1) \times (2d+1)$ square kernels; non-isotropic structuring elements were not evaluated as Boundary IoU definition specifies isotropic Euclidean/Chebyshev boundary distances.

---

## 5. Logic Chain

1. **Premise 1 (Contract Requirement)**: `PROJECT.md` Section 4.3 and Dispatch Task 3 dictate that `verify_split_isolation` must intercept Drawing ID overlap between train and test splits with an immediate `ValueError`, and zero leakage must exist across all splits at both project and drawing levels.
2. **Premise 2 (Direct Observation)**: In `trainer.py` line 96, `test_drawings` is parsed, but lines 98–101 only compute `train_drawings.intersection(val_drawings)`. Neither `train_drawings.intersection(test_drawings)` nor `val_drawings.intersection(test_drawings)` is computed.
3. **Premise 3 (Direct Observation)**: In `metrics.py` lines 346–352, only `v_tiles` is inspected for `quarantine` and `is_pseudo_label`. `te_tiles` is not inspected.
4. **Empirical Verification**: Pytest execution of `drywall_detection/tests/test_m3_adversarial_loss_splits.py` produced 4 concrete failures when hostile test splits were supplied.
5. **Deductive Conclusion**: The implementation does not satisfy the zero-leakage invariant for train-test drawing overlap or test set quarantine enforcement. Therefore, changes must be requested before advancing to Milestone M4.

---

## 6. Caveats

- **No False Positives**: The existing production split manifests (`drywall_detection/data/processed/splits/`) do not currently have drawing leaks (train has MTA A-100..A-103 and MSD; test has MTA A-104 and Spark Lake Grove). However, the validator functions are our protective guardrails against future dataset additions, automated cross-validation splits, and pipeline regressions.
- **Review-Only Constraint**: In strict adherence to Challenger constraints, no implementation code was altered by this agent.

---

## 7. Conclusion & Verdict

**Verdict**: **REQUEST_CHANGES**

The M3 implementation worker must apply the two straightforward fixes:
1. In `drywall_detection/models/trainer.py` (`verify_split_isolation`): Add checks for `train_drawings.intersection(test_drawings)` and `val_drawings.intersection(test_drawings)` raising `ValueError`.
2. In `drywall_detection/models/metrics.py` (`assert_zero_leakage_manifests`): Add test drawing overlap check and add `("test", te_tiles)` to the quarantine/pseudo-label assertion loop.

Once applied, running `python -m pytest drywall_detection/tests/test_m3_adversarial_loss_splits.py -v` will produce 100% (18/18) passed.

---

## 8. Verification Method

To verify these findings:
```powershell
python -m pytest drywall_detection/tests/test_m3_adversarial_loss_splits.py -v
```
Expected output currently: 14 passed, 4 failed (reproducing the exact vulnerabilities).
After fixes are applied by the worker: 18 passed.
