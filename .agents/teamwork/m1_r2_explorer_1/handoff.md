# Handoff Report: Tiling & Hard Negative Quota Architecture & Algorithm Specification

- **Subagent**: `m1_r2_explorer_1`
- **Role**: Tiling & Hard Negative Quota Explorer (explorer, investigator)
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2)
- **Handoff Type**: Hard (Investigation Complete)
- **Recipient**: Orchestrator (`3c1a82ae-9b50-494e-b173-0369a8d4a486`) / `m1_worker_1`
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_1`
- **Detailed Technical Report**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_1\analysis.md`
- **Timestamp**: 2026-11-08T02:40:00Z

---

## 1. Observation

1. **Reviewer Failure Report**:
   - In `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_reviewer_2\handoff.md`, reviewer `m1_reviewer_2` observed that:
     ```python
     # Adversarial stress test on 2000x2000 drawing with 1 wall tile and 24 linework tiles:
     Total tiles generated: 25
     Wall tiles: 1
     Hard negative tiles: 24
     Actual hard negative ratio: 96.00%
     Config max_hard_negative_ratio: 15.00%
     ```
   - Reviewer issued `REQUEST_CHANGES` due to unconstrained retention of hard negatives.

2. **Code Inspection of `drywall_detection/datasets/unified_format.py`**:
   - `UnifiedDatasetConfig` (line 94):
     `max_hard_negative_ratio: float = 0.15`
   - In `SlidingWindowTiler.tile_drawing()` (lines 511–535):
     ```python
     is_pure_blank = (img_std < self.config.min_variance_threshold) and (img_mean > self.config.blank_mean_threshold)
     is_hard_negative = (not has_walls) and (not is_pure_blank)

     # Pure blank tiles without walls are 100% discarded
     if is_pure_blank and not has_walls:
         continue

     metadata = TileMetadata(...)
     results.append((img_tile, mask_tile, metadata))
     ```
   - Verbatim finding: `max_hard_negative_ratio` was never accessed or used in `tile_drawing()`. Any tile with linework (`is_hard_negative == True`) was appended immediately to `results`.

3. **Current Test Suite Execution**:
   - Ran `python -m pytest drywall_detection/tests/unit/test_datasets.py -v`.
   - Output: `28 passed in 19.95s`.
   - Line 171 `test_tile_filtering_blank_and_hard_neg` currently tests an isolated 512x512 tile with zero walls:
     ```python
     tiles_hn = tiler.tile_drawing(hn_img, hn_mask, "draw_hn", "test_source")
     assert len(tiles_hn) == 1
     ```
     This passed previously only because 100% of hard negatives were retained unconditionally.

---

## 2. Logic Chain

1. *Premise*: Dispatch Requirement 3 and Project specification mandate blank tile filtering and hard negative retention within a 15% quota ($r = 0.15$).
2. *Observation 2*: `tile_drawing()` appends tiles synchronously in a coordinate grid loop without accumulating wall tiles or candidate hard negatives.
3. *Observation 1*: An architectural drawing with sparse walls but pervasive linework (gridlines, notes, furniture) produces 96% hard negative tiles under the current implementation.
4. *Deduction (Mathematical Quota)*:
   To ensure that hard negative tiles comprise at most fraction $r$ of the retained tiles:
   $$\frac{N_{hn}^{retained}}{N_w + N_{hn}^{retained}} \le r \iff N_{hn}^{retained} \le \frac{r}{1 - r} \cdot N_w$$
   Using ceiling:
   $$\text{max\_hn} = \left\lceil N_w \cdot \frac{r}{1 - r} \right\rceil$$
   For $r = 0.15$, $\frac{r}{1 - r} \approx 0.17647$. For $N_w = 1$, $\text{max\_hn} = 1$.
5. *Deduction (Zero-Wall Edge Case)*:
   If $N_w = 0$, strict ratio enforcement yields $\text{max\_hn} = 0$.
   In real production, this is desirable: non-floorplan drawings (e.g., G-001 Title Block, General Notes) produce 0 tiles rather than polluting the dataset with 100% negative tiles.
   To preserve developer flexibility and allow unit tests to extract single hard negative tiles, `UnifiedDatasetConfig` must introduce `nominal_hard_negative_min: int = 0`. When $N_w == 0$, $\text{max\_hn} = \text{nominal\_hard\_negative\_min}$.
6. *Deduction (Ranking Criteria)*:
   When candidate hard negatives exceed $\text{max\_hn}$, candidates must be sorted by descending linework variance (`img_std`), which is already computed during blank checking (0 additional compute overhead). A secondary spatial tie-breaker `(row_idx, col_idx)` ensures 100% deterministic reproducibility across platforms.
