# Test Design & Validation Analysis: Milestone M1 Iteration 2
**Author**: `m1_r2_explorer_3` (Test Design & Validation Explorer)  
**Date**: 2026-11-08  
**Context**: Fixing defect identified in Reviewer Report (`.agents/teamwork/m1_reviewer_2/handoff.md`)  
**Target Test Suite**: `drywall_detection/tests/unit/test_datasets.py`

---

## 1. Executive Summary & Root Cause Analysis

### 1.1 The Identified Defect
Reviewer `m1_reviewer_2` observed that while `UnifiedDatasetConfig.max_hard_negative_ratio = 0.15` was defined, `SlidingWindowTiler.tile_drawing()` lacked any retention quota enforcement. When subjected to an adversarial multi-tile drawing (2000x2000 canvas with 1 wall tile and 24 linework tiles), **100% of candidate hard negatives (24/24) were retained**, resulting in a **96.00% hard negative ratio** instead of the mandated $\le 15.00\%$.

### 1.2 Root Cause of the Test Gap in Iteration 1
In Iteration 1, `drywall_detection/tests/unit/test_datasets.py:test_tile_filtering_blank_and_hard_neg` tested tiles strictly in isolation using 512x512 single-tile canvases:
1. Pure blank white tile (512x512) $\to$ asserted 0 tiles retained.
2. Hard negative tile with linework and zero walls (512x512) $\to$ asserted 1 tile retained (`assert len(tiles_hn) == 1`).
3. Positive tile with wall mask (512x512) $\to$ asserted 1 tile retained.

Because each test case operated on an isolated single tile, the global drawing-level interaction between wall tiles and hard negative candidates was never evaluated. Furthermore:
- Multi-tile drawings ($H, W \gg 512$) with mixed tile populations were not tested.
- Zero-wall multi-tile drawings were not tested under quota capping.
- Configuration ratios other than default were never exercised.
- `verify_split_isolation()` never explicitly checked quarantine overlap against val/test splits.
- `validate_mask_array()` was not exposed as a top-level callable, only tested indirectly via `UnifiedMask`.

---

## 2. Specification of New Unit Test Suites

To eliminate these blind spots permanently, we specify 5 comprehensive unit test suites to be integrated directly into `drywall_detection/tests/unit/test_datasets.py`.

```
========================================================================================
Test Suite Inventory for M1 Iteration 2 in test_datasets.py
----------------------------------------------------------------------------------------
Suite 1: Multi-Tile Hard Negative Quota Verification
         - test_multi_tile_hard_negative_quota_capping (2000x2000, 1 wall, 24 HN -> capped)
         - test_hard_negative_selection_prioritizes_highest_variance (informative linework)
Suite 2: Zero-Wall Drawings Hard Negative Capping Behavior
         - test_zero_wall_drawing_hard_negative_capping (2000x2000 canvas, 0 walls)
Suite 3: Varying Quota Ratios & Monotonicity
         - test_varying_hard_negative_quota_ratios (ratios: 0.0, 0.05, 0.15, 0.30)
Suite 4: Standalone Quarantine Isolation Validation
         - test_quarantine_isolation_validation_clean (valid manifest passes)
         - test_quarantine_leak_into_val_raises_error (leak into val detected)
         - test_quarantine_leak_into_test_raises_error (leak into test detected)
         - test_pseudo_label_in_val_or_test_raises_error (flag check)
Suite 5: Standalone validate_mask_array() Function Validation
         - test_validate_mask_array_valid_all_classes (uint8, 2D, values 0..3)
         - test_validate_mask_array_invalid_values (values > 3 rejected)
         - test_validate_mask_array_invalid_dtypes (float, int32, bool rejected)
         - test_validate_mask_array_invalid_shapes (1D, 3D, 4D rejected)
         - test_validate_mask_array_invalid_types (list, tensor, None rejected)
         - test_validate_mask_array_exported_at_package_level
========================================================================================
```

---

## 3. Test Suite 1: Multi-Tile Hard Negative Quota Verification

### 3.1 Objective
Verify that on a multi-tile drawing (2000x2000 px, 512x512 tile size, stride 410 px $\implies 5 \times 5 = 25$ tiles) containing exactly 1 wall tile and 24 non-blank linework tiles, candidate hard negatives are capped according to `config.max_hard_negative_ratio = 0.15`.

