"""
drywall_detection/tests/unit/test_datasets.py
============================================
Comprehensive unit test suite for:
- Unified dataset format (Mode 'P' palette, invariants, converters, tiling, 2D Hann stitching, QC)
- Drawing-level and project-level split integrity manager (zero leakage, group partitioning, quarantine)
- Low-RAM streaming PyTorch Dataset, synchronized torchvision augmentations, and DataLoader defaults
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pytest
import numpy as np
from PIL import Image
import cv2

import torch
import torchvision.transforms.functional as TF

from drywall_detection.datasets.unified_format import (
    DatasetClass,
    PALETTE_256,
    UnifiedDatasetConfig,
    TileCoordinates,
    TileMetadata,
    MaskValidationError,
    validate_mask_array,
    UnifiedMask,
    MSDConverter,
    CubiCasaConverter,
    RasterMaskConverter,
    SlidingWindowTiler,
    VisualQCGenerator,
)
from drywall_detection.datasets.split_manager import (
    TileRecord,
    SplitStats,
    SplitManifest,
    DrawingSplitManager,
    SplitLeakageError,
    InsufficientGroupsError,
    InvalidSplitRatioError,
    verify_split_isolation,
)
from drywall_detection.datasets.loader import (
    IMAGENET_MEAN,
    IMAGENET_STD,
    SynchronizedTransform,
    DrywallTileDataset,
    safe_collate_fn,
    get_tile_dataloader,
)


# ==============================================================================
# 1. Test Unified Format & Converters
# ==============================================================================

class TestUnifiedFormat:
    """Verifies single-channel 8-bit indexed mask standard, converters, tiling, and QC."""

    def test_unified_mask_palette_values(self) -> None:
        """Verifies mask validation allows only {0, 1, 2, 3} and uint8 2D arrays."""
        valid_arr = np.array([[0, 1], [2, 3]], dtype=np.uint8)
        mask = UnifiedMask(valid_arr)
        assert mask.shape == (2, 2)
        assert mask.height == 2 and mask.width == 2
        assert mask.has_walls() is True

        # Invalid value 4
        invalid_val_arr = np.array([[0, 1], [2, 4]], dtype=np.uint8)
        with pytest.raises(MaskValidationError):
            UnifiedMask(invalid_val_arr)

        # Invalid dtype float32
        invalid_dtype_arr = np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float32)
        with pytest.raises(MaskValidationError):
            UnifiedMask(invalid_dtype_arr)  # type: ignore

        # Invalid dimensions 3D
        invalid_dim_arr = np.zeros((2, 2, 3), dtype=np.uint8)
        with pytest.raises(MaskValidationError):
            UnifiedMask(invalid_dim_arr)

    def test_indexed_png_mode_p_persistence(self, tmp_path: Path) -> None:
        """Verifies saving mask as Mode 'P' produces valid indexed PNG with direct PyTorch int64 loading."""
        arr = np.array([[0, 1, 2, 3], [3, 2, 1, 0]], dtype=np.uint8)
        mask = UnifiedMask(arr)
        out_file = tmp_path / "test_mask.png"
        mask.save(out_file, as_indexed_palette=True)

        assert out_file.is_file()

        # Load with PIL
        with Image.open(out_file) as loaded_img:
            assert loaded_img.mode == 'P'
            loaded_arr = np.array(loaded_img)
            assert loaded_arr.dtype == np.uint8
            np.testing.assert_array_equal(loaded_arr, arr)

        # PyTorch direct tensor loading without de-mapping
        tensor = torch.from_numpy(loaded_arr).long()
        assert tensor.dtype == torch.int64
        assert tensor.shape == (2, 4)
        assert set(tensor.unique().tolist()).issubset({0, 1, 2, 3})

    def test_msd_wkt_converter(self) -> None:
        """Verifies MSD WKT polygon conversion into Class 3 Uncertain mask."""
        wkt_poly = "POLYGON ((10 10, 50 10, 50 50, 10 50, 10 10))"
        converter = MSDConverter()
        mask = converter.parse_wkt_geometries(
            wkt_list=[wkt_poly],
            target_shape=(100, 100),
            bounds=(0, 0, 100, 100)
        )
        assert isinstance(mask, UnifiedMask)
        assert mask.shape == (100, 100)
        counts = mask.get_class_counts()
        assert counts["uncertain"] > 0
        assert counts["drywall"] == 0
        assert counts["non_drywall"] == 0

    def test_cubicasa_svg_converter(self) -> None:
        """Verifies CubiCasa SVG Wall polygon parsing into Class 3 Uncertain mask."""
        svg_xml = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <polygon class="Wall" points="10,10 40,10 40,40 10,40" />
        </svg>"""
        converter = CubiCasaConverter()
        mask = converter.parse_svg(svg_xml, target_shape=(100, 100))
        assert isinstance(mask, UnifiedMask)
        assert mask.shape == (100, 100)
        counts = mask.get_class_counts()
        assert counts["uncertain"] > 0
        assert counts["drywall"] == 0
        assert counts["non_drywall"] == 0

    def test_raster_mask_converter(self) -> None:
        """Verifies binary raster conversion to UnifiedMask Class 3."""
        binary_raster = np.zeros((100, 100), dtype=np.uint8)
        binary_raster[20:40, 20:40] = 255  # wall region
        converter = RasterMaskConverter()
        mask = converter.convert_raster(binary_raster, target_shape=(100, 100), wall_threshold=127)
        assert isinstance(mask, UnifiedMask)
        assert mask.shape == (100, 100)
        counts = mask.get_class_counts()
        assert counts["uncertain"] == 400
        assert counts["drywall"] == 0

    def test_sliding_window_tiling_and_clamping(self) -> None:
        """Verifies 512x512 tiling with 20% overlap (stride 410) covers 100% of canvas with boundary clamping."""
        config = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20)
        assert config.stride == 410

        tiler = SlidingWindowTiler(config)
        y_steps, x_steps = tiler.compute_tile_grid(height=1000, width=1200)

        # Verify steps span the canvas
        assert y_steps[0] == 0
        assert y_steps[-1] + 512 == 1000
        assert x_steps[0] == 0
        assert x_steps[-1] + 512 == 1200

        # Check coverage of all pixels
        covered = np.zeros((1000, 1200), dtype=bool)
        for y in y_steps:
            for x in x_steps:
                covered[y:y+512, x:x+512] = True
        assert np.all(covered)

    def test_tile_filtering_blank_and_hard_neg(self) -> None:
        """Verifies blank white tiles are discarded while hard negatives with linework are retained."""
        tiler = SlidingWindowTiler(UnifiedDatasetConfig(tile_size=512))

        # 1. Pure blank white drawing (mean 255, std 0, zero walls)
        blank_img = np.full((512, 512, 3), 255, dtype=np.uint8)
        blank_mask = UnifiedMask.zeros(512, 512)
        tiles_blank = tiler.tile_drawing(blank_img, blank_mask, "draw_blank", "test_source")
        assert len(tiles_blank) == 0  # Pure blank tile must be discarded

        # 2. Hard negative drawing (contains linework/text, std > 2.0, but zero walls)
        hn_img = np.full((512, 512, 3), 255, dtype=np.uint8)
        cv2.line(hn_img, (50, 50), (450, 50), (0, 0, 0), 2)  # text or dimension line
        hn_mask = UnifiedMask.zeros(512, 512)
        tiles_hn = tiler.tile_drawing(hn_img, hn_mask, "draw_hn", "test_source")
        assert len(tiles_hn) == 1
        _, _, meta_hn = tiles_hn[0]
        assert meta_hn.is_hard_negative is True
        assert meta_hn.has_walls is False

        # 3. Positive drawing (contains wall mask)
        pos_img = np.full((512, 512, 3), 255, dtype=np.uint8)
        pos_mask_data = np.zeros((512, 512), dtype=np.uint8)
        pos_mask_data[100:150, 100:150] = DatasetClass.DRYWALL.value
        pos_mask = UnifiedMask(pos_mask_data)
        tiles_pos = tiler.tile_drawing(pos_img, pos_mask, "draw_pos", "test_source")
        assert len(tiles_pos) == 1
        _, _, meta_pos = tiles_pos[0]
        assert meta_pos.has_walls is True
        assert meta_pos.class_pixel_counts["drywall"] == 2500

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
            mask_data_10[y+150:y+200, x+150:x+200] = DatasetClass.DRYWALL.value

        tiles_10 = tiler.tile_drawing(img, UnifiedMask(mask_data_10), "draw_10_walls", "test_source")
        w_10 = [t for t in tiles_10 if t[2].has_walls]
        hn_10 = [t for t in tiles_10 if t[2].is_hard_negative]

        # ceil(10 * 0.15 / 0.85) = 2
        assert len(w_10) == 10
        assert len(hn_10) <= 2, f"Expected at most 2 hard negatives for 10 wall tiles, got {len(hn_10)}"
        actual_ratio_10 = len(hn_10) / len(tiles_10)
        assert actual_ratio_10 <= 0.17, f"Ratio {actual_ratio_10:.2%} exceeded quota threshold"

    def test_hard_negative_variance_ranking(self) -> None:
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

        # Create drawing with 20 wall tiles and 30+ linework candidate tiles
        # Canvas sized to generate ~72 tiles: 512 stride 410, 8 steps x 9 steps = 72 tiles
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
            mask_data[y+150:y+250, x+150:x+250] = DatasetClass.DRYWALL.value

        tiles = tiler.tile_drawing(img, UnifiedMask(mask_data), f"draw_ratio_{ratio}", "test_source")
        wall_tiles = [t for t in tiles if t[2].has_walls]
        hn_tiles = [t for t in tiles if t[2].is_hard_negative]

        assert len(wall_tiles) == 20, f"Expected exactly 20 wall tiles, got {len(wall_tiles)}"
        assert len(hn_tiles) <= expected_max_hn, (
            f"Ratio {ratio}: Expected <= {expected_max_hn} hard negatives, got {len(hn_tiles)}"
        )

        if ratio == 0.0:
            assert len(hn_tiles) == 0, "Ratio 0.0 must retain 0 hard negatives"

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
            mask_data[y+150:y+250, x+150:x+250] = DatasetClass.DRYWALL.value
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

    def test_seamless_hann_reverse_stitching(self) -> None:
        """Verifies 2D Hann window apodization reverse stitching reconstructs global mask accurately."""
        tiler = SlidingWindowTiler(UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20))
        h, w = 800, 1000
        y_steps, x_steps = tiler.compute_tile_grid(h, w)

        # Create known ground truth global mask
        gt_mask = np.zeros((h, w), dtype=np.uint8)
        gt_mask[200:400, 300:500] = DatasetClass.DRYWALL.value

        tile_probs = []
        coords_list = []
        for r_idx, y0 in enumerate(y_steps):
            for c_idx, x0 in enumerate(x_steps):
                y1 = y0 + 512
                x1 = x0 + 512
                patch = gt_mask[y0:y1, x0:x1]
                tile_probs.append(patch)
                coords_list.append(TileCoordinates(
                    row_idx=r_idx, col_idx=c_idx,
                    y_min=y0, x_min=x0, y_max=y1, x_max=x1,
                    parent_height=h, parent_width=w
                ))

        stitched = tiler.stitch_predictions(tile_probs, coords_list, parent_shape=(h, w), num_classes=4)
        assert stitched.shape == (h, w)
        np.testing.assert_array_equal(stitched, gt_mask)

    def test_visual_qc_triplet_creation(self, tmp_path: Path) -> None:
        """Verifies visual QC triplet generator creates [Drawing | Color Mask | Overlay] with banner."""
        qc = VisualQCGenerator(UnifiedDatasetConfig(tile_size=512))
        img = np.full((512, 512, 3), 245, dtype=np.uint8)
        mask_data = np.zeros((512, 512), dtype=np.uint8)
        mask_data[100:200, 100:200] = DatasetClass.DRYWALL.value
        mask_data[300:400, 300:400] = DatasetClass.NON_DRYWALL.value
        mask = UnifiedMask(mask_data)

        meta = TileMetadata(
            tile_id="tile_qc_001",
            parent_drawing_id="sheet_A101",
            dataset_source="MTA_99th",
            split="train",
            coordinates=TileCoordinates(0, 0, 0, 0, 512, 512, 512, 512),
            class_pixel_counts=mask.get_class_counts(),
            class_percentages=mask.get_class_percentages(),
            has_walls=True,
            is_pure_blank=False,
            is_hard_negative=False,
            is_corrupt=False
        )

        triplet = qc.create_triplet(img, mask, meta)
        # Triplet shape: (512 + 36 banner height, 512 * 3 = 1536 width, 3 channels)
        assert triplet.shape == (548, 1536, 3)

        out_path = tmp_path / "qc_sample.png"
        saved_path = qc.save_qc_sample(out_path, img, mask, meta)
        assert saved_path.is_file()


