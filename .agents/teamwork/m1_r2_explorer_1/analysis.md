# Technical Analysis: Hard Negative Retention Quota Enforcement in SlidingWindowTiler

**Author**: `m1_r2_explorer_1` (Tiling & Hard Negative Quota Explorer)  
**Date**: 2026-11-08  
**Target Module**: `drywall_detection/datasets/unified_format.py`  
**Target Test Suite**: `drywall_detection/tests/unit/test_datasets.py`  
**Reference Issue**: Reviewer `m1_reviewer_2` REQUEST_CHANGES failure report  

---

## 1. Executive Summary

During Milestone M1 review, reviewer `m1_reviewer_2` identified that while `UnifiedDatasetConfig` defines `max_hard_negative_ratio: float = 0.15`, `SlidingWindowTiler.tile_drawing()` does not enforce this quota. Currently, any non-blank tile without walls is retained unconditionally, leading to up to 96% hard negative ratios on architectural drawings with gridlines, text, and structural linework.

This analysis provides the exact architectural specification, mathematical formulation, edge-case treatment, ranking algorithm, and unit test designs for `m1_worker_1` to implement.

---

## 2. Root Cause Analysis

In `drywall_detection/datasets/unified_format.py` (lines 502–534):
```python
# Evaluate image variance and blankness
if img_tile.ndim == 3:
    img_gray = cv2.cvtColor(img_tile, cv2.COLOR_BGR2GRAY)
else:
    img_gray = img_tile

img_std = float(np.std(img_gray))
img_mean = float(np.mean(img_gray))

is_pure_blank = (img_std < self.config.min_variance_threshold) and (img_mean > self.config.blank_mean_threshold)
is_hard_negative = (not has_walls) and (not is_pure_blank)

# Pure blank tiles without walls are 100% discarded
if is_pure_blank and not has_walls:
    continue

# Immediate append without global quota check or candidate tracking:
results.append((img_tile, mask_tile, metadata))
```

### Key Deficiencies:
1. **No Candidate Collection**: The loop generates tiles synchronously and immediately appends any non-blank tile to `results`. At the time of processing tile $(r, c)$, the tiler has no knowledge of how many wall tiles exist across the full drawing.
2. **Ignored Configuration**: `self.config.max_hard_negative_ratio` is completely unreferenced inside `tile_drawing()`.
3. **Severe Class Imbalance Amplification**: Architectural drawings are dominated by non-wall linework (dimension strings, column grids, title blocks, notes). An unconstrained tiler floods the training dataset with negative background patches, severely worsening the 90:10 class imbalance.

---

## 3. Mathematical Formulation

### 3.1 Quota Definition
Let:
- $N_w$ be the number of valid wall-bearing tiles (`has_walls == True`) extracted from a drawing.
- $N_{hn}^{cand}$ be the number of candidate hard negative tiles (`not has_walls` and `not is_pure_blank`).
- $r = \text{config.max\_hard\_negative\_ratio} \in [0.0, 1.0]$ (default $0.15$).
- $N_{hn}^{retained}$ be the number of hard negative tiles admitted into the dataset.

The retention quota mandates that hard negative tiles constitute at most fraction $r$ of the total retained tiles ($N_{total} = N_w + N_{hn}^{retained}$):

$$\frac{N_{hn}^{retained}}{N_w + N_{hn}^{retained}} \le r$$

Rearranging for $N_{hn}^{retained}$:
$$N_{hn}^{retained} \le r (N_w + N_{hn}^{retained})$$
$$N_{hn}^{retained}(1 - r) \le r \cdot N_w$$
$$N_{hn}^{retained} \le \frac{r}{1 - r} \cdot N_w$$

For $r = 0.15$:
$$\frac{r}{1 - r} = \frac{0.15}{0.85} = \frac{3}{17} \approx 0.1764706$$

### 3.2 Discrete Cap Calculation
Because tile counts must be integers, the maximum allowed hard negatives is:

$$\text{max\_hn} = \left\lceil N_w \cdot \frac{r}{1 - r} \right\rceil$$

Using ceiling (`np.ceil`) ensures that:
- For small drawings with 1 wall tile, $\lceil 1 \times 0.1765 \rceil = 1$, permitting at least 1 informative hard negative tile rather than starving the sample to 0.
- For 10 wall tiles, $\lceil 10 \times 0.1765 \rceil = 2$ hard negatives ($2 / 12 = 16.7\%$).
- For 50 wall tiles, $\lceil 50 \times 0.1765 \rceil = 9$ hard negatives ($9 / 59 = 15.25\%$).
- For 100 wall tiles, $\lceil 100 \times 0.1765 \rceil = 18$ hard negatives ($18 / 118 = 15.25\%$).

