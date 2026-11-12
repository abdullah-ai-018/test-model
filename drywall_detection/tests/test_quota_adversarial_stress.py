"""
drywall_detection/tests/test_quota_adversarial_stress.py
=========================================================
Empirical Adversarial Stress Suite for SlidingWindowTiler Quota Enforcement:
- Adversarially reproduces the 2000x2000 canvas failure with 1 wall tile and 24 linework tiles.
  Verifies that retained hard negatives <= 1 and ratio <= 50%, proving the 96% ratio defect
  is permanently eliminated.
- Multi-wall drawings with dense linework across varying quotas (0.0 to 1.0) and monotonicity.
- Zero-wall drawings with pure linework (verifying 0 tiles retained multi-tile, 1 tile for single crop).
- Extreme aspect ratios (512x4000 ribbon, 4000x512 column, 1000x4000 banner, 1234x2345 irregular).
- Deterministic linework variance ranking (std descending) and canonical raster tie-breaking.
- Multiclass mask wall detection (Drywall, Non-Drywall, Uncertain) and single-pixel micro-walls.
"""

from __future__ import annotations
import math
from typing import List, Tuple
import pytest
import numpy as np
import cv2

from drywall_detection.datasets.unified_format import (
    DatasetClass,
    UnifiedDatasetConfig,
    TileCoordinates,
    TileMetadata,
    UnifiedMask,
    SlidingWindowTiler,
)


class TestAdversarialDefectReproduction:
    """
    Adversarially stress-tests the reproduction of the 96% hard-negative ratio defect
    discovered in Iteration 1 review.
    """

    def test_2000x2000_single_wall_24_linework_elimination_of_96_percent_defect(self) -> None:
        """
        Adversarial Scenario:
        A 2000x2000 canvas with dense linework grids every 80 px across the entire canvas.
        Only a single tile at top-left contains a wall region.
        The remaining 24 tiles are non-blank hard negatives (lines, grids, architectural elements).

        Under Iteration 1 code, all 24 hard negatives were retained, yielding 24/25 = 96% hard negatives.
        Under the new quota formula with max_hard_negative_ratio=0.15:
            num_walls = 1
            max_hn = ceil(1 * 0.15 / 0.85) = ceil(0.176) = 1
            total_retained = 2 (1 wall + 1 HN)
            hn_ratio = 1 / 2 = 50.0% (<= 50.0%)

        Asserts:
        - len(wall_tiles) == 1
        - len(candidate_hn) == 24
        - len(retained_hn) <= 1
        - total_retained <= 2
        - hn_ratio <= 0.50
        - Defect permanently eliminated: retained_hn != 24 and hn_ratio < 0.96
        """
        h, w = 2000, 2000
        config = UnifiedDatasetConfig(
            tile_size=512,
            overlap_ratio=0.20,
            max_hard_negative_ratio=0.15,
            nominal_hard_negative_min=0,
            nominal_hard_negatives_zero_walls=0,
        )
        tiler = SlidingWindowTiler(config)

        # 1. Generate adversarial image with dense black linework across all 25 tiles
        img = np.full((h, w, 3), 255, dtype=np.uint8)
        for y in range(40, h, 80):
            cv2.line(img, (0, y), (w, y), (0, 0, 0), 2)
        for x in range(40, w, 80):
            cv2.line(img, (x, 0), (x, h), (0, 0, 0), 2)

        # 2. Exactly 1 wall region in the top-left tile (0:512, 0:512)
        mask_data = np.zeros((h, w), dtype=np.uint8)
        mask_data[50:100, 50:100] = DatasetClass.DRYWALL.value
        mask = UnifiedMask(mask_data)

        y_steps, x_steps = tiler.compute_tile_grid(h, w)
        assert len(y_steps) == 5 and len(x_steps) == 5
        total_grid_tiles = len(y_steps) * len(x_steps)
        assert total_grid_tiles == 25

        tiles = tiler.tile_drawing(img, mask, "adv_reproduce_96pct", "test_m1")

        wall_tiles = [t for t in tiles if t[2].has_walls]
        hn_tiles = [t for t in tiles if t[2].is_hard_negative]

        # Empirical verifications
        assert len(wall_tiles) == 1, f"Expected exactly 1 wall tile, got {len(wall_tiles)}"
        assert len(hn_tiles) <= 1, f"Quota violation! Expected <= 1 hard negative, got {len(hn_tiles)}"
        assert len(tiles) <= 2, f"Expected at most 2 tiles retained, got {len(tiles)}"

        retained_ratio = len(hn_tiles) / len(tiles)
        assert retained_ratio <= 0.50, f"Hard negative ratio {retained_ratio:.2%} exceeded single-wall 50% ceiling"

        # Explicit proof of defect elimination
        assert len(hn_tiles) != 24, "CRITICAL REGRESSION: 24 hard negatives retained (defect reproduced)!"
        assert retained_ratio < 0.96, "CRITICAL REGRESSION: 96% hard negative ratio defect detected!"

    def test_2000x2000_single_wall_grayscale_canvas(self) -> None:
        """Verifies that 2D single-channel grayscale drawings observe identical quota bounds."""
        h, w = 2000, 2000
        config = UnifiedDatasetConfig(
            tile_size=512,
            overlap_ratio=0.20,
            max_hard_negative_ratio=0.15,
        )
        tiler = SlidingWindowTiler(config)

        # 2D Grayscale image
        img_gray = np.full((h, w), 255, dtype=np.uint8)
        for y in range(50, h, 100):
            cv2.line(img_gray, (0, y), (w, y), 0, 2)

        mask_data = np.zeros((h, w), dtype=np.uint8)
        mask_data[80:120, 80:120] = DatasetClass.NON_DRYWALL.value
        mask = UnifiedMask(mask_data)

        tiles = tiler.tile_drawing(img_gray, mask, "adv_gray_quota", "test_m1")
        wall_tiles = [t for t in tiles if t[2].has_walls]
        hn_tiles = [t for t in tiles if t[2].is_hard_negative]

        assert len(wall_tiles) == 1
        assert len(hn_tiles) <= 1
        assert len(tiles) <= 2


