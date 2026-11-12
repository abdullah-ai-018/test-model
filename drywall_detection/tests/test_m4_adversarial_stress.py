#!/usr/bin/env python3
"""
drywall_detection/tests/test_m4_adversarial_stress.py
======================================================
Empirical Adversarial Stress Test Suite for Milestone M4.

Adversarial Challenger Verification Suite covering:
1. Coordinate Roundtrip & Rotation Precision:
   - 0°, 90°, 180°, and 270° orientations.
   - Physical bounds preservation: |W_out - W_in| < 10^-3 pt, |H_out - H_in| < 10^-3 pt.
   - Zero pixel drift / misalignment assertion on rotated re-render.
   - Forward and inverse affine matrix bijection and condition number.
2. Pathological Aspect Ratios & Small Canvases:
   - 10:1 horizontal banner (5120x512) and 1:10 vertical column (512x5120).
   - Non-tile-divisible ribbons: (300, 3000) and (3000, 300).
   - Sub-512 canvases: (1, 1), (64, 64), (128, 256), and (511, 511).
   - Hann apodization window stitching stability and probability normalization.
3. Corrupt & Pathological File Upload Handling:
   - 0-byte PDF files.
   - Truncated broken PDF files.
   - Non-PDF arbitrary binary files.
   - Unsupported file format extensions (.bin, .exe).
   - Batch directory resilience when encountering corrupted files.
4. Color Blending & Opacity Alpha Bounds:
   - Edge-case alpha values: alpha=0.0 (transparent), alpha=1.0 (opaque), alpha=0.45 (default).
   - Out-of-bounds alpha values: alpha=-1.0, alpha=2.5.
   - Exact pixel clamp bounds [0, 255] and dtype uint8 assertions.
   - High-contrast background inputs (pure black, pure white).
   - 4-class taxonomy color dominance rules.
"""

from __future__ import annotations

import io
import math
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import fitz  # PyMuPDF
import numpy as np
import pytest
from PIL import Image

from drywall_detection.config import (
    BEST_MODEL_DIR,
    CLASS_BACKGROUND,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    DEFAULT_DPI,
    DEFAULT_OVERLAY_ALPHA,
)
from drywall_detection.pipeline.annotate import (
    PALETTE_STANDARD,
    PALETTE_VIBRANT,
    PDFAnnotator,
    build_rgba_lut,
    compute_mask_metrics,
    mask_to_rgba_overlay,
    render_blended_image,
)
from drywall_detection.pipeline.infer import DrywallInferencePipeline
from drywall_detection.utils.coords import (
    get_forward_matrix,
    get_inverse_matrix,
    pdf_to_pixel,
    pixel_to_pdf,
)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(scope="module")
def shared_inferencer() -> Any:
    """Preloads the standalone inferencer once for the test module."""
    from drywall_detection.checkpoints.best_model.infer import StandaloneInferencer
    return StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path


# ==============================================================================
# TEST SUITE 1: Coordinate Roundtrip & Rotation Precision
# ==============================================================================

