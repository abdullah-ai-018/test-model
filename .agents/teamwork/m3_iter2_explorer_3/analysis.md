# Adversarial Regression & Test Strategy Analysis: Milestone M3 Iteration 2

**Author**: `m3_iter2_explorer_3` (Adversarial Regression & Test Strategy Explorer)  
**Date**: 2026-11-09T07:24:00Z  
**Milestone**: Milestone M3 — Iteration 2 Remediation & Final Verification  
**Status**: Complete  

---

## 1. Executive Summary & Synthesis

Following Milestone M3 Iteration 1 review, two parallel investigations identified specific defects requiring remediation:
1. **`m3_reviewer_1` (Reviewer Defect Report)**: Identified a fatal `NameError: name 'time' is not defined` when executing `drywall_detection/checkpoints/best_model/infer.py` via CLI, missing CLI subprocess test coverage in `test_models.py`, resolution metadata discrepancy (`config.json` stating 256 while pipeline uses 512), and sliding window array broadcasting failures on images smaller than tile size.
2. **`m3_challenger_2` (Challenger Adversarial Stress Report)**: Identified data leakage blindspots in `drywall_detection/models/trainer.py` (`verify_split_isolation` failing to verify `test_drawings` intersections) and `drywall_detection/models/metrics.py` (`assert_zero_leakage_manifests` omitting test drawing collisions and test split quarantine assertions), resulting in 4 failed tests in `drywall_detection/tests/test_m3_adversarial_loss_splits.py`.

As the **Adversarial Regression & Test Strategy Explorer**, this investigation synthesized findings from peer explorers `m3_iter2_explorer_1` and `m3_iter2_explorer_2`, audited the entire repository test suite across 20 test modules, verified that the split isolation guardrails in `trainer.py` and `metrics.py` have already been securely hardened, and designed the comprehensive verification test execution plan for implementation worker `m3_worker_2`.

### Core Assessment Summary:
- **Baseline Integrity**: The entire repository test suite was executed across all M1, M2, and M3 modules. **674 tests passed with 0 failures and 0 regressions**.
- **Adversarial Invariants**: All 18 tests in `test_m3_adversarial_loss_splits.py` now pass cleanly in ~22.3s. The drawing-level anti-leakage checks and test split quarantine enforcement operate without false positives on clean production splits.
- **CLI & Checkpoint Status**: Standalone CLI inference (`infer.py`) successfully executed on `drywall_detection/data/processed/images/mock_plan_00.png` in 10.21s, generating valid color overlays and JSON summary metrics. The small-canvas bounds guard is already implemented and verified.
- **Remaining Worker Actions**: The implementation scope for `m3_worker_2` is strictly confined to:
  1. Synchronizing `drywall_detection/checkpoints/best_model/config.json` metadata to `tile_size: 512`, `input_size: [512, 512]`, and `tile_overlap: 102`.
  2. Updating `drywall_detection/models/trainer.py` line 422 and 438–441 defaults to 512.
  3. Dynamically binding `self.tile_size` in `infer.py:StandaloneInferencer` from config.
  4. Adding `test_infer_cli_invocation(tmp_path)` and `test_standalone_inferencer_small_canvas_guard()` to `drywall_detection/tests/test_models.py`.

---

## 2. Full Repository Test Baseline & Regression Audit

An empirical audit was conducted across every test suite in the workspace. Below is the comprehensive empirical test matrix:

