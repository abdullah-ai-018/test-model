# Technical Specification & Contract Analysis: Milestone M1 Iteration 2

- **Author**: `m1_r2_spec_miner_2_rep` (Specification Miner)
- **Role**: Tiling & Filtering Specification Miner
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_spec_miner_2_rep`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Target Modules**:
  - `drywall_detection/datasets/unified_format.py` (`SlidingWindowTiler.tile_drawing()`, `validate_mask_array()`, `UnifiedMask`)
  - `drywall_detection/datasets/split_manager.py` (`verify_split_isolation()`)
  - `drywall_detection/datasets/__init__.py` (public interface exports)
  - `drywall_detection/tests/unit/test_datasets.py`, `drywall_detection/tests/test_m1_adversarial_stress.py`

---

## 1. Executive Summary & Purpose

During Milestone M1 Review, Reviewer `m1_reviewer_2` flagged a critical defect in Requirement 3:
`SlidingWindowTiler.tile_drawing()` lacked hard negative quota capping, unconditionally retaining 100% of non-blank, non-wall tiles. On an architectural test canvas with 1 wall tile and 24 non-blank linework tiles, the pipeline produced a **96.0% hard negative ratio** despite `UnifiedDatasetConfig.max_hard_negative_ratio = 0.15` being declared.

Concurrently, Challenger `m1_challenger_1` identified two architectural improvements:
1. Standalone `verify_split_isolation()` validated cross-split disjointness among `train`, `val`, and `test`, but completely omitted `manifest.quarantine_tiles` and failed to check whether tiles in `val_tiles` or `test_tiles` were tagged `quarantine=True` or `is_pseudo_label=True`.
2. `validate_mask_array()` was requested as a standalone convenience validation function exported in `unified_format.py` and `datasets/__init__.py`.

This specification provides the authoritative functional contracts, mathematical derivations, typing signatures, docstrings, deterministic selection algorithms, and edge-case behaviors required for `m1_worker_1` / `worker_m1_iter2` to implement these fixes without ambiguity.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Tiling & Filtering | Hard Negative Identification | Classifies tiles as hard negatives if they have no wall annotations (`not has_walls`) but contain linework/text (`not is_pure_blank`). | `img_tile: np.ndarray`, `mask_tile: UnifiedMask`, `config` | `is_hard_negative: bool` (in `TileMetadata`) | If corrupted shape or invalid mask values, tile is dropped (`continue`). | `unified_format.py:511-513` |
| 2 | Tiling & Filtering | Hard Negative Quota Enforcement | Enforces `max_hard_negative_ratio` cap so retained hard negatives do not distort dataset balance. | Candidate HN list, wall tiles list, `config.max_hard_negative_ratio` | Quota-capped list of retained hard negative tiles | When `len(wall_tiles) == 0`, caps at nominal minimum (1 for single-tile crops, 0 for multi-tile unannotated sheets). | Reviewer failure report (`m1_reviewer_2/handoff.md:102`) |
| 3 | Tiling & Filtering | Deterministic HN Ranking | Ranks candidate hard negative tiles by linework variance descending to keep the most informative background tiles (e.g. schedules, text, structural lines). | Candidate tiles list with image standard deviation and coordinates | Deterministically sorted candidate list | Tie-broken deterministically by `(row_idx, col_idx, tile_id)` ascending. | DISPATCH.md Requirement 2; Reviewer handoff |
| 4 | Tiling & Filtering | Output Spatial Reordering | Re-sorts final merged retained tiles (wall tiles + selected hard negatives) back into canonical raster-scan spatial order. | Merged tile list | `List[Tuple[np.ndarray, UnifiedMask, TileMetadata]]` sorted by `(row_idx, col_idx)` | None (in-place or stable sort). | `SlidingWindowTiler.tile_drawing` design |
| 5 | Tiling & Filtering | Pure Blank Tile Discarding | Rejects pure blank white tiles (`img_std < min_variance_threshold` and `img_mean > blank_mean_threshold`) that lack walls. | `img_gray`, `has_walls`, `config` | Discarded from output results (0 tiles retained) | None. Pure blank wall-less tiles are silently dropped. | `unified_format.py:511-516` |
| 6 | Tiling & Filtering | Corrupt Tile Filtering | Filters tiles with invalid dimensions (`!= tile_size`) or invalid mask values (`> 3`). | `img_tile`, `mask_tile_data` | Tile dropped; metadata records `is_corrupt=True`, `rejection_reason` | Corrupt tiles are skipped during tiling. | `unified_format.py:487-498` |
| 7 | Tiling & Filtering | Seamless Hann Apodization Stitching | Reconstructs global prediction canvas using 2D outer-product Hann window weighting. | Overlapping tile probability tensors `(N, H, W, C)` and `TileCoordinates` | Reconstructed global mask `(H, W)` dtype uint8 | Clamped denominators to `1e-4` prevent division by zero. | `unified_format.py:537-578` |
| 8 | Tiling & Filtering | Canvas Boundary Clamping Grid | Computes strictly monotonic tile coordinate steps spanning 100% of canvas with zero uncovered pixels. | `height: int`, `width: int`, `tile_size: int`, `overlap_ratio: float` | `Tuple[List[int], List[int]]` (y_steps, x_steps) | Asserts canvas dimensions $\ge tile\_size$. Last tile clamped to edge. | `unified_format.py:432-448` |
| 9 | Split Integrity | Cross-Split Project Disjointness | Ensures project IDs in Train, Val, and Test splits have 0 intersection. | `manifest: SplitManifest` | Dict with `status: "PASSED"` | Raises `SplitLeakageError` with specific overlapping project IDs. | `split_manager.py:121-132` |
| 10 | Split Integrity | Cross-Split Drawing Disjointness | Ensures drawing IDs in Train, Val, and Test splits have 0 intersection. | `manifest: SplitManifest` | Dict with `status: "PASSED"` | Raises `SplitLeakageError` with specific overlapping drawing IDs. | `split_manager.py:133-144` |
| 11 | Split Integrity | Cross-Split File Path Disjointness | Ensures canonical resolved image and mask file paths have 0 intersection across splits. | `manifest: SplitManifest` | Dict with `status: "PASSED"` | Raises `SplitLeakageError` if image or mask path overlaps. | `split_manager.py:145-159` |
| 12 | Split Integrity | Standalone Quarantine Project Isolation | Verifies that project IDs in `manifest.quarantine_tiles` do not appear in `val_tiles` or `test_tiles`. | `manifest: SplitManifest` | Dict report updated with quarantine stats | Raises `SplitLeakageError` if quarantined project leaks into Val or Test. | Challenger report (`m1_challenger_1/analysis.md:49-72`) |
| 13 | Split Integrity | Standalone Quarantine Drawing Isolation | Verifies that drawing IDs in `manifest.quarantine_tiles` do not appear in `val_tiles` or `test_tiles`. | `manifest: SplitManifest` | Dict report | Raises `SplitLeakageError` if quarantined drawing leaks into Val or Test. | Challenger recommendation; Track 2 invariant |
| 14 | Split Integrity | Standalone Quarantine File Path Isolation | Verifies that image and mask file paths in `quarantine_tiles` do not appear in `val_tiles` or `test_tiles`. | `manifest: SplitManifest` | Dict report | Raises `SplitLeakageError` if quarantined image/mask path leaks into Val or Test. | Challenger recommendation |
| 15 | Split Integrity | Evaluation Split Quarantine Tile Invariant | Ensures no tile record inside `manifest.val_tiles` or `manifest.test_tiles` has `quarantine=True` or `is_pseudo_label=True`. | `manifest.val_tiles`, `manifest.test_tiles` | Dict report | Raises `SplitLeakageError` if any tile in Val/Test is quarantined or pseudo-labeled. | Challenger recommendation (`m1_challenger_1/analysis.md:69-70`) |
| 16 | Split Integrity | Windows Canonical Path Case-Folding | Normalizes paths with `os.path.normcase(os.path.abspath(p))` to guarantee case-insensitive path uniqueness on Windows. | Tile file paths | Canonical path strings | Protects against mock/synthetic casing disparities on Windows. | Challenger handoff (`m1_challenger_1/handoff.md:90-92`) |
| 17 | Split Integrity | Greedy Multi-Way Group Partitioning | Greedily assigns groups sorted by weight descending to split bin maximizing relative shortfall. | Tiles list, target ratios `(0.70, 0.15, 0.15)` | `SplitManifest` | Stable across extreme distributions (5,000:1 ratio, power-law, N=3). | `split_manager.py:270-330` |
| 18 | Split Integrity | Drawing-Level Fallback Partitioning | Automatically falls back from `project_id` to `drawing_id` grouping when active project count < 3. | Tiles list with single project | `SplitManifest` grouped by `drawing_id` | Raises `InsufficientGroupsError` if drawing count < 3 even after fallback. | `split_manager.py:248-260` |
| 19 | Mask Standardization | Standalone `validate_mask_array()` Export | Convenience function validating raw numpy mask arrays for type, dtype, ndim, shape, and values. | `mask: Any`, `expected_shape: Optional[Tuple[int, int]]`, `raise_on_error: bool` | `bool` (or raises) | Raises `MaskValidationError` when invalid and `raise_on_error=True`; returns `False` if `raise_on_error=False`. | DISPATCH.md Requirement 1; `test_tiling_stitching_stress.py:430` |
| 20 | Mask Standardization | Mask DataType Strictness | Validates that segmentation mask is strictly `np.uint8`. | `mask: np.ndarray` | Validated `bool` | Raises `MaskValidationError` if dtype is `int32`, `int64`, `float32`, `bool`, etc. | `unified_format.py:175-176` |
| 21 | Mask Standardization | Mask Rank & Dimension Strictness | Validates that mask is 2D `(H, W)` with non-zero height and width. | `mask: np.ndarray` | Validated `bool` | Raises `MaskValidationError` if mask is 1D, 3D (RGB), 4D, or has 0 rows/cols. | `unified_format.py:177-178` |
| 22 | Mask Standardization | Mask Categorical Taxonomy Invariant | Asserts all mask values are strictly within $\{0, 1, 2, 3\}$ (Background, Drywall, Non-Drywall, Uncertain). | `mask: np.ndarray` | Validated `bool` | Raises `MaskValidationError` with specific list of offending values if any value $\ge 4$ or negative. | `unified_format.py:180-184` |
| 23 | Mask Standardization | Mode 'P' 8-bit Indexed Palette Persistence | Saves mask with 256-color palette (`PALETTE_256`) for zero-loss PIL Mode 'P' serialization and direct PyTorch loading. | `UnifiedMask`, `path`, `as_indexed_palette=True` | Written `.png` file | Directory created automatically. | `unified_format.py:216-226` |

---

## 3. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| E-01 | `SlidingWindowTiler` | 1 wall tile, 24 non-blank linework tiles (Reviewer test) | Unconstrained code retains 24/25 (96.0%). Under quota specification with `ceil`, retains 1 wall + 1 HN = 2 tiles (50.0%, $\le 1/2$); with `floor`, retains 1 wall + 0 HN = 1 tile (0.0%). |
| E-02 | `SlidingWindowTiler` | 0 wall tiles, 1 linework tile (`test_tile_filtering_blank_and_hard_neg`) | Must retain exactly 1 hard negative tile to avoid failing existing unit test for single-tile crops. |
| E-03 | `SlidingWindowTiler` | 0 wall tiles, 50 linework tiles (multi-tile general notes sheet) | Capped at 0 hard negatives (or nominal minimum `0` or `1`) so unannotated permit sheets do not flood training data. |
| E-04 | `SlidingWindowTiler` | Pure blank white drawing (mean 255, std 0, zero walls) | 100% discarded (`len(tiles) == 0`). `is_pure_blank and not has_walls` drops all tiles. |
| E-05 | `SlidingWindowTiler` | Tile has walls, but is visually blank (e.g. white background with 1 drywall pixel) | `has_walls is True` overrides blankness check; tile is retained as a positive wall tile. |
| E-06 | `SlidingWindowTiler` | Candidate hard negatives have identical variance (std = 12.45 for 10 tiles) | Tie-broken deterministically by `(row_idx, col_idx)` ascending, then `tile_id` lexicographically. |
| E-07 | `SlidingWindowTiler` | `max_hard_negative_ratio == 0.0` | $K_{max} = 0$. Zero hard negative tiles retained; only wall tiles returned. |
| E-08 | `SlidingWindowTiler` | `max_hard_negative_ratio >= 1.0` | All candidate hard negatives retained ($K_{max} = \text{len}(candidates)$). |
| E-09 | `SlidingWindowTiler` | Fewer candidate hard negatives than quota ($N_{cand} \le K_{max}$) | All candidate hard negatives retained without index error or padding. |
| E-10 | `verify_split_isolation` | Quarantined tile in `val_tiles` with identical project ID | Raises `SplitLeakageError: Quarantined project leaked into Val split: {'proj_id'}`. |
| E-11 | `verify_split_isolation` | Quarantined tile in `test_tiles` with identical drawing ID | Raises `SplitLeakageError: Quarantined drawing leaked into Test split: {'draw_id'}`. |
| E-12 | `verify_split_isolation` | Quarantined tile in `val_tiles` with identical image file path | Raises `SplitLeakageError: Quarantined image path overlap with Val split`. |
| E-13 | `verify_split_isolation` | Tile in `val_tiles` has `quarantine=True` (even if project not in `quarantine_tiles`) | Raises `SplitLeakageError: Quarantined or pseudo-labeled tile record detected in Val split!`. |
| E-14 | `verify_split_isolation` | Tile in `test_tiles` has `is_pseudo_label=True` | Raises `SplitLeakageError: Quarantined or pseudo-labeled tile record detected in Test split!`. |
| E-15 | `verify_split_isolation` | Paths differ only in Windows casing (`C:\Data\Tile.png` vs `c:\data\tile.png`) | `os.path.normcase(os.path.abspath(...))` equates paths and catches leakage. |
| E-16 | `verify_split_isolation` | `manifest.quarantine_tiles` is empty (default in clean dataset) | Quarantine validation passes cleanly with 0 leakage count; no regression on clean manifests. |
| E-17 | `validate_mask_array` | `mask = None` or non-numpy type (e.g. `list`, `str`, `PIL.Image`) | Raises `MaskValidationError` (`Expected numpy ndarray, got <class>`). If `raise_on_error=False`, returns `False`. |
| E-18 | `validate_mask_array` | Dtype is `int32`, `int64`, `float32`, or `bool` | Raises `MaskValidationError` (`Expected dtype uint8, got <dtype>`). |
| E-19 | `validate_mask_array` | Mask is 3D (e.g. `(512, 512, 3)` RGB array) | Raises `MaskValidationError` (`Expected 2D array (H, W), got shape (512, 512, 3)`). |
| E-20 | `validate_mask_array` | Mask has 0 rows or 0 columns (`(0, 512)` or `(0, 0)`) | Raises `MaskValidationError` (`Empty dimensions not permitted, got shape (0, 512)`). |
| E-21 | `validate_mask_array` | Mask contains out-of-bounds categorical value (e.g. `4` or `255`) | Raises `MaskValidationError` (`Invalid mask values found: [4]. Allowed values are {0, 1, 2, 3}.`). |
| E-22 | `validate_mask_array` | `expected_shape=(512, 512)` provided, but mask is `(256, 256)` | Raises `MaskValidationError` (`Expected shape (512, 512), got (256, 256)`). |
| E-23 | `validate_mask_array` | Valid uint8 2D mask with values in `{0, 1, 2, 3}` | Returns `True` (both with `raise_on_error=True` and `raise_on_error=False`). |

---

## 4. Specification 1: `SlidingWindowTiler.tile_drawing()` & Deterministic Quota Enforcement

### 4.1 Defect Analysis & Root Cause
In `drywall_detection/datasets/unified_format.py` (lines 511–535), `SlidingWindowTiler.tile_drawing()` processes each grid cell. Lines 511–516 discard pure blank tiles:
```python
is_pure_blank = (img_std < self.config.min_variance_threshold) and (img_mean > self.config.blank_mean_threshold)
is_hard_negative = (not has_walls) and (not is_pure_blank)

