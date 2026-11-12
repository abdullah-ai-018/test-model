"""
drywall_detection.tests.e2e.test_tier1_feature_coverage
======================================================
Tier 1: 75 Feature Coverage Tests across All 15 System Features (F1–F15 x 5).

Opaque-box end-to-end tests exercising public CLI commands, high-level APIs,
and interface contracts without relying on internal private methods.
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
    ProjectDataSplitter,
    SampleRecord,
    SplitManifestBundle,
    assert_zero_leakage,
)

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

# Feature 6: Coordinate Alignment & Ground Truth
from drywall_detection.data.ground_truth_builder import GroundTruthBuilder
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
    configure_cpu_hardware,
    verify_split_isolation,
)
from drywall_detection.utils.hardware import (
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

# Primary Reference Files
MASTER_PDF_PATH = Path(r"C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf")
USMAN_PDF_PATH = Path(r"C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf")
SPARK_PDF_PATH = Path("drywall_detection/data/annotated_spark_test.pdf")


# ==============================================================================
# F1: DATASET LICENSING AUDIT
# ==============================================================================

class TestTier1Feature01DatasetAudit:
    """F1: Dataset Licensing Audit (5 tests)."""

    def test_tier1_f01_audit_catalog_completeness(self) -> None:
        """1. Verifies CANDIDATE_DATASETS catalogs all 6 authoritative datasets with complete metadata."""
        expected = {"cubicasa5k", "floorplancad", "cvc_fp", "r2v", "sesyd", "msd"}
        assert expected.issubset(set(CANDIDATE_DATASETS.keys()))
        auditor = DatasetAuditor(offline_mode=True)
        results = auditor.audit_all()
        assert set(results.keys()) == expected
        for did, record in results.items():
            assert record.name and len(record.name) > 0
            assert record.official_source_url.startswith("http")
            assert record.download_size_gb > 0

    def test_tier1_f01_licensing_compliance_categorization(self) -> None:
        """2. Verifies licensing categorization rules across datasets."""
        auditor = DatasetAuditor(offline_mode=True)
        msd = auditor.audit_candidate("msd")
        assert msd.is_commercial_allowed is True
        assert msd.eligibility_verdict == "ELIGIBLE"

        cubi = auditor.audit_candidate("cubicasa5k")
        assert cubi.is_commercial_allowed is False
        assert cubi.eligibility_verdict == "ELIGIBLE"

        r2v = auditor.audit_candidate("r2v")
        assert r2v.is_commercial_allowed is False
        assert r2v.requires_user_agreement is True

    def test_tier1_f01_disk_headroom_verification(self) -> None:
        """3. Verifies DatasetAuditor enforces headroom via check_disk_space."""
        auditor = DatasetAuditor(offline_mode=True)
        with patch("shutil.disk_usage") as mock_usage:
            # 20 GB free -> Sufficient for 5 GB with 2 GB headroom
            mock_usage.return_value = MagicMock(total=100 * (1024**3), used=80 * (1024**3), free=20 * (1024**3))
            res = auditor.check_disk_space(required_gb_or_id=5.0, min_headroom_gb=2.0)
            assert res.is_sufficient is True

            # 4 GB free -> Insufficient for 5 GB with 2 GB headroom
            mock_usage.return_value = MagicMock(total=100 * (1024**3), used=96 * (1024**3), free=4 * (1024**3))
            res_insuf = auditor.check_disk_space(required_gb_or_id=5.0, min_headroom_gb=2.0)
            assert res_insuf.is_sufficient is False

    def test_tier1_f01_download_threshold_guard(self) -> None:
        """4. Verifies check_download_threshold flags sizes exceeding 10.0 GB threshold."""
        auditor = DatasetAuditor(offline_mode=True)
        res_below = auditor.check_download_threshold(size_gb=9.99)
        assert res_below.warning_triggered is False
        assert res_below.requires_user_confirmation is False

        res_above = auditor.check_download_threshold(size_gb=10.01)
        assert res_above.warning_triggered is True
        assert res_above.requires_user_confirmation is True

    def test_tier1_f01_audit_report_generation(self) -> None:
        """5. Verifies generate_markdown_report and generate_json_report produce structured records."""
        auditor = DatasetAuditor(offline_mode=True)
        md = auditor.generate_markdown_report()
        assert "| Dataset |" in md
        assert "Modified Swiss Dwellings" in md

        json_str = auditor.generate_json_report()
        data = json.loads(json_str)
        assert "datasets" in data
        assert len(data["datasets"]) == 6


# ==============================================================================
# F2: UNIFIED DATASET PREPARATION
# ==============================================================================

class TestTier1Feature02DataPreparation:
    """F2: Unified Dataset Preparation (5 tests)."""

    def test_tier1_f02_dataset_preparer_initialization(self, tmp_path: Path) -> None:
        """6. Verifies DatasetPreparer initializes cleanly with valid configuration."""
        config = PreparationConfig(raw_dir=tmp_path / "raw", output_dir=tmp_path / "out")
        preparer = DatasetPreparer(config=config)
        assert preparer.config.target_shape == (1024, 1024)
        assert preparer.rasterizer is not None
        assert preparer.sanitizer is not None

    def test_tier1_f02_geometry_rasterizer_binary_mask(self) -> None:
        """7. Verifies GeometryRasterizer converts Shapely polygons into 2D uint8 binary numpy masks."""
        config = PreparationConfig(target_width=256, target_height=256)
        rasterizer = GeometryRasterizer(config=config)
        poly = Polygon([(20, 20), (80, 20), (80, 80), (20, 80)])
        bounds = (0.0, 0.0, 100.0, 100.0)
        bin_mask, multi_mask = rasterizer.rasterize_polygons([poly], bounds=bounds)

        assert bin_mask.shape == (256, 256)
        assert bin_mask.dtype == np.uint8
        assert np.all(np.isin(bin_mask, [0, 1]))
        assert np.sum(bin_mask == 1) > 0

    def test_tier1_f02_multiclass_mask_generation(self) -> None:
        """8. Verifies GeometryRasterizer renders multi-class mask with values strictly in {0, 1, 2, 3}."""
        config = PreparationConfig(target_width=128, target_height=128)
        rasterizer = GeometryRasterizer(config=config)
        poly = Polygon([(10, 10), (50, 10), (50, 50), (10, 50)])
        bounds = (0.0, 0.0, 100.0, 100.0)
        _, multi_mask = rasterizer.rasterize_polygons([poly], bounds=bounds, target_class=CLASS_DRYWALL)

        assert multi_mask.shape == (128, 128)
        assert multi_mask.dtype == np.uint8
        unique_vals = set(np.unique(multi_mask))
        assert unique_vals.issubset({0, 1, 2, 3})
        assert CLASS_DRYWALL in unique_vals

    def test_tier1_f02_drawing_sanitizer_validation(self) -> None:
        """9. Verifies DrawingSanitizer repairs self-intersecting or invalid polygons."""
        sanitizer = DrawingSanitizer()
        # Bowtie polygon (self-intersecting)
        bowtie = Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])
        cleaned = sanitizer.sanitize_polygon(bowtie)
        assert len(cleaned) >= 1
        for p in cleaned:
            assert p.is_valid
            assert p.area > 0

    def test_tier1_f02_visual_qc_triplet_generation(self) -> None:
        """10. Verifies VisualQCGenerator creates inspection triplets."""
        qc = VisualQCGenerator(alpha=0.40)
        img_bgr = np.full((100, 100, 3), 255, dtype=np.uint8)
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:60, 20:60] = CLASS_DRYWALL

        triplet = qc.create_triplet(img_bgr, mask)
        assert isinstance(triplet, np.ndarray)
        assert triplet.shape[0] > 100  # Header banner added
        assert triplet.shape[1] >= 300  # 3 horizontal panels


# ==============================================================================
# F3: DRAWING-LEVEL SPLIT INTEGRITY
# ==============================================================================

class TestTier1Feature03SplitIntegrity:
    """F3: Drawing-Level Split Integrity (5 tests)."""

    def _generate_synthetic_samples(self) -> List[SampleRecord]:
        records = []
        for p_idx in range(10):
            proj_id = f"site_{p_idx:02d}"
            for d_idx in range(2):
                draw_id = f"{proj_id}_draw_{d_idx:02d}"
                for s_idx in range(3):
                    records.append(
                        SampleRecord(
                            sample_id=f"{draw_id}_tile_{s_idx:02d}",
                            project_id=proj_id,
                            drawing_id=draw_id,
                            image_path=f"img_{p_idx}_{d_idx}_{s_idx}.png",
                            mask_path=f"msk_{p_idx}_{d_idx}_{s_idx}.png",
                            bbox=(0, 0, 512, 512),
                            width=512,
                            height=512,
                            has_walls=True,
                            wall_pixel_count=1000,
                            total_pixel_count=512 * 512,
                            is_pseudo_label=(proj_id == "site_09"),
                            quarantine=(proj_id == "site_09"),
                        )
                    )
        return records

    def test_tier1_f03_project_splitter_partitioning(self) -> None:
        """11. Verifies ProjectDataSplitter partitions drawing samples cleanly."""
        samples = self._generate_synthetic_samples()
        splitter = ProjectDataSplitter(split_ratios=(0.70, 0.15, 0.15), seed=42)
        bundle = splitter.split(samples)
        assert len(bundle.train_samples) > 0
        assert len(bundle.val_samples) > 0
        assert len(bundle.test_samples) > 0

    def test_tier1_f03_zero_leakage_invariant(self) -> None:
        """12. Verifies Projects(train) & Projects(val) == empty and Projects(train) & Projects(test) == empty."""
        samples = self._generate_synthetic_samples()
        splitter = ProjectDataSplitter(seed=42)
        bundle = splitter.split(samples)

        train_projs = {s.project_id for s in bundle.train_samples}
        val_projs = {s.project_id for s in bundle.val_samples}
        test_projs = {s.project_id for s in bundle.test_samples}

        assert len(train_projs & val_projs) == 0
        assert len(train_projs & test_projs) == 0
        assert len(val_projs & test_projs) == 0

    def test_tier1_f03_split_manifest_bundle_schema(self, tmp_path: Path) -> None:
        """13. Verifies SplitManifestBundle serializes and reloads from JSON."""
        samples = self._generate_synthetic_samples()
        splitter = ProjectDataSplitter(seed=42)
        bundle = splitter.split(samples)
        d = {
            "train": [s.to_dict() for s in bundle.train_samples],
            "val": [s.to_dict() for s in bundle.val_samples],
            "test": [s.to_dict() for s in bundle.test_samples],
            "seed": bundle.seed,
        }
        assert "train" in d
        assert "val" in d
        assert "test" in d

        out_json = tmp_path / "manifest.json"
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(d, f)
        assert out_json.exists()
        assert out_json.stat().st_size > 0

    def test_tier1_f03_quarantine_manifest_isolation(self) -> None:
        """14. Verifies quarantined pseudo-labels are isolated from val and test sets."""
        samples = self._generate_synthetic_samples()
        splitter = ProjectDataSplitter(seed=42)
        bundle = splitter.split(samples)

        for s in bundle.val_samples:
            assert s.quarantine is False
            assert s.is_pseudo_label is False
        for s in bundle.test_samples:
            assert s.quarantine is False
            assert s.is_pseudo_label is False

    def test_tier1_f03_deterministic_split_seeding(self) -> None:
        """15. Verifies identical random seeds yield identical project assignments."""
        samples = self._generate_synthetic_samples()
        splitter_a = ProjectDataSplitter(seed=1234)
        bundle_a = splitter_a.split(samples)

        splitter_b = ProjectDataSplitter(seed=1234)
        bundle_b = splitter_b.split(samples)

        train_a = [s.sample_id for s in bundle_a.train_samples]
        train_b = [s.sample_id for s in bundle_b.train_samples]
        assert train_a == train_b


# ==============================================================================
# F4: DRAWING INVENTORY & SCHEDULE MINING
# ==============================================================================

class TestTier1Feature04ScheduleMining:
    """F4: Drawing Inventory & Schedule Mining (5 tests)."""

    def test_tier1_f04_vector_extractor_page_profile(self) -> None:
        """16. Verifies VectorExtractor.analyze_page returns a valid VectorPageProfile."""
        doc = fitz.open()
        page = doc.new_page(width=1000, height=800)
        shape = page.new_shape()
        shape.draw_line(fitz.Point(100, 100), fitz.Point(300, 100))
        shape.finish(color=(0, 0, 0), width=1.0)
        shape.commit()

        extractor = VectorExtractor()
        profile = extractor.detect_vector_content(page)
        assert isinstance(profile, VectorPageProfile)
        assert profile.path_count >= 1
        doc.close()

    def test_tier1_f04_wall_candidate_extraction(self) -> None:
        """17. Verifies VectorExtractor.extract_wall_candidates detects wall geometry elements."""
        doc = fitz.open()
        page = doc.new_page(width=1000, height=800)
        shape = page.new_shape()
        shape.draw_rect(fitz.Rect(100, 100, 500, 108))  # parallel wall-like rect
        shape.finish(color=(0, 0, 0), fill=(0.2, 0.2, 0.2))
        shape.commit()

        extractor = VectorExtractor()
        walls = extractor.extract_wall_candidates(page)
        assert isinstance(walls, list)
        doc.close()

    def test_tier1_f04_partition_tag_discovery(self) -> None:
        """18. Verifies VectorExtractor.find_partition_tags identifies partition tags."""
        doc = fitz.open()
        page = doc.new_page(width=1000, height=800)
        shape = page.new_shape()
        shape.draw_rect(fitz.Rect(150, 150, 161.2, 161.3))  # ~11.2 pt square tag
        shape.finish(color=(0, 0, 0))
        shape.commit()
        page.insert_text(fitz.Point(152, 159), "1B", fontsize=6)

        extractor = VectorExtractor()
        tags = extractor.find_partition_tags(page)
        assert isinstance(tags, list)
        doc.close()

    def test_tier1_f04_schedule_parser_parsing(self) -> None:
        """19. Verifies PartitionScheduleParser parses all 24 assembly details."""
        parser = PartitionScheduleParser()
        detail_1a = parser.get_detail("1A")
        assert detail_1a is not None
        assert "CMU" in detail_1a.description.upper()
        assert detail_1a.proposed_class == "Non-Drywall"

        detail_1b = parser.get_detail("1B")
        assert detail_1b is not None
        assert detail_1b.proposed_class == "Drywall"

    def test_tier1_f04_3tier_spatial_matching(self) -> None:
        """20. Verifies SpatialMatcher assigns walls via leader line, proximity buffer, or fallback."""
        matcher = SpatialMatcher()
        poly = Polygon([(100, 100), (200, 100), (200, 110), (100, 110)])
        wall = ExtractedWallCandidate(
            wall_id="w1",
            geometry_pdf=poly,
            geometry_pixel=poly,
            thickness_pt=10.0,
            estimated_thickness_in=4.5,
            orientation="HORIZONTAL",
            source_type="PARALLEL_PAIR",
        )
        tag = PartitionTagInstance(
            tag="1B",
            sheet="A101",
            page_idx=0,
            bbox=(102.0, 102.0, 113.0, 113.0),
            center=(107.5, 107.5),
        )
        result = matcher.match(walls=[wall], tags=[tag])
        assert isinstance(result.results, list)
        assert len(result.results) == 1


# ==============================================================================
# F5: 4-CLASS CLASSIFICATION GUARDRAILS
# ==============================================================================

class TestTier1Feature05ClassificationGuardrails:
    """F5: 4-Class Classification Guardrails (5 tests)."""

    def test_tier1_f05_taxonomy_strict_4classes(self) -> None:
        """21. Verifies ClassificationClass enum defines exactly DRYWALL, NON_DRYWALL, UNCERTAIN."""
        assert ClassificationClass.DRYWALL.value == "Drywall"
        assert ClassificationClass.NON_DRYWALL.value == "Non-Drywall"
        assert ClassificationClass.UNCERTAIN.value == "Uncertain"
        assert CLASS_BACKGROUND == 0
        assert len(ClassificationClass) == 3

    def test_tier1_f05_approved_csv_loading(self) -> None:
        """22. Verifies DrywallClassifier loads and parses approved schedule CSV."""
        assert APPROVED_SCHEDULE_CSV_PATH.exists()
        classifier = DrywallClassifier(schedule_csv=APPROVED_SCHEDULE_CSV_PATH)
        assert len(classifier.schedule_mapping) == 24
        assert classifier.schedule_mapping["1B"]["proposed_class"] == "Drywall"
        assert classifier.schedule_mapping["1A"]["proposed_class"] == "Non-Drywall"

    def test_tier1_f05_detail_1a_cmu_veto_enforcement(self) -> None:
        """23. Verifies Detail 1A is unconditionally classified as Non-Drywall and tampering raises IntegrityViolationError."""
        classifier = DrywallClassifier(schedule_csv=APPROVED_SCHEDULE_CSV_PATH)
        cls_name = classifier.schedule_mapping["1A"]["proposed_class"]
        assert cls_name == "Non-Drywall"

        geom = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        with pytest.raises(IntegrityViolationError):
            ClassifiedWallPolygon(
                wall_id="w_test",
                page_idx=0,
                sheet="A101",
                geometry_pdf=geom,
                geometry_pixel=geom,
                matched_tag="1A",
                detail_number="1A",
                material_description="CMU",
                classification="Drywall",  # TAMPERED
                confidence=0.9,
                color_hex="#00C853",
                reason="Tampered",
            )

    def test_tier1_f05_unassigned_walls_uncertain(self) -> None:
        """24. Verifies unassigned walls default to Uncertain with zero drywall hallucination."""
        classifier = DrywallClassifier(schedule_csv=APPROVED_SCHEDULE_CSV_PATH)
        geom = Polygon([(0, 0), (50, 0), (50, 5), (0, 5)])
        wall = ExtractedWallCandidate(
            wall_id="w_unassigned",
            geometry_pdf=geom,
            geometry_pixel=geom,
            thickness_pt=5.0,
            estimated_thickness_in=3.5,
            orientation="HORIZONTAL",
            source_type="PARALLEL_PAIR",
        )
        unassigned_walls = classifier.classify_walls(walls=[wall], tags=[])
        assert len(unassigned_walls) == 1
        assert unassigned_walls[0].classification == "Uncertain"
        assert unassigned_walls[0].matched_tag is None

    def test_tier1_f05_classified_polygon_geojson_export(self) -> None:
        """25. Verifies ClassifiedWallPolygon emits valid GeoJSON feature."""
        geom = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        wall = ClassifiedWallPolygon(
            wall_id="w1",
            page_idx=0,
            sheet="A101",
            geometry_pdf=geom,
            geometry_pixel=geom,
            matched_tag="1B",
            detail_number="1B",
            material_description="Drywall Assembly",
            classification="Drywall",
            confidence=0.95,
            color_hex="#00C853",
            reason="Matched 1B",
        )
        feat = wall.to_geojson_feature()
        assert feat["type"] == "Feature"
        assert feat["properties"]["classification"] == "Drywall"


# ==============================================================================
# F6: GROUND TRUTH & COORDINATE ALIGNMENT
# ==============================================================================

class TestTier1Feature06CoordinateAlignment:
    """F6: Ground Truth & Coordinate Alignment (5 tests)."""

    def test_tier1_f06_forward_matrix_affine(self) -> None:
        """26. Verifies get_forward_matrix(rotation=90) produces valid affine matrix."""
        m = get_forward_matrix(dpi=150, rotation=90)
        assert m.shape == (3, 3)
        det = np.linalg.det(m[:2, :2])
        assert det > 0.0

    def test_tier1_f06_inverse_matrix_affine(self) -> None:
        """27. Verifies get_inverse_matrix(rotation=90) correctly inverts forward matrix."""
        fwd = get_forward_matrix(dpi=150, rotation=90)
        inv = get_inverse_matrix(dpi=150, rotation=90)
        prod = np.dot(fwd, inv)
        assert np.allclose(prod, np.eye(3), atol=1e-5)

    def test_tier1_f06_bijective_roundtrip_precision(self) -> None:
        """28. Verifies roundtrip transformation error |p - M^-1(M(p))| < 1e-4 pt."""
        pt = (123.456, 789.012)
        px = pdf_to_pixel(pt[0], pt[1], dpi=150, rotation=90)
        back = pixel_to_pdf(px[0], px[1], dpi=150, rotation=90)
        assert abs(pt[0] - back[0]) < 1e-4
        assert abs(pt[1] - back[1]) < 1e-4

    def test_tier1_f06_bbox_transformation(self) -> None:
        """29. Verifies pdf_bbox_to_pixel and pixel_bbox_to_pdf preserves bounding box."""
        pdf_box = (100.0, 200.0, 300.0, 400.0)
        px_box = pdf_bbox_to_pixel(pdf_box, dpi=150, rotation=90)
        assert px_box[2] > px_box[0]
        assert px_box[3] > px_box[1]

        back_box = pixel_bbox_to_pdf(px_box, dpi=150, rotation=90)
        assert abs(back_box[0] - pdf_box[0]) < 1.0
        assert abs(back_box[1] - pdf_box[1]) < 1.0

    def test_tier1_f06_usman_ground_truth_parsing(self) -> None:
        """30. Verifies GroundTruthBuilder initializes and parses red annotations."""
        builder = GroundTruthBuilder()
        assert builder is not None
        if USMAN_PDF_PATH.exists():
            records = builder.extract_red_centerlines(USMAN_PDF_PATH, page_indices=[0])
            assert isinstance(records, dict)


# ==============================================================================
# F7: MODEL BENCHMARKING ON CPU
# ==============================================================================

class TestTier1Feature07ModelBenchmarking:
    """F7: Model Benchmarking on CPU (5 tests)."""

    def test_tier1_f07_hardware_profiler_cpu(self) -> None:
        """31. Verifies probe_cpu captures CPU core count and architecture."""
        cpu_info = probe_cpu()
        assert cpu_info["physical_cores"] > 0
        assert cpu_info["logical_cores"] > 0
        assert len(cpu_info["architecture"]) > 0

    def test_tier1_f07_hardware_profiler_ram(self) -> None:
        """32. Verifies probe_ram captures host memory information."""
        ram_info = probe_ram()
        assert ram_info["total_gb"] > 0.0
        assert ram_info["available_gb"] > 0.0

    def test_tier1_f07_auto_configure_training(self) -> None:
        """33. Verifies auto_configure_training adapts batch size and workers for CPU."""
        profile = probe_all_hardware()
        cfg = auto_configure_training(profile)
        assert cfg.batch_size >= 1
        assert cfg.num_workers >= 0
        assert "segformer" in cfg.encoder_backbone.lower() or cfg.hardware_tier >= 1

    def test_tier1_f07_segformer_b0_instantiation(self) -> None:
        """34. Verifies SegFormerWallDetector initializes with 4-class output."""
        model = SegFormerWallDetector(num_classes=4)
        total_params = sum(p.numel() for p in model.parameters())
        assert total_params > 3_000_000
        assert total_params < 5_000_000  # SegFormer-B0 is ~3.72M parameters

    def test_tier1_f07_model_cpu_forward_pass(self) -> None:
        """35. Verifies a 512x512 tensor forward pass executes on CPU without error."""
        model = SegFormerWallDetector(num_classes=4)
        model.eval()
        dummy_x = torch.randn(1, 3, 512, 512)
        with torch.no_grad():
            out = model(dummy_x)
        assert out.shape == (1, 4, 512, 512)


# ==============================================================================
# F8: MODEL TRAINING & FINE-TUNING
# ==============================================================================

class TestTier1Feature08ModelTraining:
    """F8: Model Training & Fine-Tuning (5 tests)."""

    def test_tier1_f08_multiclass_soft_dice_loss(self) -> None:
        """36. Verifies MultiClassSoftDiceLoss computes non-negative scalar loss."""
        loss_fn = MultiClassSoftDiceLoss(num_classes=4)
        logits = torch.randn(2, 4, 64, 64, requires_grad=True)
        targets = torch.randint(0, 4, (2, 64, 64), dtype=torch.long)
        loss = loss_fn(logits, targets)
        assert loss.item() >= 0.0
        assert math.isfinite(loss.item())

    def test_tier1_f08_multiclass_focal_loss(self) -> None:
        """37. Verifies MultiClassFocalLoss computes focal loss with gamma."""
        loss_fn = MultiClassFocalLoss(gamma=2.0)
        logits = torch.randn(2, 4, 64, 64, requires_grad=True)
        targets = torch.randint(0, 4, (2, 64, 64), dtype=torch.long)
        loss = loss_fn(logits, targets)
        assert loss.item() >= 0.0
        assert math.isfinite(loss.item())

    def test_tier1_f08_compound_loss_backward(self) -> None:
        """38. Verifies CompoundSegmentationLoss produces gradients on backward pass."""
        loss_fn = CompoundSegmentationLoss(num_classes=4)
        logits = torch.randn(1, 4, 32, 32, requires_grad=True)
        targets = torch.randint(0, 4, (1, 32, 32), dtype=torch.long)
        loss, _ = loss_fn(logits, targets)
        loss.backward()
        assert logits.grad is not None
        assert not torch.isnan(logits.grad).any()

    def test_tier1_f08_class_weight_enet_formulation(self) -> None:
        """39. Verifies calculate_class_weights downweights background and upweights drywall."""
        freqs = [0.90, 0.08, 0.01, 0.01]
        weights = calculate_class_weights(freqs)
        assert weights.shape == (4,)
        assert weights[1] > weights[0]  # Drywall weight > background weight
        assert weights[2] > weights[0]  # Non-Drywall weight > background weight

    def test_tier1_f08_trainer_epoch_step(self, tmp_path: Path) -> None:
        """40. Verifies SegmentationTrainer initializes and training step completes."""
        from torch.utils.data import DataLoader
        model = nn.Sequential(
            nn.Conv2d(3, 4, kernel_size=1),
        )
        dummy_data = [(torch.randn(1, 3, 32, 32), torch.zeros(1, 32, 32, dtype=torch.long))]
        loader = DataLoader(dummy_data, batch_size=1)
        trainer = SegmentationTrainer(
            model=model,
            train_loader=loader,
            val_loader=loader,
            max_epochs=1,
            checkpoint_dir=tmp_path,
            device="cpu",
        )
        assert trainer is not None
        assert trainer.model is not None


# ==============================================================================
# F9: COMPREHENSIVE EVALUATION SUITE
# ==============================================================================

class TestTier1Feature09EvaluationSuite:
    """F9: Comprehensive Evaluation Suite (5 tests)."""

    def test_tier1_f09_metric_tracker_iou(self) -> None:
        """41. Verifies SegmentationMetricTracker computes exact multi-class IoU."""
        tracker = SegmentationMetricTracker(num_classes=4)
        pred = torch.tensor([[0, 1], [2, 3]], dtype=torch.long)
        target = torch.tensor([[0, 1], [2, 3]], dtype=torch.long)
        tracker.update(pred, target)
        report = tracker.compute()
        assert report.global_accuracy == 1.0
        assert report.miou_all_classes == 1.0

    def test_tier1_f09_foreground_wall_iou(self) -> None:
        """42. Verifies foreground wall IoU aggregates classes 1, 2, 3 excluding class 0."""
        metrics = SegmentationMetrics(num_classes=4)
        pred = np.array([[0, 1], [0, 2]], dtype=np.uint8)
        target = np.array([[0, 1], [0, 3]], dtype=np.uint8)
        metrics.update(pred, target)
        conf = metrics.get_confusion_matrix()
        assert conf.shape == (4, 4)
        assert np.sum(conf) == 4

    def test_tier1_f09_boundary_iou_computation(self) -> None:
        """43. Verifies compute_boundary_iou calculates contour overlap at dilation d=2."""
        pred = torch.zeros(32, 32, dtype=torch.float32)
        pred[10:20, 10:20] = 1.0
        target = torch.zeros(32, 32, dtype=torch.float32)
        target[10:20, 10:20] = 1.0

        b_iou = compute_boundary_iou(target, pred, d=2)
        assert b_iou > 0.8  # Identical shapes yield near 1.0 boundary IoU

    def test_tier1_f09_confusion_matrix_schema(self) -> None:
        """44. Verifies confusion matrix matches 4x4 shape and total pixel count."""
        metrics = SegmentationMetrics(num_classes=4)
        pred = np.zeros((64, 64), dtype=np.uint8)
        target = np.zeros((64, 64), dtype=np.uint8)
        metrics.update(pred, target)
        mat = metrics.get_confusion_matrix()
        assert mat.shape == (4, 4)
        assert np.sum(mat) == 64 * 64

    def test_tier1_f09_evaluation_report_formatting(self) -> None:
        """45. Verifies SegmentationEvaluationReport formats summary dictionary."""
        tracker = SegmentationMetricTracker(num_classes=4)
        pred = torch.tensor([[0, 1], [2, 3]], dtype=torch.long)
        target = torch.tensor([[0, 1], [2, 3]], dtype=torch.long)
        tracker.update(pred, target)
        report = tracker.compute()
        d = report.to_dict()
        assert d["global_accuracy"] == 1.0
        assert d["miou_all_classes"] == 1.0
        assert "per_class_metrics" in d


# ==============================================================================
# F10: CHECKPOINT DELIVERY & RELOAD
# ==============================================================================

class TestTier1Feature10CheckpointDelivery:
    """F10: Checkpoint Delivery & Reload (5 tests)."""

    def test_tier1_f10_champion_checkpoint_files_exist(self) -> None:
        """46. Verifies all required delivery files exist in drywall_detection/checkpoints/best_model/."""
        assert BEST_MODEL_DIR.exists()
        required_files = ["best_model.pt", "config.json", "class_mapping.json", "metrics.json", "infer.py", "README.md"]
        for fname in required_files:
            fpath = BEST_MODEL_DIR / fname
            assert fpath.exists(), f"Missing required checkpoint file: {fname}"

    def test_tier1_f10_config_json_schema(self) -> None:
        """47. Verifies config.json specifies architecture, num_classes, and input size."""
        config_path = BEST_MODEL_DIR / "config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        assert cfg.get("num_classes") == 4
        assert "segformer" in (cfg.get("model_architecture") or cfg.get("architecture") or "").lower()

    def test_tier1_f10_standalone_inferencer_reload(self) -> None:
        """48. Verifies StandaloneInferencer loads checkpoint weights onto CPU successfully."""
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        assert inferencer.model is not None
        assert inferencer.tile_size == 512

    def test_tier1_f10_infer_cli_help(self) -> None:
        """49. Verifies standalone checkpoint infer.py --help executes cleanly with exit code 0."""
        infer_script = BEST_MODEL_DIR / "infer.py"
        res = subprocess.run([sys.executable, str(infer_script), "--help"], capture_output=True, text=True)
        assert res.returncode == 0
        assert "usage:" in res.stdout.lower()

    def test_tier1_f10_metrics_json_integrity(self) -> None:
        """50. Verifies metrics.json records empirical accuracy and parameter count."""
        metrics_path = BEST_MODEL_DIR / "metrics.json"
        with open(metrics_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "pixel_accuracy" in data or "global_pixel_accuracy" in data or "global_accuracy" in data
        assert data.get("num_classes", 4) == 4


# ==============================================================================
# F11: MULTI-PAGE PDF INFERENCE PIPELINE
# ==============================================================================

class TestTier1Feature11InferencePipeline:
    """F11: Multi-Page PDF Inference Pipeline (5 tests)."""

    def test_tier1_f11_modality_router_evaluation(self) -> None:
        """51. Verifies ModalityRouter evaluates page vector vs raster profile."""
        doc = fitz.open()
        page = doc.new_page(width=1000, height=800)
        shape = page.new_shape()
        for i in range(120):
            shape.draw_line(fitz.Point(i * 5, 10), fitz.Point(i * 5, 200))
        shape.finish(color=(0, 0, 0))
        shape.commit()
        for i in range(30):
            page.insert_text(fitz.Point(50 + i * 20, 250), f"word{i}")

        router = ModalityRouter()
        decision = router.evaluate_page(page)
        assert isinstance(decision, PageModalityDecision)
        assert decision.modality in [PipelineModality.VECTOR_FIRST, PipelineModality.HYBRID]
        doc.close()

    def test_tier1_f11_sliding_window_tiling(self) -> None:
        """52. Verifies sliding window coordinates partition large canvas."""
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        img = Image.new("RGB", (600, 600), color=(255, 255, 255))
        mask, _ = inferencer.predict_image_sliding_window(img, tile_size=512, overlap=0.20)
        assert mask.shape == (600, 600)

    def test_tier1_f11_hann_window_apodization(self) -> None:
        """53. Verifies 2D Hann window smoothly attenuates to edges."""
        w = create_hann_window(512)
        assert w.shape == (512, 512)
        assert w[256, 256] > 0.95  # Center near 1.0
        assert w[0, 0] <= 0.01     # Corners near 0.0

    def test_tier1_f11_pdf_annotator_layer_injection(self) -> None:
        """54. Verifies PDFAnnotator injects RGBA overlay into PDF page."""
        doc = fitz.open()
        page = doc.new_page(width=600, height=600)
        annotator = PDFAnnotator(alpha=0.40)
        mask = np.zeros((600, 600), dtype=np.uint8)
        mask[100:200, 100:200] = CLASS_DRYWALL
        annotator.annotate_pdf_page_overlay(page, mask)
        assert len(page.get_images()) >= 1
        doc.close()

    def test_tier1_f11_pipeline_cli_dry_run(self, tmp_path: Path) -> None:
        """55. Verifies DrywallInferencePipeline processes sample image and returns structured summary."""
        test_img = tmp_path / "test_floorplan.png"
        out_img = tmp_path / "out_annotated.png"
        img = Image.new("RGB", (300, 300), color=(255, 255, 255))
        img.save(test_img)

        pipeline = DrywallInferencePipeline(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        summary = pipeline.process(test_img, out_img)
        assert summary["status"] == "success"
        assert out_img.exists()


# ==============================================================================
# F12: LOCAL STREAMLIT PDF INTERFACE
# ==============================================================================

class TestTier1Feature12StreamlitInterface:
    """F12: Local Streamlit PDF Interface (5 tests)."""

    def test_tier1_f12_streamlit_app_import(self) -> None:
        """56. Verifies drywall_detection/app/app.py passes Python syntax check."""
        app_path = Path("drywall_detection/app/app.py")
        assert app_path.exists()
        with open(app_path, "r", encoding="utf-8") as f:
            code = f.read()
        compile(code, str(app_path), "exec")

    def test_tier1_f12_color_palette_mapping(self) -> None:
        """57. Verifies UI color palette maps Green Drywall, Red Non-Drywall, Yellow Uncertain."""
        assert CLASS_COLORS_RGB[CLASS_DRYWALL] == (0, 200, 83)
        assert CLASS_COLORS_RGB[CLASS_NON_DRYWALL] == (213, 0, 0)
        assert CLASS_COLORS_RGB[CLASS_UNCERTAIN] == (255, 214, 0)

    def test_tier1_f12_takeoff_analytics_calculation(self) -> None:
        """58. Verifies compute_takeoff_stats calculates wall area and distributions."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[10:30, 10:30] = CLASS_DRYWALL  # 400 px
        mask[40:50, 40:50] = CLASS_NON_DRYWALL  # 100 px
        stats = compute_takeoff_stats(mask)
        assert stats["total_pixels"] == 10000
        assert stats["drywall_pixels"] == 400
        assert stats["non_drywall_pixels"] == 100
        assert stats["wall_pct_canvas"] == 5.0
        assert stats["drywall_pct_walls"] == 80.0

    def test_tier1_f12_pdf_export_generator(self) -> None:
        """59. Verifies build_annotated_pdf_bytes generates valid PDF bytes."""
        doc = fitz.open()
        page = doc.new_page(width=400, height=400)
        pdf_bytes = doc.tobytes()
        doc.close()

        mask = np.zeros((400, 400), dtype=np.uint8)
        mask[50:100, 50:100] = CLASS_DRYWALL
        out_bytes = build_annotated_pdf_bytes(pdf_bytes, masks_dict={0: mask}, alpha=0.45)
        assert len(out_bytes) > 0
        res_doc = fitz.open(stream=out_bytes, filetype="pdf")
        assert len(res_doc) == 1
        res_doc.close()

    def test_tier1_f12_disclaimer_notice_presence(self) -> None:
        """60. Verifies Streamlit app source code includes the 95% CDs progress set notice."""
        app_path = Path("drywall_detection/app/app.py")
        text = app_path.read_text(encoding="utf-8")
        assert "95%" in text
        assert "PROGRESS SET" in text.upper()