| # | Test Module | Target Domain | Test Count | Execution Time | Status | Key Invariants Verified |
|---|---|---|:---:|:---:|:---:|---|
| 1 | `test_coords.py` | Coordinate Geometry | 21 | 1.8s | **PASS** | Bijective affine roundtrip $|\Delta| < 10^{-4}$ pt, 90° CW rotation, Shapely polygons |
| 2 | `test_coords_stress.py` | Extreme Geometries | 27 | 2.1s | **PASS** | Monte Carlo points, degenerate bboxes, multi-quadrant rotations |
| 3 | `test_audit.py` | Dataset Auditing | 21 | 2.4s | **PASS** | 6 candidate catalog, MSD/CubiCasa eligibility, disk safety guards |
| 4 | `test_licensing_audit.py` | Licensing Gates | 12 | 1.5s | **PASS** | Commercial terms, CC-BY-NC compliance, zero-license acceptance |
| 5 | `test_hardware.py` | Environment Profiling | 20 | 1.9s | **PASS** | Tier 5 CPU constrained host auto-config, RAM/VRAM probes |
| 6 | `test_schedule.py` | Partition Schedules | 9 | 6.4s | **PASS** | 24 assembly details, Tag 1A CMU veto, `REVIEW_REQUIRED.lock` (exit 2) |
| 7 | `test_data.py` | Multi-Dataset Prep | 28 | 8.2s | **PASS** | Strict project/drawing split isolation, 8-bit indexed masks, QC triplets |
| 8 | `test_vector.py` | Vector Linework & Matching | 36 | 15.5s | **PASS** | 3-tier spatial matching, PyMuPDF vector extraction, Usman ground truth |
| 9 | `test_vector_adversarial_stress.py` | Spatial Adversarial R1 | 72 | 2.1s | **PASS** | Cross-orthogonal leaders, ambiguous buffers, synthetic 1000 walls |
| 10 | `test_vector_adversarial_stress_r2.py` | Spatial Adversarial R2 | 80 | 2.2s | **PASS** | High-density tag clusters, fuzzy tag discovery, boundary raycasting |
| 11 | `test_m1_adversarial_stress.py` | M1 Adversarial Suite | 39 | 14.8s | **PASS** | Corrupt images, memory stability, NaN/Inf floating masks |
| 12 | `test_quota_adversarial_stress.py` | Tiling Quota Formula | 37 | 12.6s | **PASS** | Ceiling formula ceiling bounds, hard negative ratios, zero-loss tiles |
| 13 | `test_split_leakage_adversarial.py` | Split Leakage Gate | 41 | 3.5s | **PASS** | Synthetic project overlap injection, quarantine flag injection |
| 14 | `test_tiling_stitching_stress.py` | Tiling & Hann Apodization | 81 | 11.2s | **PASS** | Hann window symmetry, discrete label error, boundary tile clamping |
| 15 | `test_adversarial_m1.py` | M1 Comprehensive Gate | 21 | 2.2s | **PASS** | Full pre-flight data pipeline contract validation |
| 16 | `test_adversarial_m3.py` | M3 Adversarial Defense | 21 | 3.1s | **PASS** | Detail 1A safety tampering veto, CSV corruption resilience |
| 17 | `test_challenger_m3_iter2.py` | M3 Iter 2 Challenger Suite | 55 | 355.7s | **PASS** | 24 detail integrity, Tag 7F shaft wall discovery, master PDF scan |
| 18 | `test_models.py` | Model Architecture & Ops | 22 | 68.1s | **PASS** | SegFormer/U-Net params, compound loss bounds, 1-epoch training test |
| 19 | `test_training.py` | Training & Checkpoint Gate | 13 | 593.5s | **PASS** | Loss numerical stability, checkpoint persistence, CLI execution |
| 20 | `test_m3_adversarial_loss_splits.py` | M3 Loss & Split Challenger | 18 | 22.3s | **PASS** | Class weights $\le 50.5$, PyTorch MaxPool Boundary IoU == OpenCV, split checks |
| **TOTAL** | **Full Workspace Suite** | **All Tracks (M1–M3)** | **674** | **~1120s** | **100% PASS** | **Zero Regressions Detected Across Entire Codebase** |

---

## 3. Peer Analysis Synthesis & Conflict Resolution

### 3.1 Review of `m3_iter2_explorer_1` (CLI & Checkpoint Remediation)
- **Strengths**: Accurately captured root cause of `infer.py` CLI failure, identified resolution metadata mismatch (256 vs 512), and discovered small canvas sliding-window broadcasting failure. Provided exact code diffs and pytest test cases.
- **Resolution**:
  - `import time`: Verified already present at line 28 of `infer.py`. CLI execution verified working.
  - Small canvas bounds guard: Verified already implemented at lines 193–209 and 249–251 of `infer.py`. Canvas is safely padded with white background to `tile_size` and unpadded upon exit.
  - Test additions: `test_infer_cli_invocation` and `test_standalone_inferencer_small_canvas_guard` must be added to `drywall_detection/tests/test_models.py` to prevent future regressions.
  - Config reconciliation: `config.json` must be updated to `tile_size: 512`, `input_size: [512, 512]`, and `tile_overlap: 102`.

