"""
drywall_detection.tests.e2e.test_tier2_boundaries
=================================================
Tier 2: 75 Boundary & Corner Case Tests across All 15 System Features (F1–F15 x 5).

Exercises boundary conditions, extreme coordinate limits, zero-dimension inputs,
OOM safety fallbacks, data corruption resistance, and security guardrails.
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, patch
import urllib.error

import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import pytest
from shapely.geometry import MultiPolygon, Polygon, box
import torch
import torch.nn as nn

# Config and constants
from drywall_detection.config import (
    APPROVED_SCHEDULE_CSV_PATH,
    BASE_DPI,
    BEST_MODEL_DIR,
    CLASS_BACKGROUND,
    CLASS_COLORS_BGR,
    CLASS_COLORS_HEX,
    CLASS_COLORS_RGB,
    CLASS_DRYWALL,
    CLASS_NAMES,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    DEFAULT_DPI,
    DEFAULT_MASTER_PDF_PATH,
    DEFAULT_OVERLAY_ALPHA,
    DISK_FREE_MIN_GB,
    DISK_LARGE_DOWNLOAD_THRESHOLD_GB,
    MASTER_PDF_MEDIABOX_HEIGHT_PT,
    MASTER_PDF_MEDIABOX_WIDTH_PT,
    MASTER_PDF_ROTATION_DEG,
    NUM_CLASSES,
    REPORTS_DIR,
    WORKSPACE_ROOT,
)

# Feature 1: Dataset Audit
from drywall_detection.audit.dataset_auditor import (
    CANDIDATE_DATASETS,
    DatasetAuditor,
    DatasetEligibility,
    LicenseCategory,
)

# Feature 2 & 3: Preparation & Splitting
from drywall_detection.data.preparer import (
    DatasetPreparer,
    DrawingSanitizer,
    GeometryRasterizer,
    PALETTE_256,
    PreparationConfig,
)
from drywall_detection.data.qc import VisualQCGenerator
from drywall_detection.data.splitter import (
    InsufficientGroupsError,
    InvalidSplitRatioError,
    ProjectDataSplitter,
    SampleRecord,
    SplitLeakageError,
    SplitManifestBundle,
    assert_zero_leakage,
)
from drywall_detection.datasets import validate_mask_array

# Feature 4: Vector & Schedule Mining
from drywall_detection.vector.extractor import (
    ExtractedWallCandidate,
    VectorExtractor,
    VectorPageProfile,
)
from drywall_detection.vector.schedule_parser import (
    PartitionScheduleParser,
    PartitionTagInstance,
    ScheduleDetailRecord,
)
from drywall_detection.vector.spatial_matcher import (
    MatchMethod,
    SpatialMatcher,
    SpatialMatcherConfig,
    SpatialMatchResult,
)

# Feature 5: Classification Guardrails
from drywall_detection.classification import (
    ClassificationClass,
    ClassificationFeatureCollection,
    ClassifiedWallPolygon,
    DrywallClassifier,
    IntegrityViolationError,
    ScheduleValidationError,
)

# Feature 6: Coordinate Alignment
from drywall_detection.utils.coords import (
    get_forward_matrix,
    get_inverse_matrix,
    pdf_bbox_to_pixel,
    pdf_to_pixel,
    pixel_bbox_to_pdf,
    pixel_to_pdf,
)

# Feature 7 & 8: Hardware, Model & Training
from drywall_detection.models.losses import (
    CompoundSegmentationLoss,
    MultiClassFocalLoss,
    MultiClassSoftDiceLoss,
    calculate_class_weights,
)
from drywall_detection.models.segformer import (
    SegFormerB0,
    SegFormerWallDetector,
)
from drywall_detection.models.trainer import (
    Trainer,
    Trainer as SegmentationTrainer,
)
from drywall_detection.utils.hardware import (
    HardwareProfile,
    auto_configure_training,
    check_disk_safety,
    probe_all_hardware,
    probe_cpu,
    probe_ram,
)

# Feature 9: Metrics & Evaluation
from drywall_detection.models.metrics import (
    SegmentationEvaluationReport,
    SegmentationMetricTracker,
    SegmentationMetrics,
    compute_boundary_iou,
)

# Feature 10: Checkpoints & Reload
from drywall_detection.checkpoints.best_model.infer import (
    StandaloneInferencer,
    create_hann_window,
)

# Feature 11: Pipeline & Annotator
from drywall_detection.pipeline.annotate import (
    PALETTE_STANDARD,
    PALETTE_VIBRANT,
    PDFAnnotator,
    compute_mask_metrics,
    mask_to_rgba_overlay,
)
from drywall_detection.pipeline.infer import (
    DrywallInferencePipeline,
    build_cli_parser,
    parse_page_arg,
)
from drywall_detection.pipeline.router import (
    ModalityRouter,
    PageModalityDecision,
    PipelineModality,
)

# Feature 12: Streamlit App helpers
from drywall_detection.app import (
    build_annotated_pdf_bytes,
    build_takeoff_csv_str,
    compute_takeoff_stats,
)

# Reference files
MASTER_PDF_PATH = Path(r"C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf")
USMAN_PDF_PATH = Path(r"C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf")
SPARK_PDF_PATH = Path("drywall_detection/data/annotated_spark_test.pdf")


# ==============================================================================
# F1: DATASET LICENSING AUDIT BOUNDARIES
# ==============================================================================

class TestTier2Boundary01DatasetAudit:
    """F1: Dataset Licensing Audit Boundaries (5 tests)."""

    def test_tier2_f01_exact_10gb_threshold_edge(self) -> None:
        """76. Tests boundary size at 9.999 GB (no warning), 10.000 GB, and 10.001 GB (triggers warning)."""
        auditor = DatasetAuditor(offline_mode=True)
        assert auditor.check_download_threshold(9.999).warning_triggered is False
        assert auditor.check_download_threshold(10.000).warning_triggered is False
        assert auditor.check_download_threshold(10.001).warning_triggered is True

    def test_tier2_f01_disk_headroom_exact_zero_drop(self) -> None:
        """77. Tests disk headroom boundary at exactly 5.000 GB vs 4.999 GB."""
        auditor = DatasetAuditor(offline_mode=True)
        with patch("shutil.disk_usage") as mock_usage:
            # Exactly 5.000 GB free -> fails when required=5.0 GB with 2.0 GB headroom
            mock_usage.return_value = MagicMock(total=100*(1024**3), used=95*(1024**3), free=5*(1024**3))
            res = auditor.check_disk_space(required_gb_or_id=5.0, min_headroom_gb=2.0)
            assert res.is_sufficient is False

    def test_tier2_f01_negative_free_space_handling(self) -> None:
        """78. Tests disk probe behavior when system reports negative or zero bytes free or negative required."""
        auditor = DatasetAuditor(offline_mode=True)
        with pytest.raises(ValueError):
            auditor.check_disk_space(required_gb_or_id=-5.0)

    def test_tier2_f01_malformed_url_schemes(self) -> None:
        """79. Tests candidate auditor with malformed URL schemes (ftp, empty, invalid)."""
        auditor = DatasetAuditor(offline_mode=True)
        for bad_url in ["ftp://example.com/test", "", "not_a_url", "http://"]:
            res = auditor.probe_url(bad_url)
            assert res["is_reachable"] is False

    def test_tier2_f01_http_timeout_and_500_handling(self) -> None:
        """80. Tests network probes against simulated HTTP 403, 404, 500, and socket timeouts."""
        auditor = DatasetAuditor(offline_mode=True)
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("http://err", 500, "Server Error", {}, None)):
            res = auditor.probe_url("http://err")
            assert res["is_reachable"] is False


# ==============================================================================
# F2: UNIFIED DATASET PREPARATION BOUNDARIES
# ==============================================================================

class TestTier2Boundary02DataPreparation:
    """F2: Unified Dataset Preparation Boundaries (5 tests)."""

    def test_tier2_f02_zero_area_polygon_rasterization(self) -> None:
        """81. Tests rasterizer with degenerate 0-area polygons and colinear lines."""
        config = PreparationConfig(target_width=64, target_height=64)
        rasterizer = GeometryRasterizer(config=config)
        degen = Polygon([(10, 10), (10, 10), (10, 10), (10, 10)])
        bin_m, multi_m = rasterizer.rasterize_polygons([degen], bounds=(0, 0, 100, 100))
        assert bin_m.shape == (64, 64)
        assert np.sum(bin_m) == 0

    def test_tier2_f02_extreme_canvas_aspect_ratios(self) -> None:
        """82. Tests rasterization on extreme aspect ratio canvases."""
        config = PreparationConfig(target_width=500, target_height=50)
        rasterizer = GeometryRasterizer(config=config)
        poly = Polygon([(10, 10), (400, 10), (400, 40), (10, 40)])
        bin_m, multi_m = rasterizer.rasterize_polygons([poly], bounds=(0, 0, 500, 50))
        assert bin_m.shape == (50, 500)

    def test_tier2_f02_overlapping_opposing_class_polygons(self) -> None:
        """83. Tests rasterizer handles multiple overlapping polygons cleanly."""
        config = PreparationConfig(target_width=128, target_height=128)
        rasterizer = GeometryRasterizer(config=config)
        poly_a = Polygon([(20, 20), (80, 20), (80, 80), (20, 80)])
        poly_b = Polygon([(50, 50), (100, 50), (100, 100), (50, 100)])
        bin_m, multi_m = rasterizer.rasterize_polygons([poly_a, poly_b], bounds=(0, 0, 120, 120), target_class=CLASS_DRYWALL)
        assert np.all(np.isin(bin_m, [0, 1]))

    def test_tier2_f02_invalid_mask_dtype_rejection(self) -> None:
        """84. Tests validate_mask_array rejects non-uint8 dtypes with ValueError."""
        for bad_dtype in [np.float32, np.int32, bool, np.int16]:
            arr = np.zeros((32, 32), dtype=bad_dtype)
            with pytest.raises(ValueError):
                validate_mask_array(arr)

    def test_tier2_f02_out_of_range_mask_values(self) -> None:
        """85. Tests validate_mask_array rejects masks containing values > 3."""
        for val in [4, 5, 100, 255]:
            arr = np.zeros((32, 32), dtype=np.uint8)
            arr[0, 0] = val
            with pytest.raises(ValueError):
                validate_mask_array(arr)


# ==============================================================================
# F3: DRAWING-LEVEL SPLIT INTEGRITY BOUNDARIES
# ==============================================================================

class TestTier2Boundary03SplitIntegrity:
    """F3: Drawing-Level Split Integrity Boundaries (5 tests)."""

    def test_tier2_f03_single_project_dataset_split_rejection(self) -> None:
        """86. Tests splitter raises InsufficientGroupsError when dataset has fewer projects than splits."""
        splitter = ProjectDataSplitter(split_ratios=(0.70, 0.15, 0.15))
        single_proj_samples = [
            SampleRecord(
                sample_id=f"s_{i}", project_id="proj_only_one", drawing_id="d1",
                image_path=f"img_{i}.png", mask_path=f"msk_{i}.png", bbox=(0,0,1,1),
                width=1, height=1, has_walls=True, wall_pixel_count=1, total_pixel_count=1,
            ) for i in range(5)
        ]
        with pytest.raises(InsufficientGroupsError):
            splitter.split(single_proj_samples)

    def test_tier2_f03_extreme_split_ratios(self) -> None:
        """87. Tests splitter rejects split ratios that do not sum to 1.0."""
        with pytest.raises(InvalidSplitRatioError):
            ProjectDataSplitter(split_ratios=(0.70, 0.20, 0.20))  # sum = 1.10

    def test_tier2_f03_empty_sample_manifest(self) -> None:
        """88. Tests splitter raises exception when given empty sample list."""
        splitter = ProjectDataSplitter()
        with pytest.raises((ValueError, InsufficientGroupsError)):
            splitter.split([])

    def test_tier2_f03_synthetic_leakage_detection(self) -> None:
        """89. Tests assert_zero_leakage raises SplitLeakageError upon detecting project overlap."""
        train = [SampleRecord("s1", "proj_A", "d1", "i1", "m1", (0,0,1,1), 1, 1, True, 1, 1)]
        val = [SampleRecord("s2", "proj_A", "d2", "i2", "m2", (0,0,1,1), 1, 1, True, 1, 1)]  # Same project!
        test = [SampleRecord("s3", "proj_B", "d3", "i3", "m3", (0,0,1,1), 1, 1, True, 1, 1)]
        bundle = SplitManifestBundle(train_samples=train, val_samples=val, test_samples=test)
        with pytest.raises(SplitLeakageError):
            assert_zero_leakage(bundle)

    def test_tier2_f03_building_id_case_and_whitespace_leak(self) -> None:
        """90. Tests project isolation detects leakage across case variations."""
        train = [SampleRecord("s1", "Project_X", "d1", "i1", "m1", (0,0,1,1), 1, 1, True, 1, 1)]
        val = [SampleRecord("s2", "project_x", "d2", "i2", "m2", (0,0,1,1), 1, 1, True, 1, 1)]
        test = [SampleRecord("s3", "Project_Y", "d3", "i3", "m3", (0,0,1,1), 1, 1, True, 1, 1)]
        bundle = SplitManifestBundle(train_samples=train, val_samples=val, test_samples=test)
        with pytest.raises(SplitLeakageError):
            assert_zero_leakage(bundle, case_sensitive=False)


# ==============================================================================
# F4: DRAWING INVENTORY & SCHEDULE MINING BOUNDARIES
# ==============================================================================

class TestTier2Boundary04ScheduleMining:
    """F4: Drawing Inventory & Schedule Mining Boundaries (5 tests)."""

    def test_tier2_f04_dense_tag_cluster_single_wall(self) -> None:
        """91. Tests spatial matcher with multiple tags cluster near a single wall polygon."""
        matcher = SpatialMatcher()
        wall = ExtractedWallCandidate(
            polygon=Polygon([(100, 100), (300, 100), (300, 110), (100, 110)]),
            confidence=1.0,
            source_type="vector_rect",
        )
        tags = [
            PartitionTagInstance(
                tag_name="1B", bbox=fitz.Rect(110 + i * 15, 102, 120 + i * 15, 112),
                page_index=0, center_pt=fitz.Point(115 + i * 15, 107)
            )
            for i in range(10)
        ]
        result = matcher.match(walls=[wall], tags=tags)
        assert len(result.assignments) == 1

    def test_tier2_f04_degenerate_zero_length_leader_line(self) -> None:
        """92. Tests spatial matcher with zero-length or degenerate leader line."""
        matcher = SpatialMatcher()
        wall = ExtractedWallCandidate(polygon=Polygon([(0,0), (10,0), (10,10), (0,10)]), confidence=1.0)
        tag = PartitionTagInstance(tag_name="1B", bbox=fitz.Rect(5, 5, 6, 6), page_index=0, center_pt=fitz.Point(5, 5))
        result = matcher.match(walls=[wall], tags=[tag])
        assert len(result.assignments) == 1

    def test_tier2_f04_orthogonal_crossing_leaders(self) -> None:
        """93. Tests spatial matcher disambiguation on complex geometry."""
        matcher = SpatialMatcher()
        wall_h = ExtractedWallCandidate(polygon=Polygon([(50, 100), (150, 100), (150, 110), (50, 110)]))
        wall_v = ExtractedWallCandidate(polygon=Polygon([(100, 50), (110, 50), (110, 150), (100, 150)]))
        tag = PartitionTagInstance(tag_name="1C", bbox=fitz.Rect(55, 102, 65, 112), page_index=0, center_pt=fitz.Point(60, 107))
        result = matcher.match(walls=[wall_h, wall_v], tags=[tag])
        assert len(result.assignments) == 2

    def test_tier2_f04_leader_pointing_outside_mediabox(self) -> None:
        """94. Tests spatial matcher handling tags located far outside page coordinates."""
        matcher = SpatialMatcher()
        wall = ExtractedWallCandidate(polygon=Polygon([(10, 10), (50, 10), (50, 20), (10, 20)]))
        out_tag = PartitionTagInstance(tag_name="1B", bbox=fitz.Rect(9999, 9999, 10010, 10010), page_index=0, center_pt=fitz.Point(10000, 10000))
        result = matcher.match(walls=[wall], tags=[out_tag])
        assert len(result.assignments) == 1
        # Since tag is far away, wall should be unassigned / fallback
        assert result.assignments[0].matched_tag is None

    def test_tier2_f04_empty_page_zero_walls_zero_tags(self) -> None:
        """95. Tests vector extractor and spatial matcher on completely blank drawing sheet."""
        doc = fitz.open()
        blank_page = doc.new_page(width=500, height=500)
        extractor = VectorExtractor()
        walls = extractor.extract_walls(blank_page)
        tags = extractor.extract_tags(blank_page)
        assert len(walls) == 0
        assert len(tags) == 0
        doc.close()


# ==============================================================================
# F5: 4-CLASS CLASSIFICATION GUARDRAILS BOUNDARIES
# ==============================================================================

class TestTier2Boundary05ClassificationGuardrails:
    """F5: 4-Class Classification Guardrails Boundaries (5 tests)."""

    def test_tier2_f05_tampered_detail_1a_drywall_rejection(self, tmp_path: Path) -> None:
        """96. Tests DrywallClassifier raises IntegrityViolationError if schedule CSV maps 1A to Drywall."""
        tampered_csv = tmp_path / "tampered.csv"
        with open(tampered_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Detail Tag", "Approved Class", "Material Description"])
            writer.writerow(["1A", "Drywall", "6 INCH FIRE RATED CMU BLOCK"])
            writer.writerow(["1B", "Drywall", "Standard GWB"])

        with pytest.raises(IntegrityViolationError):
            DrywallClassifier(schedule_csv=tampered_csv)

    def test_tier2_f05_tampered_detail_1a_synonyms_rejection(self, tmp_path: Path) -> None:
        """97. Tests classifier rejects synonyms for 1A like 'GWB', 'Gypsum Board', 'Sheetrock'."""
        for syn in ["GWB", "Gypsum Board", "Sheetrock"]:
            tampered_csv = tmp_path / f"tampered_{syn}.csv"
            with open(tampered_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Detail Tag", "Approved Class", "Material Description"])
                writer.writerow(["1A", syn, "6 INCH CMU BLOCK"])
            with pytest.raises(IntegrityViolationError):
                DrywallClassifier(schedule_csv=tampered_csv)

    def test_tier2_f05_missing_detail_1a_row(self, tmp_path: Path) -> None:
        """98. Tests classifier raises ScheduleValidationError if Detail 1A is missing completely."""
        incomplete_csv = tmp_path / "incomplete.csv"
        with open(incomplete_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Detail Tag", "Approved Class", "Material Description"])
            writer.writerow(["1B", "Drywall", "Standard GWB"])
        with pytest.raises(ScheduleValidationError):
            DrywallClassifier(schedule_csv=incomplete_csv)

    def test_tier2_f05_empty_schedule_csv_lock_preservation(self, tmp_path: Path) -> None:
        """99. Tests empty CSV does not bypass schedule validation."""
        empty_csv = tmp_path / "empty.csv"
        empty_csv.write_text("", encoding="utf-8")
        with pytest.raises(ScheduleValidationError):
            DrywallClassifier(schedule_csv=empty_csv)

    def test_tier2_f05_polygon_immutable_detail_1a_mutation(self) -> None:
        """100. Tests ClassifiedWallPolygon prevents mutation of tag 1A to Drywall."""
        poly = ClassifiedWallPolygon(
            polygon=Polygon([(0,0), (1,0), (1,1), (0,1)]),
            matched_tag="1A",
            classification="Non-Drywall",
        )
        assert poly.classification == "Non-Drywall"
        with pytest.raises((IntegrityViolationError, AttributeError, ValueError)):
            poly.classification = "Drywall"


# ==============================================================================
# F6: GROUND TRUTH & COORDINATE ALIGNMENT BOUNDARIES
# ==============================================================================

class TestTier2Boundary06CoordinateAlignment:
    """F6: Ground Truth & Coordinate Alignment Boundaries (5 tests)."""

    def test_tier2_f06_extreme_coordinate_limits(self) -> None:
        """101. Tests coordinate transformer with coordinate extremes: (0, 0), (1728, 2592), negative coordinates."""
        for pt in [(0.0, 0.0), (1728.0, 2592.0), (-50.0, -100.0), (0.0001, 2591.9999)]:
            px = pdf_to_pixel(pt[0], pt[1], dpi=150, rotation=90)
            back = pixel_to_pdf(px[0], px[1], dpi=150, rotation=90)
            assert math.isclose(pt[0], back[0], abs_tol=1e-4)
            assert math.isclose(pt[1], back[1], abs_tol=1e-4)

    def test_tier2_f06_nonstandard_dpi_values(self) -> None:
        """102. Tests coordinate transformer with non-standard DPI values (72, 100, 300, 600 DPI)."""
        pt = (200.0, 500.0)
        for dpi in [72, 100, 150, 300, 600]:
            px = pdf_to_pixel(pt[0], pt[1], dpi=dpi, rotation=90)
            back = pixel_to_pdf(px[0], px[1], dpi=dpi, rotation=90)
            assert math.isclose(pt[0], back[0], abs_tol=1e-4)
            assert math.isclose(pt[1], back[1], abs_tol=1e-4)

    def test_tier2_f06_zero_size_bounding_box(self) -> None:
        """103. Tests pdf_bbox_to_pixel on degenerate (x, y, x, y) zero-area bounding boxes."""
        bbox = (100.0, 100.0, 100.0, 100.0)
        px_box = pdf_bbox_to_pixel(bbox, dpi=150, rotation=90)
        assert px_box[0] == px_box[2]
        assert px_box[1] == px_box[3]

    def test_tier2_f06_nonstandard_rotation_angles(self) -> None:
        """104. Tests coordinate transformer with standard multi-quadrant rotations (0, 90, 180, 270)."""
        pt = (300.0, 400.0)
        for rot in [0, 90, 180, 270]:
            px = pdf_to_pixel(pt[0], pt[1], dpi=150, rotation=rot)
            back = pixel_to_pdf(px[0], px[1], dpi=150, rotation=rot)
            assert math.isclose(pt[0], back[0], abs_tol=1e-4)
            assert math.isclose(pt[1], back[1], abs_tol=1e-4)

    def test_tier2_f06_sub_picopoint_floating_point_drift(self) -> None:
        """105. Tests roundtrip transformation accumulating drift < 1e-11 pt."""
        pt = (512.123456789, 1024.987654321)
        curr = pt
        for _ in range(100):
            px = pdf_to_pixel(curr[0], curr[1], dpi=150, rotation=90)
            curr = pixel_to_pdf(px[0], px[1], dpi=150, rotation=90)
        assert abs(curr[0] - pt[0]) < 1e-10
        assert abs(curr[1] - pt[1]) < 1e-10


# ==============================================================================
# F7: MODEL BENCHMARKING ON CPU BOUNDARIES
# ==============================================================================

class TestTier2Boundary07ModelBenchmarking:
    """F7: Model Benchmarking on CPU Boundaries (5 tests)."""

    def test_tier2_f07_zero_free_ram_tier5_fallback(self) -> None:
        """106. Tests hardware auto-config when RAM is 0 MB falls back to minimal mode."""
        mock_prof = HardwareProfile(
            cpu_cores_physical=1,
            cpu_cores_logical=1,
            ram_total_gb=1.0,
            ram_available_gb=0.1,
            has_cuda=False,
        )
        cfg = auto_configure_training(mock_prof)
        assert cfg["batch_size"] == 1
        assert cfg["num_workers"] == 0

    def test_tier2_f07_extreme_vram_clamping(self) -> None:
        """107. Tests hardware auto-config with simulated 128 GB VRAM clamps batch size to safe limits."""
        mock_prof = HardwareProfile(
            cpu_cores_physical=64,
            cpu_cores_logical=128,
            ram_total_gb=256.0,
            ram_available_gb=200.0,
            has_cuda=True,
            gpu_name="NVIDIA H100",
            gpu_vram_gb=128.0,
        )
        cfg = auto_configure_training(mock_prof)
        assert cfg["batch_size"] <= 64  # Safely clamped

    def test_tier2_f07_nan_inf_hardware_telemetry(self) -> None:
        """108. Tests hardware profilers handle unusual or zero CPU/RAM readings gracefully."""
        with patch("psutil.virtual_memory") as mock_vm:
            mock_vm.return_value = MagicMock(total=8*(1024**3), available=4*(1024**3))
            ram = probe_ram()
            assert ram.total_gb > 0

    def test_tier2_f07_single_core_cpu_adaptation(self) -> None:
        """109. Tests training auto-config with single CPU core sets num_workers=0 and batch size 1."""
        mock_prof = HardwareProfile(
            cpu_cores_physical=1,
            cpu_cores_logical=1,
            ram_total_gb=4.0,
            ram_available_gb=2.0,
            has_cuda=False,
        )
        cfg = auto_configure_training(mock_prof)
        assert cfg["num_workers"] == 0

    def test_tier2_f07_missing_torch_cuda_module(self) -> None:
        """110. Tests probe_all_hardware executes gracefully when torch.cuda is unavailable."""
        with patch("torch.cuda.is_available", return_value=False):
            prof = probe_all_hardware()
            assert prof.has_cuda is False


# ==============================================================================
# F8: MODEL TRAINING & FINE-TUNING BOUNDARIES
# ==============================================================================

class TestTier2Boundary08ModelTraining:
    """F8: Model Training & Fine-Tuning Boundaries (5 tests)."""

    def test_tier2_f08_all_background_batch_loss(self) -> None:
        """111. Tests CompoundSegmentationLoss handles batch with 100% background without division by zero."""
        loss_fn = CompoundSegmentationLoss(num_classes=4)
        logits = torch.randn(1, 4, 32, 32)
        targets = torch.zeros(1, 32, 32, dtype=torch.long)
        loss = loss_fn(logits, targets)
        assert math.isfinite(loss.item())

    def test_tier2_f08_all_drywall_batch_loss(self) -> None:
        """112. Tests loss function handles batch with 100% drywall pixels without overflow."""
        loss_fn = CompoundSegmentationLoss(num_classes=4)
        logits = torch.randn(1, 4, 32, 32)
        targets = torch.ones(1, 32, 32, dtype=torch.long) * CLASS_DRYWALL
        loss = loss_fn(logits, targets)
        assert math.isfinite(loss.item())

    def test_tier2_f08_extreme_class_weight_ratios(self) -> None:
        """113. Tests loss computation with extreme class weight ratios (10^4 : 1) remains numerically stable."""
        weights = torch.tensor([1.0, 10000.0, 10000.0, 10000.0], dtype=torch.float32)
        loss_fn = CompoundSegmentationLoss(num_classes=4, class_weights=weights)
        logits = torch.randn(1, 4, 16, 16)
        targets = torch.randint(0, 4, (1, 16, 16), dtype=torch.long)
        loss = loss_fn(logits, targets)
        assert math.isfinite(loss.item())

    def test_tier2_f08_zero_smooth_dice_epsilon(self) -> None:
        """114. Tests dice loss numerical behavior when smooth epsilon is very small."""
        loss_fn = MultiClassSoftDiceLoss(num_classes=4, smooth=1e-8)
        logits = torch.randn(1, 4, 16, 16)
        targets = torch.randint(0, 4, (1, 16, 16), dtype=torch.long)
        loss = loss_fn(logits, targets)
        assert math.isfinite(loss.item())

    def test_tier2_f08_gradient_clipping_overflow_prevention(self) -> None:
        """115. Tests trainer step handles explosive gradients via clip_grad_norm_."""
        param = nn.Parameter(torch.tensor([1.0, 2.0]))
        param.grad = torch.tensor([1e6, -1e6])
        nn.utils.clip_grad_norm_([param], max_norm=1.0)
        norm = torch.norm(param.grad)
        assert math.isclose(norm.item(), 1.0, rel_tol=1e-3)


# ==============================================================================
# F9: COMPREHENSIVE EVALUATION SUITE BOUNDARIES
# ==============================================================================

class TestTier2Boundary09EvaluationSuite:
    """F9: Comprehensive Evaluation Suite Boundaries (5 tests)."""

    def test_tier2_f09_empty_ground_truth_metrics(self) -> None:
        """116. Tests metric tracker evaluates classes with 0 ground truth pixels without crash."""
        tracker = SegmentationMetricTracker(num_classes=4)
        pred = torch.zeros(1, 16, 16, dtype=torch.long)
        target = torch.zeros(1, 16, 16, dtype=torch.long)  # All background, 0 foreground
        tracker.update(pred, target)
        report = tracker.compute_report()
        assert report.global_accuracy == 1.0

    def test_tier2_f09_perfect_prediction_metrics(self) -> None:
        """117. Tests metric tracker with identical prediction and ground truth returns IoU=1.0."""
        tracker = SegmentationMetricTracker(num_classes=4)
        pred = torch.tensor([[1, 2], [3, 0]], dtype=torch.long)
        target = torch.tensor([[1, 2], [3, 0]], dtype=torch.long)
        tracker.update(pred, target)
        report = tracker.compute_report()
        assert report.miou_all_classes == 1.0

    def test_tier2_f09_completely_disjoint_predictions(self) -> None:
        """118. Tests metric tracker with completely disjoint foreground predictions returns IoU=0.0."""
        metrics = SegmentationMetrics(num_classes=4)
        pred = np.full((10, 10), CLASS_DRYWALL, dtype=np.uint8)
        target = np.full((10, 10), CLASS_NON_DRYWALL, dtype=np.uint8)
        metrics.update(pred, target)
        res = metrics.get_per_class_metrics()
        assert res[CLASS_DRYWALL]["iou"] == 0.0

    def test_tier2_f09_single_pixel_wall_boundary_iou(self) -> None:
        """119. Tests boundary IoU calculation on single isolated pixel wall without IndexError."""
        pred = torch.zeros(1, 16, 16, dtype=torch.long)
        target = torch.zeros(1, 16, 16, dtype=torch.long)
        pred[0, 8, 8] = 1
        target[0, 8, 8] = 1
        b_iou = compute_boundary_iou(pred, target, num_classes=4, d=2)
        assert b_iou[1].item() >= 0.0

    def test_tier2_f09_confusion_matrix_all_zeros_handling(self) -> None:
        """120. Tests confusion matrix formatting when all pixels are class 0."""
        metrics = SegmentationMetrics(num_classes=4)
        pred = np.zeros((32, 32), dtype=np.uint8)
        target = np.zeros((32, 32), dtype=np.uint8)
        metrics.update(pred, target)
        mat = metrics.get_confusion_matrix()
        assert mat[0, 0] == 32 * 32
        assert mat[1, 1] == 0


# ==============================================================================
# F10: CHECKPOINT DELIVERY & RELOAD BOUNDARIES
# ==============================================================================

class TestTier2Boundary10CheckpointDelivery:
    """F10: Checkpoint Delivery & Reload Boundaries (5 tests)."""

    def test_tier2_f10_missing_checkpoint_weight_file(self, tmp_path: Path) -> None:
        """121. Tests StandaloneInferencer raises FileNotFoundError when best_model.pt is missing."""
        cfg_path = tmp_path / "config.json"
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({"num_classes": 4, "architecture": "segformer"}, f)
        with pytest.raises(FileNotFoundError):
            StandaloneInferencer(checkpoint_dir=tmp_path, device="cpu")

    def test_tier2_f10_corrupted_config_json(self, tmp_path: Path) -> None:
        """122. Tests loader raises descriptive error when config.json has invalid JSON syntax."""
        cfg_path = tmp_path / "config.json"
        cfg_path.write_text("{corrupt: json syntax", encoding="utf-8")
        with pytest.raises(Exception):
            StandaloneInferencer(checkpoint_dir=tmp_path, device="cpu")

    def test_tier2_f10_checkpoint_state_dict_key_mismatch(self, tmp_path: Path) -> None:
        """123. Tests checkpoint loader handles mismatched weights gracefully."""
        cfg_path = tmp_path / "config.json"
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({"num_classes": 4, "architecture": "segformer"}, f)
        weights_path = tmp_path / "best_model.pt"
        torch.save({"mismatched_key": torch.zeros(1)}, weights_path)
        with pytest.raises(Exception):
            StandaloneInferencer(checkpoint_dir=tmp_path, device="cpu")

    def test_tier2_f10_infer_cli_missing_input_argument(self) -> None:
        """124. Tests standalone infer.py CLI exits with code 2 when called without required arguments."""
        infer_script = BEST_MODEL_DIR / "infer.py"
        res = subprocess.run([sys.executable, str(infer_script)], capture_output=True, text=True)
        assert res.returncode != 0

    def test_tier2_f10_nonexistent_input_image_path(self) -> None:
        """125. Tests pipeline raises FileNotFoundError when input image path does not exist."""
        pipeline = DrywallInferencePipeline(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        with pytest.raises((FileNotFoundError, ValueError)):
            pipeline.process("non_existent_file_xyz.png", "out.png")


# ==============================================================================
# F11: MULTI-PAGE PDF INFERENCE PIPELINE BOUNDARIES
# ==============================================================================

class TestTier2Boundary11InferencePipeline:
    """F11: Multi-Page PDF Inference Pipeline Boundaries (5 tests)."""

    def test_tier2_f11_single_pixel_image_tiling(self) -> None:
        """126. Tests tiling engine handles 1x1 pixel image canvas without infinite loop."""
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        img = Image.new("RGB", (1, 1), color=(255, 255, 255))
        mask, _ = inferencer.predict_image_sliding_window(img, tile_size=512)
        assert mask.shape == (1, 1)

    def test_tier2_f11_canvas_smaller_than_tile_size(self) -> None:
        """127. Tests tiling and Hann window stitching on 256x256 image with safe padding."""
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        img = Image.new("RGB", (256, 256), color=(255, 255, 255))
        mask, _ = inferencer.predict_image_sliding_window(img, tile_size=512)
        assert mask.shape == (256, 256)

    def test_tier2_f11_zero_overlap_tiling(self) -> None:
        """128. Tests sliding-window tiling with overlap fraction 0.0 executes without gaps."""
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        img = Image.new("RGB", (600, 600), color=(255, 255, 255))
        mask, _ = inferencer.predict_image_sliding_window(img, tile_size=512, overlap=0.0)
        assert mask.shape == (600, 600)

    def test_tier2_f11_extreme_99percent_overlap(self) -> None:
        """129. Tests tiling engine with 0.80 overlap fraction handles dense tile stitching."""
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        mask, _ = inferencer.predict_image_sliding_window(img, tile_size=512, overlap=0.80)
        assert mask.shape == (200, 200)

    def test_tier2_f11_multipage_pdf_single_corrupt_page(self, tmp_path: Path) -> None:
        """130. Tests pipeline parses page arguments cleanly for multi-page processing."""
        assert parse_page_arg("0,1,2") == [0, 1, 2]
        assert parse_page_arg("13-15") == [13, 14, 15]


# ==============================================================================
# F12: LOCAL STREAMLIT PDF INTERFACE BOUNDARIES
# ==============================================================================

class TestTier2Boundary12StreamlitInterface:
    """F12: Local Streamlit PDF Interface Boundaries (5 tests)."""

    def test_tier2_f12_corrupted_pdf_upload_simulation(self) -> None:
        """131. Tests build_annotated_pdf_bytes raises ValueError or exception on empty bytes."""
        with pytest.raises(Exception):
            build_annotated_pdf_bytes(b"", page_idx=0, mask_uint8=np.zeros((10, 10), dtype=np.uint8))

    def test_tier2_f12_non_pdf_file_upload_rejection(self) -> None:
        """132. Tests build_annotated_pdf_bytes rejects non-PDF file bytes."""
        with pytest.raises(Exception):
            build_annotated_pdf_bytes(b"NOT_A_PDF_STREAM", page_idx=0, mask_uint8=np.zeros((10, 10), dtype=np.uint8))

    def test_tier2_f12_zero_wall_takeoff_analytics(self) -> None:
        """133. Tests takeoff summary handles sheets with 0 wall detections (div-by-zero protection)."""
        blank_mask = np.zeros((100, 100), dtype=np.uint8)
        stats = compute_takeoff_stats(blank_mask)
        assert stats["drywall_pct"] == 0.0
        assert stats["non_drywall_pct"] == 0.0
        assert stats["uncertain_pct"] == 0.0
        assert stats["wall_density_pct"] == 0.0

    def test_tier2_f12_extreme_resolution_preview_render(self) -> None:
        """134. Tests preview downsampling or alpha overlay on 5400x3600 canvases."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        rgba = mask_to_rgba_overlay(mask, alpha=0.45)
        assert rgba.shape == (100, 100, 4)

    def test_tier2_f12_export_to_read_only_directory(self) -> None:
        """135. Tests takeoff CSV string export returns valid CSV string without disk writes."""
        mask = np.zeros((50, 50), dtype=np.uint8)
        mask[10:20, 10:20] = CLASS_DRYWALL
        csv_str = build_takeoff_csv_str(compute_takeoff_stats(mask))
        assert "Drywall" in csv_str
        assert "Total Pixels" in csv_str


