#!/usr/bin/env python3
"""
drywall_detection/tests/test_pipeline.py
=======================================
Test Suite for Architectural PDF Inference & Annotation Pipeline (Milestone M4).

Covers:
1. PDF Loading and Dimension Metadata Extraction
2. Coordinate and Multi-Quadrant Rotation Preservation Roundtrip
3. Small-Canvas Bounds and Extreme Aspect Ratio Handling
4. 4-Class Color Mapping and Detail 1A CMU Safety Veto
5. End-to-End PDF Annotation & CLI JSON Execution
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import fitz  # PyMuPDF
import numpy as np
import pytest
from PIL import Image

from drywall_detection.config import (
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
from drywall_detection.pipeline.infer import (
    DrywallInferencePipeline,
    build_cli_parser,
    parse_page_arg,
)


# ==============================================================================
# TEST FIXTURES
# ==============================================================================

@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provides an isolated temporary directory for test artifacts."""
    return tmp_path


@pytest.fixture
def synthetic_single_page_pdf(temp_dir: Path) -> Path:
    """Creates a synthetic 1-page vector PDF (2592 x 1728 pt)."""
    pdf_path = temp_dir / "synthetic_arch_d.pdf"
    doc = fitz.open()
    page = doc.new_page(width=2592.0, height=1728.0)

    # Draw some CAD-like vector lines
    page.draw_line(fitz.Point(100, 100), fitz.Point(2400, 100), color=(0, 0, 0), width=2)
    page.draw_line(fitz.Point(100, 100), fitz.Point(100, 1600), color=(0, 0, 0), width=2)
    page.draw_rect(fitz.Rect(300, 300, 1500, 1200), color=(0, 0, 0), width=1.5)
    page.insert_text(fitz.Point(320, 340), "SAMPLE ROOM 101 - ARCH D", fontsize=24)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def synthetic_multipage_pdf(temp_dir: Path) -> Path:
    """Creates a synthetic 3-page PDF with mixed rotations (0°, 90°, 270°)."""
    pdf_path = temp_dir / "synthetic_multipage.pdf"
    doc = fitz.open()

    # Page 0: 0° rotation
    p0 = doc.new_page(width=2592.0, height=1728.0)
    p0.set_rotation(0)
    p0.insert_text(fitz.Point(100, 100), "PAGE 0 (0°)", fontsize=20)

    # Page 1: 90° clockwise rotation
    p1 = doc.new_page(width=1728.0, height=2592.0)
    p1.set_rotation(90)
    p1.insert_text(fitz.Point(100, 100), "PAGE 1 (90° CW)", fontsize=20)

    # Page 2: 270° clockwise rotation
    p2 = doc.new_page(width=1728.0, height=2592.0)
    p2.set_rotation(270)
    p2.insert_text(fitz.Point(100, 100), "PAGE 2 (270° CW)", fontsize=20)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


# ==============================================================================
# TEST CLASS 1: PDF Loading and Metadata Extraction
# ==============================================================================

class TestPDFLoadingAndMetadata:
    """Tests PDF ingestion, dimension extraction, and multi-DPI scaling."""

    def test_load_single_page_pdf(self, synthetic_single_page_pdf: Path) -> None:
        doc = fitz.open(str(synthetic_single_page_pdf))
        assert len(doc) == 1
        page = doc[0]
        assert abs(page.mediabox.width - 2592.0) < 1e-3
        assert abs(page.mediabox.height - 1728.0) < 1e-3
        assert page.rotation == 0
        doc.close()

    def test_load_multipage_pdf(self, synthetic_multipage_pdf: Path) -> None:
        doc = fitz.open(str(synthetic_multipage_pdf))
        assert len(doc) == 3
        assert doc[0].rotation == 0
        assert doc[1].rotation == 90
        assert doc[2].rotation == 270
        doc.close()

    def test_render_dpi_scaling(self, synthetic_single_page_pdf: Path) -> None:
        doc = fitz.open(str(synthetic_single_page_pdf))
        page = doc[0]

        for test_dpi in (72, 150):
            zoom = test_dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            expected_w = int(round(page.rect.width * zoom))
            expected_h = int(round(page.rect.height * zoom))
            assert abs(pix.width - expected_w) <= 1
            assert abs(pix.height - expected_h) <= 1

        doc.close()


# ==============================================================================
# TEST CLASS 2: Coordinate & Rotation Preservation Roundtrip
# ==============================================================================