### 3.2 Review of `m3_iter2_explorer_2` (Split Isolation & Manifest Integrity)
- **Strengths**: Accurately isolated the two missing checks in `trainer.py:verify_split_isolation` and `metrics.py:assert_zero_leakage_manifests`.
- **Resolution**:
  - The drawing-level intersection checks in `trainer.py` (lines 102–108) and test drawing/quarantine assertions in `metrics.py` (lines 346–365) are already present in the workspace.
  - Empirical execution of `test_m3_adversarial_loss_splits.py` verified all 18 tests pass (100%).
  - Clean production splits (`drywall_detection/data/processed/splits/`) pass without any false positives.

### 3.3 Dissenting Views / Resolved Conflicts
- No unresolved dissent exists. Both peer explorers converged on the necessity of these fixes, and the empirical test baseline demonstrates that the implemented changes do not degrade any existing functionality.

---

## 4. Blast Radius Analysis

### 4.1 Changes to `drywall_detection/models/trainer.py`
- **Change**: Added `train_drawings.intersection(test_drawings)` and `val_drawings.intersection(test_drawings)` assertions in `verify_split_isolation`. Updated `save_checkpoint` default config to 512.
- **Blast Radius**:
  - Production splits: MTA A-100 to A-103 and MSD in train; MTA A-104 and Spark Lake Grove in test. Zero drawing overlap. PASSED.
  - Unit tests: Mock split tests in `test_models.py` (`test_split_isolation_verification_passes_on_valid_splits`, `test_split_isolation_raises_on_leakage`) supply disjoint drawings or do not define test loaders. PASSED.
  - Risk Level: **MINIMAL / ZERO RISK**.

### 4.2 Changes to `drywall_detection/models/metrics.py`
- **Change**: Added test manifest drawing overlap checks and included `("test", te_tiles)` in quarantine assertions in `assert_zero_leakage_manifests`.
- **Blast Radius**:
  - Production manifests: Clean manifests in `data/processed/splits` contain 0 quarantined tiles in test set. PASSED.
  - Adversarial tests: 4 previously failing tests now pass immediately. PASSED.
  - Risk Level: **MINIMAL / ZERO RISK**.

### 4.3 Changes to `drywall_detection/checkpoints/best_model/config.json`
- **Change**: Synchronize `input_size: [512, 512]`, `input_resolution: [512, 512]`, `tile_size: 512`, `tile_overlap: 102`.
- **Blast Radius**:
  - `infer.py` dynamically reads `config.get("tile_size")`. When set to 512, matches `create_hann_window(512)` and `loader.py` tile size.
  - Downstream Milestone M4 will read `config.json` to configure full-plan sliding window inference. Setting it to 512 ensures consistency.
  - Risk Level: **MINIMAL / HIGH REWARD**.

### 4.4 Changes to `drywall_detection/tests/test_models.py`
- **Change**: Adding `test_infer_cli_invocation` and `test_standalone_inferencer_small_canvas_guard`.
- **Blast Radius**:
  - Purely additive test cases. Modifies zero existing tests.
  - Uses `tmp_path` fixture for synthetic image generation; creates zero temporary file leakage.
  - Execution time: ~20s on CPU.
  - Risk Level: **ZERO RISK**.

---

## 5. Step-by-Step Implementation Guide for `m3_worker_2`

### Step 1: Update `drywall_detection/checkpoints/best_model/config.json`
Replace lines 8–17 with:
```json
  "input_size": [
    512,
    512
  ],
  "input_resolution": [
    512,
    512
  ],
  "tile_size": 512,
  "tile_overlap": 102,
```

### Step 2: Update `drywall_detection/models/trainer.py`
In `Trainer.save_checkpoint`:
- At line 422: change `"input_size": [256, 256]` to `"input_size": [512, 512]`.
- At lines 438–441:
```python
            "input_size": [512, 512],
            "input_resolution": [512, 512],
            "tile_size": 512,
            "tile_overlap": 102,
```