### 3.2 Mathematical Formulation & Invariants
Let:
- $N_{wall}$ = count of wall tiles ($N_{wall} = 1$).
- $N_{hn}^{cand}$ = count of candidate hard negative tiles ($N_{hn}^{cand} = 24$).
- $r = \text{max\_hard\_negative\_ratio} = 0.15$.

Under standard quota capping:
$$N_{hn}^{max} = \left\lceil \frac{r}{1 - r} \cdot N_{wall} \right\rceil = \left\lceil \frac{0.15}{0.85} \cdot 1 \right\rceil = \lceil 0.1765 \rceil = 1$$
*(or with floor policy: $\lfloor 0.1765 \rfloor = 0$)*.

In both policies:
- Retained hard negatives $N_{hn}^{ret} \le 1$.
- Total retained tiles $N_{total} = N_{wall} + N_{hn}^{ret} \in \{1, 2\}$.
- Under no circumstances may $N_{hn}^{ret} = 24$ (which would produce a 96% ratio).
- For drawings with larger wall counts (e.g. $N_{wall} = 20, N_{hn}^{cand} = 30$):
  $$N_{hn}^{max} = \left\lceil \frac{0.15}{0.85} \cdot 20 \right\rceil = \lceil 3.529 \rceil = 4 \implies \frac{N_{hn}^{ret}}{N_{wall} + N_{hn}^{ret}} \le 17\%$$

### 3.3 Proposed Test Implementation

```python
def test_multi_tile_hard_negative_quota_capping(self) -> None:
    """
    Verifies that a multi-tile drawing (2000x2000) with 1 wall tile and 24 linework tiles
    strictly caps hard negative retention within max_hard_negative_ratio (15%).
    Directly addresses Reviewer m1_reviewer_2 defect report.
    """
    config = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20, max_hard_negative_ratio=0.15)
    tiler = SlidingWindowTiler(config)

    # 1. Canvas with 1 wall tile at top-left and dense linework throughout
    h, w = 2000, 2000
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    for y in range(100, 1900, 100):
        cv2.line(img, (0, y), (w, y), (0, 0, 0), 2)
    for x in range(100, 1900, 100):
        cv2.line(img, (x, 0), (x, h), (0, 0, 0), 2)

    # Exactly 1 wall region located inside the first tile (0:512, 0:512)
    mask_data = np.zeros((h, w), dtype=np.uint8)
    mask_data[50:100, 50:100] = DatasetClass.DRYWALL.value
    mask = UnifiedMask(mask_data)

    tiles = tiler.tile_drawing(img, mask, "draw_multi_tile_quota", "test_source")
    wall_tiles = [t for t in tiles if t[2].has_walls]
    hn_tiles = [t for t in tiles if t[2].is_hard_negative]

    # Invariants
    assert len(wall_tiles) >= 1, "Expected at least 1 wall tile"
    # Under 15% quota with 1 wall tile, ceil(1 * 0.15 / 0.85) = 1, floor = 0
    assert len(hn_tiles) <= 1, f"Expected at most 1 hard negative tile retained, got {len(hn_tiles)}"
    assert len(tiles) == len(wall_tiles) + len(hn_tiles)

    # Hard negative ratio must not exceed ceiling-allowed quota
    total_retained = len(tiles)
    retained_ratio = len(hn_tiles) / total_retained
    assert retained_ratio <= 0.50, f"Retained ratio {retained_ratio:.2%} exceeded single-wall ceiling bound"

    # Multi-tile drawing with 10 wall tiles and 15 linework tiles
    mask_data_10 = np.zeros((h, w), dtype=np.uint8)
    # Place walls across 10 distinct tile regions
    y_steps, x_steps = tiler.compute_tile_grid(h, w)
    step_coords = [(y, x) for y in y_steps for x in x_steps][:10]
    for y, x in step_coords:
        mask_data_10[y+50:y+100, x+50:x+100] = DatasetClass.DRYWALL.value

    tiles_10 = tiler.tile_drawing(img, UnifiedMask(mask_data_10), "draw_10_walls", "test_source")
    w_10 = [t for t in tiles_10 if t[2].has_walls]
    hn_10 = [t for t in tiles_10 if t[2].is_hard_negative]

    # ceil(10 * 0.15 / 0.85) = 2
    assert len(w_10) == 10
    assert len(hn_10) <= 2, f"Expected at most 2 hard negatives for 10 wall tiles, got {len(hn_10)}"
    actual_ratio_10 = len(hn_10) / len(tiles_10)
    assert actual_ratio_10 <= 0.17, f"Ratio {actual_ratio_10:.2%} exceeded quota threshold"
```

