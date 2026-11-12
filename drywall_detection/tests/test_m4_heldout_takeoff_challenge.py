#!/usr/bin/env python3
"""
drywall_detection/tests/test_m4_heldout_takeoff_challenge.py
============================================================
Adversarial Empirical Challenge Suite for Milestone M4:
- Held-Out Architectural Drawings (Sheet A-104 / Usman Markup Page 4)
- Vector Linework & Searchable Text Zero-Drift Overlay Verification
- Multi-Page Streaming & Memory Management (Reclamation / Stability)
- Detail 1A CMU Safety Veto Invariant Enforcement
- Takeoff Dashboard Zero-Division Protection on Non-Floorplan Sheets
"""

from __future__ import annotations

import csv
import gc
import math
import os
from pathlib import Path
import tempfile
from typing import Dict, List, Tuple

import fitz  # PyMuPDF
import numpy as np
import psutil
import pytest
from shapely.geometry import Polygon

from drywall_detection.classification.classifier import (
    ClassifiedWallPolygon,
    DrywallClassifier,
    IntegrityViolationError,
)
from drywall_detection.config import (
    CLASS_BACKGROUND,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    MASTER_PDF_ROTATION_DEG,
)
from drywall_detection.data.ground_truth_builder import GroundTruthBuilder
from drywall_detection.pipeline.annotate import (
    PDFAnnotator,
    compute_mask_metrics,
    mask_to_rgba_overlay,
)

MASTER_PDF_PATH = Path(r"C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf")
USMAN_PDF_PATH = Path(r"C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf")
APPROVED_CSV_PATH = Path("drywall_detection/data/partition_schedule_mapping.approved.csv")


# ==============================================================================
# 1. HELD-OUT SHEET A-104 & USMAN GROUND TRUTH MARKUP EVALUATION
# ==============================================================================

