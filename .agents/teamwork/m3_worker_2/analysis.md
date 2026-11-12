# Milestone M3 Iteration 2 Implementation Analysis

**Author**: `m3_worker_2` (Milestone M3 Iteration 2 Implementation Worker)  
**Date**: 2026-11-09T07:38:00Z  
**State Folder**: `.agents/teamwork/m3_worker_2/`  

---

## 1. Context & Scope

This analysis outlines the precise implementation changes required for Milestone M3 Iteration 2, synthesizing the verified findings from Explorers `m3_iter2_explorer_1`, `m3_iter2_explorer_2`, and `m3_iter2_explorer_3`.

Exclusive File Ownership:
- `drywall_detection/checkpoints/best_model/config.json`
- `drywall_detection/models/trainer.py`
- `drywall_detection/models/metrics.py`
- `drywall_detection/checkpoints/best_model/infer.py`
- `drywall_detection/tests/test_models.py`

---

## 2. Target File Audit & Status

1. **`drywall_detection/checkpoints/best_model/config.json`**:
   - Currently contains `"input_size": [256, 256]`, `"input_resolution": [256, 256]`, `"tile_size": 256`, `"tile_overlap": 64`.
   - Action: Update to 512x512 resolution, tile_size 512, tile_overlap 102 (20% overlap).

2. **`drywall_detection/models/trainer.py`**:
   - `verify_split_isolation` lines 102–108: Already contains drawing-level train/test and val/test intersection checks.
   - `Trainer.save_checkpoint`: Line 430 and lines 446–449 currently serialize `input_size: [256, 256]`, `input_resolution: [256, 256]`, `tile_size: 256`, `tile_overlap: 64`.
   - Action: Update defaults to `input_size: [512, 512]`, `input_resolution: [512, 512]`, `tile_size: 512`, `tile_overlap: 102`.

3. **`drywall_detection/models/metrics.py`**:
   - `assert_zero_leakage_manifests`: Lines 349–379 already check `te_draws`, `t_draws & te_draws`, `v_draws & te_draws`, `t_imgs & te_imgs`, `v_imgs & te_imgs`, and quarantine/pseudo-label flags on `("test", te_tiles)`.
   - Status: Verified intact, no edits required.

4. **`drywall_detection/checkpoints/best_model/infer.py`**:
   - `import time` at line 28: Confirmed present.
   - Line 97: `self.hann_window = create_hann_window(512)` -> Needs dynamic binding `self.tile_size = int(self.config.get("tile_size") or 512)` and `self.hann_window = create_hann_window(self.tile_size)`.
   - Lines 152–154: `predict_tile` checks `(512, 512)` -> Needs to use `(self.tile_size, self.tile_size)`.
   - Lines 193–209 and 249–251: Small-canvas bounds guard is already present.
   - Action: Update `__init__` and `predict_tile` to dynamically use `self.tile_size`.

5. **`drywall_detection/tests/test_models.py`**:
   - Test Group 6 currently ends at line 525.
   - Action: Append `test_infer_cli_invocation(tmp_path)` and `test_standalone_inferencer_small_canvas_guard()`.

---

## 3. Implementation Plan

1. Edit `drywall_detection/checkpoints/best_model/config.json`.
2. Edit `drywall_detection/models/trainer.py`.
3. Edit `drywall_detection/checkpoints/best_model/infer.py`.
4. Edit `drywall_detection/tests/test_models.py`.
5. Execute verification commands:
   - Pytest `test_models.py` for new tests.
   - Pytest `test_m3_adversarial_loss_splits.py`.
   - `infer.py --help`.
   - `infer.py` mock image inference with cleanup.
   - Python command checking `assert_zero_leakage_manifests`.
   - Fast regression test suite (115 tests).
6. Document in `progress.md` and `handoff.md`.