### 3.4 Informative Linework Variance Ranking Test
When candidate hard negatives exceed quota, the tiler must deterministically retain tiles with the highest variance (`img_std`), representing dense notes, schedules, or structural gridlines.

```python
def test_hard_negative_selection_prioritizes_highest_variance(self) -> None:
    """
    Verifies that when hard negatives exceed the quota, candidate hard negatives
    with the highest linework variance (highest information density) are retained.
    """
    config = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.0, max_hard_negative_ratio=0.15)
    tiler = SlidingWindowTiler(config)

    # Canvas of 2x2 grid (1024x1024) -> 4 non-overlapping tiles:
    # Tile (0,0): Wall tile
    # Tile (0,1): High-variance linework (dense grid)
    # Tile (1,0): Low-variance linework (single line)
    # Tile (1,1): Pure blank (discarded)
    img = np.full((1024, 1024, 3), 255, dtype=np.uint8)
    # Dense lines in Tile (0,1) [y: 0..512, x: 512..1024]
    for y in range(20, 500, 20):
        cv2.line(img, (520, y), (1000, y), (0, 0, 0), 2)
    # Single line in Tile (1,0) [y: 512..1024, x: 0..512]
    cv2.line(img, (20, 700), (500, 700), (0, 0, 0), 1)

    mask_data = np.zeros((1024, 1024), dtype=np.uint8)
    mask_data[100:200, 100:200] = DatasetClass.DRYWALL.value  # in Tile (0,0)

    tiles = tiler.tile_drawing(img, UnifiedMask(mask_data), "draw_var_rank", "test_source")
    wall_tiles = [t for t in tiles if t[2].has_walls]
    hn_tiles = [t for t in tiles if t[2].is_hard_negative]

    assert len(wall_tiles) == 1
    assert len(hn_tiles) == 1, "Expected exactly 1 hard negative retained under quota"

    # Retained hard negative must be Tile (row=0, col=1) which has dense linework
    retained_hn_coord = hn_tiles[0][2].coordinates
    assert retained_hn_coord.row_idx == 0 and retained_hn_coord.col_idx == 1, (
        f"Expected high-variance tile (0, 1) to be retained, got ({retained_hn_coord.row_idx}, {retained_hn_coord.col_idx})"
    )
```

---

## 4. Test Suite 2: Zero-Wall Drawings Hard Negative Capping Behavior

### 4.1 Objective
Verify behavior when an architectural sheet contains linework (notes, title blocks, schedules, or general conditions) but **0 wall tiles**.
Under the quota formula:
$$N_{hn}^{max} = \left\lceil \frac{r}{1 - r} \cdot 0 \right\rceil = 0$$
No wall signal exists to calibrate against, so zero-wall drawings must cap hard negatives at 0 by default, avoiding flooding the training split with unanchored background.

### 4.2 Proposed Test Implementation

```python
def test_zero_wall_drawing_hard_negative_capping(self) -> None:
    """
    Verifies that a drawing with zero wall tiles (e.g. general notes or title sheet)
    caps hard negative retention at 0, preventing unanchored negative flooding.
    """
    config = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20, max_hard_negative_ratio=0.15)
    tiler = SlidingWindowTiler(config)

    # 2000x2000 drawing full of linework (schedules, notes) but ZERO walls
    h, w = 2000, 2000
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    for i in range(100, 1900, 80):
        cv2.line(img, (0, i), (w, i), (0, 0, 0), 2)
        cv2.line(img, (i, 0), (i, h), (0, 0, 0), 2)

    zero_mask = UnifiedMask.zeros(h, w)
    assert zero_mask.has_walls() is False

    tiles = tiler.tile_drawing(img, zero_mask, "zero_wall_sheet", "test_source")

    # Invariants: 0 wall tiles -> 0 hard negatives retained
    wall_tiles = [t for t in tiles if t[2].has_walls]
    hn_tiles = [t for t in tiles if t[2].is_hard_negative]

    assert len(wall_tiles) == 0
    assert len(hn_tiles) == 0, f"Expected 0 hard negatives for zero-wall drawing, got {len(hn_tiles)}"
    assert len(tiles) == 0, f"Expected 0 tiles retained from zero-wall drawing, got {len(tiles)}"
```