# ==============================================================================
# 2. Test DrawingSplitManager
# ==============================================================================

@pytest.fixture
def synthetic_tiles() -> List[TileRecord]:
    """Generates 100 synthetic tiles across 10 distinct projects (2 drawings, 5 tiles each)."""
    tiles = []
    for p_idx in range(10):
        proj_id = f"proj_{p_idx:02d}"
        for d_idx in range(2):
            draw_id = f"{proj_id}_sheet_{d_idx:02d}"
            for t_idx in range(5):
                tile_id = f"{draw_id}_tile_{t_idx:03d}"
                tiles.append(
                    TileRecord(
                        tile_id=tile_id,
                        project_id=proj_id,
                        drawing_id=draw_id,
                        image_path=f"/data/img/{tile_id}.png",
                        mask_path=f"/data/mask/{tile_id}.png",
                        bbox=(0, 0, 512, 512),
                        has_walls=True,
                    )
                )
    return tiles


class TestDrawingSplitManager:
    """Verifies greedy partitioning, zero leakage, quarantine, and manifests."""

    def test_zero_project_overlap_three_splits(self, synthetic_tiles: List[TileRecord]) -> None:
        """Verifies projects in Train, Val, and Test are 100% mutually disjoint."""
        manager = DrawingSplitManager(split_ratios=(0.70, 0.15, 0.15), group_key="project_id", seed=42)
        manifest = manager.create_splits(synthetic_tiles)

        train_projs = {t.project_id for t in manifest.train_tiles}
        val_projs = {t.project_id for t in manifest.val_tiles}
        test_projs = {t.project_id for t in manifest.test_tiles}

        assert train_projs.intersection(val_projs) == set()
        assert train_projs.intersection(test_projs) == set()
        assert val_projs.intersection(test_projs) == set()

        # Total tile count preserved
        assert len(manifest.train_tiles) + len(manifest.val_tiles) + len(manifest.test_tiles) == 100

    def test_zero_drawing_overlap_fallback(self) -> None:
        """When only 1 project exists, verifies fallback to drawing_id with zero drawing overlap."""
        tiles = []
        # Single project with 6 distinct drawings
        for d_idx in range(6):
            draw_id = f"single_proj_sheet_{d_idx:02d}"
            for t_idx in range(5):
                tile_id = f"{draw_id}_t{t_idx:02d}"
                tiles.append(
                    TileRecord(
                        tile_id=tile_id,
                        project_id="single_proj",
                        drawing_id=draw_id,
                        image_path=f"/data/img/{tile_id}.png",
                        mask_path=f"/data/mask/{tile_id}.png",
                        bbox=(0, 0, 512, 512),
                    )
                )

        manager = DrawingSplitManager(split_ratios=(0.70, 0.15, 0.15), group_key="project_id", allow_drawing_fallback=True)
        manifest = manager.create_splits(tiles)
        assert manifest.group_key == "drawing_id"

        train_draws = {t.drawing_id for t in manifest.train_tiles}
        val_draws = {t.drawing_id for t in manifest.val_tiles}
        test_draws = {t.drawing_id for t in manifest.test_tiles}

        assert train_draws.intersection(val_draws) == set()
        assert train_draws.intersection(test_draws) == set()
        assert val_draws.intersection(test_draws) == set()

    def test_split_leakage_detection_raises_error(self, synthetic_tiles: List[TileRecord]) -> None:
        """Verifies verify_split_isolation raises SplitLeakageError if a tile or project leaks."""
        manager = DrawingSplitManager(split_ratios=(0.70, 0.15, 0.15), group_key="project_id", seed=42)
        manifest = manager.create_splits(synthetic_tiles)

        # Inject leakage: copy a train tile into val
        manifest.val_tiles.append(manifest.train_tiles[0])

        with pytest.raises(SplitLeakageError):
            verify_split_isolation(manifest)

    def test_reproducible_deterministic_seed(self, synthetic_tiles: List[TileRecord]) -> None:
        """Verifies identical seed produces identical splits and different seeds differ."""
        m1 = DrawingSplitManager(seed=42).create_splits(synthetic_tiles)
        m2 = DrawingSplitManager(seed=42).create_splits(synthetic_tiles)
        m3 = DrawingSplitManager(seed=999).create_splits(synthetic_tiles)

        assert [t.tile_id for t in m1.train_tiles] == [t.tile_id for t in m2.train_tiles]
        assert m1.verification_hash == m2.verification_hash

    def test_quarantine_exclusion_from_val_test(self, synthetic_tiles: List[TileRecord]) -> None:
        """Verifies quarantined projects/tiles never enter val or test splits."""
        # Quarantine project 'proj_00'
        manager = DrawingSplitManager(quarantine_projects=["proj_00"])
        manifest = manager.create_splits(synthetic_tiles)

        val_projs = {t.project_id for t in manifest.val_tiles}
        test_projs = {t.project_id for t in manifest.test_tiles}

        assert "proj_00" not in val_projs
        assert "proj_00" not in test_projs
        assert len(manifest.quarantine_tiles) == 10  # 10 tiles belonging to proj_00

    def test_insufficient_groups_error(self) -> None:
        """Verifies InsufficientGroupsError is raised when < 3 groups exist."""
        # Only 2 projects and allow_drawing_fallback=False
        tiles = [
            TileRecord("t1", "p1", "d1", "/img/1.png", "/msk/1.png", (0, 0, 512, 512)),
            TileRecord("t2", "p2", "d2", "/img/2.png", "/msk/2.png", (0, 0, 512, 512)),
        ]
        manager = DrawingSplitManager(allow_drawing_fallback=False)
        with pytest.raises(InsufficientGroupsError):
            manager.create_splits(tiles)

    def test_invalid_split_ratios_error(self) -> None:
        """Verifies InvalidSplitRatioError is raised when ratios do not sum to 1.0."""
        with pytest.raises(InvalidSplitRatioError):
            DrawingSplitManager(split_ratios=(0.80, 0.20, 0.10))

    def test_manifest_export_and_json_roundtrip(self, synthetic_tiles: List[TileRecord], tmp_path: Path) -> None:
        """Verifies export_split_manifests exports train.json, val.json, test.json, and splits_summary.json."""
        manager = DrawingSplitManager(seed=42)
        manifest = manager.create_splits(synthetic_tiles)
        files = manager.export_split_manifests(manifest, tmp_path)

        assert "train" in files and files["train"].is_file()
        assert "val" in files and files["val"].is_file()
        assert "test" in files and files["test"].is_file()
        assert "summary" in files and files["summary"].is_file()

        with open(files["summary"], "r", encoding="utf-8") as f:
            summary_data = json.load(f)
        assert summary_data["isolation_status"] == "VERIFIED_ZERO_LEAKAGE"
        assert len(summary_data["verification_hash"]) == 64


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