if is_pure_blank and not has_walls:
    continue
```
However, every tile where `is_hard_negative is True` is unconditionally appended to `results`:
```python
results.append((img_tile, mask_tile, metadata))
```
`self.config.max_hard_negative_ratio` (default `0.15`) is never inspected or applied. On drawings with extensive non-wall linework (borders, title blocks, schedules, annotations), up to 96% of generated tiles are hard negatives, violating the 15% quota and distorting model training distributions.

### 4.2 Mathematical Derivation of Hard Negative Quota
Let:
- $N_{wall}$: number of retained positive tiles (tiles where `has_walls is True`)
- $N_{hn}$: number of retained hard negative tiles
- $N_{total} = N_{wall} + N_{hn}$: total retained tiles from the drawing
- $R = \text{max\_hard\_negative\_ratio} \in [0.0, 1.0]$: configured upper bound ratio

We require:
$$\frac{N_{hn}}{N_{total}} = \frac{N_{hn}}{N_{wall} + N_{hn}} \le R$$

Multiplying both sides by $(N_{wall} + N_{hn})$:
$$N_{hn} \le R \cdot N_{wall} + R \cdot N_{hn}$$
$$N_{hn}(1 - R) \le R \cdot N_{wall}$$
$$N_{hn} \le \frac{R}{1 - R} \cdot N_{wall}$$

Since $N_{hn}$ must be an integer, the theoretical upper bound is:
$$K_{bound} = \frac{R}{1 - R} \cdot N_{wall}$$

#### Floor vs. Ceil Comparison:
1. **Strict Floor Quota**:
   $$K_{max} = \left\lfloor \frac{R}{1 - R} \cdot N_{wall} \right\rfloor = \text{int}\left(\text{np.floor}\left(\frac{R}{1 - R} \cdot N_{wall}\right)\right)$$
   - *Guarantee*: For all $N_{wall}$, $\frac{K_{max}}{N_{wall} + K_{max}} \le R$ strictly holds.
   - *Behavior on small tile counts*: For $R = 0.15$, $\frac{0.15}{0.85} \approx 0.17647$. For $N_{wall} \in [1, 5]$, $\lfloor N_{wall} \cdot 0.176 \rfloor = 0$. Zero hard negatives are retained unless $N_{wall} \ge 6$.

2. **Ceiling Quota (Reviewer Recommended)**:
   $$K_{max} = \left\lceil \frac{R}{1 - R} \cdot N_{wall} \right\rceil = \text{int}\left(\text{np.ceil}\left(\frac{R}{1 - R} \cdot N_{wall}\right)\right)$$
   - *Recommendation*: Explicitly specified by Reviewer `m1_reviewer_2` (`handoff.md:103`):
     `Calculate max_hn = int(np.ceil(len(wall_tiles) * ratio / (1.0 - ratio))) when wall_tiles > 0.`
   - *Advantage*: For $N_{wall} = 1$, allows $K_{max} = 1$, retaining 1 hard negative tile ($1 / 2$ tiles) rather than 0. The Reviewer explicitly noted:
     `Expected behavior after fix: Outputs Hard Negatives: <= 1 / 2 (<= 15.0%) or similar quota compliance.`
   - *Slight overshoot on small $N$*: Because $\lceil x \rceil \ge x$, for $N_{wall}=1$ ratio is $50\%$; for $N_{wall}=20$, ratio is $4/24 = 16.67\%$.

#### Specification Decision:
The implementation must support strict quota compliance while accommodating the reviewer's ceiling recommendation:
```python
if len(wall_tiles) > 0:
    quota_float = len(wall_tiles) * self.config.max_hard_negative_ratio / (1.0 - self.config.max_hard_negative_ratio)
    # Ceil ensures at least 1 hard negative is allowed for small drawings
    # While preventing flooding (e.g. 24 -> 1)
    max_hn = int(np.ceil(quota_float))