---

## 5. Test Suite 3: Varying Quota Ratios & Monotonicity

### 5.1 Objective
Verify that `SlidingWindowTiler.tile_drawing()` dynamically adapts to different configured values of `max_hard_negative_ratio` (0.0, 0.05, 0.15, 0.30) and exhibits strict monotonicity.

### 5.2 Mathematical Bounds
Given $N_{wall} = 20$ and $N_{hn}^{cand} = 30$:
- $r = 0.00 \implies N_{hn}^{max} = 0 \implies \text{Retained HN} = 0$.
- $r = 0.05 \implies N_{hn}^{max} = \lceil 20 \cdot 0.05 / 0.95 \rceil = 2 \implies \text{Retained HN} \le 2$.
- $r = 0.15 \implies N_{hn}^{max} = \lceil 20 \cdot 0.15 / 0.85 \rceil = 4 \implies \text{Retained HN} \le 4$.
- $r = 0.30 \implies N_{hn}^{max} = \lceil 20 \cdot 0.30 / 0.70 \rceil = 9 \implies \text{Retained HN} \le 9$.

Monotonicity condition:
$$\text{Retained}(r=0.0) \le \text{Retained}(r=0.05) \le \text{Retained}(r=0.15) \le \text{Retained}(r=0.30)$$

### 5.3 Proposed Test Implementation

```python
@pytest.mark.parametrize("ratio, expected_max_hn", [
    (0.00, 0),
    (0.05, 2),
    (0.15, 4),
    (0.30, 9),
])
def test_varying_hard_negative_quota_ratios(self, ratio: float, expected_max_hn: int) -> None:
    """
    Verifies that SlidingWindowTiler correctly enforces hard negative quotas across
    varying max_hard_negative_ratio values (0.0, 0.05, 0.15, 0.30).
    """
    config = UnifiedDatasetConfig(
        tile_size=512,
        overlap_ratio=0.20,
        max_hard_negative_ratio=ratio
    )
    tiler = SlidingWindowTiler(config)

    # Create drawing with 20 wall tiles and 30 linework candidate tiles
    # Canvas sized to generate ~50 tiles: 512 stride 410, 7 steps x 8 steps = 56 tiles
    h, w = 3300, 3700
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    for y in range(100, h - 100, 120):
        cv2.line(img, (0, y), (w, y), (0, 0, 0), 2)

    y_steps, x_steps = tiler.compute_tile_grid(h, w)
    all_tile_coords = [(y, x) for y in y_steps for x in x_steps]
    total_grid_tiles = len(all_tile_coords)
    assert total_grid_tiles >= 40, f"Expected >= 40 grid tiles, got {total_grid_tiles}"

    # Set exactly 20 tiles with walls
    mask_data = np.zeros((h, w), dtype=np.uint8)
    for y, x in all_tile_coords[:20]:
        mask_data[y+100:y+200, x+100:x+200] = DatasetClass.DRYWALL.value

    tiles = tiler.tile_drawing(img, UnifiedMask(mask_data), f"draw_ratio_{ratio}", "test_source")
    wall_tiles = [t for t in tiles if t[2].has_walls]
    hn_tiles = [t for t in tiles if t[2].is_hard_negative]

    assert len(wall_tiles) == 20, f"Expected exactly 20 wall tiles, got {len(wall_tiles)}"
    assert len(hn_tiles) <= expected_max_hn, (
        f"Ratio {ratio}: Expected <= {expected_max_hn} hard negatives, got {len(hn_tiles)}"
    )

    if ratio == 0.0:
        assert len(hn_tiles) == 0, "Ratio 0.0 must retain 0 hard negatives"
```