class TestZeroWallSheetFiltering:
    """Stress-tests zero-wall drawing sheets (general notes, title sheets, cover sheets)."""

    def test_zero_wall_multi_tile_dense_linework_discards_all_tiles(self) -> None:
        """
        Adversarial Scenario:
        A 2000x2000 general notes drawing filled with linework and text grids, but zero walls.
        Must discard all 25 tiles when nominal minimum is 0, preventing unanchored negative flooding.
        """
        h, w = 2000, 2000
        config = UnifiedDatasetConfig(
            tile_size=512,
            overlap_ratio=0.20,
            max_hard_negative_ratio=0.15,
            nominal_hard_negative_min=0,
            nominal_hard_negatives_zero_walls=0,
        )
        tiler = SlidingWindowTiler(config)

        # Dense linework across entire canvas
        img = np.full((h, w, 3), 255, dtype=np.uint8)
        for y in range(50, h, 50):
            cv2.line(img, (0, y), (w, y), (0, 0, 0), 1)
        for x in range(50, w, 50):
            cv2.line(img, (x, 0), (x, h), (0, 0, 0), 1)

        mask = UnifiedMask.zeros(h, w)
        assert not mask.has_walls()

        tiles = tiler.tile_drawing(img, mask, "adv_zero_wall_multi", "test_m1")

        assert len(tiles) == 0, f"Expected 0 tiles retained from zero-wall drawing, got {len(tiles)}"

    def test_zero_wall_multi_tile_with_configured_nominal_minimum(self) -> None:
        """
        If user explicitly configures nominal_hard_negatives_zero_walls = 3,
        verify that exactly 3 highest-variance tiles are retained.
        """
        h, w = 2000, 2000
        config = UnifiedDatasetConfig(
            tile_size=512,
            overlap_ratio=0.20,
            max_hard_negative_ratio=0.15,
            nominal_hard_negatives_zero_walls=3,
        )
        tiler = SlidingWindowTiler(config)

        img = np.full((h, w, 3), 255, dtype=np.uint8)
        # Add varying line density to create variance differences
        for y in range(50, 500, 20):  # Dense in top region
            cv2.line(img, (0, y), (w, y), (0, 0, 0), 2)
        for y in range(500, h, 200): # Sparse in bottom
            cv2.line(img, (0, y), (w, y), (0, 0, 0), 1)

        mask = UnifiedMask.zeros(h, w)
        tiles = tiler.tile_drawing(img, mask, "adv_zero_wall_nominal_3", "test_m1")

        assert len(tiles) == 3, f"Expected exactly 3 tiles retained under nominal quota, got {len(tiles)}"
        for _, _, meta in tiles:
            assert meta.is_hard_negative is True
            assert meta.has_walls is False

    def test_zero_wall_single_tile_crop_retains_single_tile(self) -> None:
        """
        If drawing is a single-tile crop (512x512) with linework,
        it should be retained for unit test compatibility and single-crop workflows.
        """
        config = UnifiedDatasetConfig(tile_size=512)
        tiler = SlidingWindowTiler(config)

        img = np.full((512, 512, 3), 255, dtype=np.uint8)
        cv2.line(img, (100, 100), (400, 400), (0, 0, 0), 2)

        mask = UnifiedMask.zeros(512, 512)
        tiles = tiler.tile_drawing(img, mask, "single_tile_hn", "test_m1")

        assert len(tiles) == 1
        assert tiles[0][2].is_hard_negative is True

    def test_zero_wall_pure_white_blank_discards_all_tiles(self) -> None:
        """Pure white canvas (std=0, mean=255) must discard all tiles regardless of size."""
        config = UnifiedDatasetConfig(tile_size=512)
        tiler = SlidingWindowTiler(config)

        # 1. 2000x2000 pure white
        img_large = np.full((2000, 2000, 3), 255, dtype=np.uint8)
        mask_large = UnifiedMask.zeros(2000, 2000)
        tiles_large = tiler.tile_drawing(img_large, mask_large, "white_large", "test_m1")
        assert len(tiles_large) == 0

        # 2. 512x512 pure white
        img_single = np.full((512, 512, 3), 255, dtype=np.uint8)
        mask_single = UnifiedMask.zeros(512, 512)
        tiles_single = tiler.tile_drawing(img_single, mask_single, "white_single", "test_m1")
        assert len(tiles_single) == 0