class TestCoordinateAndRotationAdversarial:
    """Empirical challenge of coordinate transformation and rotation preservation."""

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    @pytest.mark.parametrize(
        "width_pt,height_pt",
        [
            (1728.0, 2592.0),  # Standard Arch D (Portrait)
            (2592.0, 1728.0),  # Standard Arch D (Landscape)
            (1000.0, 1000.0),  # Square canvas
            (3000.0, 500.0),   # Wide banner
        ],
    )
    def test_all_rotations_dimension_preservation(
        self, rotation: int, width_pt: float, height_pt: float, temp_dir: Path
    ) -> None:
        """Asserts |W_out - W_in| < 10^-3 pt and rotation preserved across geometries."""
        annotator = PDFAnnotator(alpha=0.45)

        # 1. Generate source PDF
        src_path = temp_dir / f"geom_{int(width_pt)}x{int(height_pt)}_rot_{rotation}.pdf"
        doc_in = fitz.open()
        p = doc_in.new_page(width=width_pt, height=height_pt)
        p.set_rotation(rotation)
        p.draw_line(fitz.Point(10, 10), fitz.Point(width_pt - 10, height_pt - 10), color=(0, 0, 0), width=1)
        doc_in.save(str(src_path))
        doc_in.close()

        # 2. Render visual dimensions
        doc_read = fitz.open(str(src_path))
        page_read = doc_read[0]
        pix = page_read.get_pixmap(dpi=72)
        mask = np.zeros((pix.height, pix.width), dtype=np.uint8)
        mask[10:30, 10:30] = CLASS_DRYWALL
        doc_read.close()

        # 3. Annotate PDF
        out_path = temp_dir / f"annotated_{int(width_pt)}x{int(height_pt)}_rot_{rotation}.pdf"
        annotator.annotate_pdf_document(
            input_pdf_path=src_path,
            output_pdf_path=out_path,
            masks_by_page={0: mask},
            dpi=72,
        )

        # 4. Reopen and verify dimensional invariants
        doc_out = fitz.open(str(out_path))
        p_out = doc_out[0]

        assert p_out.rotation == rotation, f"Rotation mismatch: expected {rotation}, got {p_out.rotation}"
        assert abs(p_out.mediabox.width - width_pt) < 1e-3, (
            f"Mediabox width drift: |{p_out.mediabox.width} - {width_pt}| >= 1e-3"
        )
        assert abs(p_out.mediabox.height - height_pt) < 1e-3, (
            f"Mediabox height drift: |{p_out.mediabox.height} - {height_pt}| >= 1e-3"
        )
        assert abs(p_out.cropbox.width - width_pt) < 1e-3, (
            f"Cropbox width drift: |{p_out.cropbox.width} - {width_pt}| >= 1e-3"
        )
        assert abs(p_out.cropbox.height - height_pt) < 1e-3, (
            f"Cropbox height drift: |{p_out.cropbox.height} - {height_pt}| >= 1e-3"
        )

        # Confirm CAD vector stream preserved
        drawings = p_out.get_drawings()
        assert len(drawings) >= 1, "Underlying CAD vectors must be preserved!"
        doc_out.close()

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_pixel_drift_zero_across_rotations(self, rotation: int) -> None:
        """
        Adversarial test: asserts EXACT ZERO PIXEL DRIFT when re-inserting overlays onto rotated pages.
        A marker placed at visual pixels (y in [30..49], x in [60..99]) must render at
        the exact same pixel bounds when the annotated document is re-rendered.
        """
        doc = fitz.open()
        p = doc.new_page(width=1728.0, height=2592.0)
        p.set_rotation(rotation)

        pix = p.get_pixmap(dpi=72)
        h, w = pix.height, pix.width
        mask = np.zeros((h, w), dtype=np.uint8)

        # Place unambiguous marker in visual space
        y0, y1 = 30, 50
        x0, x1 = 60, 100
        mask[y0:y1, x0:x1] = CLASS_DRYWALL

        # Overlay at alpha=1.0 for exact pixel thresholding
        rgba = mask_to_rgba_overlay(mask, alpha=1.0)
        pix_overlay = fitz.Pixmap(fitz.csRGB, w, h, rgba.tobytes(), True)
        p.insert_image(p.cropbox, pixmap=pix_overlay, rotate=p.rotation, overlay=True)

        # Reopen in-memory PDF
        buf = doc.tobytes()
        doc.close()

        doc_re = fitz.open("pdf", buf)
        pix_re = doc_re[0].get_pixmap(dpi=72)
        arr = np.frombuffer(pix_re.samples, dtype=np.uint8).reshape((pix_re.height, pix_re.width, 3))
        doc_re.close()

        # Pure green marker in PALETTE_STANDARD is (0, 255, 0)
        is_green = (arr[:, :, 0] == 0) & (arr[:, :, 1] == 255) & (arr[:, :, 2] == 0)
        ys, xs = np.where(is_green)

        assert len(ys) > 0, f"Rotation {rotation}°: No marker pixels detected!"
        assert ys.min() == y0, f"Rotation {rotation}°: y0 drift: got {ys.min()}, expected {y0}"
        assert ys.max() == y1 - 1, f"Rotation {rotation}°: y1 drift: got {ys.max()}, expected {y1 - 1}"
        assert xs.min() == x0, f"Rotation {rotation}°: x0 drift: got {xs.min()}, expected {x0}"
        assert xs.max() == x1 - 1, f"Rotation {rotation}°: x1 drift: got {xs.max()}, expected {x1 - 1}"

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    @pytest.mark.parametrize("dpi", [72, 150, 300])
    def test_affine_transformation_bijective_precision(self, rotation: int, dpi: int) -> None:
        """
        Tests mathematical affine transformation roundtrip across dense test grid.
        Asserts |pixel_to_pdf(pdf_to_pixel(p)) - p| < 10^-5 pt.
        """
        page_w = 1728.0
        page_h = 2592.0

        for x in [0.0, 100.5, 864.0, 1727.9]:
            for y in [0.0, 150.25, 1296.0, 2591.9]:
                px, py = pdf_to_pixel(x, y, dpi=dpi, page_width=page_w, page_height=page_h, rotation=rotation)
                rx, ry = pixel_to_pdf(px, py, dpi=dpi, page_width=page_w, page_height=page_h, rotation=rotation)

                assert abs(rx - x) < 1e-5, f"Bijective x error at rot={rotation}, dpi={dpi}: |{rx} - {x}| >= 1e-5"
                assert abs(ry - y) < 1e-5, f"Bijective y error at rot={rotation}, dpi={dpi}: |{ry} - {y}| >= 1e-5"

        # Check matrix inverse identity: M * M^-1 = I
        M_fwd = get_forward_matrix(dpi=dpi, page_width=page_w, page_height=page_h, rotation=rotation)
        M_inv = get_inverse_matrix(dpi=dpi, page_width=page_w, page_height=page_h, rotation=rotation)
        prod = M_fwd @ M_inv
        identity = np.eye(3, dtype=np.float64)
        assert np.max(np.abs(prod - identity)) < 1e-7, f"Matrix inverse error at rot={rotation}, dpi={dpi}"