```python
def test_hard_negative_quota_monotonicity(self) -> None:
    """
    Verifies that the number of retained hard negatives is strictly monotonic
    non-decreasing as max_hard_negative_ratio increases.
    """
    h, w = 3300, 3700
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    for y in range(100, h - 100, 100):
        cv2.line(img, (0, y), (w, y), (0, 0, 0), 2)

    # Use 512 tile size, stride 410
    config_probe = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20)
    tiler_probe = SlidingWindowTiler(config_probe)
    y_steps, x_steps = tiler_probe.compute_tile_grid(h, w)
    all_tile_coords = [(y, x) for y in y_steps for x in x_steps]

    mask_data = np.zeros((h, w), dtype=np.uint8)
    for y, x in all_tile_coords[:15]:
        mask_data[y+100:y+200, x+100:x+200] = DatasetClass.DRYWALL.value
    mask = UnifiedMask(mask_data)

    ratios = [0.0, 0.05, 0.15, 0.30]
    hn_counts = []

    for r in ratios:
        cfg = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20, max_hard_negative_ratio=r)
        t = SlidingWindowTiler(cfg)
        res = t.tile_drawing(img, mask, f"draw_mono_{r}", "test_source")
        hns = [tile for tile in res if tile[2].is_hard_negative]
        hn_counts.append(len(hns))

    # Verify monotonic non-decreasing: hn_counts[0] <= hn_counts[1] <= hn_counts[2] <= hn_counts[3]
    for i in range(len(hn_counts) - 1):
        assert hn_counts[i] <= hn_counts[i+1], (
            f"Monotonicity violation: ratio {ratios[i]} gave {hn_counts[i]} HN, "
            f"but ratio {ratios[i+1]} gave {hn_counts[i+1]} HN"
        )
```

---

## 6. Test Suite 4: Standalone Quarantine Isolation Validation

### 6.1 Objective
`verify_split_isolation()` must explicitly validate that `manifest.quarantine_tiles` (and tiles flagged `quarantine=True` or `is_pseudo_label=True`) **never overlap** with `val_tiles` or `test_tiles` by tile ID, project ID, drawing ID, image file path, or mask file path.

### 6.2 Proposed Test Implementation

```python
class TestQuarantineIsolationValidation:
    """Verifies verify_split_isolation() quarantine validation against val/test sets."""

    def test_quarantine_clean_manifest_passes_isolation(self, synthetic_tiles: List[TileRecord]) -> None:
        """Verifies a manifest with legitimate quarantine partition passes verification cleanly."""
        manager = DrawingSplitManager(
            split_ratios=(0.70, 0.15, 0.15),
            group_key="project_id",
            quarantine_projects=["proj_00"],
            seed=42
        )
        manifest = manager.create_splits(synthetic_tiles)
        assert len(manifest.quarantine_tiles) == 10

        report = verify_split_isolation(manifest)
        assert report["status"] == "PASSED"
        assert report["quarantine_tiles"] == 10
        assert report.get("quarantine_val_overlap_count", 0) == 0
        assert report.get("quarantine_test_overlap_count", 0) == 0

    def test_quarantine_tile_leak_into_val_raises_split_leakage_error(self, synthetic_tiles: List[TileRecord]) -> None:
        """Verifies that injecting a quarantined tile into val_tiles raises SplitLeakageError."""
        manager = DrawingSplitManager(
            split_ratios=(0.70, 0.15, 0.15),
            quarantine_projects=["proj_00"],
            seed=42
        )
        manifest = manager.create_splits(synthetic_tiles)
        assert len(manifest.quarantine_tiles) > 0

        # Inject leak: quarantine tile into validation split
        leaked_tile = manifest.quarantine_tiles[0]
        manifest.val_tiles.append(leaked_tile)

        with pytest.raises(SplitLeakageError, match="(?i)quarantine.*leak|leakage"):
            verify_split_isolation(manifest)

    def test_quarantine_tile_leak_into_test_raises_split_leakage_error(self, synthetic_tiles: List[TileRecord]) -> None:
        """Verifies that injecting a quarantined tile into test_tiles raises SplitLeakageError."""
        manager = DrawingSplitManager(
            split_ratios=(0.70, 0.15, 0.15),
            quarantine_projects=["proj_00"],
            seed=42
        )
        manifest = manager.create_splits(synthetic_tiles)
        leaked_tile = manifest.quarantine_tiles[0]
        manifest.test_tiles.append(leaked_tile)

        with pytest.raises(SplitLeakageError, match="(?i)quarantine.*leak|leakage"):
            verify_split_isolation(manifest)

    def test_pseudo_label_tile_in_val_or_test_raises_split_leakage_error(self, synthetic_tiles: List[TileRecord]) -> None:
        """
        Verifies that any tile flagged is_pseudo_label=True or quarantine=True
        present inside val_tiles or test_tiles raises SplitLeakageError immediately.
        """
        manager = DrawingSplitManager(seed=42)
        manifest = manager.create_splits(synthetic_tiles)

        # Flag an existing val tile as pseudo-label without placing in quarantine_tiles list
        manifest.val_tiles[0].is_pseudo_label = True

        with pytest.raises(SplitLeakageError, match="(?i)pseudo|quarantine"):
            verify_split_isolation(manifest)

    def test_quarantine_path_overlap_with_val_raises_split_leakage_error(self, synthetic_tiles: List[TileRecord]) -> None:
        """Verifies that duplicate file paths between quarantine and val splits trigger SplitLeakageError."""
        manager = DrawingSplitManager(quarantine_projects=["proj_00"], seed=42)
        manifest = manager.create_splits(synthetic_tiles)

        # Duplicate file path from quarantine into val tile
        q_tile = manifest.quarantine_tiles[0]
        manifest.val_tiles[0].image_path = q_tile.image_path

        with pytest.raises(SplitLeakageError, match="(?i)path.*overlap|leakage"):
            verify_split_isolation(manifest)
```