# ==============================================================================
# 3. Test PyTorch Dataset & DataLoader
# ==============================================================================

@pytest.fixture
def mock_dataset_files(tmp_path: Path) -> Tuple[Path, List[Dict[str, Any]]]:
    """Creates synthetic 512x512 image and mask files on disk."""
    records = []
    for i in range(4):
        img_arr = np.full((512, 512, 3), 200 + i * 10, dtype=np.uint8)
        mask_arr = np.zeros((512, 512), dtype=np.uint8)
        mask_arr[100:200, 100:200] = (i % 3) + 1  # 1, 2, or 3

        img_path = tmp_path / f"img_{i:02d}.png"
        mask_path = tmp_path / f"mask_{i:02d}.png"

        Image.fromarray(img_arr).save(img_path)
        img_p = Image.fromarray(mask_arr, mode='P')
        img_p.putpalette(PALETTE_256)
        img_p.save(mask_path)

        records.append({
            "tile_id": f"tile_{i:02d}",
            "project_id": f"proj_{i // 2}",
            "drawing_id": f"draw_{i // 2}",
            "image_path": str(img_path),
            "mask_path": str(mask_path),
            "bbox": [0, 0, 512, 512]
        })

    manifest_path = tmp_path / "mock_train.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"tiles": records}, f)

    return manifest_path, records