class TestHeldOutSheetA104Preservation:
    """Empirical challenge on held-out architectural drawing Sheet A-104."""

    def test_sheet_a104_rotation_and_dimensions(self) -> None:
        """Verify Sheet A-104 renders with native 90° CW rotation preserved."""
        assert MASTER_PDF_PATH.exists(), f"Master PDF not found at {MASTER_PDF_PATH}"

        doc = fitz.open(str(MASTER_PDF_PATH))
        assert len(doc) >= 18, f"Master PDF has fewer pages than expected: {len(doc)}"

        # Sheet A-104 is Page Index 17 (Page 18 of 71)
        page = doc[17]
        assert page.rotation == 90, f"Expected 90° rotation, got {page.rotation}°"
        assert page.mediabox.width == 1728.0, f"Unexpected width: {page.mediabox.width}"
        assert page.mediabox.height == 2592.0, f"Unexpected height: {page.mediabox.height}"
        assert page.rect.width == 2592.0, f"Unexpected visual width: {page.rect.width}"
        assert page.rect.height == 1728.0, f"Unexpected visual height: {page.rect.height}"

        text = page.get_text()
        assert "A-104" in text, "Sheet identifier A-104 not found in page text"
        assert "FOURTH FLOOR" in text.upper(), "Sheet title Fourth Floor not found in page text"
        doc.close()

    def test_usman_heldout_drywall_annotations_page4(self) -> None:
        """Verify line annotation extraction on Page Index 4 yields exactly 69 verified drywall annotations."""
        assert USMAN_PDF_PATH.exists(), f"Usman PDF not found at {USMAN_PDF_PATH}"

        # 1. Direct PyMuPDF annotation extraction
        doc = fitz.open(str(USMAN_PDF_PATH))
        assert len(doc) >= 5, f"Usman PDF has fewer pages than expected: {len(doc)}"
        page = doc[4]

        annots = list(page.annots() or [])
        line_annots = [a for a in annots if a.type[1] == "Line"]
        square_annots = [a for a in annots if a.type[1] == "Square"]

        assert len(annots) == 138, f"Expected 138 total annotations, got {len(annots)}"
        assert len(line_annots) == 69, f"Expected exactly 69 line annotations, got {len(line_annots)}"
        assert len(square_annots) == 69, f"Expected exactly 69 square tag annotations, got {len(square_annots)}"
        doc.close()

        # 2. Production GroundTruthBuilder extraction
        builder = GroundTruthBuilder()
        extracted = builder.extract_red_centerlines(pdf_path=USMAN_PDF_PATH, page_indices=[4])
        page4_records = extracted.get(4, [])
        assert len(page4_records) == 69, f"GroundTruthBuilder extracted {len(page4_records)} records, expected 69"

    def test_pdf_annotator_overlay_vector_and_text_zero_drift(self) -> None:
        """Verify PDFAnnotator.annotate_pdf_page_overlay preserves 100% vector linework and searchable text."""
        assert MASTER_PDF_PATH.exists()

        doc = fitz.open(str(MASTER_PDF_PATH))
        page = doc[17]

        # Extract pre-annotation vector linework and searchable text
        drawings_before = page.get_drawings()
        text_before = page.get_text()
        drawings_count_before = len(drawings_before)
        text_len_before = len(text_before)

        assert drawings_count_before > 10000, f"Expected rich vector linework, got {drawings_count_before}"
        assert text_len_before > 1000, f"Expected rich text layer, got {text_len_before}"

        # Construct a synthetic multi-class segmentation mask
        h_px, w_px = int(page.rect.height), int(page.rect.width)
        mask = np.zeros((h_px // 2, w_px // 2), dtype=np.uint8)
        mask[100:300, 100:300] = CLASS_DRYWALL
        mask[400:600, 400:600] = CLASS_NON_DRYWALL
        mask[700:900, 700:900] = CLASS_UNCERTAIN

        annotator = PDFAnnotator(alpha=0.45)
        annotator.annotate_pdf_page_overlay(page, mask)

        # Extract post-annotation linework and text
        drawings_after = page.get_drawings()
        text_after = page.get_text()

        # Assert zero vector or text drift
        assert len(drawings_after) == drawings_count_before, (
            f"Vector linework was altered! Before: {drawings_count_before}, After: {len(drawings_after)}"
        )
        assert text_after == text_before, "Searchable text layer was corrupted or shifted!"
        assert page.rotation == 90, f"Page rotation was altered: {page.rotation}"
        assert page.mediabox.width == 1728.0 and page.mediabox.height == 2592.0
        doc.close()


# ==============================================================================
# 2. MULTI-PAGE STREAMING & MEMORY RECLAMATION STABILITY
# ==============================================================================

class TestMultiPageStreamingAndMemoryStability:
    """Stress tests multi-page document streaming and memory stability."""

    def test_multipage_streaming_synthetic_all_rotations(self) -> None:
        """Stream annotations across synthetic multi-page document with 0°, 90°, 180°, 270° rotations."""
        proc = psutil.Process(os.getpid())
        gc.collect()
        rss_start_mb = proc.memory_info().rss / (1024 * 1024)

        doc = fitz.open()
        rotations = [0, 90, 180, 270]
        for rot in rotations:
            page = doc.new_page(width=1728, height=2592)
            page.set_rotation(rot)
            shape = page.new_shape()
            shape.draw_rect(fitz.Rect(100, 100, 600, 600))
            shape.finish(color=(0, 0, 0), fill=(0.9, 0.9, 0.9))
            shape.commit()

        with tempfile.TemporaryDirectory() as tmp_dir:
            in_pdf = Path(tmp_dir) / "synthetic_multi.pdf"
            out_pdf = Path(tmp_dir) / "synthetic_annotated.pdf"
            doc.save(str(in_pdf))
            doc.close()

            annotator = PDFAnnotator(alpha=0.40)
            masks = {
                p: np.random.choice([0, 1, 2, 3], size=(600, 400), p=[0.7, 0.1, 0.1, 0.1]).astype(np.uint8)
                for p in range(len(rotations))
            }

            res = annotator.annotate_pdf_document(in_pdf, out_pdf, masks)
            assert res["annotated_pages"] == 4
            assert out_pdf.exists()
            assert out_pdf.stat().st_size > 0

            # Verify output orientations
            doc_out = fitz.open(str(out_pdf))
            assert len(doc_out) == 4
            for p_idx, exp_rot in enumerate(rotations):
                assert doc_out[p_idx].rotation == exp_rot
                assert len(doc_out[p_idx].get_images()) >= 1
            doc_out.close()

        gc.collect()
        rss_end_mb = proc.memory_info().rss / (1024 * 1024)
        rss_delta_mb = rss_end_mb - rss_start_mb
        # Memory growth must remain strictly bounded (< 60 MB)
        assert rss_delta_mb < 60.0, f"Excessive memory growth detected: {rss_delta_mb:.2f} MB"

    def test_multipage_streaming_master_pdf_pages(self) -> None:
        """Stream annotations across first 3 pages of master 71-page PDF."""
        assert MASTER_PDF_PATH.exists()

        proc = psutil.Process(os.getpid())
        gc.collect()
        rss_start_mb = proc.memory_info().rss / (1024 * 1024)

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_pdf = Path(tmp_dir) / "master_3page_annotated.pdf"
            annotator = PDFAnnotator(alpha=0.45)
            masks = {
                0: np.zeros((800, 600), dtype=np.uint8),
                1: np.zeros((800, 600), dtype=np.uint8),
                2: np.zeros((800, 600), dtype=np.uint8),
            }
            masks[0][100:200, 100:200] = CLASS_DRYWALL
            masks[1][150:250, 150:250] = CLASS_NON_DRYWALL
            masks[2][200:300, 200:300] = CLASS_UNCERTAIN

            res = annotator.annotate_pdf_document(MASTER_PDF_PATH, out_pdf, masks)
            assert res["annotated_pages"] == 3
            assert out_pdf.exists()

            doc_out = fitz.open(str(out_pdf))
            assert len(doc_out) == 71  # All pages preserved
            for p in range(3):
                assert len(doc_out[p].get_images()) >= 1
            doc_out.close()

        gc.collect()
        rss_end_mb = proc.memory_info().rss / (1024 * 1024)
        rss_delta_mb = rss_end_mb - rss_start_mb
        assert rss_delta_mb < 80.0, f"Memory leak in master streaming: {rss_delta_mb:.2f} MB"


# ==============================================================================
# 3. DETAIL 1A CMU SAFETY VETO INVARIANT
# ==============================================================================

class TestDetail1ACMUSafetyVeto:
    """Verifies mandatory safety veto protecting Detail 1A CMU from being classified as Drywall."""

    def test_approved_schedule_detail_1a_mapped_to_nondrywall(self) -> None:
        """Query partition_schedule_mapping.approved.csv and verify Detail 1A is Non-Drywall."""
        assert APPROVED_CSV_PATH.exists(), f"Approved CSV not found at {APPROVED_CSV_PATH}"

        with open(APPROVED_CSV_PATH, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            records = {row["tag"].strip(): row for row in reader}

        assert "1A" in records, "Tag 1A missing from approved partition schedule!"
        rec_1a = records["1A"]
        assert rec_1a["proposed_class"] == "Non-Drywall", (
            f"Detail 1A must be classified as Non-Drywall, found {rec_1a['proposed_class']}"
        )
        assert "CMU" in rec_1a["description"].upper(), "Detail 1A description must identify CMU masonry block"
        assert rec_1a["material_trade"].lower() == "masonry"

    def test_runtime_veto_raises_integrity_violation_error(self) -> None:
        """Assert that ClassifiedWallPolygon raises IntegrityViolationError when Tag 1A is tagged Drywall."""
        dummy_poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])

        # 1. Direct "Drywall" classification violation
        with pytest.raises(IntegrityViolationError) as exc_info:
            ClassifiedWallPolygon(
                wall_id="wall_cmu_fail",
                page_idx=0,
                sheet="A-104",
                geometry_pdf=dummy_poly,
                geometry_pixel=dummy_poly,
                matched_tag="1A",
                detail_number="1A",
                material_description="6\" CMU Block",
                classification="Drywall",
                confidence=1.0,
                color_hex="#00C853",
                reason="Adversarial attack attempting to misclassify CMU as Drywall",
            )
        assert "INTEGRITY VIOLATION" in str(exc_info.value)
        assert "Detail 1A is explicitly 6\" CMU masonry block" in str(exc_info.value)

        # 2. Case-insensitive and synonym violations ("gwb", "gypsum", "sheetrock")
        for bad_class in ["gwb", "GYPSUM", "drywall", "Sheetrock", "1"]:
            with pytest.raises(IntegrityViolationError):
                ClassifiedWallPolygon(
                    wall_id=f"wall_synonym_{bad_class}",
                    page_idx=0,
                    sheet="A-104",
                    geometry_pdf=dummy_poly,
                    geometry_pixel=dummy_poly,
                    matched_tag="1a",  # lowercase check
                    detail_number="1A",
                    material_description="CMU",
                    classification=bad_class,
                    confidence=1.0,
                    color_hex="#00C853",
                    reason="Synonym evasion attempt",
                )

    def test_schedule_ingestion_veto_raises_error(self) -> None:
        """Assert classifier ingestion gate raises IntegrityViolationError if 1A is tampered in CSV."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["tag", "sheet", "detail_title", "description", "material_trade", "proposed_class", "confidence", "notes"])
            # Provide 24 rows but tamper 1A
            writer.writerow(["1A", "A-900", "DETAIL 1A", "6 CMU", "Masonry", "Drywall", "1.0", "Tampered row"])
            for i in range(2, 25):
                writer.writerow([f"T{i}", "A-900", f"DETAIL {i}", "GWB", "Drywall", "Drywall", "1.0", "Valid row"])
            temp_csv = f.name

        try:
            with pytest.raises(IntegrityViolationError) as exc_info:
                DrywallClassifier(approved_schedule_path=temp_csv)
            assert "INTEGRITY VIOLATION" in str(exc_info.value)
        finally:
            if os.path.exists(temp_csv):
                os.remove(temp_csv)


# ==============================================================================
# 4. TAKEOFF DASHBOARD ZERO-DIVISION & EDGE CASE DEFENSE
# ==============================================================================

class TestTakeoffZeroDivisionProtection:
    """Verifies zero-division and edge-case defenses in mask metrics and takeoff dashboard calculations."""

    @pytest.fixture
    def app_module(self) -> Any:
        import drywall_detection.app as app
        return app

    def test_empty_canvas_and_100_percent_background(self, app_module: Any) -> None:
        """Test compute_mask_metrics and compute_takeoff_stats on 100% background canvas."""
        # 1. 100% background mask (e.g. cover sheet or empty room)
        bg_mask = np.zeros((1000, 1000), dtype=np.uint8)

        # Pipeline metrics
        p_metrics = compute_mask_metrics(bg_mask, page_num=1)
        assert p_metrics["class_pixel_counts"]["drywall"] == 0
        assert p_metrics["drywall_percentage"] == 0.0
        assert not math.isnan(p_metrics["drywall_percentage"])
        assert not math.isinf(p_metrics["drywall_percentage"])

        # UI takeoff stats
        u_stats = app_module.compute_takeoff_stats(bg_mask, latency_sec=0.123)
        assert u_stats["total_pixels"] == 1000000
        assert u_stats["drywall_pixels"] == 0
        assert u_stats["wall_total_pixels"] == 0
        assert u_stats["wall_pct_canvas"] == 0.0
        assert u_stats["drywall_pct_walls"] == 0.0
        assert u_stats["non_drywall_pct_walls"] == 0.0
        assert u_stats["uncertain_pct_walls"] == 0.0
        assert not math.isnan(u_stats["drywall_pct_walls"])
        assert not math.isinf(u_stats["drywall_pct_walls"])

    def test_zero_dimension_canvas(self, app_module: Any) -> None:
        """Test zero-dimension canvas (0, 0) handling without ZeroDivisionError."""
        empty_mask = np.zeros((0, 0), dtype=np.uint8)

        # Pipeline metrics
        p_metrics = compute_mask_metrics(empty_mask, dimensions_px=(0, 0))
        assert p_metrics["total_pixels"] == 0
        assert p_metrics["drywall_percentage"] == 0.0
        assert not math.isnan(p_metrics["drywall_percentage"])

        # UI takeoff stats
        u_stats = app_module.compute_takeoff_stats(empty_mask)
        assert u_stats["total_pixels"] == 0
        assert u_stats["wall_total_pixels"] == 0
        assert u_stats["drywall_pct_walls"] == 0.0
        assert u_stats["wall_pct_canvas"] == 0.0

    def test_non_floorplan_sheet_resilience(self, app_module: Any) -> None:
        """Test non-floorplan sheet with only Non-Drywall and Uncertain partitions (0 drywall pixels)."""
        # Synthetic sheet: 10,000 px non-drywall, 5,000 px uncertain, 0 drywall
        mask = np.zeros((500, 500), dtype=np.uint8)
        mask[50:150, 50:150] = CLASS_NON_DRYWALL
        mask[200:250, 200:300] = CLASS_UNCERTAIN

        p_metrics = compute_mask_metrics(mask)
        assert p_metrics["class_pixel_counts"]["drywall"] == 0
        assert p_metrics["drywall_percentage"] == 0.0

        u_stats = app_module.compute_takeoff_stats(mask)
        assert u_stats["drywall_pixels"] == 0
        assert u_stats["drywall_pct_walls"] == 0.0
        assert u_stats["non_drywall_pixels"] == 10000
        assert u_stats["uncertain_pixels"] == 5000
        assert u_stats["wall_total_pixels"] == 15000
        assert round(u_stats["non_drywall_pct_walls"], 2) == 66.67
        assert round(u_stats["uncertain_pct_walls"], 2) == 33.33