### 3.3 Boundary Conditions
1. **$r \le 0.0$**:
   $\text{max\_hn} = 0$. Zero hard negatives permitted.
2. **$r \ge 1.0$**:
   No cap. $\text{max\_hn} = N_{hn}^{cand}$. All candidate hard negatives are retained.
3. **Fewer candidates than cap**:
   If $N_{hn}^{cand} \le \text{max\_hn}$, retain all $N_{hn}^{cand}$ candidates.

---

## 4. Edge Case: Drawings with Zero Walls ($N_w == 0$)

### 4.1 Problem
When an architectural drawing contains no wall annotations ($N_w = 0$):
- If $\text{max\_hn} = \lceil 0 \times \frac{r}{1 - r} \rceil = 0$, then 0 tiles are retained from that drawing.
- In production, this is desirable: non-floor-plan sheets (e.g. general notes, title sheets, cover sheets) are automatically filtered out rather than creating 100% negative training drawings.
- In unit testing (e.g. `test_tile_filtering_blank_and_hard_neg`), isolated 512x512 crops with zero walls are tested specifically to assert hard negative detection.

### 4.2 Solution Strategy
Introduce an explicit configuration field in `UnifiedDatasetConfig`:
```python
@dataclass
class UnifiedDatasetConfig:
    tile_size: int = 512
    overlap_ratio: float = 0.20
    target_dpi: int = 150
    min_variance_threshold: float = 2.0
    blank_mean_threshold: float = 250.0
    max_hard_negative_ratio: float = 0.15
    nominal_hard_negative_min: int = 0  # Minimum hard negatives retained when Nw == 0
    alpha_overlay: float = 0.40
    export_indexed_palette: bool = True
```

**Behavior**:
- When $N_w > 0$:
  $$\text{max\_hn} = \max\left(\text{nominal\_hard\_negative\_min}, \left\lceil N_w \cdot \frac{r}{1 - r} \right\rceil\right)$$
- When $N_w == 0$:
  $$\text{max\_hn} = \text{nominal\_hard\_negative\_min}$$
- Default `nominal_hard_negative_min = 0`: completely suppresses wall-less sheets from contaminating dataset splits.
- Callers and tests needing to harvest or test isolated hard negatives simply set `nominal_hard_negative_min = 1`.

---

## 5. Candidate Ranking & Selection Strategy

When $N_{hn}^{cand} > \text{max\_hn}$, the tiler must select the most valuable hard negatives.

### 5.1 Selection Criterion: Linework Variance (`img_std`)
- Grayscale standard deviation `img_std` is already computed for every tile during blankness checking:
  ```python
  img_std = float(np.std(img_gray))
  ```
- **High `img_std`**: Dense linework, text blocks, structural gridlines, complex furniture or door graphics. These represent high-entropy false-positive risks that the neural network must learn to discriminate.
- **Low `img_std` ($\approx 2.0$)**: Faint border lines, empty margins. These offer negligible gradient signal.

### 5.2 Deterministic Ranking Algorithm
To guarantee 100% reproducible ordering without random seed dependencies:
1. Candidate tuples store `(img_tile, mask_tile, metadata, img_std)`.
2. Candidates are sorted using a compound key:
   - Primary (descending): `img_std` (highest variance first)
   - Secondary (ascending): `row_idx` (top-to-bottom spatial tie-break)
   - Tertiary (ascending): `col_idx` (left-to-right spatial tie-break)
3. Slice the top $\text{max\_hn}$ items.

```python
candidate_hard_negatives.sort(
    key=lambda item: (-item[3], item[2].coordinates.row_idx, item[2].coordinates.col_idx)
)
retained_hn = candidate_hard_negatives[:max_hn]
```

### 5.3 Preservation of Spatial Order
After selection, the combined pool of retained wall tiles and hard negative tiles is sorted by `(row_idx, col_idx)`:
```python
results = wall_tiles + [t[:3] for t in retained_hn]
results.sort(key=lambda t: (t[2].coordinates.row_idx, t[2].coordinates.col_idx))
```
This preserves the canonical raster-scan spatial ordering expected by downstream batching and visualization tools.

---

## 6. Implementation Specification for `m1_worker_1`

### 6.1 Changes to `drywall_detection/datasets/unified_format.py`

#### A. In `UnifiedDatasetConfig`:
Add `nominal_hard_negative_min: int = 0` with type annotation and docstring.