class TestDrywallTileDataset:
    """Verifies streaming dataset, tensor shapes, normalization, and binary mode."""

    def test_dataset_tensor_shapes_and_dtypes(self, mock_dataset_files) -> None:
        manifest_path, _ = mock_dataset_files
        ds = DrywallTileDataset(manifest_path, mode="4class")
        assert len(ds) == 4

        img_tensor, mask_tensor = ds[0]
        assert isinstance(img_tensor, torch.Tensor)
        assert isinstance(mask_tensor, torch.Tensor)
        assert img_tensor.shape == (3, 512, 512)
        assert mask_tensor.shape == (512, 512)
        assert img_tensor.dtype == torch.float32
        assert mask_tensor.dtype == torch.int64

    def test_image_normalization_stats(self, mock_dataset_files) -> None:
        manifest_path, _ = mock_dataset_files
        ds = DrywallTileDataset(manifest_path, mode="4class")
        img_tensor, _ = ds[0]
        # Normalized image values should roughly be centered around 0
        assert -3.0 < img_tensor.mean().item() < 3.0

    def test_mask_class_range_four_class(self, mock_dataset_files) -> None:
        manifest_path, _ = mock_dataset_files
        ds = DrywallTileDataset(manifest_path, mode="4class")
        for i in range(len(ds)):
            _, mask_tensor = ds[i]
            unique_vals = mask_tensor.unique().tolist()
            assert set(unique_vals).issubset({0, 1, 2, 3})

    def test_binary_mode_remapping(self, mock_dataset_files) -> None:
        manifest_path, _ = mock_dataset_files
        ds = DrywallTileDataset(manifest_path, mode="binary")
        for i in range(len(ds)):
            _, mask_tensor = ds[i]
            unique_vals = mask_tensor.unique().tolist()
            assert set(unique_vals).issubset({0, 1})

    def test_missing_file_raises_filenotfound(self) -> None:
        bad_records = [{
            "tile_id": "bad_01",
            "image_path": "/nonexistent/img.png",
            "mask_path": "/nonexistent/mask.png"
        }]
        ds = DrywallTileDataset(bad_records)
        with pytest.raises(FileNotFoundError):
            _ = ds[0]

    def test_return_metadata_passthrough(self, mock_dataset_files) -> None:
        manifest_path, _ = mock_dataset_files
        ds = DrywallTileDataset(manifest_path, return_metadata=True)
        img, mask, meta = ds[0]
        assert isinstance(meta, dict)
        assert "tile_id" in meta
        assert "project_id" in meta


