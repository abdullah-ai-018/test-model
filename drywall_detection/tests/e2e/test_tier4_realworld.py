"""
drywall_detection.tests.e2e.test_tier4_realworld
===============================================
Tier 4: 5 Real-World Workload Scenarios.

Exercises complete multi-feature end-to-end workflows on:
- Scenario 1: MTA Drawing Set Ingestion & Sheet A-101 Extraction
- Scenario 2: High-Res Sliding-Window Tiling & Hann Window Apodization Re-Assembly
- Scenario 3: Checkpoint Reload from checkpoints/best_model/ & Offline CPU Inference
- Scenario 4: Streamlit PDF Processing, Preview Rendering & Vector-Preserving Export
- Scenario 5: Held-Out Sheet A-104 & External Permit Drawing Takeoff Challenge
"""

from __future__ import annotations

import io
import json
import math
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Dict, List, Tuple

import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import pytest
from shapely.geometry import Polygon
import torch

from drywall_detection.app import (
    build_annotated_pdf_bytes,
    build_takeoff_csv_str,
    compute_takeoff_stats,
)
from drywall_detection.checkpoints.best_model.infer import (
    StandaloneInferencer,
    create_hann_window,
)
from drywall_detection.classification import (
    ClassificationClass,
    ClassifiedWallPolygon,
    DrywallClassifier,
    IntegrityViolationError,
)
from drywall_detection.config import (
    APPROVED_SCHEDULE_CSV_PATH,
    BEST_MODEL_DIR,
    CLASS_BACKGROUND,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    DEFAULT_DPI,
    MASTER_PDF_ROTATION_DEG,
    REPORTS_DIR,
)
from drywall_detection.data.ground_truth_builder import GroundTruthBuilder
from drywall_detection.models.metrics import SegmentationMetricTracker
from drywall_detection.pipeline.annotate import (
    PALETTE_STANDARD,
    PALETTE_VIBRANT,
    PDFAnnotator,
    compute_mask_metrics,
    mask_to_rgba_overlay,
)
from drywall_detection.pipeline.infer import DrywallInferencePipeline
from drywall_detection.pipeline.router import ModalityRouter, PipelineModality
from drywall_detection.vector.extractor import (
    ExtractedWallCandidate,
    VectorExtractor,
)
from drywall_detection.vector.schedule_parser import PartitionScheduleParser
from drywall_detection.vector.spatial_matcher import SpatialMatcher

MASTER_PDF_PATH = Path(r"C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf")
USMAN_PDF_PATH = Path(r"C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf")
SPARK_PDF_PATH = Path("drywall_detection/data/annotated_spark_test.pdf")


# ==============================================================================
# TIER 4: REAL-WORLD WORKLOAD SCENARIOS (5 TESTS)
# ==============================================================================

def test_tier4_scenario1_mta_full_set_sheet_a101_ingestion() -> None:
    """166. Scenario 1: Full 71-Page MTA Drawing Set Ingestion & Sheet A-101 Extraction
    Features: F4 (Inventory & Mining), F6 (Coordinate Alignment), F11 (Inference Pipeline).
    """
    if not MASTER_PDF_PATH.exists():
        pytest.skip(f"Master PDF not found at {MASTER_PDF_PATH}")

    doc = fitz.open(str(MASTER_PDF_PATH))
    assert len(doc) == 71, f"Expected 71 pages, found {len(doc)}"

    # Sheet A-101 is Page Index 14 (Page 15 of 71)
    page_14 = doc[14]
    assert page_14.rotation == 90
    assert page_14.mediabox.width == 1728.0
    assert page_14.mediabox.height == 2592.0
    text_content = page_14.get_text()
    assert "A-101" in text_content

    # Run vector extractor on page 14
    extractor = VectorExtractor()
    profile = extractor.analyze_page(page_14)
    assert profile.path_count > 1000

    # Extract wall candidates and tags
    walls = extractor.extract_walls(page_14)
    tags = extractor.extract_tags(page_14)
    assert len(walls) > 0
    assert len(tags) > 0

    # Match and assert zero hallucination (unassigned walls strictly Uncertain)
    matcher = SpatialMatcher()
    result = matcher.match(walls=walls, tags=tags)
    assert len(result.assignments) == len(walls)
    classifier = DrywallClassifier(schedule_csv=APPROVED_SCHEDULE_CSV_PATH)

    for assign in result.assignments:
        cls_name = classifier.get_class(assign.matched_tag)
        if assign.matched_tag is None:
            assert cls_name == "Uncertain"
    doc.close()