class TestCoordinateAndRotationPreservation:
    """Validates that annotations preserve physical dimensions, aspect ratio, and rotation."""

    def test_roundtrip_dimension_preservation(
        self, synthetic_single_page_pdf: Path, temp_dir: Path
    ) -> None:
        doc_in = fitz.open(str(synthetic_single_page_pdf))
        orig_w = doc_in[0].mediabox.width
        orig_h = doc_in[0].mediabox.height
        orig_rot = doc_in[0].rotation
        doc_in.close()

        # Create dummy mask matching 150 DPI render
        w_px = int(round(orig_w * 150.0 / 72.0))
        h_px = int(round(orig_h * 150.0 / 72.0))
        mask = np.zeros((h_px, w_px), dtype=np.uint8)
        mask[100:300, 100:300] = CLASS_DRYWALL

        annotator = PDFAnnotator(alpha=0.45)
        out_pdf = temp_dir / "annotated_roundtrip.pdf"
        annotator.annotate_pdf_document(
            input_pdf_path=synthetic_single_page_pdf,
            output_pdf_path=out_pdf,
            masks_by_page={0: mask},
            dpi=150,
        )

        doc_out = fitz.open(str(out_pdf))
        assert len(doc_out) == 1
        p_out = doc_out[0]

        # Dimension preservation invariant: delta < 0.001 pt
        assert abs(p_out.mediabox.width - orig_w) < 1e-3
        assert abs(p_out.mediabox.height - orig_h) < 1e-3
        assert p_out.rotation == orig_rot

        # Underlying vector drawings preserved
        drawings = p_out.get_drawings()
        assert len(drawings) > 0, "Underlying CAD vectors must not be destroyed!"
        doc_out.close()

    def test_page_rotation_preservation(self, temp_dir: Path) -> None:
        """Asserts out_page.rotation == in_page.rotation across all 4 orientations (0°, 90°, 180°, 270°)."""
        annotator = PDFAnnotator(alpha=0.45)

        for rot in (0, 90, 180, 270):
            pdf_path = temp_dir / f"test_rot_{rot}.pdf"
            doc = fitz.open()
            page = doc.new_page(width=1728.0, height=2592.0)
            page.set_rotation(rot)
            doc.save(str(pdf_path))
            doc.close()

            # Render visual dimensions
            doc = fitz.open(str(pdf_path))
            p = doc[0]
            zoom = 72.0 / 72.0
            pix = p.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            mask = np.zeros((pix.height, pix.width), dtype=np.uint8)
            mask[10:50, 10:50] = CLASS_NON_DRYWALL
            doc.close()

            out_pdf = temp_dir / f"annotated_rot_{rot}.pdf"
            annotator.annotate_pdf_document(
                input_pdf_path=pdf_path,
                output_pdf_path=out_pdf,
                masks_by_page={0: mask},
                dpi=72,
            )

            doc_reopen = fitz.open(str(out_pdf))
            p_reopen = doc_reopen[0]
            assert p_reopen.rotation == rot, f"Rotation {rot}° failed to roundtrip!"
            assert abs(p_reopen.cropbox.width - 1728.0) < 1e-3
            assert abs(p_reopen.cropbox.height - 2592.0) < 1e-3
            doc_reopen.close()


# ==============================================================================
# TEST CLASS 3: Small-Canvas & Extreme Aspect Ratio Bounds
# ==============================================================================

class TestSmallCanvasAndAspectRatios:
    """Verifies that sliding-window and pipeline tiling handle non-standard shapes."""

    def test_sub_512_canvas_handling(self) -> None:
        from drywall_detection.checkpoints.best_model.infer import StandaloneInferencer

        inferencer = StandaloneInferencer(device="cpu")
        sub_sizes = [(64, 64), (128, 256), (256, 256), (511, 511)]

        for h, w in sub_sizes:
            dummy_img = Image.new("RGB", (w, h), (255, 255, 255))
            mask, probs = inferencer.predict_image_sliding_window(dummy_img, tile_size=512)
            assert mask.shape == (h, w), f"Expected shape ({h}, {w}), got {mask.shape}"
            assert probs.shape == (h, w, 4), f"Expected probs ({h}, {w}, 4), got {probs.shape}"

    def test_extreme_aspect_ratio_ribbons(self) -> None:
        from drywall_detection.checkpoints.best_model.infer import StandaloneInferencer

        inferencer = StandaloneInferencer(device="cpu")
        # Extreme ribbons: wide horizontal and tall vertical
        ribbons = [(200, 2000), (2000, 200)]

        for h, w in ribbons:
            dummy_img = Image.new("RGB", (w, h), (255, 255, 255))
            mask, probs = inferencer.predict_image_sliding_window(dummy_img, tile_size=512, overlap=0.20)
            assert mask.shape == (h, w), f"Expected ({h}, {w}), got {mask.shape}"
            assert probs.shape == (h, w, 4)