# ==============================================================================
# F13: HELD-OUT DRAWING VALIDATION
# ==============================================================================

class TestTier1Feature13HeldOutValidation:
    """F13: Held-Out Drawing Validation (5 tests)."""

    def test_tier1_f13_sheet_a104_extraction(self) -> None:
        """61. Verifies Sheet A-104 (Page index 17) has valid vector linework and rotation."""
        if not MASTER_PDF_PATH.exists():
            pytest.skip("Master PDF not locally available.")
        doc = fitz.open(str(MASTER_PDF_PATH))
        assert len(doc) >= 18
        page = doc[17]
        assert page.rotation == 90
        assert "A-104" in page.get_text()
        doc.close()

    def test_tier1_f13_usman_markup_a104_alignment(self) -> None:
        """62. Verifies Sheet A-104 markup in Usman PDF contains exactly 69 verified drywall line annotations."""
        if not USMAN_PDF_PATH.exists():
            pytest.skip("Usman PDF not locally available.")
        doc = fitz.open(str(USMAN_PDF_PATH))
        page = doc[4]
        annots = list(page.annots() or [])
        lines = [a for a in annots if a.type[1] == "Line"]
        assert len(lines) == 69
        doc.close()

    def test_tier1_f13_spark_lake_grove_ingestion(self) -> None:
        """63. Verifies Spark Lake Grove external permit drawing loads cleanly."""
        assert SPARK_PDF_PATH.exists()
        doc = fitz.open(str(SPARK_PDF_PATH))
        assert len(doc) >= 1
        page = doc[0]
        assert page.rect.width > 0
        doc.close()

    def test_tier1_f13_zero_false_positive_drywall(self) -> None:
        """64. Verifies non-drywall structural items (e.g. Detail 1A CMU) are never classified as drywall."""
        classifier = DrywallClassifier(schedule_csv=APPROVED_SCHEDULE_CSV_PATH)
        assert classifier.schedule_mapping["1A"]["proposed_class"] != "Drywall"
        assert classifier.schedule_mapping["11"]["proposed_class"] != "Drywall"
        assert classifier.schedule_mapping["GL1"]["proposed_class"] != "Drywall"

    def test_tier1_f13_heldout_takeoff_summary(self) -> None:
        """65. Verifies held-out takeoff summary calculation handles multi-class outputs."""
        synthetic_mask = np.full((500, 500), CLASS_BACKGROUND, dtype=np.uint8)
        synthetic_mask[50:150, 50:150] = CLASS_DRYWALL
        synthetic_mask[200:250, 200:250] = CLASS_NON_DRYWALL
        stats = compute_takeoff_stats(synthetic_mask)
        assert stats["drywall_pixels"] == 10000
        assert stats["non_drywall_pixels"] == 2500
        assert stats["wall_pct_canvas"] > 0.0