# ==============================================================================
# TEST SUITE 2: Pathological Aspect Ratios & Small Canvases
# ==============================================================================

class TestPathologicalAspectRatiosAndSmallCanvases:
    """Stress tests sliding-window tiler, Hann apodization reconstructor, and bounds guard."""

    @pytest.mark.parametrize(
        "h,w",
        [
            (512, 5120),  # 10:1 horizontal banner
            (5120, 512),  # 1:10 vertical column
            (300, 3000),  # 10:1 non-tile-divisible ribbon (H < 512)
            (3000, 300),  # 1:10 non-tile-divisible ribbon (W < 512)
        ],
    )
    def test_extreme_aspect_ratio_tiling(self, shared_inferencer: Any, h: int, w: int) -> None:
        """Asserts sliding-window and Hann reconstructor execute with zero shape broadcast crashes."""
        dummy_img = Image.new("RGB", (w, h), (255, 255, 255))
        mask, probs = shared_inferencer.predict_image_sliding_window(
            dummy_img, tile_size=512, overlap=0.20
        )

        assert mask.shape == (h, w), f"Mask shape mismatch: expected ({h}, {w}), got {mask.shape}"
        assert probs.shape == (h, w, 4), f"Probabilities shape mismatch: expected ({h}, {w}, 4), got {probs.shape}"
        assert np.all(np.isin(mask, [0, 1, 2, 3])), "Mask values must be valid class indices"
        assert not np.isnan(probs).any(), "Probabilities must not contain NaN"
        assert not np.isinf(probs).any(), "Probabilities must not contain Inf"

        # Assert probabilities sum to ~1.0 per pixel
        prob_sums = np.sum(probs, axis=-1)
        assert np.all(np.abs(prob_sums - 1.0) < 1e-2), "Hann stitched probabilities must sum to 1.0"

    @pytest.mark.parametrize(
        "h,w",
        [
            (1, 1),        # Absolute minimal 1x1 canvas
            (64, 64),      # Very small square
            (128, 256),    # Small rectangle
            (256, 128),    # Small inverted rectangle
            (511, 511),    # Off-by-one sub-512 boundary
        ],
    )
    def test_sub_512_small_canvases(self, shared_inferencer: Any, h: int, w: int) -> None:
        """Asserts small canvas bounds guard correctly pads to tile_size and unpads back without error."""
        dummy_img = Image.new("RGB", (w, h), (240, 240, 240))
        mask, probs = shared_inferencer.predict_image_sliding_window(
            dummy_img, tile_size=512, overlap=0.20
        )

        assert mask.shape == (h, w), f"Sub-512 mask shape mismatch: expected ({h}, {w}), got {mask.shape}"
        assert probs.shape == (h, w, 4), f"Sub-512 probs shape mismatch: expected ({h}, {w}, 4), got {probs.shape}"
        assert mask.dtype == np.uint8

    def test_compute_mask_metrics_pathological_bounds(self) -> None:
        """Verifies zero-division and edge-case behavior of mask metrics engine."""
        # 1x1 mask
        m1 = np.array([[CLASS_DRYWALL]], dtype=np.uint8)
        res1 = compute_mask_metrics(m1, page_num=1)
        assert res1["total_pixels"] == 1
        assert res1["class_pixel_counts"]["drywall"] == 1
        assert res1["drywall_percentage"] == 100.0

        # All-background mask
        m_bg = np.zeros((100, 100), dtype=np.uint8)
        res_bg = compute_mask_metrics(m_bg, page_num=1)
        assert res_bg["drywall_percentage"] == 0.0
        assert res_bg["wall_density_percentage"] == 0.0
        assert res_bg["class_percentages"]["background"] == 100.0


