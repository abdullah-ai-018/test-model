# Handoff Report: Test Design & Validation Specification (M1 Iteration 2)

- **Subagent**: `m1_r2_explorer_3`
- **Role**: Test Design & Validation Explorer
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2)
- **Handoff Type**: Hard (Investigation & Test Design Complete)
- **Recipient**: Orchestrator (`3c1a82ae-9b50-494e-b173-0369a8d4a486`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_3`
- **Date**: 2026-11-08T02:40:00Z
- **Reference Analysis**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_3\analysis.md`

---

## 1. Observation

1. **Adversarial Defect Reproduction by Reviewer `m1_reviewer_2`**:
   - In `.agents/teamwork/m1_reviewer_2/handoff.md` (lines 33–58), reviewer demonstrated that on a 2000x2000 drawing containing 1 wall tile and 24 hard negative linework tiles:
     ```
     Total tiles generated: 25
     Wall tiles: 1
     Hard negative tiles: 24
     Actual hard negative ratio: 96.00%
     Config max_hard_negative_ratio: 15.00%
     ```
   - All 24 candidate hard negatives were retained unconditionally, violating the 15% quota mandate.

2. **Code Inspection of `drywall_detection/datasets/unified_format.py`**:
   - Line 94: `max_hard_negative_ratio: float = 0.15` is declared in `UnifiedDatasetConfig`.
   - Lines 511–533: In `SlidingWindowTiler.tile_drawing()`, tiles are checked for `is_pure_blank` and `has_walls`. Pure blank tiles without walls are skipped (`continue`), but all other tiles (including every hard negative) are unconditionally appended to `results`. The attribute `max_hard_negative_ratio` is never referenced.

3. **Code Inspection of `drywall_detection/tests/unit/test_datasets.py`**:
   - Lines 170–200: `test_tile_filtering_blank_and_hard_neg` tested hard negative retention on only a single 512x512 tile in isolation (`assert len(tiles_hn) == 1`). It never generated a multi-tile drawing with mixed wall and non-wall tiles, never computed the ratio $N_{HN} / (N_W + N_{HN})$, and never tested zero-wall drawings under quota capping.

4. **Code Inspection of `drywall_detection/datasets/split_manager.py`**:
   - Lines 99–176: `verify_split_isolation(manifest)` verifies pairwise disjointness between `train_tiles`, `val_tiles`, and `test_tiles` across project IDs, drawing IDs, and image/mask paths.
   - However, `manifest.quarantine_tiles` is never cross-checked against `val_tiles` or `test_tiles`, and individual tiles with `is_pseudo_label=True` or `quarantine=True` residing in validation or test splits are not caught.

5. **Standalone API Gap for `validate_mask_array()`**:
   - `drywall_detection/tests/test_tiling_stitching_stress.py` (lines 429–444) documented that `validate_mask_array()` was not exposed as a top-level callable in `unified_format.py` or `drywall_detection/datasets/__init__.py`; mask validation logic was strictly embedded in `UnifiedMask.__init__`.

---

## 2. Logic Chain

1. *Premise*: Requirement R1 and dispatch mandate: *"Blank tile filtering and hard negative retention within 15% quota"* with project-isolated zero-leakage splits and pseudo-label quarantine.
2. *Observation 1 & 2*: `SlidingWindowTiler` lacked quota enforcement because `tile_drawing()` unconditionally retained every hard negative candidate, causing the ratio to reach 96% on linework-rich drawings.
3. *Observation 3*: `test_datasets.py` failed to detect this because tests evaluated 512x512 images with 1 tile each, missing multi-tile population dynamics.
4. *Observation 4 & 5*: `verify_split_isolation()` and `validate_mask_array()` lack dedicated test assertions for quarantine isolation against validation/test sets and standalone convenience function contracts.
5. *Deduction*: To ensure the defect is permanently resolved and future regressions are prevented, `test_datasets.py` requires 5 dedicated unit test suites covering:
   - Multi-tile drawings with 1 wall and 24 linework tiles verifying hard negative capping ($\le 15\%$ or ceiling bound).
   - Zero-wall drawings verifying that hard negatives are capped at 0.
   - Varying quota ratios ($r \in \{0.0, 0.05, 0.15, 0.30\}$) verifying monotonic non-decreasing retention.
   - Quarantine isolation verification in `verify_split_isolation()` raising `SplitLeakageError` upon any leak into val/test.
   - Standalone `validate_mask_array()` validation across valid classes, invalid values, invalid dtypes, and invalid shapes.
6. *Synthesis*: The comprehensive test specifications authored in `analysis.md` provide concrete, drop-in Python code with exact assertions and invariants for implementation by `m1_worker_1`.

---

## 3. Caveats

1. **Ceiling vs Floor Rounding Policy on Small Wall Counts**:
   - For $N_W = 1$ and $r = 0.15$:
     $\lceil 1 \cdot 0.15 / 0.85 \rceil = 1 \implies 1 \text{ HN retained} \implies 1/2 = 50\%$.
     $\lfloor 1 \cdot 0.15 / 0.85 \rfloor = 0 \implies 0 \text{ HN retained} \implies 0/1 = 0\%$.
   - The test specifications in `analysis.md` accommodate both: asserting `len(hn_tiles) <= 1` for $N_W = 1$ and asserting strict $\le 17\%$ quota adherence for $N_W \ge 10$ ($10 \cdot 0.15 / 0.85 = 1.76 \implies \le 2$ HN). Under no circumstance is $N_W=1, N_{HN}=24$ (96%) permitted.
2. **Zero-Wall Drawing Capping**:
   - Under standard formula $N_{HN}^{max} = \lceil 0 \cdot r / (1 - r) \rceil = 0$. Zero-wall drawings yield 0 tiles by default.
   - If an optional override is implemented for negative-control sheets (`allow_zero_wall_drawings=True`), tests should evaluate both default (0 tiles) and override behaviors.
3. **Quarantine In Train vs Val/Test**:
   - MTA 99th Street weak pseudo-labels may be partitioned into a quarantine pool or used experimentally in `train_tiles`, but must **strictly never enter `val_tiles` or `test_tiles`**.

---

## 4. Conclusion

The test specifications for Milestone M1 Iteration 2 are fully designed, documented, and mathematically verified in `analysis.md`. 

### Summary of Test Suites Designed for `m1_worker_1`:
1. `test_multi_tile_hard_negative_quota_capping`: Multi-tile 2000x2000 drawing, 1 wall, 24 HN $\implies$ caps HN at $\le 1$. Multi-tile 10 walls, 15 HN $\implies$ caps HN at $\le 2$ ($\le 17\%$).
2. `test_hard_negative_selection_prioritizes_highest_variance`: When candidates exceed quota, tiles with highest linework variance (`img_std`) are deterministically retained.
3. `test_zero_wall_drawing_hard_negative_capping`: 2000x2000 drawing with 0 walls $\implies$ caps HN at 0 (0 total tiles retained).
4. `test_varying_hard_negative_quota_ratios` & `test_hard_negative_quota_monotonicity`: Evaluates $r \in \{0.00, 0.05, 0.15, 0.30\}$ asserting exact bound adherence and monotonic non-decreasing retention.
5. `TestQuarantineIsolationValidation`: Evaluates `verify_split_isolation()` on clean quarantine, quarantine leak into `val_tiles`, quarantine leak into `test_tiles`, duplicate file paths, and `is_pseudo_label=True` in val/test.
6. `TestValidateMaskArrayStandalone`: Validates `validate_mask_array()` on valid arrays, values $> 3$, non-uint8 dtypes (`float32`, `int32`, `bool`), non-2D shapes (1D, 3D, 4D), and non-array objects.

---

## 5. Verification Method

Once `m1_worker_1` implements the code fixes and integrates these tests:

1. **Execute Unit Tests in `test_datasets.py`**:
   ```powershell
   python -m pytest drywall_detection/tests/unit/test_datasets.py -v
   ```
   *Expected result*: All existing tests plus the new multi-tile quota, zero-wall capping, varying ratio, quarantine isolation, and `validate_mask_array` tests pass with 0 failures.

2. **Execute Full Test Suite**:
   ```powershell
   python -m pytest drywall_detection/tests/ -v
   ```
   *Expected result*: All 174+ tests pass cleanly.

3. **Adversarial Stress Verification Command**:
   ```powershell
   python -c "import numpy as np, cv2; from drywall_detection.datasets.unified_format import SlidingWindowTiler, UnifiedDatasetConfig, UnifiedMask, DatasetClass; config = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20, max_hard_negative_ratio=0.15); tiler = SlidingWindowTiler(config); img = np.full((2000, 2000, 3), 255, dtype=np.uint8); [cv2.line(img, (0, i), (2000, i), (0, 0, 0), 2) for i in range(100, 1900, 100)]; mask_data = np.zeros((2000, 2000), dtype=np.uint8); mask_data[50:100, 50:100] = DatasetClass.DRYWALL.value; tiles = tiler.tile_drawing(img, UnifiedMask(mask_data), 'test', 'src'); hn = [t for t in tiles if t[2].is_hard_negative]; print(f'Hard Negatives: {len(hn)}/{len(tiles)} ({len(hn)/len(tiles):.1%})'); assert len(hn) <= 1"
   ```
   *Expected output*: `Hard Negatives: <= 1 / 2 (<= 50.0%)` without assertion error.

4. **Invalidation Conditions**:
   - Any multi-tile drawing retaining $> \lceil N_W \cdot r / (1 - r) \rceil$ hard negatives.
   - Any zero-wall drawing retaining $> 0$ hard negatives under default config.
   - Any quarantined tile or project appearing in `val_tiles` or `test_tiles` without raising `SplitLeakageError`.
   - Any mask array containing values $> 3$ passing `validate_mask_array()` without raising `MaskValidationError`.