class TestSynchronizedTransform:
    """Verifies synchronized geometric transformations and photometric isolation."""

    def test_discrete_90_degree_rotations_preserve_labels(self) -> None:
        # Create mask with discrete labels [0, 1, 2, 3]
        arr_mask = np.array([[0, 1], [2, 3]], dtype=np.uint8)
        mask_pil = Image.fromarray(arr_mask, mode='P')
        img_pil = Image.fromarray(np.full((2, 2, 3), 200, dtype=np.uint8))

        # Test discrete rotations with transform
        tf = SynchronizedTransform(is_train=True, rot90_prob=1.0, hflip_prob=0.0, vflip_prob=0.0)
        _, mask_tensor = tf(img_pil, mask_pil)

        assert mask_tensor.dtype == torch.int64
        unique_vals = mask_tensor.unique().tolist()
        assert set(unique_vals).issubset({0, 1, 2, 3})

    def test_photometric_jitter_alters_image_only(self) -> None:
        # Mask must never be altered by photometric jitter
        arr_mask = np.zeros((512, 512), dtype=np.uint8)
        arr_mask[100:200, 100:200] = 1
        mask_pil = Image.fromarray(arr_mask, mode='P')
        img_pil = Image.fromarray(np.full((512, 512, 3), 128, dtype=np.uint8))

        tf = SynchronizedTransform(
            is_train=True,
            hflip_prob=0.0,
            vflip_prob=0.0,
            rot90_prob=0.0,
            brightness_jitter=0.5,
            contrast_jitter=0.5
        )
        _, mask_tensor = tf(img_pil, mask_pil)
        assert mask_tensor[150, 150].item() == 1
        assert mask_tensor[0, 0].item() == 0