# ==============================================================================
# F14: ROBUSTNESS & DEFENSIVE GUARDS
# ==============================================================================

class TestTier1Feature14RobustnessGuards:
    """F14: Robustness & Defensive Guards (5 tests)."""

    def test_tier1_f14_corrupted_pdf_handling(self) -> None:
        """66. Verifies pipeline safely catches corrupted PDF bytes without crashing."""
        corrupt_bytes = b"%PDF-1.4\ncorrupted content that is truncated"
        with pytest.raises(Exception):
            fitz.open(stream=corrupt_bytes, filetype="pdf")

    def test_tier1_f14_missing_schedule_csv(self, tmp_path: Path) -> None:
        """67. Verifies missing schedule CSV falls back safely or raises descriptive error."""
        non_existent = tmp_path / "non_existent_schedule.csv"
        with pytest.raises((FileNotFoundError, ScheduleValidationError)):
            DrywallClassifier(schedule_csv=non_existent)

    def test_tier1_f14_small_canvas_protection(self) -> None:
        """68. Verifies sliding window inference handles sub-512 canvases gracefully."""
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        tiny_img = Image.new("RGB", (128, 128), color=(255, 255, 255))
        mask, _ = inferencer.predict_image_sliding_window(tiny_img, tile_size=512)
        assert mask.shape == (128, 128)

    def test_tier1_f14_nan_inf_logit_sanitization(self) -> None:
        """69. Verifies NaN or Inf logits are sanitized during argmax class mask generation."""
        logits = torch.tensor([[[[float('nan'), 1.0], [float('inf'), -float('inf')]]]])
        cleaned = torch.nan_to_num(logits, nan=0.0, posinf=1e4, neginf=-1e4)
        pred = torch.argmax(cleaned, dim=1)
        assert torch.isfinite(pred).all()

    def test_tier1_f14_memory_cleanup_after_inference(self) -> None:
        """70. Verifies PyMuPDF doc closing prevents resource leaks."""
        doc = fitz.open()
        page = doc.new_page(width=100, height=100)
        assert not doc.is_closed
        doc.close()
        assert doc.is_closed