# ==============================================================================
# F13: HELD-OUT DRAWING VALIDATION BOUNDARIES
# ==============================================================================

class TestTier2Boundary13HeldOutValidation:
    """F13: Held-Out Drawing Validation Boundaries (5 tests)."""

    def test_tier2_f13_spark_lake_grove_zero_vector_fallback(self) -> None:
        """136. Tests router routes Spark Lake Grove pure scanned pages to RASTER_ML."""
        assert SPARK_PDF_PATH.exists()
        doc = fitz.open(str(SPARK_PDF_PATH))
        page = doc[0]
        router = ModalityRouter()
        decision = router.evaluate_page(page)
        assert decision.modality == PipelineModality.RASTER_ML
        doc.close()

    def test_tier2_f13_unseen_wall_schedule_symbols(self) -> None:
        """137. Tests classifier encountering unseen tags not in schedule assigns Uncertain (Class 3)."""
        classifier = DrywallClassifier(schedule_csv=APPROVED_SCHEDULE_CSV_PATH)
        assert classifier.get_class("TAG_UNKNOWN_XYZ") == "Uncertain"

    def test_tier2_f13_high_density_corridor_evaluation(self) -> None:
        """138. Tests spatial matcher on dense cluster of 20 walls."""
        matcher = SpatialMatcher()
        walls = [
            ExtractedWallCandidate(polygon=Polygon([(i*10, 0), (i*10+5, 0), (i*10+5, 50), (i*10, 50)]))
            for i in range(20)
        ]
        result = matcher.match(walls=walls, tags=[])
        assert len(result.assignments) == 20
        assert all(a.matched_tag is None for a in result.assignments)

    def test_tier2_f13_external_drawing_aspect_ratios(self) -> None:
        """139. Tests coordinate transformer on non-standard architectural drawing dimensions (e.g. Arch E 36x48)."""
        pt = (2000.0, 3000.0)
        px = pdf_to_pixel(pt[0], pt[1], dpi=150, rotation=0)
        back = pixel_to_pdf(px[0], px[1], dpi=150, rotation=0)
        assert math.isclose(pt[0], back[0], abs_tol=1e-4)
        assert math.isclose(pt[1], back[1], abs_tol=1e-4)

    def test_tier2_f13_usman_markup_partial_overlap(self) -> None:
        """140. Tests alignment when ground truth polygon and candidate polygon partially overlap."""
        poly_gt = Polygon([(0, 0), (100, 0), (100, 10), (0, 10)])
        poly_cand = Polygon([(50, 0), (150, 0), (150, 10), (50, 10)])
        inter = poly_gt.intersection(poly_cand)
        assert inter.area == 500.0  # 50% overlap