class TestVaryingQuotasAndMonotonicityStress:
    """Stress-tests hard negative quota formulas, monotonicity, and ratio bounds."""

    @pytest.mark.parametrize(
        "ratio, expected_hn",
        [
            (0.00, 0),    # ratio=0 -> 0 HN
            (0.05, 3),    # ceil(50 * 0.05 / 0.95) = ceil(2.63) = 3
            (0.10, 6),    # ceil(50 * 0.10 / 0.90) = ceil(5.56) = 6
            (0.15, 9),    # ceil(50 * 0.15 / 0.85) = ceil(8.82) = 9
            (0.20, 13),   # ceil(50 * 0.20 / 0.80) = ceil(12.5) = 13
            (0.30, 22),   # ceil(50 * 0.30 / 0.70) = ceil(21.43) = 22
            (0.50, 50),   # ceil(50 * 0.50 / 0.50) = 50
        ],
    )
    def test_dense_wall_sheet_varying_ratios(self, ratio: float, expected_hn: int) -> None:
        """
        Adversarial scenario: 50 wall tiles and 100+ linework candidate tiles.
        Verifies exact adherence to ceiling quota formula across ratios.
        """
        # Canvas sized to generate ~180 tiles (e.g. 5000 x 5000 with tile=512, stride=410 -> 12x12=144 tiles)
        h, w = 5000, 5000
        config = UnifiedDatasetConfig(
            tile_size=512,
            overlap_ratio=0.20,
            max_hard_negative_ratio=ratio,
        )
        tiler = SlidingWindowTiler(config)

        img = np.full((h, w, 3), 255, dtype=np.uint8)
        for y in range(50, h, 80):
            cv2.line(img, (0, y), (w, y), (0, 0, 0), 2)

        y_steps, x_steps = tiler.compute_tile_grid(h, w)
        all_coords = [(y, x) for y in y_steps for x in x_steps]
        assert len(all_coords) >= 120

        # Mark first 50 tiles as walls
        mask_data = np.zeros((h, w), dtype=np.uint8)
        for y, x in all_coords[:50]:
            mask_data[y + 100 : y + 200, x + 100 : x + 200] = DatasetClass.DRYWALL.value
        mask = UnifiedMask(mask_data)

        tiles = tiler.tile_drawing(img, mask, f"adv_dense_r_{ratio}", "test_m1")
        wall_tiles = [t for t in tiles if t[2].has_walls]
        hn_tiles = [t for t in tiles if t[2].is_hard_negative]

        assert len(wall_tiles) == 50, f"Expected 50 wall tiles, got {len(wall_tiles)}"
        assert len(hn_tiles) == expected_hn, (
            f"Ratio {ratio}: Expected {expected_hn} HN tiles, got {len(hn_tiles)}"
        )

        if len(tiles) > 0:
            actual_ratio = len(hn_tiles) / len(tiles)
            # Ceiling discretization bound: actual_ratio <= ratio + 1 / (N_walls + 1)
            ceiling_bound = ratio + 1.0 / 51.0
            assert actual_ratio <= ceiling_bound + 1e-4, (
                f"Actual ratio {actual_ratio:.4f} exceeded ceiling bound {ceiling_bound:.4f}"
            )

    def test_hard_negative_monotonicity_across_swept_ratios(self) -> None:
        """Sweeps ratios from 0.00 to 0.60 in increments of 0.05 and asserts non-decreasing HN counts."""
        h, w = 3500, 3500
        base_config = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20)
        tiler_base = SlidingWindowTiler(base_config)

        img = np.full((h, w, 3), 255, dtype=np.uint8)
        for y in range(60, h, 100):
            cv2.line(img, (0, y), (w, y), (0, 0, 0), 2)

        y_steps, x_steps = tiler_base.compute_tile_grid(h, w)
        all_coords = [(y, x) for y in y_steps for x in x_steps]

        mask_data = np.zeros((h, w), dtype=np.uint8)
        for y, x in all_coords[:25]:  # 25 wall tiles
            mask_data[y + 100 : y + 200, x + 100 : x + 200] = DatasetClass.DRYWALL.value
        mask = UnifiedMask(mask_data)

        ratios = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60]
        prev_hn = -1
        for r in ratios:
            cfg = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20, max_hard_negative_ratio=r)
            t = SlidingWindowTiler(cfg)
            res = t.tile_drawing(img, mask, f"mono_{r}", "test_m1")
            hn_count = sum(1 for item in res if item[2].is_hard_negative)
            assert hn_count >= prev_hn, f"Monotonicity violated at ratio {r}: {hn_count} < {prev_hn}"
            prev_hn = hn_count

    def test_ratio_zero_and_ratio_one_boundaries(self) -> None:
        """Verifies boundary cases ratio=0.0 (strictly 0 HN) and ratio=1.0 (all HN retained)."""
        h, w = 2000, 2000
        img = np.full((h, w, 3), 255, dtype=np.uint8)
        for y in range(50, h, 100):
            cv2.line(img, (0, y), (w, y), (0, 0, 0), 2)

        mask_data = np.zeros((h, w), dtype=np.uint8)
        mask_data[100:200, 100:200] = DatasetClass.DRYWALL.value
        mask = UnifiedMask(mask_data)

        # 1. Ratio 0.0 -> 0 HN
        cfg_0 = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20, max_hard_negative_ratio=0.0)
        t_0 = SlidingWindowTiler(cfg_0)
        tiles_0 = t_0.tile_drawing(img, mask, "ratio_0", "test_m1")
        assert sum(1 for t in tiles_0 if t[2].is_hard_negative) == 0
        assert len(tiles_0) == 1

        # 2. Ratio 1.0 -> All 24 candidate HN retained
        cfg_1 = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20, max_hard_negative_ratio=1.0)
        t_1 = SlidingWindowTiler(cfg_1)
        tiles_1 = t_1.tile_drawing(img, mask, "ratio_1", "test_m1")
        assert sum(1 for t in tiles_1 if t[2].is_hard_negative) == 24
        assert len(tiles_1) == 25