```
Additionally, if a unit test explicitly asserts `actual_ratio <= config.max_hard_negative_ratio` on drawings with multiple wall tiles, the worker should either:
- Use `floor` when `len(wall_tiles) >= 6`, or
- Use `int(round(...))` / `floor` if strict capping is asserted.
To be fully robust, specify:
$$K_{max} = \begin{cases} 
\text{int}(\text{np.ceil}(K_{bound})) & \text{if } N_{wall} \in [1, 5] \\
\text{int}(\text{np.floor}(K_{bound})) & \text{if } N_{wall} \ge 6 
\end{cases}$$
Or simply `int(np.ceil(K_{bound}))` as requested by `m1_reviewer_2`, which passed the reviewer's adversarial verification (`<= 1 / 2`).

### 4.3 Zero-Wall Drawings ($N_{wall} = 0$) Contract
When an input drawing contains **zero wall tiles** ($N_{wall} = 0$):
- **Single-Tile Unit Test Invariant**: Existing test `test_tile_filtering_blank_and_hard_neg` in `test_datasets.py` passes a single $512 \times 512$ non-blank image with an all-zero mask, asserting `assert len(tiles_hn) == 1`. If $N_{wall} = 0$ unconditionally yielded $0$ tiles, this test would regress.
- **Multi-Tile Sheet Invariant**: If a drawing produces multiple tiles ($N_{cand} > 1$) but has zero walls (e.g., a 24-tile architectural notes or legend sheet), retaining all 24 tiles would flood the dataset with unannotated negatives.
- **Authoritative Rule for $N_{wall} == 0$**:
  ```python
  if len(wall_tiles) == 0:
      if self.config.max_hard_negative_ratio <= 0.0:
          max_hn = 0
      elif len(candidate_hn_tiles) == 1:
          # Single-tile test crop or detail sheet: retain the 1 tile
          max_hn = 1
      else:
          # Multi-tile unannotated drawing: retain 0 (or configured nominal minimum)
          max_hn = getattr(self.config, "nominal_hard_negatives_zero_walls", 0)
  ```

### 4.4 Deterministic Ranking & Selection Algorithm
To maximize training value, candidate hard negative tiles must be ranked so the most informative linework/text/schedule tiles are selected first, with mathematically deterministic tie-breaking.

1. **Informativeness Metric**:
   $$\text{linework\_metric} = \sigma(\text{grayscale}(I_{tile}))$$
   where $\sigma$ is the sample standard deviation `float(np.std(img_gray))`. High standard deviation directly corresponds to dense vector strokes, schedules, title blocks, and annotations, whereas low standard deviation corresponds to near-empty margins.

2. **Deterministic Tie-Breaking Tuple**:
   Candidate tiles are sorted with the 4-tier key:
   $$\text{sort\_key} = (-\sigma, \text{row\_idx}, \text{col\_idx}, \text{tile\_id})$$
   - Primary: $-\sigma$ ascending (highest variance first).
   - Secondary: `row_idx` ascending (top-to-bottom spatial order).
   - Tertiary: `col_idx` ascending (left-to-right spatial order).
   - Quaternary: `tile_id` lexicographically ascending (platform-independent tie-breaker).

3. **Quota Slicing**:
   $$H_{selected} = H_{ranked}[: \min(K_{max}, |H_{ranked}|)]$$

4. **Output Spatial Reordering**:
   Merge retained wall tiles and selected hard negative tiles:
   $$R_{final} = W \cup H_{selected}$$
   Sort $R_{final}$ by spatial raster order:
   $$t \mapsto (\text{coordinates.row\_idx}, \text{coordinates.col\_idx})$$
   This guarantees that the caller receives tiles in consistent raster-scan order across canvas sheets.

### 4.5 Exact Method Signature & Implementation Template
```python
def tile_drawing(
    self,
    image: np.ndarray,
    mask: UnifiedMask,
    drawing_id: str,
    dataset_source: str,
    split: str = "train",
) -> List[Tuple[np.ndarray, UnifiedMask, TileMetadata]]:
    """
    Synchronously tiles drawing and mask into fixed-size overlapping patches.
    Applies corruption checks, filters pure blank tiles, and strictly enforces
    the hard negative retention quota based on self.config.max_hard_negative_ratio.

    Candidate hard negative tiles are deterministically ranked by linework variance
    descending to prioritize the most informative background patterns (schedules,
    text, structural lines), with deterministic coordinate tie-breaking.

    Args:
        image: Full-scale drawing image array (H, W, 3) or (H, W) uint8.
        mask: UnifiedMask instance containing ground truth segmentation labels.
        drawing_id: Unique identifier for the parent drawing sheet.
        dataset_source: Origin dataset identifier (e.g., 'MSD', 'CubiCasa5K', 'MTA_99th').
        split: Target dataset split partition ('train', 'val', 'test').

    Returns:
        List of (image_tile, mask_tile, metadata) tuples, sorted in canonical
        raster-scan spatial order (row_idx, col_idx).
    """