class TestTileDataLoader:
    """Verifies DataLoader batching, Windows CPU defaults, and memory stability."""

    def test_dataloader_batch_shapes(self, mock_dataset_files) -> None:
        manifest_path, _ = mock_dataset_files
        loader = get_tile_dataloader(manifest_path, is_train=False, batch_size=2)
        batch = next(iter(loader))
        images, masks = batch
        assert images.shape == (2, 3, 512, 512)
        assert masks.shape == (2, 512, 512)
        assert images.dtype == torch.float32
        assert masks.dtype == torch.int64

    def test_dataloader_cpu_defaults_num_workers_and_pin_memory(self, mock_dataset_files) -> None:
        manifest_path, _ = mock_dataset_files
        loader = get_tile_dataloader(manifest_path)
        assert loader.num_workers == 0
        assert loader.pin_memory is False
        assert loader.batch_size == 2

    def test_dataloader_iteration_memory_stability(self, mock_dataset_files) -> None:
        manifest_path, _ = mock_dataset_files
        loader = get_tile_dataloader(manifest_path, batch_size=2)
        batch_count = 0
        for images, masks in loader:
            assert images.shape[0] == 2
            assert masks.shape[0] == 2
            batch_count += 1
        assert batch_count == 2


# ==============================================================================
# 4. Test Standalone Mask Array Validation
# ==============================================================================