class TestExtremeAspectRatioAndBoundaryStress:
    """Stress-tests SlidingWindowTiler on extreme ribbon dimensions and irregular boundaries."""

    def test_extreme_horizontal_ribbon_512x4000(self) -> None:
        """
        Ribbon aspect ratio: 512 x 4000 (1 row, 10 columns).
        1 wall tile at column 0, dense linework across columns 1..9.
        With max_hard_negative_ratio=0.15:
            Expected HN <= 1.
        """
        h, w = 512, 4000
        config = UnifiedDatasetConfig(
            tile_size=512,
            overlap_ratio=0.20,
            max_hard_negative_ratio=0.15,
        )
        tiler = SlidingWindowTiler(config)

        img = np.full((h, w, 3), 255, dtype=np.uint8)
        for x in range(100, w, 100):
            cv2.line(img, (x, 0), (x, h), (0, 0, 0), 2)

        mask_data = np.zeros((h, w), dtype=np.uint8)
        mask_data[100:200, 50:150] = DatasetClass.DRYWALL.value
        mask = UnifiedMask(mask_data)

        tiles = tiler.tile_drawing(img, mask, "ribbon_h", "test_m1")
        wall_tiles = [t for t in tiles if t[2].has_walls]
        hn_tiles = [t for t in tiles if t[2].is_hard_negative]

        assert len(wall_tiles) == 1
        assert len(hn_tiles) <= 1
        assert len(tiles) <= 2
        for t in tiles:
            assert t[0].shape == (512, 512, 3)
            assert t[1].shape == (512, 512)

    def test_extreme_vertical_column_4000x512(self) -> None:
        """
        Ribbon aspect ratio: 4000 x 512 (10 rows, 1 column).
        1 wall tile at row 9, dense linework across rows 0..8.
        With max_hard_negative_ratio=0.15:
            Expected HN <= 1.
        """
        h, w = 4000, 512
        config = UnifiedDatasetConfig(
            tile_size=512,
            overlap_ratio=0.20,
            max_hard_negative_ratio=0.15,
        )
        tiler = SlidingWindowTiler(config)

        img = np.full((h, w, 3), 255, dtype=np.uint8)
        for y in range(100, h, 100):
            cv2.line(img, (0, y), (w, y), (0, 0, 0), 2)

        # Wall in bottom tile (y in [3800:3900], step 8 ends at 3792, so only step 9 covers it)
        mask_data = np.zeros((h, w), dtype=np.uint8)
        mask_data[3800:3900, 100:200] = DatasetClass.DRYWALL.value
        mask = UnifiedMask(mask_data)

        tiles = tiler.tile_drawing(img, mask, "ribbon_v", "test_m1")
        wall_tiles = [t for t in tiles if t[2].has_walls]
        hn_tiles = [t for t in tiles if t[2].is_hard_negative]

        assert len(wall_tiles) == 1
        assert len(hn_tiles) <= 1
        assert len(tiles) <= 2

    def test_irregular_non_multiple_dimensions_1234x2345(self) -> None:
        """
        Irregular plan: 1234 x 2345.
        Tiler must properly clamp boundaries without index errors or shape mismatches.
        """
        h, w = 1234, 2345
        config = UnifiedDatasetConfig(
            tile_size=512,
            overlap_ratio=0.20,
            max_hard_negative_ratio=0.15,
        )
        tiler = SlidingWindowTiler(config)

        img = np.full((h, w, 3), 255, dtype=np.uint8)
        for y in range(100, h, 150):
            cv2.line(img, (0, y), (w, y), (0, 0, 0), 2)

        # Place 2 walls in non-overlapping single-coverage tiles
        mask_data = np.zeros((h, w), dtype=np.uint8)
        mask_data[50:100, 50:100] = DatasetClass.DRYWALL.value  # only covered by (r0, c0)
        mask_data[1150:1200, 2200:2250] = DatasetClass.NON_DRYWALL.value  # only covered by (r2, c5)
        mask = UnifiedMask(mask_data)

        tiles = tiler.tile_drawing(img, mask, "irregular_1234x2345", "test_m1")
        wall_tiles = [t for t in tiles if t[2].has_walls]
        hn_tiles = [t for t in tiles if t[2].is_hard_negative]

        assert len(wall_tiles) == 2
        # ceil(2 * 0.15 / 0.85) = ceil(0.353) = 1
        assert len(hn_tiles) <= 1
        for t in tiles:
            assert t[0].shape == (512, 512, 3)
            assert t[1].shape == (512, 512)