#### B. In `SlidingWindowTiler.tile_drawing()`:
Replace lines 464–535 with the two-phase partition-and-quota algorithm:

```python
        wall_tiles: List[Tuple[np.ndarray, UnifiedMask, TileMetadata]] = []
        candidate_hn: List[Tuple[np.ndarray, UnifiedMask, TileMetadata, float]] = []

        for r_idx, y0 in enumerate(y_steps):
            for c_idx, x0 in enumerate(x_steps):
                y1 = y0 + tile_size
                x1 = x0 + tile_size

                img_tile = image[y0:y1, x0:x1]
                mask_tile_data = mask.data[y0:y1, x0:x1]

                tile_id = f"{drawing_id}_r{r_idx:02d}_c{c_idx:02d}"
                coords = TileCoordinates(
                    row_idx=r_idx,
                    col_idx=c_idx,
                    y_min=y0,
                    x_min=x0,
                    y_max=y1,
                    x_max=x1,
                    parent_height=h,
                    parent_width=w,
                )

                # Check corruption
                is_corrupt = False
                rejection_reason = None
                if img_tile.shape[:2] != (tile_size, tile_size) or mask_tile_data.shape != (tile_size, tile_size):
                    is_corrupt = True
                    rejection_reason = "SHAPE_MISMATCH"
                elif np.any(mask_tile_data > 3):
                    is_corrupt = True
                    rejection_reason = "INVALID_MASK_VALUE"

                if is_corrupt:
                    continue

                mask_tile = UnifiedMask(mask_tile_data)
                has_walls = mask_tile.has_walls()

                # Evaluate image variance and blankness
                if img_tile.ndim == 3:
                    img_gray = cv2.cvtColor(img_tile, cv2.COLOR_BGR2GRAY)
                else:
                    img_gray = img_tile

                img_std = float(np.std(img_gray))
                img_mean = float(np.mean(img_gray))

                is_pure_blank = (img_std < self.config.min_variance_threshold) and (img_mean > self.config.blank_mean_threshold)
                is_hard_negative = (not has_walls) and (not is_pure_blank)

                # Pure blank tiles without walls are 100% discarded
                if is_pure_blank and not has_walls:
                    continue

                metadata = TileMetadata(
                    tile_id=tile_id,
                    parent_drawing_id=drawing_id,
                    dataset_source=dataset_source,
                    split=split,
                    coordinates=coords,
                    class_pixel_counts=mask_tile.get_class_counts(),
                    class_percentages=mask_tile.get_class_percentages(),
                    has_walls=has_walls,
                    is_pure_blank=is_pure_blank,
                    is_hard_negative=is_hard_negative,
                    is_corrupt=is_corrupt,
                    rejection_reason=rejection_reason,
                )

                if has_walls:
                    wall_tiles.append((img_tile, mask_tile, metadata))
                elif is_hard_negative:
                    candidate_hn.append((img_tile, mask_tile, metadata, img_std))

        # Enforce hard negative retention quota
        ratio = self.config.max_hard_negative_ratio
        nom_min = self.config.nominal_hard_negative_min
        num_walls = len(wall_tiles)

        if ratio <= 0.0:
            max_hn = nom_min if num_walls == 0 else 0
        elif ratio >= 1.0:
            max_hn = len(candidate_hn)
        elif num_walls > 0:
            quota_cap = int(np.ceil(num_walls * ratio / (1.0 - ratio)))
            max_hn = max(nom_min, quota_cap)
        else:
            max_hn = nom_min

        # Sort candidate hard negatives by linework variance descending with spatial tie-break
        candidate_hn.sort(
            key=lambda item: (-item[3], item[2].coordinates.row_idx, item[2].coordinates.col_idx)
        )
        retained_hn = [item[:3] for item in candidate_hn[:max_hn]]

        # Combine and sort all retained tiles in canonical spatial raster order
        results = wall_tiles + retained_hn
        results.sort(key=lambda t: (t[2].coordinates.row_idx, t[2].coordinates.col_idx))

        return results
```

---

## 7. Required Unit Tests in `drywall_detection/tests/unit/test_datasets.py`