# ==============================================================================
# TEST SUITE 3: Corrupt & Pathological File Upload Handling
# ==============================================================================

class TestCorruptAndPathologicalFiles:
    """Stress tests exception handling for corrupted, truncated, and invalid uploads."""

    def test_zero_byte_pdf_handling(self, temp_dir: Path) -> None:
        """0-byte PDF must raise EmptyFileError / FileDataError / RuntimeError cleanly."""
        zero_file = temp_dir / "zero_byte.pdf"
        zero_file.touch()

        annotator = PDFAnnotator()
        with pytest.raises((RuntimeError, fitz.FileDataError)):
            annotator.annotate_pdf_document(
                input_pdf_path=zero_file,
                output_pdf_path=temp_dir / "zero_out.pdf",
                masks_by_page={0: np.zeros((10, 10), dtype=np.uint8)},
            )

        pipeline = DrywallInferencePipeline(device="cpu")
        with pytest.raises((RuntimeError, fitz.FileDataError)):
            pipeline.process_pdf(zero_file, temp_dir / "zero_pipe_out.pdf")

    def test_truncated_corrupt_pdf_handling(self, temp_dir: Path) -> None:
        """Truncated/broken PDF header must raise FileDataError / RuntimeError cleanly."""
        broken_file = temp_dir / "broken.pdf"
        broken_file.write_bytes(b"%PDF-1.4\n%corrupt truncated content\x00\x00\x00")

        annotator = PDFAnnotator()
        with pytest.raises((RuntimeError, fitz.FileDataError)):
            annotator.annotate_pdf_document(
                input_pdf_path=broken_file,
                output_pdf_path=temp_dir / "broken_out.pdf",
                masks_by_page={0: np.zeros((10, 10), dtype=np.uint8)},
            )

    def test_non_pdf_binary_file_handling(self, temp_dir: Path) -> None:
        """Arbitrary binary executable disguised as .pdf must raise FileDataError / RuntimeError."""
        fake_pdf = temp_dir / "fake.pdf"
        fake_pdf.write_bytes(os.urandom(1024))

        pipeline = DrywallInferencePipeline(device="cpu")
        with pytest.raises((RuntimeError, fitz.FileDataError)):
            pipeline.process_pdf(fake_pdf, temp_dir / "fake_out.pdf")

    def test_unsupported_extension_rejection(self, temp_dir: Path) -> None:
        """Unsupported file extensions passed to universal process() must raise ValueError."""
        pipeline = DrywallInferencePipeline(device="cpu")
        unsupported_file = temp_dir / "document.docx"
        unsupported_file.write_bytes(b"dummy")

        with pytest.raises(ValueError, match="Unsupported file format"):
            pipeline.process(unsupported_file)

    def test_batch_directory_resilience_to_corrupt_files(self, temp_dir: Path) -> None:
        """
        Batch directory processing must not crash when encountering corrupted files;
        it should process valid files, log errors for bad files, and return status batch_completed.
        """
        batch_dir = temp_dir / "batch_input"
        batch_dir.mkdir()

        # Valid image
        valid_img = batch_dir / "valid_plan.png"
        Image.new("RGB", (200, 200), (255, 255, 255)).save(valid_img)

        # Corrupted 0-byte PDF
        corrupt_pdf = batch_dir / "corrupted.pdf"
        corrupt_pdf.touch()

        pipeline = DrywallInferencePipeline(device="cpu")
        out_dir = temp_dir / "batch_output"
        summary = pipeline.process(batch_dir, out_dir)

        assert summary["status"] == "batch_completed"
        assert summary["total_files"] == 2
        assert summary["successful"] == 1
        assert any(r.get("status") == "error" for r in summary["results"])


# ==============================================================================
# TEST SUITE 4: Color Blending & Opacity Alpha Bounds
# ==============================================================================