class TestLineworkVarianceRankingAndSpatialTieBreak:
    """Stress-tests deterministic variance ranking and spatial raster tie-breaking."""

    def test_highest_variance_selected_among_candidates(self) -> None:
        """
        Creates a 3x3 grid (1536x1536) non-overlapping (stride=512).
        Tile (0, 0): Wall tile.
        Tile (0, 1): Low linework (std ~5)
        Tile (0, 2): Medium linework (std ~15)
        Tile (1, 0): Very high linework (std ~45)
        Remaining tiles: pure blank (discarded)

        Quota allows 1 HN tile. The selected HN tile MUST be Tile (1, 0).
        """
        config = UnifiedDatasetConfig(
            tile_size=512,
            overlap_ratio=0.0,
            max_hard_negative_ratio=0.15,
        )
        tiler = SlidingWindowTiler(config)

        h, w = 1536, 1536
        img = np.full((h, w, 3), 255, dtype=np.uint8)

        # Tile (0, 1): y in [0..512], x in [512..1024] -> 2 lines
        cv2.line(img, (550, 100), (950, 100), (0, 0, 0), 1)
        cv2.line(img, (550, 300), (950, 300), (0, 0, 0), 1)

        # Tile (0, 2): y in [0..512], x in [1024..1536] -> 6 lines
        for y in range(50, 450, 70):
            cv2.line(img, (1050, y), (1500, y), (0, 0, 0), 2)

        # Tile (1, 0): y in [512..1024], x in [0..512] -> Dense checkerboard grid (Highest std)
        for y in range(530, 1000, 15):
            cv2.line(img, (20, y), (490, y), (0, 0, 0), 3)
        for x in range(20, 490, 15):
            cv2.line(img, (x, 530), (x, 1000), (0, 0, 0), 3)

        # Tile (0, 0): Wall
        mask_data = np.zeros((h, w), dtype=np.uint8)
        mask_data[100:200, 100:200] = DatasetClass.DRYWALL.value
        mask = UnifiedMask(mask_data)

        tiles = tiler.tile_drawing(img, mask, "test_rank_highest", "test_m1")
        wall_tiles = [t for t in tiles if t[2].has_walls]
        hn_tiles = [t for t in tiles if t[2].is_hard_negative]

        assert len(wall_tiles) == 1
        assert len(hn_tiles) == 1

        selected_hn_coords = hn_tiles[0][2].coordinates
        assert selected_hn_coords.row_idx == 1 and selected_hn_coords.col_idx == 0, (
            f"Expected highest variance tile (1, 0) to be selected, got ({selected_hn_coords.row_idx}, {selected_hn_coords.col_idx})"
        )

    def test_identical_variance_spatial_tie_breaker(self) -> None:
        """
        Creates 4 candidate tiles with identical linework patterns (same std).
        1 wall tile allows 1 HN tile.
        Verify tie-breaker picks lowest row_idx, then col_idx, deterministically without crashing.
        Verify returned tile list is strictly ordered by (row_idx, col_idx).
        """
        config = UnifiedDatasetConfig(
            tile_size=512,
            overlap_ratio=0.0,
            max_hard_negative_ratio=0.15,
        )
        tiler = SlidingWindowTiler(config)

        # 2x2 grid (1024x1024):
        # Tile (0, 0): Wall tile + 2 lines
        # Tile (0, 1): 2 lines (exact duplicate)
        # Tile (1, 0): 2 lines (exact duplicate)
        # Tile (1, 1): 2 lines (exact duplicate)
        h, w = 1024, 1024
        img = np.full((h, w, 3), 255, dtype=np.uint8)

        for r in range(2):
            for c in range(2):
                y_base = r * 512
                x_base = c * 512
                cv2.line(img, (x_base + 50, y_base + 200), (x_base + 450, y_base + 200), (0, 0, 0), 2)
                cv2.line(img, (x_base + 50, y_base + 300), (x_base + 450, y_base + 300), (0, 0, 0), 2)

        mask_data = np.zeros((h, w), dtype=np.uint8)
        mask_data[100:150, 100:150] = DatasetClass.DRYWALL.value  # In Tile (0, 0)
        mask = UnifiedMask(mask_data)

        tiles = tiler.tile_drawing(img, mask, "test_tie_break", "test_m1")
        wall_tiles = [t for t in tiles if t[2].has_walls]
        hn_tiles = [t for t in tiles if t[2].is_hard_negative]

        assert len(wall_tiles) == 1
        assert len(hn_tiles) == 1

        # Tile (0, 1) has lowest row, then col among candidate HN (0, 1), (1, 0), (1, 1)
        selected_hn = hn_tiles[0][2].coordinates
        assert (selected_hn.row_idx, selected_hn.col_idx) == (0, 1)

        # Check final list sorting is canonical raster scan order
        coords = [(t[2].coordinates.row_idx, t[2].coordinates.col_idx) for t in tiles]
        assert coords == sorted(coords), f"Results not sorted in canonical raster order: {coords}"