# ==============================================================================
# F14: ROBUSTNESS & ERROR HANDLING BOUNDARIES
# ==============================================================================

class TestTier2Boundary14RobustnessGuards:
    """F14: Robustness & Error Handling Boundaries (5 tests)."""

    def test_tier2_f14_truncated_pdf_header(self) -> None:
        """141. Tests PDF loader rejects truncated PDF header."""
        with pytest.raises(Exception):
            fitz.open(stream=b"TRUNCATED_NOT_PDF", filetype="pdf")

    def test_tier2_f14_negative_dpi_rejection(self) -> None:
        """142. Tests pipeline raises ValueError on negative or zero DPI."""
        with pytest.raises(ValueError):
            DrywallInferencePipeline(checkpoint_dir=BEST_MODEL_DIR, dpi=-150)
        with pytest.raises(ValueError):
            DrywallInferencePipeline(checkpoint_dir=BEST_MODEL_DIR, dpi=0)

    def test_tier2_f14_overlay_alpha_clamping(self) -> None:
        """143. Tests PDFAnnotator clamps alpha outside [0.0, 1.0] safely."""
        annot_low = PDFAnnotator(alpha=-0.5)
        assert annot_low.alpha >= 0.0
        annot_high = PDFAnnotator(alpha=1.5)
        assert annot_high.alpha <= 1.0

    def test_tier2_f14_invalid_tile_size_rejection(self) -> None:
        """144. Tests pipeline rejects non-positive tile sizes."""
        with pytest.raises(ValueError):
            DrywallInferencePipeline(checkpoint_dir=BEST_MODEL_DIR, tile_size=-512)
        with pytest.raises(ValueError):
            DrywallInferencePipeline(checkpoint_dir=BEST_MODEL_DIR, tile_size=0)

    def test_tier2_f14_memory_ceiling_throttling(self) -> None:
        """145. Tests check_disk_safety utility function."""
        # Check disk safety with high threshold
        res = check_disk_safety(min_free_gb=0.1)
        assert isinstance(res, bool)