7. *Deduction (Existing Test Compatibility)*:
   In `test_datasets.py::test_tile_filtering_blank_and_hard_neg`, the single-tile test with $N_w = 0$ must test default rejection (`nominal_hard_negative_min = 0` yielding 0 tiles) and isolated retention with `nominal_hard_negative_min = 1` (yielding 1 tile).

---

## 3. Caveats

1. **Integer Ceiling at Low Wall Counts**:
   With $N_w = 1$ and $r = 0.15$, $\lceil 1 \times 0.1765 \rceil = 1$, resulting in 1 wall tile and 1 hard negative tile (50% local ratio). This is an expected artifact of integer discreteness on small drawings. As $N_w$ grows to 10 or 100, the retained ratio converges to $16.7\%$ and $15.25\%$, strictly bounding hard negative explosion.
2. **Inference vs Training Tiling**:
   During inference in Milestones M4 and M6, `compute_tile_grid` and `stitch_predictions` are used over the entire grid without dropping tiles to ensure 100% surface coverage. Quota filtering applies strictly to dataset creation during `tile_drawing`.

---

## 4. Conclusion

The fix strategy is completely specified and validated:
1. **Partition**: In `SlidingWindowTiler.tile_drawing()`, separate valid tiles into `wall_tiles` and `candidate_hn` (storing `img_std`).
2. **Quota Calculation**:
   - If $r \le 0.0$: `max_hn = nom_min if num_walls == 0 else 0`
   - Elif $r \ge 1.0$: `max_hn = len(candidate_hn)`
   - Elif $num\_walls > 0$: `max_hn = max(nom_min, int(np.ceil(num_walls * ratio / (1.0 - ratio))))`
   - Else: `max_hn = nom_min`
3. **Variance Ranking**: Sort `candidate_hn` by `(-img_std, row_idx, col_idx)` and retain `[:max_hn]`.
4. **Canonical Spatial Order**: Combine `wall_tiles + retained_hn` and sort by `(row_idx, col_idx)`.
5. **Config Update**: Add `nominal_hard_negative_min: int = 0` to `UnifiedDatasetConfig`.
6. **Test Suite Expansion**:
   - Update `test_tile_filtering_blank_and_hard_neg` to verify default suppression of wall-less sheets and `nominal_hard_negative_min=1` single-tile extraction.
   - Add `test_hard_negative_quota_enforcement` (replicating the 2000x2000 24-candidate adversarial scenario, asserting only 1 hard negative is kept).
   - Add `test_hard_negative_variance_ranking` (asserting highest variance tile is chosen over faint lines).

Complete implementation blueprint and code snippets are available in `analysis.md`.

---

## 5. Verification Method

To independently verify the implementation when `m1_worker_1` finishes:

1. **Adversarial Stress Test Verification**:
   ```powershell
   python -c "import numpy as np, cv2; from drywall_detection.datasets.unified_format import SlidingWindowTiler, UnifiedDatasetConfig, UnifiedMask, DatasetClass; config = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20, max_hard_negative_ratio=0.15); tiler = SlidingWindowTiler(config); img = np.full((2000, 2000, 3), 255, dtype=np.uint8); [cv2.line(img, (0, i), (2000, i), (0, 0, 0), 2) for i in range(100, 1900, 100)]; mask_data = np.zeros((2000, 2000), dtype=np.uint8); mask_data[50:100, 50:100] = DatasetClass.DRYWALL.value; tiles = tiler.tile_drawing(img, UnifiedMask(mask_data), 'test', 'src'); hn = [t for t in tiles if t[2].is_hard_negative]; print(f'Hard Negatives: {len(hn)}/{len(tiles)} ({len(hn)/len(tiles):.1%})'); assert len(hn) == 1; assert len(tiles) == 2"
   ```
   *Expected Output*: `Hard Negatives: 1/2 (50.0%)` (down from 24/25, 96.0%).

2. **Full Unit Test Suite Execution**:
   ```powershell
   python -m pytest drywall_detection/tests/unit/test_datasets.py -v
   ```
   *Expected Output*: 30 passed (including 2 new tests for quota enforcement and variance ranking).

3. **Invalidation Conditions**:
   - Any drawing with multiple hard negatives retaining $> \text{ceil}(N_w \cdot \frac{r}{1 - r})$.
   - Hard negatives selected arbitrarily or non-deterministically instead of by highest `img_std`.
   - Broken spatial sorting order in returned `tiles`.
   - Any failure in `drywall_detection/tests/`.