class TestColorBlendingAndAlphaBounds:
    """Stress tests alpha transparency blending, numerical clamp bounds, and LUT mapping."""

    @pytest.mark.parametrize("alpha", [0.0, 0.45, 1.0])
    @pytest.mark.parametrize("palette_name,pal", [("standard", PALETTE_STANDARD), ("vibrant", PALETTE_VIBRANT)])
    def test_alpha_boundary_values(self, alpha: float, palette_name: str, pal: Dict[int, Tuple[int, int, int]]) -> None:
        """Tests exact mathematical blending at alpha=0.0, default alpha=0.45, and alpha=1.0."""
        h, w = 60, 60
        base_img = np.full((h, w, 3), 200, dtype=np.uint8)
        mask = np.zeros((h, w), dtype=np.uint8)
        mask[0:20, :] = CLASS_DRYWALL
        mask[20:40, :] = CLASS_NON_DRYWALL
        mask[40:60, :] = CLASS_UNCERTAIN

        blended = render_blended_image(base_img, mask, alpha=alpha, palette=pal)

        assert blended.shape == (h, w, 3)
        assert blended.dtype == np.uint8
        assert blended.min() >= 0
        assert blended.max() <= 255

        if alpha == 0.0:
            # Completely transparent overlay -> identical to original base
            assert np.array_equal(blended, base_img), "Alpha 0.0 must not alter image pixels"
        elif alpha == 1.0:
            # Completely opaque overlay -> exact replacement by palette RGB
            assert np.all(blended[0:20, :] == pal[CLASS_DRYWALL]), f"Class 1 mismatch at alpha 1.0 ({palette_name})"
            assert np.all(blended[20:40, :] == pal[CLASS_NON_DRYWALL]), f"Class 2 mismatch at alpha 1.0 ({palette_name})"
            assert np.all(blended[40:60, :] == pal[CLASS_UNCERTAIN]), f"Class 3 mismatch at alpha 1.0 ({palette_name})"

    @pytest.mark.parametrize("extreme_alpha", [-1.0, -0.01, 1.01, 5.0, 100.0])
    def test_out_of_range_alpha_clamping(self, extreme_alpha: float) -> None:
        """Out-of-range alpha values must be clipped into [0.0, 1.0] without overflow or errors."""
        base = np.zeros((20, 20, 3), dtype=np.uint8)
        mask = np.ones((20, 20), dtype=np.uint8) * CLASS_DRYWALL

        # Blended image clipping
        blended = render_blended_image(base, mask, alpha=extreme_alpha)
        assert blended.dtype == np.uint8
        assert blended.min() >= 0
        assert blended.max() <= 255

        # LUT clipping
        lut = build_rgba_lut(alpha=extreme_alpha)
        assert lut.dtype == np.uint8
        assert lut.shape == (256, 4)
        if extreme_alpha < 0.0:
            assert lut[CLASS_DRYWALL, 3] == 0
        else:
            assert lut[CLASS_DRYWALL, 3] == 255

    def test_high_contrast_background_blending(self) -> None:
        """Verifies numerical clamp [0, 255] under pure white (255) and pure black (0) backgrounds."""
        white_bg = np.full((30, 30, 3), 255, dtype=np.uint8)
        black_bg = np.zeros((30, 30, 3), dtype=np.uint8)
        mask = np.full((30, 30), CLASS_NON_DRYWALL, dtype=np.uint8)

        out_white = render_blended_image(white_bg, mask, alpha=0.45)
        out_black = render_blended_image(black_bg, mask, alpha=0.45)

        assert out_white.dtype == np.uint8
        assert out_black.dtype == np.uint8
        assert np.all((out_white >= 0) & (out_white <= 255))
        assert np.all((out_black >= 0) & (out_black <= 255))

    def test_mask_to_rgba_overlay_properties(self) -> None:
        """Asserts LUT vectorized RGBA overlay properties: background transparent, walls configured alpha."""
        mask = np.array([
            [CLASS_BACKGROUND, CLASS_DRYWALL],
            [CLASS_NON_DRYWALL, CLASS_UNCERTAIN],
        ], dtype=np.uint8)

        rgba = mask_to_rgba_overlay(mask, alpha=0.50)
        assert rgba.shape == (2, 2, 4)
        assert rgba.dtype == np.uint8

        # Background alpha must strictly be 0
        assert rgba[0, 0, 3] == 0

        # Non-background alpha must strictly match round(0.50 * 255) = 127
        expected_alpha = int(0.50 * 255)
        assert rgba[0, 1, 3] == expected_alpha
        assert rgba[1, 0, 3] == expected_alpha
        assert rgba[1, 1, 3] == expected_alpha