def test_tier4_scenario2_highres_tiling_hann_reassembly() -> None:
    """167. Scenario 2: High-Res Sliding-Window Tiling & Hann Window Apodization Re-Assembly
    Features: F2 (Dataset Preparation), F11 (Inference Pipeline).
    """
    canvas_w, canvas_h = 1024, 1024
    test_img = Image.new("RGB", (canvas_w, canvas_h), color=(255, 255, 255))

    inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
    mask, norm_probs = inferencer.predict_image_sliding_window(
        test_img,
        tile_size=512,
        overlap=0.20,
    )

    assert mask.shape == (canvas_h, canvas_w)
    assert norm_probs.shape == (4, canvas_h, canvas_w)
    # Check that norm_probs sum to ~1.0 across classes
    prob_sums = np.sum(norm_probs, axis=0)
    assert np.allclose(prob_sums, 1.0, atol=1e-3)


def test_tier4_scenario3_model_reload_and_cpu_inference() -> None:
    """168. Scenario 3: Checkpoint Reload from checkpoints/best_model/ & Offline CPU Inference
    Features: F10 (Checkpoint Delivery), F11 (Inference Pipeline).
    """
    inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
    assert inferencer.config.get("num_classes") == 4

    test_input = Image.new("RGB", (512, 512), color=(240, 240, 240))
    t0 = time.time()
    mask, probs = inferencer.predict_image_sliding_window(test_input, tile_size=512, overlap=0.0)
    latency = time.time() - t0

    assert latency < 5.0, f"Latency {latency:.2f}s exceeded 5.0s ceiling"
    assert mask.shape == (512, 512)
    assert set(np.unique(mask)).issubset({0, 1, 2, 3})


def test_tier4_scenario4_streamlit_preview_and_annotated_export() -> None:
    """169. Scenario 4: Streamlit PDF Processing, Preview Rendering & Vector-Preserving Export
    Features: F11 (Inference Pipeline), F12 (Streamlit Local Interface).
    """
    doc = fitz.open()
    page = doc.new_page(width=800, height=600)
    page.insert_text(fitz.Point(100, 100), "Searchable Architectural Linework Text", fontsize=12)
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(100, 150, 500, 160))
    shape.finish(color=(0, 0, 0))
    shape.commit()
    orig_bytes = doc.tobytes()
    doc.close()

    mask = np.zeros((600, 800), dtype=np.uint8)
    mask[150:160, 100:500] = CLASS_DRYWALL
    stats = compute_takeoff_stats(mask)
    assert stats["drywall_pixels"] == 4000
    assert stats["drywall_pct"] > 0.0

    annotated_bytes = build_annotated_pdf_bytes(orig_bytes, page_idx=0, mask_uint8=mask, alpha=0.45)
    res_doc = fitz.open(stream=annotated_bytes, filetype="pdf")
    res_page = res_doc[0]
    assert "Searchable Architectural Linework Text" in res_page.get_text()
    assert len(res_page.get_images()) >= 1
    res_doc.close()


def test_tier4_scenario5_heldout_a104_and_spark_permit_takeoff() -> None:
    """170. Scenario 5: Held-Out Sheet A-104 & External Permit Drawing Takeoff Challenge
    Features: F5 (Classification Guardrails), F13 (Held-Out Validation), F15 (Documentation).
    """
    # 1. Verify Sheet A-104 against Usman markups
    if USMAN_PDF_PATH.exists():
        builder = GroundTruthBuilder()
        extracted = builder.extract_red_centerlines(pdf_path=USMAN_PDF_PATH, page_indices=[4])
        assert len(extracted.get(4, [])) == 69

    # 2. Ingest Spark Lake Grove external permit drawing
    assert SPARK_PDF_PATH.exists()
    doc = fitz.open(str(SPARK_PDF_PATH))
    router = ModalityRouter()
    decision = router.evaluate_page(doc[0])
    assert decision.modality == PipelineModality.RASTER_ML
    doc.close()

    # 3. Enforce strict 4-class taxonomy and Detail 1A CMU veto
    classifier = DrywallClassifier(schedule_csv=APPROVED_SCHEDULE_CSV_PATH)
    assert classifier.get_class("1A") == "Non-Drywall"

    # 4. Takeoff report consistency
    showcase_path = REPORTS_DIR / "FINAL_SHOWCASE_REPORT.md"
    assert showcase_path.exists()
    report_text = showcase_path.read_text(encoding="utf-8")
    assert "SPARK" in report_text.upper()
    assert "CMU" in report_text