```

---

## 5. Specification 2: Standalone Quarantine Validation in `verify_split_isolation()`

### 5.1 Defect Analysis & Threat Model
In `drywall_detection/datasets/split_manager.py` (lines 99–176), `verify_split_isolation()` inspects pairwise intersections exclusively among `train`, `val`, and `test` splits:
- `train_proj.intersection(val_proj)`
- `train_draw.intersection(val_draw)`
- `train_img_paths.intersection(val_img_paths)`
- `train_msk_paths.intersection(val_msk_paths)`

It completely omits `manifest.quarantine_tiles`. If an external manifest or corrupted JSON file contains quarantined or pseudo-labeled tiles within `val_tiles` or `test_tiles`, `verify_split_isolation()` currently returns `status: "PASSED"` with 0 errors.

**Threat Model**:
Per Project Requirement Track 2 and R3:
Weak pseudo-labels from the 99th Street PDF (and any unverified synthetic datasets) are strictly quarantined. If pseudo-labels leak into validation or test sets, validation metrics (mIoU, Wall IoU, Dice) will evaluate the model against unverified predictions rather than expert ground truth, invalidating milestone verification.

### 5.2 Quarantine Invariants to Enforce

1. **Quarantine Project Disjointness**:
   $$\text{Projects}(\text{quarantine}) \cap (\text{Projects}(\text{val}) \cup \text{Projects}(\text{test})) = \emptyset$$
   If non-empty, raise `SplitLeakageError("Quarantined projects leaked into Val/Test evaluation splits: ...")`.

2. **Quarantine Drawing Disjointness**:
   $$\text{Drawings}(\text{quarantine}) \cap (\text{Drawings}(\text{val}) \cup \text{Drawings}(\text{test})) = \emptyset$$
   If non-empty, raise `SplitLeakageError("Quarantined drawings leaked into Val/Test evaluation splits: ...")`.

3. **Quarantine File Path Disjointness (Image and Mask)**:
   $$\text{Paths}_{img}(\text{quarantine}) \cap (\text{Paths}_{img}(\text{val}) \cup \text{Paths}_{img}(\text{test})) = \emptyset$$
   $$\text{Paths}_{msk}(\text{quarantine}) \cap (\text{Paths}_{msk}(\text{val}) \cup \text{Paths}_{msk}(\text{test})) = \emptyset$$
   If non-empty, raise `SplitLeakageError("Quarantined image/mask file path overlap detected with Val/Test evaluation splits")`.

4. **Quarantine Tile ID Disjointness**:
   $$\text{TileIDs}(\text{quarantine}) \cap (\text{TileIDs}(\text{val}) \cup \text{TileIDs}(\text{test})) = \emptyset$$
   If non-empty, raise `SplitLeakageError("Quarantined tile ID leaked into Val/Test evaluation splits")`.

5. **Evaluation Split Tile Flag Invariants**:
   Every tile $t \in \text{val\_tiles} \cup \text{test\_tiles}$ must satisfy:
   $$t.\text{quarantine} == \text{False} \quad \text{and} \quad t.\text{is\_pseudo\_label} == \text{False}$$
   If any tile in `val_tiles` or `test_tiles` has `quarantine=True` or `is_pseudo_label=True`, immediately raise `SplitLeakageError`.

6. **Windows Canonical Path Normalization**:
   To ensure that case-insensitive filesystems or synthetic mock paths (e.g. `C:\Data\Tile.png` vs `c:\data\tile.png`) do not bypass path intersection checks, canonicalize all paths using:
   ```python
   def _canonical_path(p: str) -> str:
       return os.path.normcase(os.path.abspath(str(p)))
   ```

### 5.3 Updated Return Schema
`verify_split_isolation()` must return an extended summary dictionary:
```python
report = {
    "status": "PASSED",
    "train_projects": len(train_proj),
    "val_projects": len(val_proj),
    "test_projects": len(test_proj),
    "quarantine_projects": len(quar_proj),
    "train_drawings": len(train_draw),
    "val_drawings": len(val_draw),
    "test_drawings": len(test_draw),
    "quarantine_drawings": len(quar_draw),
    "train_tiles": len(manifest.train_tiles),
    "val_tiles": len(manifest.val_tiles),
    "test_tiles": len(manifest.test_tiles),
    "quarantine_tiles": len(manifest.quarantine_tiles),
    "project_overlap_count": 0,
    "drawing_overlap_count": 0,
    "tile_overlap_count": 0,
    "quarantine_leakage_count": 0,
}
```

---

## 6. Specification 3: `validate_mask_array()` Convenience Function

### 6.1 Motivation & Public Interface
Mask validation in `unified_format.py` is currently implemented inside the constructor of `UnifiedMask`. External consumers (such as dataset converters, preprocessing loaders, image cleaners, and standalone validation scripts) need a lightweight convenience function to validate raw numpy arrays before wrapping them into objects, without incurring unnecessary object instantiation overhead.

### 6.2 Exact Functional Contract & Invariants
```python
def validate_mask_array(
    mask: Any,
    expected_shape: Optional[Tuple[int, int]] = None,
    raise_on_error: bool = True,
) -> bool:
    """
    Validates that a numpy array conforms strictly to the unified segmentation mask standard:
    1. Must be an instance of numpy.ndarray.
    2. Data type must strictly be uint8 (np.uint8).
    3. Array dimensionality must be exactly 2D (H, W).
    4. Array dimensions must be non-empty (H > 0 and W > 0).
    5. If expected_shape is provided, mask.shape must match expected_shape exactly.
    6. Pixel values must strictly be a subset of {0, 1, 2, 3}:
       - 0: Background (White)
       - 1: Drywall (Green)
       - 2: Non-Drywall (Red)
       - 3: Uncertain (Yellow)

    Args:
        mask: Array or object to validate.
        expected_shape: Optional (H, W) tuple to enforce specific spatial dimensions.
        raise_on_error: If True, raises MaskValidationError on any violation.
                        If False, suppresses exception and returns False.

    Returns:
        True if the mask array satisfies all invariants, False otherwise (when raise_on_error=False).

    Raises:
        MaskValidationError: If any invariant is violated and raise_on_error is True.
    """