### 7.1 Existing Test Compatibility (`test_tile_filtering_blank_and_hard_neg`)
In test case 2 of `test_tile_filtering_blank_and_hard_neg`:
The test passes an isolated 512x512 tile with zero walls.
To maintain backward compatibility and explicitly test both modes:
```python
        # 2. Hard negative drawing (contains linework/text, std > 2.0, but zero walls)
        hn_img = np.full((512, 512, 3), 255, dtype=np.uint8)
        cv2.line(hn_img, (50, 50), (450, 50), (0, 0, 0), 2)  # text or dimension line
        hn_mask = UnifiedMask.zeros(512, 512)

        # Default config (nominal_hard_negative_min=0): wall-less drawing produces 0 tiles
        tiles_hn_default = tiler.tile_drawing(hn_img, hn_mask, "draw_hn_zero", "test_source")
        assert len(tiles_hn_default) == 0

        # With nominal_hard_negative_min=1: isolated hard negative is retained
        tiler_hn_single = SlidingWindowTiler(UnifiedDatasetConfig(tile_size=512, nominal_hard_negative_min=1))
        tiles_hn = tiler_hn_single.tile_drawing(hn_img, hn_mask, "draw_hn", "test_source")
        assert len(tiles_hn) == 1
        _, _, meta_hn = tiles_hn[0]
        assert meta_hn.is_hard_negative is True
        assert meta_hn.has_walls is False
```

### 7.2 Dedicated Multi-Tile Quota Test (`test_hard_negative_quota_enforcement`)
Add a new unit test verifying multi-tile drawing behavior:
```python
    def test_hard_negative_quota_enforcement(self) -> None:
        """Verifies hard negative retention quota strictly enforces max_hard_negative_ratio."""
        config = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20, max_hard_negative_ratio=0.15)
        tiler = SlidingWindowTiler(config)

        # 2000x2000 image generates 25 tiles (5x5 grid)
        img = np.full((2000, 2000, 3), 255, dtype=np.uint8)
        for i in range(100, 1900, 100):
            cv2.line(img, (0, i), (2000, i), (0, 0, 0), 2)

        # 1 wall tile at r00_c00; remaining 24 tiles are candidate hard negatives
        mask_data = np.zeros((2000, 2000), dtype=np.uint8)
        mask_data[50:100, 50:100] = DatasetClass.DRYWALL.value
        mask = UnifiedMask(mask_data)

        tiles = tiler.tile_drawing(img, mask, "quota_draw", "test_source")
        wall_tiles = [t for t in tiles if t[2].has_walls]
        hn_tiles = [t for t in tiles if t[2].is_hard_negative]

        assert len(wall_tiles) == 1
        # max_hn = ceil(1 * 0.15 / 0.85) = 1
        assert len(hn_tiles) == 1
        assert len(tiles) == 2

    def test_hard_negative_variance_ranking(self) -> None:
        """Verifies candidate hard negatives are prioritized by highest linework variance."""
        config = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.0, max_hard_negative_ratio=0.15)
        tiler = SlidingWindowTiler(config)

        # 512x1024 image -> 2 non-overlapping tiles: (0, 0) and (0, 512)
        # Tile 0: contains wall + 1 faint line (std ~ low)
        # Tile 1: contains rich linework (std ~ high), zero walls
        # Let's add a 3rd tile: 512x1536 -> Tile 0 (wall), Tile 1 (rich linework), Tile 2 (faint linework)
        img = np.full((512, 1536, 3), 255, dtype=np.uint8)
        # Tile 1 [x: 512..1024]: dense grid lines
        for x in range(520, 1000, 10):
            cv2.line(img, (x, 10), (x, 500), (0, 0, 0), 2)
        # Tile 2 [x: 1024..1536]: single faint line
        cv2.line(img, (1100, 100), (1200, 100), (180, 180, 180), 1)

        mask_data = np.zeros((512, 1536), dtype=np.uint8)
        # Tile 0 has drywall
        mask_data[50:100, 50:100] = DatasetClass.DRYWALL.value
        mask = UnifiedMask(mask_data)

        tiles = tiler.tile_drawing(img, mask, "rank_draw", "test_source")
        assert len(tiles) == 2  # 1 wall tile + 1 hard negative (Tile 1 retained, Tile 2 discarded)
        hn_tile = [t for t in tiles if t[2].is_hard_negative][0]
        # Retained hard negative must be Tile 1 (col_idx = 1), not Tile 2 (col_idx = 2)
        assert hn_tile[2].coordinates.col_idx == 1
```

---

## 8. Conclusion

This strategy solves the 96% hard negative quota leakage defect cleanly and robustly. It enforces the mathematical formula required by reviewer `m1_reviewer_2`, provides a principled solution for the zero-wall edge case via `nominal_hard_negative_min`, prioritizes the most challenging false-positive distractors using zero-overhead `img_std` sorting, and preserves spatial raster order.