---

## 7. Test Suite 5: Standalone `validate_mask_array()` Function Validation

### 7.1 Objective
`drywall_detection/datasets/unified_format.py` must export a standalone `validate_mask_array(arr: np.ndarray) -> np.ndarray` convenience function that validates uint8 2D arrays with values in $\{0, 1, 2, 3\}$, raising `MaskValidationError` on violation and returning the validated array on success.

### 7.2 Proposed Test Implementation

```python
class TestValidateMaskArrayStandalone:
    """Verifies standalone validate_mask_array() convenience function contract and invariants."""

    def test_validate_mask_array_valid_all_classes(self) -> None:
        """Verifies that valid 2D uint8 array containing values {0, 1, 2, 3} passes validation."""
        from drywall_detection.datasets.unified_format import validate_mask_array
        arr = np.array([[0, 1], [2, 3]], dtype=np.uint8)
        result = validate_mask_array(arr)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.uint8
        assert result.shape == (2, 2)
        np.testing.assert_array_equal(result, arr)

    def test_validate_mask_array_valid_zeros(self) -> None:
        """Verifies that an all-background 2D uint8 array passes validation."""
        from drywall_detection.datasets.unified_format import validate_mask_array
        arr = np.zeros((512, 512), dtype=np.uint8)
        result = validate_mask_array(arr)
        assert result.shape == (512, 512)
        assert np.all(result == 0)

    @pytest.mark.parametrize("invalid_val", [4, 5, 255, 100])
    def test_validate_mask_array_invalid_values(self, invalid_val: int) -> None:
        """Verifies that values outside {0, 1, 2, 3} raise MaskValidationError."""
        from drywall_detection.datasets.unified_format import validate_mask_array, MaskValidationError
        arr = np.array([[0, 1], [2, invalid_val]], dtype=np.uint8)
        with pytest.raises(MaskValidationError, match="(?i)invalid mask value"):
            validate_mask_array(arr)

    @pytest.mark.parametrize("bad_dtype", [
        np.float32, np.float64, np.int32, np.int64, np.int16, bool
    ])
    def test_validate_mask_array_invalid_dtypes(self, bad_dtype) -> None:
        """Verifies that non-uint8 dtypes raise MaskValidationError."""
        from drywall_detection.datasets.unified_format import validate_mask_array, MaskValidationError
        arr = np.array([[0, 1], [2, 3]], dtype=bad_dtype)
        with pytest.raises(MaskValidationError, match="(?i)expected dtype uint8"):
            validate_mask_array(arr)

    @pytest.mark.parametrize("bad_shape", [
        (10,),           # 1D
        (10, 10, 1),     # 3D single channel
        (10, 10, 3),     # 3D RGB
        (1, 10, 10, 1),  # 4D
    ])
    def test_validate_mask_array_invalid_shapes(self, bad_shape: tuple) -> None:
        """Verifies that non-2D arrays raise MaskValidationError."""
        from drywall_detection.datasets.unified_format import validate_mask_array, MaskValidationError
        arr = np.zeros(bad_shape, dtype=np.uint8)
        with pytest.raises(MaskValidationError, match="(?i)expected 2d array"):
            validate_mask_array(arr)

    @pytest.mark.parametrize("bad_input", [
        [[0, 1], [2, 3]],        # Python list
        "not_an_array",          # String
        None,                    # NoneType
        12345,                   # Int
    ])
    def test_validate_mask_array_invalid_input_types(self, bad_input: Any) -> None:
        """Verifies that non-ndarray objects raise MaskValidationError."""
        from drywall_detection.datasets.unified_format import validate_mask_array, MaskValidationError
        with pytest.raises(MaskValidationError, match="(?i)expected numpy ndarray"):
            validate_mask_array(bad_input)

    def test_validate_mask_array_exported_at_package_level(self) -> None:
        """Verifies validate_mask_array is exposed in both unified_format and datasets package root."""
        import drywall_detection.datasets.unified_format as uf
        import drywall_detection.datasets as ds

        assert hasattr(uf, "validate_mask_array")
        assert callable(getattr(uf, "validate_mask_array"))
        assert hasattr(ds, "validate_mask_array")
        assert callable(getattr(ds, "validate_mask_array"))
```

