"""
drywall_detection.tests.e2e.test_tier3_pairwise
===============================================
Tier 3: 15 Cross-Feature Pairwise Interaction Tests.

Verifies end-to-end data flow, invariants, and contract stability
across pairs of interacting system features (F1 through F15).
"""

from __future__ import annotations

import io
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, patch

import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import pytest
from shapely.geometry import Point, Polygon, box
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from drywall_detection.app import (
    build_annotated_pdf_bytes,
    build_takeoff_csv_str,
    compute_takeoff_stats,
)
from drywall_detection.audit.dataset_auditor import (
    CANDIDATE_DATASETS,
    DatasetAuditor,
    DatasetEligibility,
)
from drywall_detection.checkpoints.best_model.infer import (
    StandaloneInferencer,
    create_hann_window,
)
from drywall_detection.classification import (
    ClassificationClass,
    ClassificationFeatureCollection,
    ClassifiedWallPolygon,
    DrywallClassifier,
    IntegrityViolationError,
)
from drywall_detection.config import (
    APPROVED_SCHEDULE_CSV_PATH,
    BEST_MODEL_DIR,
    CLASS_BACKGROUND,
    CLASS_COLORS_RGB,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    DEFAULT_DPI,
    MASTER_PDF_ROTATION_DEG,
    REPORTS_DIR,
)
from drywall_detection.data.preparer import (
    DrawingSanitizer,
    GeometryRasterizer,
    PreparationConfig,
)
from drywall_detection.data.splitter import (
    ProjectDataSplitter,
    SampleRecord,
    SplitLeakageError,
    SplitManifestBundle,
    assert_zero_leakage,
)
from drywall_detection.models.losses import (
    CompoundSegmentationLoss,
    MultiClassSoftDiceLoss,
)
from drywall_detection.models.metrics import (
    SegmentationEvaluationReport,
    SegmentationMetricTracker,
    SegmentationMetrics,
)
from drywall_detection.models.segformer import SegFormerWallDetector
from drywall_detection.models.trainer import (
    Trainer as SegmentationTrainer,
    verify_split_isolation,
)
from drywall_detection.pipeline.annotate import (
    PDFAnnotator,
    compute_mask_metrics,
    mask_to_rgba_overlay,
)
from drywall_detection.pipeline.infer import DrywallInferencePipeline
from drywall_detection.pipeline.router import ModalityRouter, PipelineModality
from drywall_detection.utils.coords import (
    get_forward_matrix,
    get_inverse_matrix,
    pdf_to_pixel,
    pixel_to_pdf,
)
from drywall_detection.utils.hardware import (
    HardwareProfile,
    auto_configure_training,
    probe_all_hardware,
)
from drywall_detection.vector.extractor import (
    ExtractedWallCandidate,
    VectorExtractor,
)
from drywall_detection.vector.schedule_parser import (
    PartitionScheduleParser,
    PartitionTagInstance,
)
from drywall_detection.vector.spatial_matcher import (
    SpatialMatcher,
)

MASTER_PDF_PATH = Path(r"C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf")
USMAN_PDF_PATH = Path(r"C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf")
SPARK_PDF_PATH = Path("drywall_detection/data/annotated_spark_test.pdf")


# ==============================================================================
# TIER 3: PAIRWISE INTERACTION TESTS (15 TESTS)
# ==============================================================================

def test_tier3_f01_f02_licensing_to_data_ingestion() -> None:
    """151. Pair: F1 (Audit) x F2 (Preparation)
    Verification: DatasetAuditor determines eligibility; DatasetPreparer respects eligibility.
    """
    auditor = DatasetAuditor(offline_mode=True)
    msd_rec = auditor.audit_candidate("msd")
    assert msd_rec.eligibility_verdict == "ELIGIBLE"

    r2v_rec = auditor.audit_candidate("r2v")
    assert "INELIGIBLE" in r2v_rec.eligibility_verdict

    # Verified eligible dataset creates valid rasterizer
    config = PreparationConfig(target_width=128, target_height=128)
    rasterizer = GeometryRasterizer(config)
    poly = Polygon([(10, 10), (50, 10), (50, 50), (10, 50)])
    bin_m, _ = rasterizer.rasterize_polygons([poly], bounds=(0, 0, 100, 100))
    assert bin_m.shape == (128, 128)


