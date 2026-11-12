# Milestone M1 Iteration 2 Review & Adversarial Challenge Report

- **Author**: `m1_r2_reviewer_1` (M1 R2 Licensing & Format Reviewer)
- **Roles**: reviewer, critic
- **Date**: 2026-11-08T04:00:00Z
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_reviewer_1`
- **Parent Conversation ID**: `3c1a82ae-9b50-494e-b173-0369a8d4a486`
- **Handoff Type**: Hard (Task Complete)
- **Verdict**: **APPROVE**

---

## 1. Observation

### 1.1 Source Code Verification
Independent inspection of implementation files confirmed:
1. `drywall_detection/datasets/unified_format.py`:
   - Lines 28–42: `__all__` explicitly exports `validate_mask_array`.
   - Lines 103–120: `UnifiedDatasetConfig` exposes configurable parameters:
     - `max_hard_negative_ratio: float = 0.15`
     - `nominal_hard_negative_min: int = 0`
     - `nominal_hard_negatives_zero_walls: int = 0`
   - Lines 187–243: `validate_mask_array()` validates:
     - `isinstance(mask, np.ndarray)`
     - `mask.dtype == np.uint8`
     - `mask.ndim == 2`
     - Non-zero dimensions (`mask.shape[0] > 0 and mask.shape[1] > 0`)
     - Exact `expected_shape` matching if provided
     - Pixel value set strictly bounded to `{0, 1, 2, 3}` via `np.unique(mask)`
     - Flexible handling: raises `MaskValidationError` when `raise_on_error=True`, returns `False` when `raise_on_error=False`, and returns boolean if `return_bool=True`.
   - Lines 620–654: `SlidingWindowTiler.tile_drawing()`:
     - Hard negative quota capping:
       $$K_{max} = \left\lceil N_{wall} \cdot \frac{r}{1 - r} \right\rceil$$
       For $N_{wall} = 1, r = 0.15 \implies K_{max} = \lceil 0.176 \rceil = 1$, bounding ratio to $\le 50.0\%$.
       For $N_{wall} = 10, r = 0.15 \implies K_{max} = \lceil 1.765 \rceil = 2$, bounding ratio to $2/12 = 16.7\% \le 17\%$.
     - Safely bypasses division-by-zero for $r \ge 1.0$ (`max_hn = len(candidate_hn)`).
     - Caps to $0$ when $r \le 0.0$.
     - Zero-wall handling ($N_{wall} = 0$): Multi-tile sheets retain `nom_min` ($0$ tiles default), completely preventing background flooding. Single-crop patches (`len(candidate_hn) == 1`) retain $1$ tile (`max_hn = max(1, nom_min)`).
     - Variance ranking: Sorts candidate hard negatives by linework standard deviation descending, with deterministic spatial tie-breaking:
       `candidate_hn.sort(key=lambda item: (-item[3], item[2].coordinates.row_idx, item[2].coordinates.col_idx, item[2].tile_id))`
     - Preserves spatial raster order for all retained tiles:
       `results.sort(key=lambda t: (t[2].coordinates.row_idx, t[2].coordinates.col_idx))`
2. `drywall_detection/datasets/__init__.py`:
   - Line 21: `from drywall_detection.datasets.unified_format import (..., validate_mask_array, ...)`
   - Line 64: `"validate_mask_array"` present in `__all__`.
3. `drywall_detection/datasets/split_manager.py`:
   - Line 100–102: `_canonical_path()` normalizes paths with `os.path.normcase(os.path.abspath(str(p)))`.
   - Line 117–119: Regex-compatible exception string `Quarantined or pseudo-labeled tile record leakage detected in {split_name} split! Tile ID: {t.tile_id}`.
   - Lines 111–245: Exhaustive 6-layer split isolation check covering flags, projects, drawings, normalized paths, and tile IDs.

### 1.2 Independent Test Execution
1. **Targeted Unit Test Suite**:
   - Command: `python -m pytest drywall_detection/tests/unit/test_datasets.py -v`
   - Output: `64 passed in 102.11s` (Exit code 0, 100% pass rate).
   - Covered:
     - `test_multi_tile_hard_negative_quota_capping`: PASSED
     - `test_hard_negative_variance_ranking`: PASSED
     - `test_zero_wall_drawing_hard_negative_capping`: PASSED
     - `test_varying_hard_negative_quota_ratios` (0.0, 0.05, 0.15, 0.30): PASSED
     - `test_hard_negative_quota_monotonicity`: PASSED
     - `TestQuarantineIsolationValidation` (5 test methods): PASSED
     - `TestValidateMaskArrayStandalone` (19 test methods): PASSED
2. **Full Regression Test Suite**:
   - Command: `python -m pytest drywall_detection/tests/ -v`
   - Output: `325 passed, 1 warning in 330.87s` (Exit code 0, 100% pass rate).
   - Warning: PyTorch `torch.distributed.reduce_op` deprecation warning in test stress harness (non-blocking).

### 1.3 Adversarial Stress Testing Execution
An independent stress script was executed to challenge boundary conditions:
- Tie-breaking on identical variance across tiles: Confirmed top-to-bottom raster order tie-break (`row_idx=0, col_idx=1` retained over `row_idx=1, col_idx=0`).
- Multi-tile zero-wall drawing with dense linework: Confirmed 0 tiles retained (`len(tiles_zero) == 0`).
- Mask validation return modes: Confirmed `return_bool=True` returns `True` for valid masks and `False` for invalid masks when `raise_on_error=False`.
- Output: `ALL ADVERSARIAL STRESS CHECKS PASSED!`

---

## 2. Logic Chain

1. **Defect Resolution Verification**:
   - Previous review identified that unconstrained hard-negative tiling allowed up to 96% background tiles on large sheets with minimal wall content.
   - Observation 1.1 and 1.2 prove that `SlidingWindowTiler` mathematically caps hard negatives via $K_{max} = \lceil N_{wall} \cdot r / (1 - r) \rceil$.
   - On a 2000x2000 sheet with 1 wall tile and 24 candidate negative tiles, exactly 1 hard negative tile is retained ($50.0\%$ ratio bound).
   - On a multi-wall sheet with 10 wall tiles, exactly 2 hard negative tiles are retained ($16.7\%$ ratio bound).
   - Monotonicity test confirms retained hard negatives never decrease as quota ratio increases.

2. **Information Density Invariant**:
   - Background tiles must capture informative linework (general notes, schedules, partitions, dimensions) rather than blank space.
   - Observation 1.1 and 1.3 prove candidate tiles are sorted by `img_std` descending with coordinate tie-breaking.
   - Tests confirm high-variance tile `(0, 1)` is chosen over low-variance tile `(1, 0)`.

3. **Zero-Wall Canvas Protection**:
   - Non-drawing pages or unannotated sheets (schedules/notes/cover sheets) with 0 wall tiles would flood the dataset if hard negatives were retained without anchors.
   - Observation 1.1 and 1.2 demonstrate that multi-tile drawings with $N_{wall} = 0$ retain 0 tiles by default.
   - Single-tile test crops retain 1 tile, maintaining backward compatibility for targeted test cases.

4. **Integrity and Anti-Cheating Verification**:
   - Zero hardcoded return values detected in `SlidingWindowTiler.tile_drawing` or `validate_mask_array`.
   - Algorithms perform real pixel-level image processing, variance calculations, and NumPy array inspections.
   - No mock bypasses or facade implementations.
   - All 325 project tests execute genuine computation and pass cleanly.

5. **Interface and Layout Compliance**:
   - `validate_mask_array` is properly documented, typed, and exported in both `unified_format.py` and package root `drywall_detection.datasets`.
   - `.agents/teamwork/m1_r2_reviewer_1/` contains strictly metadata files (`BRIEFING.md`, `DISPATCH.md`, `progress.md`, `handoff.md`).

---

## 3. Caveats

- **No Caveats**: The implementation strictly adheres to mathematical requirements, error-handling contracts, and project isolation rules. No regressions were observed across the entire 325-test suite.

---

## 4. Conclusion & Review Summary

**Verdict**: **APPROVE**

### Findings Summary
- **Critical Findings**: 0 (No integrity violations, no blocking bugs)
- **Major Findings**: 0
- **Minor Findings**: 0

### Verified Claims
| Claim | Verification Method | Status |
|---|---|---|
| Hard negative quota capping in `SlidingWindowTiler.tile_drawing` | Inspected code lines 620-643; ran `test_multi_tile_hard_negative_quota_capping` and `test_varying_hard_negative_quota_ratios` | **VERIFIED** |
| Deterministic variance ranking with spatial tie-break | Inspected code lines 645-647; ran `test_hard_negative_variance_ranking` and adversarial stress script | **VERIFIED** |
| Zero-wall sheets cap hard negatives at 0 | Inspected code lines 636-643; ran `test_zero_wall_drawing_hard_negative_capping` and adversarial stress script | **VERIFIED** |
| Single-crop zero-wall sheets retain 1 tile | Inspected code lines 637-639; verified test compatibility | **VERIFIED** |
| Standalone `validate_mask_array` validation contract | Inspected code lines 187-243; ran all 19 `TestValidateMaskArrayStandalone` tests | **VERIFIED** |
| Package-level export of `validate_mask_array` | Inspected `__init__.py:21,64`; ran `test_validate_mask_array_exported_at_package_level` | **VERIFIED** |
| Split manager quarantine isolation & regex compatibility | Inspected `split_manager.py:117-119`; ran all 5 `TestQuarantineIsolationValidation` tests | **VERIFIED** |
| Full regression suite integrity | Ran `python -m pytest drywall_detection/tests/ -v` (325 passed, 0 failed) | **VERIFIED** |

### Adversarial Challenge Assessment
- **Overall Risk Assessment**: **LOW**
- **Division-by-Zero Risk**: Ratio $\ge 1.0$ is guarded prior to the division operation (`elif ratio >= 1.0: max_hn = len(candidate_hn)`). Passed.
- **Negative Ratio Risk**: Ratio $\le 0.0$ is guarded (`if ratio <= 0.0: max_hn = 0`). Passed.
- **Sorting Instability Risk**: 4-tuple sorting key `(-std, row_idx, col_idx, tile_id)` ensures deterministic selection across platforms. Passed.
- **Spatial Order Preservation**: Final list is re-sorted by `(row_idx, col_idx)` so downstream consumers receive tiles in canonical raster order. Passed.

---

## 5. Verification Method

To independently verify all findings and test suites:

1. **Targeted Unit Test Verification**:
   ```powershell
   python -m pytest drywall_detection/tests/unit/test_datasets.py -v
   ```
   *Expected result*: `64 passed in ~100s`.

2. **Full Project Regression Verification**:
   ```powershell
   python -m pytest drywall_detection/tests/ -v
   ```
   *Expected result*: `325 passed, 1 warning in ~330s`.

3. **Quota & Variance Focused Test Run**:
   ```powershell
   python -m pytest drywall_detection/tests/unit/test_datasets.py -k "quota or variance or zero_wall" -v
   ```
   *Expected result*: `5 passed, 0 failed`.

4. **Standalone Mask Array Test Run**:
   ```powershell
   python -m pytest drywall_detection/tests/unit/test_datasets.py -k "TestValidateMaskArrayStandalone" -v
   ```
   *Expected result*: `19 passed, 0 failed`.