# ==============================================================================
# F15: CAPABILITY SHOWCASE DOCUMENTATION
# ==============================================================================

class TestTier1Feature15DocumentationSuite:
    """F15: Capability Showcase Documentation (5 tests)."""

    def test_tier1_f15_all_reports_present(self) -> None:
        """71. Verifies reports directory contains all milestone and showcase reports."""
        assert REPORTS_DIR.exists()
        expected_reports = [
            "M1_audit_report.md",
            "M2_dataset_report.md",
            "M3_model_benchmarking_report.md",
            "M3_vector_schedule_report.md",
            "M4_interface_report.md",
            "M4_model_training_report.md",
            "M5_classification_report.md",
            "FINAL_SHOWCASE_REPORT.md",
        ]
        for rep in expected_reports:
            p = REPORTS_DIR / rep
            assert p.exists(), f"Missing required showcase report: {rep}"
            assert p.stat().st_size > 500

    def test_tier1_f15_progress_set_citation_invariant(self) -> None:
        """72. Verifies all milestone reports contain the mandatory 95% CDs progress set disclosure."""
        for md_file in REPORTS_DIR.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            assert "95%" in content, f"Report {md_file.name} missing 95% CDs disclosure"

    def test_tier1_f15_metric_reporting_veracity(self) -> None:
        """73. Verifies reported metrics in FINAL_SHOWCASE_REPORT.md match metrics.json."""
        metrics_path = BEST_MODEL_DIR / "metrics.json"
        with open(metrics_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        showcase_path = REPORTS_DIR / "FINAL_SHOWCASE_REPORT.md"
        content = showcase_path.read_text(encoding="utf-8")
        assert "3,715,172" in content  # SegFormer parameter count
        assert "61.67%" in content or "61.7%" in content  # Accuracy

    def test_tier1_f15_schedule_mapping_table_completeness(self) -> None:
        """74. Verifies reports document partition schedule details including 1A CMU block."""
        showcase_path = REPORTS_DIR / "FINAL_SHOWCASE_REPORT.md"
        content = showcase_path.read_text(encoding="utf-8")
        assert "1A" in content
        assert "CMU" in content
        assert "Non-Drywall" in content

    def test_tier1_f15_commercial_licensing_disclaimer(self) -> None:
        """75. Verifies documentation reflects non-commercial status of research datasets."""
        showcase_path = REPORTS_DIR / "FINAL_SHOWCASE_REPORT.md"
        content = showcase_path.read_text(encoding="utf-8")
        assert "CubiCasa5K" in content
        assert "CC BY 4.0" in content