# ==============================================================================
# TEST CLASS 4: Color Mapping & Detail 1A CMU Safety Veto
# ==============================================================================

class TestColorMappingAndSafetyVeto:
    """Verifies standard 4-class taxonomy color dominance and Detail 1A safety veto."""

    def test_color_taxonomy_dominance(self) -> None:
        for palette_name, pal in [("standard", PALETTE_STANDARD), ("vibrant", PALETTE_VIBRANT)]:
            # Drywall: Green dominant
            c1 = pal[CLASS_DRYWALL]
            assert c1[1] > c1[0] and c1[1] > c1[2], f"{palette_name}: Drywall must be green-dominant"

            # Non-Drywall: Red dominant
            c2 = pal[CLASS_NON_DRYWALL]
            assert c2[0] > c2[1] and c2[0] > c2[2], f"{palette_name}: Non-Drywall must be red-dominant"

            # Uncertain: Yellow (both Red and Green high, Blue low)
            c3 = pal[CLASS_UNCERTAIN]
            assert c3[0] >= 180 and c3[1] >= 180 and c3[2] <= 80, f"{palette_name}: Uncertain must be yellow"

            # Background: Transparent in LUT
            lut = build_rgba_lut(alpha=0.45, palette=pal)
            assert lut[CLASS_BACKGROUND, 3] == 0, "Background alpha must be 0 (100% transparent)"
            assert lut[CLASS_DRYWALL, 3] == int(0.45 * 255)

    def test_detail_1a_cmu_safety_veto(self) -> None:
        """
        Integrity Rule: Detail 1A (6" FIRE RATED CMU) must ALWAYS be Non-Drywall (Class 2),
        NEVER Drywall (Class 1).
        """
        approved_csv = Path(__file__).resolve().parent.parent / "data" / "partition_schedule_mapping.approved.csv"
        if approved_csv.exists():
            with open(approved_csv, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                detail_1a_rows = [r for r in reader if r.get("tag", "").strip() == "1A"]
                assert len(detail_1a_rows) >= 1, "Tag 1A must be present in approved partition schedule mapping."
                for r in detail_1a_rows:
                    proposed = r.get("proposed_class", "").strip()
                    assert proposed == "Non-Drywall", f"Integrity Violation: Tag 1A has proposed_class={proposed}"
                    assert proposed != "Drywall", "Integrity Violation: Tag 1A must never be Drywall!"


# ==============================================================================
# TEST CLASS 5: End-to-End PDF Annotation & CLI JSON Execution
# ==============================================================================

class TestEndToEndPDFAnnotation:
    """Verifies end-to-end PDF annotation, deflated file sizing, and CLI interface."""

    def test_pdf_annotation_reopen_visual_check(
        self, synthetic_single_page_pdf: Path, temp_dir: Path
    ) -> None:
        annotator = PDFAnnotator(alpha=0.45)
        out_pdf = temp_dir / "annotated_e2e.pdf"

        mask = np.zeros((360, 540), dtype=np.uint8)
        mask[50:150, 50:150] = CLASS_DRYWALL
        mask[200:300, 200:300] = CLASS_NON_DRYWALL

        res = annotator.annotate_pdf_document(
            input_pdf_path=synthetic_single_page_pdf,
            output_pdf_path=out_pdf,
            masks_by_page={0: mask},
            dpi=150,
        )

        assert res["annotated_pages"] == 1
        assert out_pdf.exists()
        assert res["file_size_kb"] > 0

        # Reopen and check image overlay count
        doc = fitz.open(str(out_pdf))
        p = doc[0]
        images = p.get_images()
        assert len(images) >= 1, "Annotated PDF must contain overlay image XObject"
        doc.close()

    def test_cli_pipeline_execution(self, temp_dir: Path) -> None:
        """Executes CLI pipeline on mock floor plan image, verifying exit code 0 and structured JSON."""
        mock_img = temp_dir / "test_floorplan.png"
        img = Image.new("RGB", (600, 600), (255, 255, 255))
        img.save(mock_img)

        out_img = temp_dir / "test_floorplan_annotated.png"
        json_out = temp_dir / "summary.json"

        cmd = [
            sys.executable,
            "-m",
            "drywall_detection.pipeline.infer",
            "--input",
            str(mock_img),
            "--output",
            str(out_img),
            "--json-output",
            str(json_out),
            "--quiet",
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 0, f"CLI failed with stderr:\n{proc.stderr}"
        assert out_img.exists()
        assert json_out.exists()

        # Parse output JSON
        with open(json_out, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["status"] == "success"
        assert data["type"] == "image"
        assert "aggregate_statistics" in data
        assert "pages" in data
        assert data["pages"][0]["dimensions_px"] == [600, 600]