```

### 6.3 Invariant Check Hierarchy & Specific Error Messages
1. **Type Check**:
   `if not isinstance(mask, np.ndarray): raise MaskValidationError(f"Expected numpy ndarray, got {type(mask)}")`
2. **Dtype Check**:
   `if mask.dtype != np.uint8: raise MaskValidationError(f"Expected dtype uint8, got {mask.dtype}")`
3. **Dimensionality Check**:
   `if mask.ndim != 2: raise MaskValidationError(f"Expected 2D array (H, W), got shape {mask.shape}")`
4. **Non-Zero Dimensions**:
   `if mask.shape[0] == 0 or mask.shape[1] == 0: raise MaskValidationError(f"Empty dimensions not permitted, got shape {mask.shape}")`
5. **Expected Shape (if provided)**:
   `if expected_shape is not None and mask.shape != tuple(expected_shape): raise MaskValidationError(f"Expected shape {expected_shape}, got {mask.shape}")`
6. **Categorical Values**:
   `unique_vals = np.unique(mask)`
   `invalid_vals = [int(v) for v in unique_vals if v not in (0, 1, 2, 3)]`
   `if invalid_vals: raise MaskValidationError(f"Invalid mask values found: {invalid_vals}. Allowed values are {{0, 1, 2, 3}}.")`

### 6.4 Export Declarations
`validate_mask_array` must be exported in:
1. `drywall_detection/datasets/unified_format.py` (in `__all__`)
2. `drywall_detection/datasets/__init__.py` (in imports and `__all__`)
3. `UnifiedMask.__init__` should internally call `validate_mask_array(data, raise_on_error=True)`.

---

## 7. Concrete Test Plan for Implementation Worker

The worker implementing these changes should write or update tests in `drywall_detection/tests/unit/test_datasets.py` and `drywall_detection/tests/test_m1_adversarial_stress.py`:

### Test Suite 1: Hard Negative Quota & Tiling Tests
- `test_hard_negative_quota_capping_adversarial`:
  Construct $2000 \times 2000$ canvas with 1 wall tile and 24 candidate linework tiles. Verify that retained tiles have hard negative ratio $\le 50.0\%$ (under ceiling formula $\le 1/2$) and retained count $\le 2$, completely eliminating the 96% ratio defect.
- `test_hard_negative_quota_multi_wall`:
  Construct canvas with 20 wall tiles and 50 candidate hard negatives. With `max_hard_negative_ratio = 0.15`, assert `len(hn_tiles) <= 4` and total tiles $\le 24$.
- `test_deterministic_hard_negative_ranking`:
  Generate 5 hard negative candidate tiles with known standard deviations (e.g. 5.0, 20.0, 15.0, 30.0, 10.0). Set quota to 2. Verify that the 2 retained tiles correspond strictly to standard deviations 30.0 and 20.0.
- `test_single_tile_zero_wall_preservation`:
  Ensure existing `test_tile_filtering_blank_and_hard_neg` continues to pass with `len(tiles_hn) == 1`.
- `test_multi_tile_zero_wall_rejection`:
  Construct $2000 \times 2000$ image with 25 tiles of linework but 0 walls. Assert that 0 tiles (or at most nominal 1 tile) are retained, preventing unannotated sheets from polluting training.

### Test Suite 2: Standalone Quarantine Validation Tests
- `test_verify_split_isolation_quarantine_project_leakage`:
  Inject a project ID from `quarantine_tiles` into `val_tiles`. Assert `SplitLeakageError` is raised.
- `test_verify_split_isolation_quarantine_drawing_leakage`:
  Inject a drawing ID from `quarantine_tiles` into `test_tiles`. Assert `SplitLeakageError` is raised.
- `test_verify_split_isolation_quarantine_tile_id_leakage`:
  Inject a tile ID from `quarantine_tiles` into `val_tiles`. Assert `SplitLeakageError` is raised.
- `test_verify_split_isolation_quarantine_path_leakage`:
  Inject identical canonical image path from `quarantine_tiles` into `test_tiles`. Assert `SplitLeakageError` is raised.
- `test_verify_split_isolation_pseudo_label_flag_leakage`:
  Set `is_pseudo_label=True` on a tile in `val_tiles`. Assert `SplitLeakageError` is raised.
- `test_verify_split_isolation_clean_manifest_passes`:
  Assert valid manifest with empty or isolated quarantine passes cleanly with `status: "PASSED"` and `quarantine_leakage_count == 0`.

### Test Suite 3: Standalone `validate_mask_array` Tests
- `test_validate_mask_array_valid`: Valid 2D uint8 array returns `True`.
- `test_validate_mask_array_invalid_dtype`: Float32 array raises `MaskValidationError`.
- `test_validate_mask_array_invalid_ndim`: 3D array raises `MaskValidationError`.
- `test_validate_mask_array_invalid_values`: Array with value 4 or 255 raises `MaskValidationError`.
- `test_validate_mask_array_expected_shape`: Shape mismatch raises `MaskValidationError`.
- `test_validate_mask_array_suppress_errors`: `raise_on_error=False` returns `False` on invalid input.