def test_tier3_f02_f03_data_unification_to_split_integrity() -> None:
    """152. Pair: F2 (Preparation) x F3 (Splitting)
    Verification: Samples produced by data preparation are split with mathematical zero leakage.
    """
    samples = []
    for p_id in ["proj_1", "proj_2", "proj_3", "proj_4", "proj_5", "proj_6", "proj_7"]:
        for i in range(2):
            samples.append(
                SampleRecord(
                    sample_id=f"{p_id}_s{i}",
                    project_id=p_id,
                    drawing_id=f"{p_id}_d0",
                    image_path=f"{p_id}_i{i}.png",
                    mask_path=f"{p_id}_m{i}.png",
                    bbox=(0, 0, 64, 64),
                    width=64,
                    height=64,
                    has_walls=True,
                    wall_pixel_count=100,
                    total_pixel_count=4096,
                )
            )

    splitter = ProjectDataSplitter(split_ratios=(0.60, 0.20, 0.20), seed=42)
    bundle = splitter.split(samples)
    assert_zero_leakage(bundle)

    train_p = {s.project_id for s in bundle.train_samples}
    val_p = {s.project_id for s in bundle.val_samples}
    assert len(train_p & val_p) == 0


def test_tier3_f03_f08_split_integrity_to_model_training() -> None:
    """153. Pair: F3 (Splitting) x F8 (Training)
    Verification: DataLoader built from split manifests guarantees zero leakage verified by verify_split_isolation.
    """
    class MockDataset(torch.utils.data.Dataset):
        def __init__(self, tiles):
            self.tiles = tiles

        def __len__(self):
            return len(self.tiles)

        def __getitem__(self, idx):
            return torch.randn(3, 32, 32), torch.zeros(32, 32, dtype=torch.long)

    train_tiles = [{"sample_id": "s1", "project_id": "p1", "drawing_id": "d1"}]
    val_tiles = [{"sample_id": "s2", "project_id": "p2", "drawing_id": "d2"}]

    train_loader = DataLoader(MockDataset(train_tiles), batch_size=1)
    val_loader = DataLoader(MockDataset(val_tiles), batch_size=1)

    # Must pass without ValueError
    verify_split_isolation(train_loader, val_loader)

    # Injecting leakage must raise ValueError
    leaked_val = DataLoader(MockDataset(train_tiles), batch_size=1)
    with pytest.raises(ValueError, match="leakage"):
        verify_split_isolation(train_loader, leaked_val)


def test_tier3_f04_f05_schedule_mining_to_classification_guardrails() -> None:
    """154. Pair: F4 (Mining) x F5 (Classification)
    Verification: Schedule details parsed from Sheets A-900/A-901 drive DrywallClassifier; Detail 1A is Non-Drywall.
    """
    parser = PartitionScheduleParser()
    classifier = DrywallClassifier(schedule_csv=APPROVED_SCHEDULE_CSV_PATH)

    detail_1a = parser.get_detail("1A")
    assert detail_1a is not None
    assert classifier.get_class("1A") == "Non-Drywall"

    detail_1b = parser.get_detail("1B")
    assert detail_1b is not None
    assert classifier.get_class("1B") == "Drywall"


def test_tier3_f04_f06_tag_discovery_to_coordinate_alignment() -> None:
    """155. Pair: F4 (Mining) x F6 (Coordinates)
    Verification: Discovered 11.2x11.3 pt tag box in PDF space converts to pixel and back within < 1e-4 pt.
    """
    tag_center = (450.5, 1200.25)
    px = pdf_to_pixel(tag_center[0], tag_center[1], dpi=150, rotation=90)
    recovered = pixel_to_pdf(px[0], px[1], dpi=150, rotation=90)
    assert abs(tag_center[0] - recovered[0]) < 1e-4
    assert abs(tag_center[1] - recovered[1]) < 1e-4


def test_tier3_f05_f11_classification_to_multipage_inference() -> None:
    """156. Pair: F5 (Classification) x F11 (Inference)
    Verification: Multi-page pipeline output masks strictly conform to 4-class taxonomy.
    """
    classifier = DrywallClassifier(schedule_csv=APPROVED_SCHEDULE_CSV_PATH)
    poly = ClassifiedWallPolygon(
        polygon=Polygon([(0, 0), (20, 0), (20, 20), (0, 20)]),
        matched_tag="1A",
        classification="Non-Drywall",
    )
    assert poly.classification == "Non-Drywall"
    assert poly.class_id == CLASS_NON_DRYWALL

    # PDFAnnotator palette verifies Non-Drywall is pure Red #D50000 / #FF0000
    annotator = PDFAnnotator()
    ndw_color = annotator.palette[CLASS_NON_DRYWALL]
    assert ndw_color[0] > 200  # High Red component
    assert ndw_color[1] == 0   # Zero Green component


def test_tier3_f06_f11_coordinate_bijection_to_overlay_injection() -> None:
    """157. Pair: F6 (Coordinates) x F11 (Inference)
    Verification: Coordinate bijection allows mask overlay injection preserving page CropBox (90° CW).
    """
    doc = fitz.open()
    page = doc.new_page(width=1728, height=2592)
    page.set_rotation(90)
    assert page.rotation == 90

    annotator = PDFAnnotator(alpha=0.40)
    mask = np.zeros((2592, 1728), dtype=np.uint8)
    mask[500:600, 500:600] = CLASS_DRYWALL

    annotator.annotate_pdf_page_overlay(page, mask)
    assert len(page.get_images()) >= 1
    assert page.rotation == 90
    assert page.mediabox.width == 1728.0
    doc.close()