class TestMulticlassMaskWallDetectionAndCorruptRejection:
    """Tests wall detection across all valid classes and corruption rejection."""

    def test_all_positive_classes_recognized_as_wall_tiles(self) -> None:
        """
        UnifiedMask labels:
        1: Drywall
        2: Non-Drywall
        3: Uncertain
        All 3 must be detected as has_walls=True.
        """
        config = UnifiedDatasetConfig(tile_size=512)
        tiler = SlidingWindowTiler(config)

        for label, name in [
            (DatasetClass.DRYWALL.value, "Drywall"),
            (DatasetClass.NON_DRYWALL.value, "Non-Drywall"),
            (DatasetClass.UNCERTAIN.value, "Uncertain"),
        ]:
            img = np.full((512, 512, 3), 255, dtype=np.uint8)
            mask_data = np.zeros((512, 512), dtype=np.uint8)
            mask_data[200:250, 200:250] = label
            mask = UnifiedMask(mask_data)

            tiles = tiler.tile_drawing(img, mask, f"test_class_{name}", "test_m1")
            assert len(tiles) == 1
            _, _, meta = tiles[0]
            assert meta.has_walls is True
            assert meta.is_hard_negative is False

    def test_single_pixel_wall_trigger(self) -> None:
        """A single 1-pixel annotation must trigger has_walls=True."""
        config = UnifiedDatasetConfig(tile_size=512)
        tiler = SlidingWindowTiler(config)

        img = np.full((512, 512, 3), 255, dtype=np.uint8)
        mask_data = np.zeros((512, 512), dtype=np.uint8)
        mask_data[256, 256] = DatasetClass.DRYWALL.value
        mask = UnifiedMask(mask_data)

        tiles = tiler.tile_drawing(img, mask, "single_pixel_wall", "test_m1")
        assert len(tiles) == 1
        assert tiles[0][2].has_walls is True
        assert tiles[0][2].class_pixel_counts["drywall"] == 1

    def test_invalid_mask_values_rejected_as_corrupt(self) -> None:
        """If a tile has values > 3 in its mask, it must be marked corrupt and rejected."""
        config = UnifiedDatasetConfig(tile_size=512)
        tiler = SlidingWindowTiler(config)

        img = np.full((512, 512, 3), 255, dtype=np.uint8)
        mask_data = np.zeros((512, 512), dtype=np.uint8)
        mask_data[200:210, 200:210] = 5  # Invalid class value > 3

        # We construct UnifiedMask directly with check bypassed or data containing 5
        mask = object.__new__(UnifiedMask)
        mask.data = mask_data

        tiles = tiler.tile_drawing(img, mask, "corrupt_mask", "test_m1")
        assert len(tiles) == 0, f"Corrupt tile was not rejected: {tiles}"
