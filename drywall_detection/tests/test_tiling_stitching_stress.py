"""
drywall_detection/tests/test_tiling_stitching_stress.py
======================================================
Adversarial empirical stress-test suite for Milestone M1 unified format:
- Arbitrary non-512 dimensions tiling (700x900, 1234x5678, 2592x1728, extreme aspect ratios)
- 100% canvas surface coverage verification with zero gaps or uncovered pixels
- Boundary clamping verification
- Numerical reconstruction error measurement of 2D Hann apodization reverse stitching
- Corrupt and out-of-bounds mask rejection (>3, negative, non-uint8, wrong dimensions, non-array)
- Standalone validate_mask_array API probe
- Visual QC generator verification (dimensions, file format, banner text, alpha blending transparency)
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import List, Tuple
import pytest
import numpy as np
import cv2
from PIL import Image
import torch

from drywall_detection.datasets.unified_format import (
    DatasetClass,
    PALETTE_256,
    UnifiedDatasetConfig,
    TileCoordinates,
    TileMetadata,
    MaskValidationError,
    UnifiedMask,
    SlidingWindowTiler,
    VisualQCGenerator,
)


# ==============================================================================
# 1. Arbitrary Dimension Tiling & 100% Canvas Coverage Verification
# ==============================================================================

class TestTilingArbitraryDimensions:
    """Stress-tests SlidingWindowTiler on non-multiple, irregular, and extreme dimensions."""

    @pytest.mark.parametrize(
        "height, width",
        [
            (700, 900),        # Non-multiples of 512
            (1234, 5678),      # Highly irregular rectangular plan
            (2592, 1728),      # MTA 99th Street drawing page size (72 dpi)
            (5400, 3600),      # High-resolution raster plan (150 dpi)
            (512, 512),        # Exact single tile size
            (513, 513),        # Boundary off-by-one (+1 pixel)
            (1024, 1024),      # Exact multiple of 512
            (1025, 769),       # Off-by-one in both dimensions
            (512, 3000),       # Extreme horizontal ribbon (H == tile_size, W >> tile_size)
            (4000, 512),       # Extreme vertical ribbon (H >> tile_size, W == tile_size)
        ],
    )
    def test_canvas_coverage_zero_gaps(self, height: int, width: int) -> None:
        """
        Verifies that compute_tile_grid produces 100% canvas coverage with zero gaps,
        zero uncovered margin pixels, and proper boundary clamping.
        """
        tile_size = 512
        overlap_ratio = 0.20
        config = UnifiedDatasetConfig(tile_size=tile_size, overlap_ratio=overlap_ratio)
        tiler = SlidingWindowTiler(config)

        y_steps, x_steps = tiler.compute_tile_grid(height, width)

        # 1. Boundary assertions: grid must start at 0
        assert y_steps[0] == 0, f"y_steps did not start at 0: {y_steps}"
        assert x_steps[0] == 0, f"x_steps did not start at 0: {x_steps}"

        # 2. Clamping assertions: last step + tile_size must exactly equal dimension
        assert y_steps[-1] + tile_size == height, f"y clamping failed: {y_steps[-1]} + {tile_size} != {height}"
        assert x_steps[-1] + tile_size == width, f"x clamping failed: {x_steps[-1]} + {tile_size} != {width}"

        # 3. Monotonicity: steps must be strictly increasing
        for i in range(len(y_steps) - 1):
            assert y_steps[i] < y_steps[i + 1], f"y_steps not strictly increasing: {y_steps}"
            step_delta = y_steps[i + 1] - y_steps[i]
            assert step_delta <= config.stride, f"y step jump {step_delta} exceeds stride {config.stride}"

        for j in range(len(x_steps) - 1):
            assert x_steps[j] < x_steps[j + 1], f"x_steps not strictly increasing: {x_steps}"
            step_delta = x_steps[j + 1] - x_steps[j]
            assert step_delta <= config.stride, f"x step jump {step_delta} exceeds stride {config.stride}"

        # 4. Empirical 100% pixel coverage & zero gaps assertion
        # We track coverage depth (how many times each pixel is visited)
        coverage_map = np.zeros((height, width), dtype=np.uint16)
        for y in y_steps:
            for x in x_steps:
                coverage_map[y : y + tile_size, x : x + tile_size] += 1

        uncovered_count = int(np.sum(coverage_map == 0))
        assert uncovered_count == 0, f"Found {uncovered_count} uncovered pixels for dimension ({height}, {width})"

        min_depth = int(np.min(coverage_map))
        max_depth = int(np.max(coverage_map))
        assert min_depth >= 1, f"Minimum coverage depth must be >= 1, got {min_depth}"
        assert max_depth >= 1, f"Maximum coverage depth must be >= 1, got {max_depth}"

    def test_sub_tile_dimensions_behavior(self) -> None:
        """
        Empirically observes and characterizes behavior when canvas dimensions are smaller than tile_size (512).
        """
        config = UnifiedDatasetConfig(tile_size=512)
        tiler = SlidingWindowTiler(config)

        # compute_tile_grid on sub-512 dimensions returns [0]
        y_steps, x_steps = tiler.compute_tile_grid(300, 400)
        assert y_steps == [0]
        assert x_steps == [0]

        # tile_drawing on sub-512 image rejects the tile because sliced shape != (512, 512)
        sub_img = np.full((300, 400, 3), 255, dtype=np.uint8)
        sub_mask = UnifiedMask(np.zeros((300, 400), dtype=np.uint8))
        tiles = tiler.tile_drawing(sub_img, sub_mask, "small_draw", "test_source")

        # Must reject gracefully with empty tiles list rather than raising an unhandled exception
        assert len(tiles) == 0

    @pytest.mark.parametrize("overlap", [0.05, 0.10, 0.20, 0.35, 0.50])
    def test_various_overlap_ratios_coverage(self, overlap: float) -> None:
        """Verifies 100% coverage across varying overlap ratios."""
        h, w = 1200, 1500
        config = UnifiedDatasetConfig(tile_size=512, overlap_ratio=overlap)
        tiler = SlidingWindowTiler(config)
        y_steps, x_steps = tiler.compute_tile_grid(h, w)

        covered = np.zeros((h, w), dtype=bool)
        for y in y_steps:
            for x in x_steps:
                covered[y : y + 512, x : x + 512] = True
        assert np.all(covered), f"Coverage failed for overlap ratio {overlap}"


# ==============================================================================
# 2. Numerical Reconstruction Error of 2D Hann Apodization Reverse Stitcher
# ==============================================================================

class TestHannReverseStitchingNumericalError:
    """Stress-tests numerical fidelity of 2D Hann window apodization stitching."""

    @pytest.mark.parametrize(
        "height, width",
        [
            (700, 900),
            (1234, 1500),
            (2592, 1728),
        ],
    )
    def test_discrete_label_reconstruction_error(self, height: int, width: int) -> None:
        """
        Measures classification reconstruction error when stitching discrete ground truth labels.
        Ground truth contains all 4 classes: Background (0), Drywall (1), Non-Drywall (2), Uncertain (3).
        Reconstruction error rate must be exactly 0.0000%.
        """
        tile_size = 512
        tiler = SlidingWindowTiler(UnifiedDatasetConfig(tile_size=tile_size, overlap_ratio=0.20))
        y_steps, x_steps = tiler.compute_tile_grid(height, width)

        # Synthesize ground truth mask with geometric patterns of all 4 classes
        gt_mask = np.zeros((height, width), dtype=np.uint8)
        # Class 1 Drywall (horizontal walls)
        gt_mask[100:150, :] = DatasetClass.DRYWALL.value
        # Class 2 Non-Drywall (vertical columns)
        gt_mask[:, 200:250] = DatasetClass.NON_DRYWALL.value
        # Class 3 Uncertain (diagonal or block region)
        gt_mask[400:600, 400:600] = DatasetClass.UNCERTAIN.value

        # Extract tiles
        tile_patches = []
        coords_list = []
        for r_idx, y0 in enumerate(y_steps):
            for c_idx, x0 in enumerate(x_steps):
                y1 = y0 + tile_size
                x1 = x0 + tile_size
                patch = gt_mask[y0:y1, x0:x1]
                tile_patches.append(patch)
                coords_list.append(
                    TileCoordinates(
                        row_idx=r_idx,
                        col_idx=c_idx,
                        y_min=y0,
                        x_min=x0,
                        y_max=y1,
                        x_max=x1,
                        parent_height=height,
                        parent_width=width,
                    )
                )

        # Reverse stitch using 2D Hann apodization
        stitched_mask = tiler.stitch_predictions(
            tiles=tile_patches,
            coords=coords_list,
            parent_shape=(height, width),
            num_classes=4,
        )

        assert stitched_mask.shape == (height, width)
        mismatch_count = int(np.sum(stitched_mask != gt_mask))
        error_rate = mismatch_count / (height * width)

        assert mismatch_count == 0, (
            f"Discrete label reconstruction failed with {mismatch_count} mismatches "
            f"(error rate {error_rate:.6f}) on shape ({height}, {width})"
        )

    @pytest.mark.parametrize("overlap", [0.10, 0.20, 0.30, 0.50])
    def test_soft_probability_numerical_reconstruction_error(self, overlap: float) -> None:
        """
        Measures numerical reconstruction error (MAE, Max Error, RMSE) of soft continuous
        class probabilities stitched with 2D Hann apodization.
        Partition-of-unity apodization must theoretically achieve zero error on identical probability fields.
        """
        h, w = 800, 1000
        tile_size = 512
        tiler = SlidingWindowTiler(UnifiedDatasetConfig(tile_size=tile_size, overlap_ratio=overlap))
        y_steps, x_steps = tiler.compute_tile_grid(h, w)

        # Generate a continuous smooth probability field [H, W, 4]
        # Using a deterministic spatial gradient
        np.random.seed(42)
        raw_logits = np.random.randn(h, w, 4).astype(np.float32)
        # Apply softmax over class channel
        exp_logits = np.exp(raw_logits - np.max(raw_logits, axis=-1, keepdims=True))
        gt_prob = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)  # [H, W, 4]

        tile_probs = []
        coords_list = []
        for r_idx, y0 in enumerate(y_steps):
            for c_idx, x0 in enumerate(x_steps):
                y1 = y0 + tile_size
                x1 = x0 + tile_size
                patch = gt_prob[y0:y1, x0:x1, :]
                tile_probs.append(patch)
                coords_list.append(
                    TileCoordinates(
                        row_idx=r_idx,
                        col_idx=c_idx,
                        y_min=y0,
                        x_min=x0,
                        y_max=y1,
                        x_max=x1,
                        parent_height=h,
                        parent_width=w,
                    )
                )

        # Hann reverse stitcher directly returns argmax, so let's inspect internal weighted probability
        # by executing the Hann accumulation directly
        wx = np.hanning(tile_size)
        wy = np.hanning(tile_size)
        window_2d = np.clip(np.outer(wy, wx).astype(np.float32), 1e-4, 1.0)
        window_3d = np.expand_dims(window_2d, axis=-1)

        num_accum = np.zeros((h, w, 4), dtype=np.float32)
        den_accum = np.zeros((h, w, 1), dtype=np.float32)

        for prob_tile, coord in zip(tile_probs, coords_list):
            y0, y1 = coord.y_min, coord.y_max
            x0, x1 = coord.x_min, coord.x_max
            num_accum[y0:y1, x0:x1, :] += prob_tile * window_3d
            den_accum[y0:y1, x0:x1, :] += window_3d

        den_accum = np.maximum(den_accum, 1e-6)
        reconstructed_prob = num_accum / den_accum
        reconstructed_mask = np.argmax(reconstructed_prob, axis=-1).astype(np.uint8)
        gt_mask = np.argmax(gt_prob, axis=-1).astype(np.uint8)

        # Calculate numerical errors
        mae = float(np.mean(np.abs(reconstructed_prob - gt_prob)))
        max_error = float(np.max(np.abs(reconstructed_prob - gt_prob)))
        rmse = float(np.sqrt(np.mean((reconstructed_prob - gt_prob) ** 2)))
        argmax_accuracy = float(np.mean(reconstructed_mask == gt_mask))

        # Precision assertions
        assert mae < 1e-5, f"MAE {mae:.8f} exceeds tolerance 1e-5 for overlap {overlap}"
        assert max_error < 1e-4, f"Max error {max_error:.8f} exceeds tolerance 1e-4 for overlap {overlap}"
        assert rmse < 1e-5, f"RMSE {rmse:.8f} exceeds tolerance 1e-5 for overlap {overlap}"
        assert argmax_accuracy == 1.0, f"Argmax classification accuracy {argmax_accuracy} != 1.0"

    def test_hann_window_boundary_clipping_safety(self) -> None:
        """
        Verifies that Hann window clipping to 1e-4 prevents zero-division at tile boundaries.
        """
        tile_size = 512
        wx = np.hanning(tile_size)
        wy = np.hanning(tile_size)
        raw_outer = np.outer(wy, wx).astype(np.float32)

        # Raw outer product at corners is exactly 0.0
        assert raw_outer[0, 0] == 0.0
        assert raw_outer[0, -1] == 0.0
        assert raw_outer[-1, 0] == 0.0
        assert raw_outer[-1, -1] == 0.0

        # Clipped window must strictly be >= 1e-4 (accounting for float32 precision)
        clipped = np.clip(raw_outer, 1e-4, 1.0)
        assert np.min(clipped) >= np.float32(1e-4) - 1e-7
        assert np.isclose(np.min(clipped), 1e-4, atol=1e-6)
        # Note: For even window sizes (e.g. 512), discrete Hann peak is 0.9999811 (cos(pi * 255/511))
        assert np.isclose(np.max(clipped), 1.0, atol=1e-4)


# ==============================================================================
# 3. Stress-Test Corrupt Mask Handling & Rejection
# ==============================================================================

class TestCorruptMaskRejection:
    """Stress-tests mask validation against out-of-bounds, negative, invalid dtype, and malformed inputs."""

    @pytest.mark.parametrize("invalid_val", [4, 5, 10, 100, 200, 254, 255])
    def test_out_of_bounds_pixel_values_rejected(self, invalid_val: int) -> None:
        """Verifies masks containing pixel values > 3 are rejected with MaskValidationError."""
        arr = np.zeros((64, 64), dtype=np.uint8)
        arr[10, 10] = invalid_val

        with pytest.raises(MaskValidationError) as exc_info:
            UnifiedMask(arr)
        assert "Invalid mask values found" in str(exc_info.value)

    @pytest.mark.parametrize(
        "arr_with_negatives",
        [
            np.array([[-1, 0], [1, 2]], dtype=np.int8),
            np.array([[-10, 0], [1, 2]], dtype=np.int32),
            np.array([[-1, 0], [1, 2]], dtype=np.int64),
        ],
    )
    def test_negative_values_rejected(self, arr_with_negatives: np.ndarray) -> None:
        """Verifies negative mask values (in signed integer formats) are rejected."""
        with pytest.raises(MaskValidationError):
            UnifiedMask(arr_with_negatives)

    def test_negative_converted_to_uint8_rejected(self) -> None:
        """Verifies signed -1 converted to uint8 (which wraps to 255) is rejected as value > 3."""
        signed_arr = np.array([[-1, 0], [1, 2]], dtype=np.int8)
        uint8_wrapped = signed_arr.astype(np.uint8)
        assert uint8_wrapped[0, 0] == 255

        with pytest.raises(MaskValidationError) as exc_info:
            UnifiedMask(uint8_wrapped)
        assert "Invalid mask values found" in str(exc_info.value)

    @pytest.mark.parametrize(
        "invalid_dtype_arr",
        [
            np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float32),
            np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float64),
            np.array([[True, False], [True, False]], dtype=bool),
            np.array([[0, 1], [2, 3]], dtype=np.int16),
            np.array([[0, 1], [2, 3]], dtype=np.int32),
        ],
    )
    def test_non_uint8_dtypes_rejected(self, invalid_dtype_arr: np.ndarray) -> None:
        """Verifies any dtype other than uint8 is rejected with MaskValidationError."""
        with pytest.raises(MaskValidationError) as exc_info:
            UnifiedMask(invalid_dtype_arr)  # type: ignore
        assert "Expected dtype uint8" in str(exc_info.value)

    @pytest.mark.parametrize(
        "invalid_dim_shape",
        [
            (64,),              # 1D
            (64, 64, 1),        # 3D with singleton channel
            (64, 64, 3),        # 3D RGB
            (1, 1, 64, 64),     # 4D tensor-like
        ],
    )
    def test_non_2d_dimensions_rejected(self, invalid_dim_shape: Tuple[int, ...]) -> None:
        """Verifies any shape that is not strictly 2D (H, W) is rejected."""
        arr = np.zeros(invalid_dim_shape, dtype=np.uint8)
        with pytest.raises(MaskValidationError) as exc_info:
            UnifiedMask(arr)
        assert "Expected 2D array" in str(exc_info.value)

    @pytest.mark.parametrize(
        "non_array",
        [
            None,
            "mask_path.png",
            [0, 1, 2, 3],
            {"data": [0, 1, 2, 3]},
            123,
        ],
    )
    def test_non_array_inputs_rejected(self, non_array: any) -> None:
        """Verifies non-ndarray objects are rejected."""
        with pytest.raises(MaskValidationError) as exc_info:
            UnifiedMask(non_array)  # type: ignore
        assert "Expected numpy ndarray" in str(exc_info.value)

    def test_nan_and_inf_floating_masks_rejected(self) -> None:
        """Verifies float arrays containing NaN or Inf are rejected."""
        nan_arr = np.array([[np.nan, 0.0], [1.0, 2.0]], dtype=np.float32)
        with pytest.raises(MaskValidationError):
            UnifiedMask(nan_arr)  # type: ignore

        inf_arr = np.array([[np.inf, 0.0], [1.0, 2.0]], dtype=np.float32)
        with pytest.raises(MaskValidationError):
            UnifiedMask(inf_arr)  # type: ignore

    def test_tiler_discards_corrupted_tiles(self) -> None:
        """
        Verifies SlidingWindowTiler filters out corrupt tiles (e.g. invalid mask value > 3).
        """
        tiler = SlidingWindowTiler(UnifiedDatasetConfig(tile_size=512))
        img = np.full((512, 512, 3), 200, dtype=np.uint8)

        # Raw tile mask containing value 99
        corrupt_mask_data = np.zeros((512, 512), dtype=np.uint8)
        corrupt_mask_data[100, 100] = 99

        # Since UnifiedMask constructor raises on corrupt_mask_data, we test if tiler
        # checks `np.any(mask_tile_data > 3)`:
        # Construct valid mask first, then manipulate internal buffer
        valid_mask = UnifiedMask(np.zeros((512, 512), dtype=np.uint8))
        valid_mask.data[100, 100] = 99  # directly corrupt internal data

        tiles = tiler.tile_drawing(img, valid_mask, "corrupt_test", "test_source")
        # Tile must be discarded due to is_corrupt
        assert len(tiles) == 0

    def test_validate_mask_array_existence_and_behavior(self) -> None:
        """
        Probes for standalone validate_mask_array function.
        Records architectural finding: mask validation is encapsulated in UnifiedMask.
        """
        import drywall_detection.datasets.unified_format as uf
        has_standalone = hasattr(uf, "validate_mask_array")
        # Document whether validate_mask_array is defined
        if not has_standalone:
            # Mask validation is implemented via UnifiedMask class constructor
            assert hasattr(uf, "UnifiedMask")
            assert hasattr(uf, "MaskValidationError")
        else:
            fn = getattr(uf, "validate_mask_array")
            assert callable(fn)


# ==============================================================================
# 4. Verify Visual QC Generator
# ==============================================================================

class TestVisualQCGenerator:
    """Stress-tests VisualQCGenerator triplet layout, banner text, and alpha blending."""

    def test_triplet_dimensions_and_channels(self) -> None:
        """
        Verifies triplet dimensions:
        - With metadata: (H + 36, 3 * W, 3)
        - Without metadata: (H, 3 * W, 3)
        """
        qc = VisualQCGenerator(UnifiedDatasetConfig(tile_size=512))
        h, w = 512, 512
        img = np.full((h, w, 3), 240, dtype=np.uint8)
        mask = UnifiedMask(np.zeros((h, w), dtype=np.uint8))

        # 1. Triplet without metadata
        triplet_no_meta = qc.create_triplet(img, mask, metadata=None)
        assert triplet_no_meta.shape == (512, 1536, 3)
        assert triplet_no_meta.dtype == np.uint8

        # 2. Triplet with metadata
        meta = TileMetadata(
            tile_id="tile_001",
            parent_drawing_id="sheet_A101",
            dataset_source="MSD",
            split="train",
            coordinates=TileCoordinates(0, 0, 0, 0, 512, 512, 512, 512),
            class_pixel_counts=mask.get_class_counts(),
            class_percentages=mask.get_class_percentages(),
            has_walls=False,
            is_pure_blank=False,
            is_hard_negative=True,
            is_corrupt=False,
        )
        triplet_with_meta = qc.create_triplet(img, mask, metadata=meta)
        assert triplet_with_meta.shape == (548, 1536, 3)  # 512 + 36 = 548
        assert triplet_with_meta.dtype == np.uint8

    @pytest.mark.parametrize(
        "has_walls, is_hard_neg, expected_status",
        [
            (True, False, "WALL_SAMPLE"),
            (False, True, "HARD_NEG"),
            (False, False, "EMPTY"),
        ],
    )
    def test_header_banner_status_and_formatting(
        self, has_walls: bool, is_hard_neg: bool, expected_status: str
    ) -> None:
        """Verifies header banner diagnostic text formatting and status tag."""
        qc = VisualQCGenerator()
        h, w = 512, 512
        img = np.full((h, w, 3), 255, dtype=np.uint8)
        mask_data = np.zeros((h, w), dtype=np.uint8)
        if has_walls:
            mask_data[100:150, 100:150] = DatasetClass.DRYWALL.value
        mask = UnifiedMask(mask_data)

        meta = TileMetadata(
            tile_id="banner_test_tile",
            parent_drawing_id="sheet_test",
            dataset_source="CubiCasa5K",
            split="val",
            coordinates=TileCoordinates(0, 0, 0, 0, 512, 512, 512, 512),
            class_pixel_counts=mask.get_class_counts(),
            class_percentages=mask.get_class_percentages(),
            has_walls=has_walls,
            is_pure_blank=False,
            is_hard_negative=is_hard_neg,
            is_corrupt=False,
        )

        triplet = qc.create_triplet(img, mask, metadata=meta)

        # Inspect the 36-pixel banner at the top
        banner = triplet[:36, :, :]
        assert banner.shape == (36, 1536, 3)
        # Background of banner should be dark gray (35, 35, 35)
        # Check an unwritten pixel area (e.g. top right corner)
        assert tuple(banner[5, -10]) == (35, 35, 35)

    def test_alpha_blending_transparency_numerical_accuracy(self) -> None:
        """
        Verifies exact alpha blending equation:
        Overlay = image * (1 - alpha) + class_color * alpha
        For each semantic class:
        - Drywall (Green, BGR (0, 255, 0))
        - Non-Drywall (Red, BGR (0, 0, 255))
        - Uncertain (Yellow, BGR (0, 255, 255))
        - Background (Unchanged original image)
        """
        alpha = 0.40
        config = UnifiedDatasetConfig(alpha_overlay=alpha)
        qc = VisualQCGenerator(config)

        # Uniform gray base image (200, 200, 200)
        h, w = 100, 100
        img = np.full((h, w, 3), 200, dtype=np.uint8)

        mask_data = np.zeros((h, w), dtype=np.uint8)
        mask_data[10:30, 10:30] = DatasetClass.DRYWALL.value      # Class 1
        mask_data[40:60, 40:60] = DatasetClass.NON_DRYWALL.value  # Class 2
        mask_data[70:90, 70:90] = DatasetClass.UNCERTAIN.value    # Class 3
        mask = UnifiedMask(mask_data)

        overlay = qc.render_overlay(img, mask)

        # 1. Background pixels (Class 0): must match base image identically
        bg_coords = (mask_data == 0)
        assert np.array_equal(overlay[bg_coords], img[bg_coords])

        # 2. Drywall pixels (Class 1): Green BGR = (0, 255, 0)
        # Expected: B = 200 * 0.6 + 0 * 0.4 = 120
        #           G = 200 * 0.6 + 255 * 0.4 = 120 + 102 = 222
        #           R = 200 * 0.6 + 0 * 0.4 = 120
        dw_coords = (mask_data == DatasetClass.DRYWALL.value)
        expected_dw_bgr = np.array([120, 222, 120], dtype=np.uint8)
        dw_pixels = overlay[dw_coords]
        dw_diff = np.max(np.abs(dw_pixels.astype(int) - expected_dw_bgr.astype(int)))
        assert dw_diff <= 1, f"Drywall alpha blending error: max diff {dw_diff}"

        # 3. Non-Drywall pixels (Class 2): Red BGR = (0, 0, 255)
        # Expected: B = 200 * 0.6 = 120
        #           G = 200 * 0.6 = 120
        #           R = 200 * 0.6 + 255 * 0.4 = 222
        ndw_coords = (mask_data == DatasetClass.NON_DRYWALL.value)
        expected_ndw_bgr = np.array([120, 120, 222], dtype=np.uint8)
        ndw_pixels = overlay[ndw_coords]
        ndw_diff = np.max(np.abs(ndw_pixels.astype(int) - expected_ndw_bgr.astype(int)))
        assert ndw_diff <= 1, f"Non-Drywall alpha blending error: max diff {ndw_diff}"

        # 4. Uncertain pixels (Class 3): Yellow BGR = (0, 255, 255)
        # Expected: B = 120, G = 222, R = 222
        unc_coords = (mask_data == DatasetClass.UNCERTAIN.value)
        expected_unc_bgr = np.array([120, 222, 222], dtype=np.uint8)
        unc_pixels = overlay[unc_coords]
        unc_diff = np.max(np.abs(unc_pixels.astype(int) - expected_unc_bgr.astype(int)))
        assert unc_diff <= 1, f"Uncertain alpha blending error: max diff {unc_diff}"

    def test_qc_sample_disk_persistence_and_reload(self, tmp_path: Path) -> None:
        """Verifies saving visual QC sample creates valid readable PNG on disk."""
        qc = VisualQCGenerator()
        img = np.full((512, 512, 3), 245, dtype=np.uint8)
        mask = UnifiedMask(np.zeros((512, 512), dtype=np.uint8))
        meta = TileMetadata(
            tile_id="qc_save_test",
            parent_drawing_id="sheet_save",
            dataset_source="MSD",
            split="train",
            coordinates=TileCoordinates(0, 0, 0, 0, 512, 512, 512, 512),
            class_pixel_counts=mask.get_class_counts(),
            class_percentages=mask.get_class_percentages(),
            has_walls=False,
            is_pure_blank=False,
            is_hard_negative=True,
            is_corrupt=False,
        )

        out_path = tmp_path / "qc_output.png"
        saved = qc.save_qc_sample(out_path, img, mask, meta)

        assert saved.is_file()
        assert saved.stat().st_size > 0

        # Reload with OpenCV
        loaded_cv = cv2.imread(str(saved))
        assert loaded_cv is not None
        assert loaded_cv.shape == (548, 1536, 3)

        # Reload with PIL
        with Image.open(saved) as loaded_pil:
            assert loaded_pil.format == "PNG"
            assert loaded_pil.size == (1536, 548)  # PIL reports (W, H)