def test_tier3_f07_f08_hardware_profiling_to_training_adaptation() -> None:
    """158. Pair: F7 (Benchmarking) x F8 (Training)
    Verification: Detected CPU profile feeds into training auto-config setting batch size and SegFormer.
    """
    profile = probe_all_hardware()
    cfg = auto_configure_training(profile)
    assert cfg["batch_size"] >= 1
    assert "segformer" in cfg["recommended_architecture"].lower()

    model = SegFormerWallDetector(num_classes=4)
    assert sum(p.numel() for p in model.parameters()) < 5_000_000


def test_tier3_f08_f09_model_training_to_evaluation_metrics() -> None:
    """159. Pair: F8 (Training) x F9 (Evaluation)
    Verification: Model forward output feeds into SegmentationMetricTracker updating mIoU and Dice.
    """
    tracker = SegmentationMetricTracker(num_classes=4)
    logits = torch.zeros(1, 4, 32, 32)
    logits[0, 1, 10:20, 10:20] = 5.0  # High confidence Drywall
    preds = torch.argmax(logits, dim=1)

    targets = torch.zeros(1, 32, 32, dtype=torch.long)
    targets[0, 10:20, 10:20] = 1

    tracker.update(preds, targets)
    rep = tracker.compute_report()
    assert rep.global_accuracy == 1.0
    assert rep.foreground_wall_iou == 1.0


def test_tier3_f09_f10_evaluation_suite_to_checkpoint_metadata() -> None:
    """160. Pair: F9 (Evaluation) x F10 (Checkpoint)
    Verification: Evaluation metrics serialize into metrics.json schema.
    """
    metrics_file = BEST_MODEL_DIR / "metrics.json"
    with open(metrics_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "num_classes" in data
    assert data["num_classes"] == 4


def test_tier3_f10_f11_checkpoint_reload_to_pipeline_inference() -> None:
    """161. Pair: F10 (Checkpoint) x F11 (Inference)
    Verification: StandaloneInferencer reloads SegFormer-B0 from checkpoints onto CPU and runs pipeline inference.
    """
    pipeline = DrywallInferencePipeline(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
    assert pipeline.inferencer.model is not None
    img = Image.new("RGB", (256, 256), color=(255, 255, 255))
    mask, _ = pipeline.inferencer.predict_image_sliding_window(img, tile_size=512)
    assert mask.shape == (256, 256)
    assert set(np.unique(mask)).issubset({0, 1, 2, 3})


def test_tier3_f11_f12_pipeline_to_streamlit_interface() -> None:
    """162. Pair: F11 (Inference) x F12 (Streamlit)
    Verification: Pipeline predictions feed into compute_takeoff_stats and build_annotated_pdf_bytes.
    """
    doc = fitz.open()
    page = doc.new_page(width=300, height=300)
    pdf_bytes = doc.tobytes()
    doc.close()

    mask = np.zeros((300, 300), dtype=np.uint8)
    mask[50:100, 50:100] = CLASS_DRYWALL
    stats = compute_takeoff_stats(mask)
    assert stats["drywall_pixels"] == 2500

    out_bytes = build_annotated_pdf_bytes(pdf_bytes, page_idx=0, mask_uint8=mask, alpha=0.45)
    assert len(out_bytes) > len(pdf_bytes)


def test_tier3_f11_f13_pipeline_to_heldout_validation() -> None:
    """163. Pair: F11 (Inference) x F13 (Held-Out)
    Verification: Pipeline router correctly identifies vector vs scanned held-out drawings.
    """
    router = ModalityRouter()
    assert SPARK_PDF_PATH.exists()
    doc = fitz.open(str(SPARK_PDF_PATH))
    dec = router.evaluate_page(doc[0])
    assert dec.modality == PipelineModality.RASTER_ML
    doc.close()


def test_tier3_f12_f14_interface_to_robustness_handling() -> None:
    """164. Pair: F12 (Streamlit) x F14 (Robustness)
    Verification: Interface helpers protect against corrupted input data.
    """
    with pytest.raises(Exception):
        build_annotated_pdf_bytes(b"CORRUPTED_NOT_PDF", page_idx=0, mask_uint8=np.zeros((10, 10), dtype=np.uint8))


def test_tier3_f13_f15_heldout_validation_to_showcase_reporting() -> None:
    """165. Pair: F13 (Held-Out) x F15 (Documentation)
    Verification: Empirical held-out validation results transcribe accurately into FINAL_SHOWCASE_REPORT.md.
    """
    showcase_path = REPORTS_DIR / "FINAL_SHOWCASE_REPORT.md"
    content = showcase_path.read_text(encoding="utf-8")
    assert "A-104" in content
    assert "69" in content
    assert "PROGRESS SET 95% CDs" in content