---

## 8. Alignment of Existing Test Cases in `test_datasets.py`

### 8.1 Existing Single-Tile Test in `TestUnifiedFormat.test_tile_filtering_blank_and_hard_neg`
In the existing test (lines 180–189):
```python
# 2. Hard negative drawing (contains linework/text, std > 2.0, but zero walls)
hn_img = np.full((512, 512, 3), 255, dtype=np.uint8)
cv2.line(hn_img, (50, 50), (450, 50), (0, 0, 0), 2)  # text or dimension line
hn_mask = UnifiedMask.zeros(512, 512)
tiles_hn = tiler.tile_drawing(hn_img, hn_mask, "draw_hn", "test_source")
assert len(tiles_hn) == 1
```
### 8.2 Rationale for Update
When zero-wall drawings cap hard negatives at 0 under standard quota rules, an entire zero-wall drawing `draw_hn` will produce 0 tiles if quota is enforced per-drawing.
To test a hard negative tile being retained alongside wall tiles in that existing test function, the canvas should include a wall tile, or the test should be updated as follows:

```python
# Updated Case 2: Multi-tile drawing with 1 wall tile and 1 linework tile
mixed_img = np.full((512, 1024, 3), 255, dtype=np.uint8)
cv2.line(mixed_img, (550, 50), (950, 50), (0, 0, 0), 2) # linework in tile 2
mixed_mask_data = np.zeros((512, 1024), dtype=np.uint8)
mixed_mask_data[100:200, 100:200] = DatasetClass.DRYWALL.value # wall in tile 1

tiles_mixed = tiler.tile_drawing(mixed_img, UnifiedMask(mixed_mask_data), "draw_mixed", "test_source")
w_tiles = [t for t in tiles_mixed if t[2].has_walls]
hn_tiles = [t for t in tiles_mixed if t[2].is_hard_negative]
assert len(w_tiles) == 1
assert len(hn_tiles) == 1
assert hn_tiles[0][2].is_hard_negative is True
```
This ensures backwards compatibility while preserving the intent of testing hard negative classification.

---

## 9. Verification Invariants & Checklist for Implementation Workers

| # | Invariant | Verification Assertion |
|---|---|---|
| 1 | Hard Negative Ratio Cap | $\frac{N_{HN}}{N_{total}} \le \max\left(r, \frac{\lceil N_{W} \cdot r / (1 - r) \rceil}{N_{W} + \lceil N_{W} \cdot r / (1 - r) \rceil}\right)$ |
| 2 | Zero-Wall Quota Bound | $N_{W} == 0 \implies N_{HN} == 0$ |
| 3 | Hard Negative Monotonicity | $r_1 < r_2 \implies N_{HN}(r_1) \le N_{HN}(r_2)$ |
| 4 | Variance-Based Negatives | Retained HN tile has $\max(\text{std})$ among candidate negatives |
| 5 | Quarantine Strict Isolation | $\text{quarantine\_tiles} \cap (\text{val\_tiles} \cup \text{test\_tiles}) = \emptyset$ |
| 6 | Pseudo-Label Prohibition | $\forall t \in (\text{val\_tiles} \cup \text{test\_tiles}): \neg t.\text{is\_pseudo\_label} \land \neg t.\text{quarantine}$ |
| 7 | Mask Validation Strictness | $\text{validate\_mask\_array}(A)$ raises `MaskValidationError` for any $A \notin \{0,1,2,3\}^{H \times W \times \text{uint8}}$ |