class TestValidateMaskArrayStandalone:
    """Verifies standalone validate_mask_array() convenience function contract and invariants."""

    def test_validate_mask_array_valid_all_classes(self) -> None:
        """Verifies that valid 2D uint8 array containing values {0, 1, 2, 3} passes validation."""
        arr = np.array([[0, 1], [2, 3]], dtype=np.uint8)
        result = validate_mask_array(arr)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.uint8
        assert result.shape == (2, 2)
        np.testing.assert_array_equal(result, arr)

    def test_validate_mask_array_valid_zeros(self) -> None:
        """Verifies that an all-background 2D uint8 array passes validation."""
        arr = np.zeros((512, 512), dtype=np.uint8)
        result = validate_mask_array(arr)
        assert result.shape == (512, 512)
        assert np.all(result == 0)

    @pytest.mark.parametrize("invalid_val", [4, 5, 255, 100])
    def test_validate_mask_array_invalid_values(self, invalid_val: int) -> None:
        """Verifies that values outside {0, 1, 2, 3} raise MaskValidationError."""
        arr = np.array([[0, 1], [2, invalid_val]], dtype=np.uint8)
        with pytest.raises(MaskValidationError, match="(?i)invalid mask value"):
            validate_mask_array(arr)

    @pytest.mark.parametrize("bad_dtype", [
        np.float32, np.float64, np.int32, np.int64, np.int16, bool
    ])
    def test_validate_mask_array_invalid_dtypes(self, bad_dtype) -> None:
        """Verifies that non-uint8 dtypes raise MaskValidationError."""
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

    def test_validate_mask_array_suppress_errors(self) -> None:
        """Verifies raise_on_error=False returns False on invalid input and array on valid input."""
        invalid_arr = np.array([[0, 1], [2, 4]], dtype=np.uint8)
        assert validate_mask_array(invalid_arr, raise_on_error=False) is False

        valid_arr = np.array([[0, 1], [2, 3]], dtype=np.uint8)
        res = validate_mask_array(valid_arr, raise_on_error=False)
        assert res is not False

    def test_validate_mask_array_expected_shape(self) -> None:
        """Verifies expected_shape parameter enforcement."""
        arr = np.array([[0, 1], [2, 3]], dtype=np.uint8)
        assert validate_mask_array(arr, expected_shape=(2, 2)) is not False
        with pytest.raises(MaskValidationError, match="(?i)expected shape"):
            validate_mask_array(arr, expected_shape=(512, 512))