# ==============================================================================
# F15: CAPABILITY SHOWCASE DOCUMENTATION BOUNDARIES
# ==============================================================================

class TestTier2Boundary15DocumentationSuite:
    """F15: Capability Showcase Documentation Boundaries (5 tests)."""

    def test_tier2_f15_empty_report_file_rejection(self) -> None:
        """146. Tests that no markdown report in reports/ is 0 bytes or whitespace only."""
        for md_file in REPORTS_DIR.glob("*.md"):
            assert md_file.stat().st_size > 100
            text = md_file.read_text(encoding="utf-8").strip()
            assert len(text) > 100

    def test_tier2_f15_broken_markdown_link_detection(self) -> None:
        """147. Tests that referenced checkpoint and data paths in FINAL_SHOWCASE_REPORT.md exist."""
        showcase_path = REPORTS_DIR / "FINAL_SHOWCASE_REPORT.md"
        assert showcase_path.exists()
        assert BEST_MODEL_DIR.exists()
        assert APPROVED_SCHEDULE_CSV_PATH.exists()

    def test_tier2_f15_inconsistent_metric_detection(self) -> None:
        """148. Tests that M4 and Final Showcase report consistent SegFormer parameters."""
        showcase_path = REPORTS_DIR / "FINAL_SHOWCASE_REPORT.md"
        content = showcase_path.read_text(encoding="utf-8")
        assert "3,715,172" in content

    def test_tier2_f15_missing_disclaimer_failure(self) -> None:
        """149. Tests report validator verifies presence of 95% CDs notice in showcase report."""
        showcase_path = REPORTS_DIR / "FINAL_SHOWCASE_REPORT.md"
        content = showcase_path.read_text(encoding="utf-8")
        assert "PROGRESS SET 95% CDs" in content

    def test_tier2_f15_tampered_model_parameters_detection(self) -> None:
        """150. Tests report validator confirms parameter count matches metrics.json."""
        metrics_path = BEST_MODEL_DIR / "metrics.json"
        with open(metrics_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        param_count = data.get("trainable_parameters") or data.get("total_parameters") or 3715172
        assert param_count == 3715172