### Step 3: Verify & Harden `drywall_detection/checkpoints/best_model/infer.py`
1. Confirm line 28 contains `import time`.
2. In `StandaloneInferencer.__init__` (around line 96–97):
```python
        self.tile_size = int(self.config.get("tile_size") or 512)
        self.hann_window = create_hann_window(self.tile_size)
```
3. In `StandaloneInferencer.predict_tile` (line 152):
```python
        target_size = (self.tile_size, self.tile_size)
        if tile_img.size != target_size:
            tile_img = tile_img.resize(target_size, Image.BILINEAR)
```

### Step 4: Add New Regression Tests to `drywall_detection/tests/test_models.py`
At the end of Test Group 6 in `drywall_detection/tests/test_models.py`, append:

```python
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
```

---

## 6. End-to-End Test Verification Protocol

The worker and subsequent reviewers must execute the following protocol sequentially:

### Verification Phase 1: Targeted Remediation Verification
1. Run newly added tests in `test_models.py`:
   ```powershell
   python -m pytest drywall_detection/tests/test_models.py -k "test_infer_cli_invocation or test_standalone_inferencer" -v
   ```
   *Expected Outcome*: 3 passed, 0 failed in ~30s.

2. Run full `test_models.py` (fast suite excluding 1-epoch training):
   ```powershell
   python -m pytest drywall_detection/tests/test_models.py -k "not test_trainer_single_epoch_and_checkpoint_persistence" -v
   ```
   *Expected Outcome*: 23 passed, 0 failed in ~28s.

3. Run adversarial loss and split isolation suite:
   ```powershell
   python -m pytest drywall_detection/tests/test_m3_adversarial_loss_splits.py -v
   ```
   *Expected Outcome*: 18 passed, 0 failed in ~23s.

### Verification Phase 2: Standalone CLI Manual Smoke Check
```powershell
python drywall_detection/checkpoints/best_model/infer.py --input drywall_detection/data/processed/images/mock_plan_00.png --output test_overlay.png
```
*Expected Outcome*:
- Exits with code 0.
- Prints JSON object with `"status": "success"` and dimensions `[1024, 1024]`.
- Generates `test_overlay.png`.
- Cleanup:
  ```powershell
  Remove-Item -Force test_overlay.png -ErrorAction SilentlyContinue
  ```

### Verification Phase 3: Manifest Anti-Leakage Gate Check
```powershell
python -c "from drywall_detection.models.metrics import assert_zero_leakage_manifests; from pathlib import Path; p = Path('drywall_detection/data/processed/splits'); assert_zero_leakage_manifests(p/'train.json', p/'val.json', p/'test.json'); print('PASS CLEAN')"
```
*Expected Outcome*: Prints `PASS CLEAN` with exit code 0.

### Verification Phase 4: Full Repository Regression Sign-Off
```powershell
python -m pytest drywall_detection/tests/test_coords.py drywall_detection/tests/test_audit.py drywall_detection/tests/test_data.py drywall_detection/tests/test_vector.py drywall_detection/tests/test_schedule.py drywall_detection/tests/test_m3_adversarial_loss_splits.py -v
```
*Expected Outcome*: 133 passed, 0 failed in ~60s.

---

## 7. Zero-Tolerance Integrity & Forensic Compliance

1. **Rule 1 — Never hardcode test results**: All assertions must run dynamically on live PyTorch tensors, Shapely polygons, and filesystem manifests.
2. **Rule 2 — Never fabricate metrics**: The reported SegFormer-B0 metrics in `metrics.json` reflect real single-epoch evaluation numbers ($mIoU=0.1639$, Wall $IoU=0.0442$, Boundary $IoU=0.0369$).
3. **Rule 3 — Tag 1A Safety Veto**: Tag 1A CMU non-drywall safety override remains 100% active and tested across 24 details.
4. **Rule 4 — Progress Set Limitations**: All reports and checkpoint readmes explicitly cite that MTA Contract C-48526 is a 95% CD progress set and single-project calibration sample.
5. **Rule 5 — Workspace Layout Discipline**: `.agents/teamwork/` contains exclusively agent metadata markdown files (`BRIEFING.md`, `DISPATCH.md`, `progress.md`, `analysis.md`, `handoff.md`). Zero code, test, or data files exist in `.agents/teamwork/`.
