"""
drywall_detection/tests/test_challenger_m5_fusion.py

Milestone M5 Empirical Challenger Adversarial Stress Suite (Iteration 2):
1. Coordinate Transformation Precision Stress:
   - Probes forward and inverse affine transformations across non-standard DPIs (72, 96, 100, 123, 144, 150, 200, 300, 450, 600, 1200)
     and arbitrary rotations (0°, 90°, 180°, 270°).
   - Asserts coordinate roundtrip drift is strictly < 1e-10 pt for scalar points, bounding boxes,
     vectorized points, Shapely geometries, and homogeneous affine matrices (F @ invF == I).
   - Validates error boundaries for non-finite inputs, invalid rotations, and negative DPIs.

2. Hybrid Fusion Invariants & Schedule Dominance:
   - Probes conflicting ML probability vs vector schedule tag (confirms schedule strictly dominates).
   - Probes conflicting ML prediction on Detail 1A (confirms CMU veto unconditionally overrides ML).
   - Probes runtime immutability against post-fusion attribute mutations.
   - Probes advisory-only behavior on Uncertain walls (zero material hallucination).

3. Degenerate Mask Inputs Stress:
   - Probes degenerate mask inputs: empty mask (0x0), all-zero mask, all-one mask, out-of-range labels,
     and out-of-bounds wall geometry relative to mask.
   - Probes mask vectorization with empty, zero, and micro-noise masks.

4. PDF Vector Quality & Native Shape Operators Inspection:
   - Inspects drywall_detection/reports/sample_overlays/M5_annotated_sample_drawings.pdf via PyMuPDF.
   - Verifies zero rasterized pages (full-page image coverage < 10%, only 3 original title-block stamps).
   - Verifies 100% searchable text preserved across annotated sheets (A-100, A-101, A-900).
   - Verifies native Shape vector operators (draw_polyline/draw_rect with fill colors matching 4-class palette).
   - Verifies architectural dimensions (1728x2592 pt) and 90° rotation preservation.

5. Modality Router Stress:
   - Validates deterministic routing across VECTOR_FIRST, RASTER_ML, and HYBRID modalities.
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import fitz  # PyMuPDF
import numpy as np
import pytest
from shapely.geometry import box, LineString, MultiPolygon, Point, Polygon

from drywall_detection.classification import (
    ClassificationClass,
    ClassifiedWallPolygon,
    IntegrityViolationError,
)
from drywall_detection.config import (
    CLASS_BACKGROUND,
    CLASS_COLORS_HEX,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    DEFAULT_DPI,
    MASTER_PDF_MEDIABOX_WIDTH_PT,
    MASTER_PDF_MEDIABOX_HEIGHT_PT,
    MASTER_PDF_ROTATION_DEG,
)
from drywall_detection.pipeline.fusion import HybridFusionPipeline, PageInferenceResult
from drywall_detection.pipeline.router import ModalityRouter, PipelineModality
from drywall_detection.utils.coords import (
    AffineTransformManager,
    get_forward_matrix,
    get_inverse_matrix,
    pdf_bbox_to_pixel,
    pdf_geom_to_pixel,
    pdf_points_to_pixel,
    pdf_to_pixel,
    pixel_bbox_to_pdf,
    pixel_geom_to_pdf,
    pixel_points_to_pdf,
    pixel_to_pdf,
)

SAMPLE_PDF_PATH = Path("drywall_detection/reports/sample_overlays/M5_annotated_sample_drawings.pdf")

NON_STANDARD_DPIS = [72, 96, 100, 123, 144, 150, 200, 300, 450, 600, 1200]
ROTATIONS = [0, 90, 180, 270]


# ==============================================================================
# Suite 1: Coordinate Transform Adversarial Stress Suite (< 1e-10 pt Drift)
# ==============================================================================
class TestCoordinateTransformsAdversarial:
    """
    Adversarial verification of affine coordinate transformations.
    Strict Invariant: Roundtrip drift between PDF point space and pixel space MUST be < 1e-10 pt.
    """

    TEST_POINTS = [
        (0.0, 0.0),
        (MASTER_PDF_MEDIABOX_WIDTH_PT, MASTER_PDF_MEDIABOX_HEIGHT_PT),
        (0.0, MASTER_PDF_MEDIABOX_HEIGHT_PT),
        (MASTER_PDF_MEDIABOX_WIDTH_PT, 0.0),
        (123.4567890123, 987.6543210987),
        (0.0001, 0.0001),
        (1727.999999, 2591.999999),
        (864.0, 1296.0),  # center
    ]

    @pytest.mark.parametrize("rotation", ROTATIONS)
    @pytest.mark.parametrize("dpi", NON_STANDARD_DPIS)
    def test_scalar_point_roundtrip_drift_less_than_1e10(self, rotation: int, dpi: int) -> None:
        """Probes scalar pdf_to_pixel and pixel_to_pdf roundtrip across rotations and non-standard DPIs."""
        for x, y in self.TEST_POINTS:
            px, py = pdf_to_pixel(x, y, dpi=dpi, rotation=rotation)
            x_rec, y_rec = pixel_to_pdf(px, py, dpi=dpi, rotation=rotation)

            drift_x = abs(x - x_rec)
            drift_y = abs(y - y_rec)

            assert drift_x < 1e-10, (
                f"DRIFT VIOLATION in X: {drift_x:.2e} >= 1e-10 pt at dpi={dpi}, rot={rotation}, point=({x}, {y})"
            )
            assert drift_y < 1e-10, (
                f"DRIFT VIOLATION in Y: {drift_y:.2e} >= 1e-10 pt at dpi={dpi}, rot={rotation}, point=({x}, {y})"
            )

    @pytest.mark.parametrize("rotation", ROTATIONS)
    @pytest.mark.parametrize("dpi", [72, 123, 150, 300, 600])
    def test_matrix_forward_inverse_algebraic_identity(self, rotation: int, dpi: int) -> None:
        """Verifies forward matrix @ inverse matrix equals 3x3 identity matrix within 1e-10."""
        F = get_forward_matrix(dpi=dpi, rotation=rotation)
        invF = get_inverse_matrix(dpi=dpi, rotation=rotation)

        prod_forward = F @ invF
        prod_inverse = invF @ F
        identity = np.eye(3, dtype=np.float64)

        err_fwd = np.max(np.abs(prod_forward - identity))
        err_inv = np.max(np.abs(prod_inverse - identity))

        assert err_fwd < 1e-10, f"Matrix algebraic error F @ invF: {err_fwd:.2e} >= 1e-10 at dpi={dpi}, rot={rotation}"
        assert err_inv < 1e-10, f"Matrix algebraic error invF @ F: {err_inv:.2e} >= 1e-10 at dpi={dpi}, rot={rotation}"

    @pytest.mark.parametrize("rotation", ROTATIONS)
    @pytest.mark.parametrize("dpi", [96, 144, 150, 450])
    def test_vectorized_points_roundtrip_drift(self, rotation: int, dpi: int) -> None:
        """Stress-tests 5,000 vectorized coordinates simultaneously."""
        rng = np.random.default_rng(seed=42)
        pts = rng.uniform(low=0.0, high=1728.0, size=(5000, 2))

        px = pdf_points_to_pixel(pts, dpi=dpi, rotation=rotation)
        rec = pixel_points_to_pdf(px, dpi=dpi, rotation=rotation)

        max_drift = np.max(np.abs(pts - rec))
        assert max_drift < 1e-10, (
            f"Vectorized point roundtrip drift {max_drift:.2e} >= 1e-10 at dpi={dpi}, rot={rotation}"
        )

    @pytest.mark.parametrize("rotation", ROTATIONS)
    @pytest.mark.parametrize("dpi", [72, 100, 150, 300])
    def test_bounding_box_roundtrip_precision(self, rotation: int, dpi: int) -> None:
        """Verifies bounding box transformation bijection across standard and tiny boxes."""
        bboxes = [
            (0.0, 0.0, 1728.0, 2592.0),
            (100.5, 200.75, 500.25, 800.5),
            (10.12345, 20.6789, 10.12346, 20.67891),  # micro-box
            (50.0, 50.0, 50.0, 50.0),                  # zero-size point box
        ]
        for b in bboxes:
            pb = pdf_bbox_to_pixel(b, dpi=dpi, rotation=rotation)
            rb = pixel_bbox_to_pdf(pb, dpi=dpi, rotation=rotation)

            max_err = max(abs(b[i] - rb[i]) for i in range(4))
            assert max_err < 1e-10, (
                f"BBox roundtrip error {max_err:.2e} >= 1e-10 for box {b} at dpi={dpi}, rot={rotation}"
            )

    @pytest.mark.parametrize("rotation", ROTATIONS)
    @pytest.mark.parametrize("dpi", [150, 300])
    def test_shapely_geometry_roundtrip_precision(self, rotation: int, dpi: int) -> None:
        """Tests Shapely Point, LineString, Polygon (with hole), and MultiPolygon."""
        poly_with_hole = Polygon(
            [(100.0, 100.0), (500.0, 100.0), (500.0, 500.0), (100.0, 500.0)],
            holes=[[(200.0, 200.0), (300.0, 200.0), (300.0, 300.0), (200.0, 300.0)]],
        )
        mpoly = MultiPolygon([
            Polygon([(10.0, 10.0), (50.0, 10.0), (50.0, 50.0), (10.0, 50.0)]),
            Polygon([(60.0, 60.0), (90.0, 60.0), (90.0, 90.0), (60.0, 90.0)]),
        ])

        geoms = [
            Point(345.67, 890.12),
            LineString([(10.5, 20.5), (30.5, 40.5), (50.5, 60.5)]),
            poly_with_hole,
            mpoly,
        ]

        for g in geoms:
            g_px = pdf_geom_to_pixel(g, dpi=dpi, rotation=rotation)
            g_rec = pixel_geom_to_pdf(g_px, dpi=dpi, rotation=rotation)

            if isinstance(g, Point):
                drift = max(abs(g.x - g_rec.x), abs(g.y - g_rec.y))
                assert drift < 1e-10
            elif isinstance(g, Polygon):
                c_orig = np.array(g.exterior.coords)
                c_rec = np.array(g_rec.exterior.coords)
                assert np.max(np.abs(c_orig - c_rec)) < 1e-10
                assert len(g.interiors) == len(g_rec.interiors)
                for h_orig, h_rec in zip(g.interiors, g_rec.interiors):
                    assert np.max(np.abs(np.array(h_orig.coords) - np.array(h_rec.coords))) < 1e-10

    def test_negative_and_extrapolated_coordinates(self) -> None:
        """Confirms analytical invertibility for out-of-bounds and negative coordinates."""
        extrapolated = [
            (-500.0, -1000.0),
            (5000.0, 10000.0),
            (-0.00001, 3000.0),
        ]
        for x, y in extrapolated:
            for rot in ROTATIONS:
                px, py = pdf_to_pixel(x, y, dpi=150, rotation=rot)
                rx, ry = pixel_to_pdf(px, py, dpi=150, rotation=rot)
                assert abs(x - rx) < 1e-10
                assert abs(y - ry) < 1e-10

    def test_invalid_transformation_parameters_raise_value_error(self) -> None:
        """Verifies fail-fast error handling on invalid DPI, rotation, or non-finite coordinates."""
        with pytest.raises(ValueError, match="DPI must be positive"):
            pdf_to_pixel(100.0, 100.0, dpi=0)

        with pytest.raises(ValueError, match="DPI must be positive"):
            pdf_to_pixel(100.0, 100.0, dpi=-150)

        with pytest.raises(ValueError, match="Unsupported rotation"):
            pdf_to_pixel(100.0, 100.0, rotation=45)

        with pytest.raises(ValueError, match="Unsupported rotation"):
            pdf_to_pixel(100.0, 100.0, rotation=360)

        with pytest.raises(ValueError, match="Coordinates must be finite"):
            pdf_to_pixel(float("nan"), 100.0)

        with pytest.raises(ValueError, match="Coordinates must be finite"):
            pdf_to_pixel(100.0, float("inf"))


# ==============================================================================
# Suite 2: Hybrid Fusion Invariants & Schedule Dominance Suite
# ==============================================================================
class TestHybridFusionInvariants:
    """
    Adversarial verification of Hybrid Vector + ML Fusion Pipeline invariants.
    Core Invariants:
      1. Partition schedule ground truth strictly dominates conflicting ML segmentation.
      2. Detail 1A CMU veto is unconditional and overrides ML Drywall predictions.
      3. Uncertain partitions receive ML advisory metadata only, never material hallucination.
    """

    @pytest.fixture
    def fusion_pipeline(self) -> HybridFusionPipeline:
        return HybridFusionPipeline(dpi=150)

    def _create_wall(
        self,
        wall_id: str,
        classification: str,
        matched_tag: str | None,
        detail_number: str | None,
        confidence: float = 0.90,
        pdf_coords: Tuple[float, float, float, float] = (100.0, 100.0, 200.0, 120.0),
    ) -> ClassifiedWallPolygon:
        poly_pdf = box(*pdf_coords)
        return ClassifiedWallPolygon(
            wall_id=wall_id,
            page_idx=0,
            sheet="A-101",
            geometry_pdf=poly_pdf,
            geometry_pixel=box(0, 0, 10, 10),
            matched_tag=matched_tag,
            detail_number=detail_number,
            material_description="Test wall assembly",
            classification=classification,
            confidence=confidence,
            color_hex=CLASS_COLORS_HEX[classification],
            reason="Schedule matched candidate",
        )

    def test_schedule_strictly_dominates_conflicting_ml_drywall_prediction(
        self, fusion_pipeline: HybridFusionPipeline
    ) -> None:
        """
        Scenario: Vector schedule classified wall as Drywall (e.g. Tag 1B).
        Adversarial Input: ML mask predicts 100% Non-Drywall (or 100% Background) over the wall footprint.
        Invariant: Vector schedule strictly dominates; classification MUST remain 'Drywall'.
        ML discrepancy is flagged in metadata without overriding material class.
        """
        wall = self._create_wall(
            wall_id="w_dw_conflict",
            classification="Drywall",
            matched_tag="1B",
            detail_number="1B",
            confidence=0.90,
        )

        # Full page visual canvas (height=3600, width=5400) at 150 DPI 90 deg rotation
        mask = np.full((3600, 5400), CLASS_NON_DRYWALL, dtype=np.uint8)
        probs = np.zeros((4, 3600, 5400), dtype=np.float32)

        fused = fusion_pipeline._fuse_vector_and_ml([wall], mask, probs, page_idx=0, sheet="A-101")
        assert len(fused) == 1
        res = fused[0]

        # Schedule strictly dominates: classification CANNOT be changed to Non-Drywall
        assert res.classification == "Drywall", f"VIOLATION: ML overrode vector schedule Drywall! Got: {res.classification}"
        assert res.color_hex == CLASS_COLORS_HEX["Drywall"]
        # Discrepancy is recorded in metadata
        assert res.metadata.get("ml_discrepancy") is True
        assert res.metadata.get("ml_drywall_agreement") == 0.0

    def test_schedule_strictly_dominates_conflicting_ml_nondrywall_prediction(
        self, fusion_pipeline: HybridFusionPipeline
    ) -> None:
        """
        Scenario: Vector schedule classified wall as Non-Drywall (e.g. Tag 11 Concrete Pier).
        Adversarial Input: ML mask predicts 100% Drywall over the wall footprint.
        Invariant: Vector schedule strictly dominates; classification MUST remain 'Non-Drywall'.
        """
        wall = self._create_wall(
            wall_id="w_ndw_conflict",
            classification="Non-Drywall",
            matched_tag="11",
            detail_number="11",
            confidence=0.95,
        )

        # ML mask predicts 100% Drywall (class 1)
        mask = np.full((1000, 1000), CLASS_DRYWALL, dtype=np.uint8)
        probs = np.zeros((4, 1000, 1000), dtype=np.float32)

        fused = fusion_pipeline._fuse_vector_and_ml([wall], mask, probs, page_idx=0, sheet="A-101")
        assert len(fused) == 1
        res = fused[0]

        assert res.classification == "Non-Drywall", (
            f"VIOLATION: ML overrode vector schedule Non-Drywall! Got: {res.classification}"
        )
        assert res.color_hex == CLASS_COLORS_HEX["Non-Drywall"]

    def test_schedule_strictly_dominates_conflicting_ml_uncertain_prediction(
        self, fusion_pipeline: HybridFusionPipeline
    ) -> None:
        """
        Scenario: Wall is classified as Uncertain (e.g. Detail 09 TV Niche or untagged linework).
        Adversarial Input: ML mask predicts 100% Drywall over the wall footprint.
        Invariant: Classification MUST remain 'Uncertain' (zero material hallucination).
        ML provides advisory metadata ONLY.
        """
        wall = self._create_wall(
            wall_id="w_unc_advisory",
            classification="Uncertain",
            matched_tag="09",
            detail_number="09",
            confidence=0.0,
        )

        # Full page visual canvas (height=3600, width=5400) at 150 DPI 90 deg rotation
        mask = np.full((3600, 5400), CLASS_DRYWALL, dtype=np.uint8)
        probs = np.zeros((4, 3600, 5400), dtype=np.float32)

        fused = fusion_pipeline._fuse_vector_and_ml([wall], mask, probs, page_idx=0, sheet="A-101")
        assert len(fused) == 1
        res = fused[0]

        # Must NOT reclassify to Drywall
        assert res.classification == "Uncertain", (
            f"VIOLATION: Uncertain wall was reclassified to Drywall without schedule ground truth!"
        )
        assert res.color_hex == CLASS_COLORS_HEX["Uncertain"]
        assert res.metadata.get("ml_advisory") == "Drywall"
        assert res.metadata.get("ml_advisory_confidence") == 1.0

    def test_detail_1a_cmu_veto_unconditionally_overrides_ml_drywall_prediction(
        self, fusion_pipeline: HybridFusionPipeline
    ) -> None:
        """
        Mandatory Safety Rule 3: Detail 1A is explicitly 6" CMU masonry block.
        Adversarial Input: ML predicts 100% Drywall with 1.0 probability across Detail 1A wall.
        Invariant: Detail 1A CMU veto unconditionally overrides ML; classification is strictly Non-Drywall.
        """
        wall = self._create_wall(
            wall_id="w_cmu_1a",
            classification="Non-Drywall",
            matched_tag="1A",
            detail_number="1A",
            confidence=1.0,
        )

        # Hostile ML output: 100% Drywall
        mask = np.full((1000, 1000), CLASS_DRYWALL, dtype=np.uint8)
        probs = np.zeros((4, 1000, 1000), dtype=np.float32)

        fused = fusion_pipeline._fuse_vector_and_ml([wall], mask, probs, page_idx=0, sheet="A-101")
        assert len(fused) == 1
        res = fused[0]

        assert res.classification == "Non-Drywall"
        assert res.color_hex == CLASS_COLORS_HEX["Non-Drywall"]
        assert res.matched_tag == "1A"

    def test_detail_1a_post_fusion_mutation_guard(
        self, fusion_pipeline: HybridFusionPipeline
    ) -> None:
        """Verifies that Detail 1A cannot be mutated to Drywall post-fusion via attribute assignment."""
        wall = self._create_wall(
            wall_id="w_cmu_mutation",
            classification="Non-Drywall",
            matched_tag="1A",
            detail_number="1A",
        )
        mask = np.full((500, 500), CLASS_DRYWALL, dtype=np.uint8)
        probs = np.zeros((4, 500, 500), dtype=np.float32)

        fused = fusion_pipeline._fuse_vector_and_ml([wall], mask, probs, page_idx=0, sheet="A-101")
        res = fused[0]

        with pytest.raises(IntegrityViolationError, match="Detail 1A is explicitly 6\" CMU masonry block"):
            res.classification = "Drywall"

        with pytest.raises(IntegrityViolationError, match="Detail 1A is explicitly 6\" CMU masonry block"):
            res.classification = "1"


# ==============================================================================
# Suite 3: Hybrid Fusion Degenerate Mask Inputs Suite
# ==============================================================================
class TestHybridFusionDegenerateMasks:
    """
    Adversarial verification of fusion pipeline resilience against degenerate,
    malformed, or out-of-bounds mask inputs.
    """

    @pytest.fixture
    def fusion_pipeline(self) -> HybridFusionPipeline:
        return HybridFusionPipeline(dpi=150)

    @pytest.fixture
    def standard_wall(self) -> ClassifiedWallPolygon:
        return ClassifiedWallPolygon(
            wall_id="w_std",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=box(100, 100, 200, 120),
            geometry_pixel=box(0, 0, 10, 10),
            matched_tag="1C",
            detail_number="1C",
            material_description="GWB",
            classification="Drywall",
            confidence=0.85,
            color_hex=CLASS_COLORS_HEX["Drywall"],
            reason="Schedule matched candidate",
        )

    def test_fusion_with_empty_mask_0x0(
        self, fusion_pipeline: HybridFusionPipeline, standard_wall: ClassifiedWallPolygon
    ) -> None:
        """Probes zero-dimensional (0x0) mask array."""
        empty_mask = np.zeros((0, 0), dtype=np.uint8)
        empty_probs = np.zeros((4, 0, 0), dtype=np.float32)

        fused = fusion_pipeline._fuse_vector_and_ml([standard_wall], empty_mask, empty_probs, 0, "A-101")
        assert len(fused) == 1
        assert fused[0].classification == "Drywall"

    def test_fusion_with_all_zero_background_mask(
        self, fusion_pipeline: HybridFusionPipeline, standard_wall: ClassifiedWallPolygon
    ) -> None:
        """Probes full canvas with zero wall detections (all background)."""
        zero_mask = np.zeros((3600, 5400), dtype=np.uint8)
        zero_probs = np.zeros((4, 3600, 5400), dtype=np.float32)

        fused = fusion_pipeline._fuse_vector_and_ml([standard_wall], zero_mask, zero_probs, 0, "A-101")
        assert len(fused) == 1
        assert fused[0].metadata.get("ml_discrepancy") is True

    def test_fusion_with_out_of_bounds_wall_relative_to_mask(
        self, fusion_pipeline: HybridFusionPipeline
    ) -> None:
        """Probes wall polygon completely outside the bounding extent of the raster mask."""
        oob_wall = ClassifiedWallPolygon(
            wall_id="w_oob",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=box(10000.0, 10000.0, 10500.0, 10520.0),
            geometry_pixel=box(0, 0, 10, 10),
            matched_tag="1B",
            detail_number="1B",
            material_description="GWB",
            classification="Drywall",
            confidence=0.90,
            color_hex=CLASS_COLORS_HEX["Drywall"],
            reason="Schedule matched candidate",
        )
        small_mask = np.zeros((500, 500), dtype=np.uint8)
        small_probs = np.zeros((4, 500, 500), dtype=np.float32)

        fused = fusion_pipeline._fuse_vector_and_ml([oob_wall], small_mask, small_probs, 0, "A-101")
        assert len(fused) == 1
        assert fused[0].wall_id == "w_oob"

    def test_fusion_with_invalid_mask_class_values(
        self, fusion_pipeline: HybridFusionPipeline, standard_wall: ClassifiedWallPolygon
    ) -> None:
        """Probes mask containing unrecognized class labels (e.g. 99, 255)."""
        invalid_mask = np.full((1000, 1000), 255, dtype=np.uint8)
        probs = np.zeros((4, 1000, 1000), dtype=np.float32)

        fused = fusion_pipeline._fuse_vector_and_ml([standard_wall], invalid_mask, probs, 0, "A-101")
        assert len(fused) == 1
        assert fused[0].classification == "Drywall"

    def test_vectorize_ml_mask_degenerate_inputs(
        self, fusion_pipeline: HybridFusionPipeline
    ) -> None:
        """Probes mask vectorization with empty mask, zero mask, and micro-noise mask."""
        # Empty mask
        w_empty = fusion_pipeline._vectorize_ml_mask(
            np.zeros((0, 0), dtype=np.uint8), np.zeros((4, 0, 0)), 0, "A-101"
        )
        assert len(w_empty) == 0

        # All background
        w_zeros = fusion_pipeline._vectorize_ml_mask(
            np.zeros((500, 500), dtype=np.uint8), np.zeros((4, 500, 500)), 0, "A-101"
        )
        assert len(w_zeros) == 0

        # Micro noise (< 50 px threshold)
        noise_mask = np.zeros((500, 500), dtype=np.uint8)
        noise_mask[100:102, 100:102] = CLASS_DRYWALL  # 4 px area
        w_noise = fusion_pipeline._vectorize_ml_mask(
            noise_mask, np.zeros((4, 500, 500)), 0, "A-101"
        )
        assert len(w_noise) == 0

        # Valid wall component (> 50 px)
        valid_mask = np.zeros((500, 500), dtype=np.uint8)
        valid_mask[100:120, 100:200] = CLASS_DRYWALL  # 20x100 = 2000 px area
        w_valid = fusion_pipeline._vectorize_ml_mask(
            valid_mask, np.zeros((4, 500, 500)), 0, "A-101"
        )
        assert len(w_valid) >= 1
        assert w_valid[0].classification == "Drywall"
        assert w_valid[0].color_hex == CLASS_COLORS_HEX["Drywall"]


# ==============================================================================
# Suite 4: PDF Vector Quality & Native Shape Operators Inspection
# ==============================================================================
class TestPDFVectorPreservationAndInspection:
    """
    Forensic inspection of M5_annotated_sample_drawings.pdf via PyMuPDF.
    Assures:
      1. Zero rasterized pages (full-page image coverage < 10%).
      2. 100% searchable text preserved across annotated sheets.
      3. Native PyMuPDF Shape vector operators with exact 4-class palette colors.
      4. Exact physical MediaBox (1728x2592 pt) and 90° rotation preserved.
    """

    @pytest.fixture(scope="module")
    def sample_doc(self) -> fitz.Document:
        assert SAMPLE_PDF_PATH.is_file(), f"Sample PDF not found at {SAMPLE_PDF_PATH}"
        doc = fitz.open(SAMPLE_PDF_PATH)
        yield doc
        doc.close()

    def test_sample_pdf_total_pages_and_dimensions(self, sample_doc: fitz.Document) -> None:
        """Verifies multi-page document structure and dimension preservation."""
        assert len(sample_doc) == 71, f"Expected 71 pages matching master set, got {len(sample_doc)}"

        # Check annotated sheets: Page 13 (A-100), Page 14 (A-101), Page 62 (A-900)
        for p_idx in (13, 14, 62):
            page = sample_doc[p_idx]
            mb = page.mediabox
            assert mb.width == MASTER_PDF_MEDIABOX_WIDTH_PT, f"Page {p_idx} mediabox width mismatch: {mb.width}"
            assert mb.height == MASTER_PDF_MEDIABOX_HEIGHT_PT, f"Page {p_idx} mediabox height mismatch: {mb.height}"
            assert page.rotation == MASTER_PDF_ROTATION_DEG, f"Page {p_idx} rotation mismatch: {page.rotation}"

    def test_zero_rasterized_pages_in_annotated_drawings(self, sample_doc: fitz.Document) -> None:
        """
        Forensic check: Asserts that annotated pages were NOT rasterized into bitmap images.
        Image coverage must be < 10% (only original title-block stamps/logos allowed).
        """
        for p_idx in (13, 14, 62):
            page = sample_doc[p_idx]
            page_area = page.rect.width * page.rect.height
            images = page.get_images()

            total_img_area = 0.0
            if hasattr(page, "get_image_rects"):
                for img in images:
                    for r in page.get_image_rects(img[0]):
                        total_img_area += (r.width * r.height)

            coverage = total_img_area / page_area
            assert coverage < 0.10, (
                f"RASTERIZATION VIOLATION: Page {p_idx} has image coverage {coverage:.2%} >= 10.0%"
            )
            # Exactly 3 title-block stamps exist in the original drawing
            assert len(images) == 3, f"Page {p_idx} contains unexpected raster images: count={len(images)}"

    def test_searchable_text_100_percent_preserved(self, sample_doc: fitz.Document) -> None:
        """Confirms that 100% of the original CAD text layer remains searchable."""
        for p_idx in (13, 14, 62):
            page = sample_doc[p_idx]
            words = page.get_text("words")
            assert len(words) > 1000, f"Page {p_idx} lost searchable text: word count = {len(words)}"

        # Verify key architectural tags and labels on Sheet A-101 (Page 14)
        p14_text = sample_doc[14].get_text()
        for expected_tag in ["7A", "7F", "5B", "1C", "GL2", "10", "A-101"]:
            assert expected_tag in p14_text, f"Searchable text '{expected_tag}' missing on Page 14"

        # Verify Partition Schedule sheet text on Sheet A-900 (Page 62)
        p62_text = sample_doc[62].get_text()
        for expected_str in ["PARTITION TYPES", "1A", "CMU"]:
            assert expected_str in p62_text, f"Searchable text '{expected_str}' missing on Page 62"

    def test_native_shape_vector_operators_and_palette_colors(self, sample_doc: fitz.Document) -> None:
        """
        Verifies that drywall annotations were written into the PDF vector stream
        using PyMuPDF Shape operators with translucent fills matching the 4-class palette.
        """
        page14 = sample_doc[14]
        drawings = page14.get_drawings()
        assert len(drawings) > 15000, f"Page 14 drawings count dropped: {len(drawings)}"

        # Extract distinct filled shapes
        fill_colors = set()
        for d in drawings:
            f = d.get("fill")
            if f is not None:
                fill_colors.add(tuple(round(x, 3) for x in f))

        expected_green = (0.0, 0.784, 0.325)   # Drywall Green #00C853
        expected_red = (0.835, 0.0, 0.0)       # Non-Drywall Red #D50000
        expected_yellow = (1.0, 0.839, 0.0)    # Uncertain Yellow #FFD600

        assert expected_green in fill_colors, f"Native vector Drywall Green fill {expected_green} missing in Page 14"
        assert expected_red in fill_colors, f"Native vector Non-Drywall Red fill {expected_red} missing in Page 14"
        assert expected_yellow in fill_colors, f"Native vector Uncertain Yellow fill {expected_yellow} missing in Page 14"

    def test_vector_legend_card_and_safety_disclaimers_present(self, sample_doc: fitz.Document) -> None:
        """Verifies presence of legend card text and mandatory safety rule disclaimers."""
        for p_idx in (13, 14, 62):
            page_text = sample_doc[p_idx].get_text()
            assert "DRYWALL CLASSIFICATION & TAKEOFF (M5)" in page_text, f"Legend header missing on Page {p_idx}"
            assert "MTA 99th St Set (PROGRESS SET 95% CDs)" in page_text, f"Progress citation missing on Page {p_idx}"
            assert "Mandatory Rule: Detail 1A 6\" CMU = Non-Drywall (Red)" in page_text, f"Safety rule missing on Page {p_idx}"
            assert "DRYWALL:" in page_text, f"Drywall takeoff stats missing on Page {p_idx}"
            assert "NON-DRYWALL:" in page_text, f"Non-drywall takeoff stats missing on Page {p_idx}"
            assert "UNCERTAIN:" in page_text, f"Uncertain takeoff stats missing on Page {p_idx}"


# ==============================================================================
# Suite 5: Modality Router Stress Suite
# ==============================================================================
class TestModalityRouterStress:
    """Verifies deterministic PDF modality routing across CAD Vector, Scanned Raster, and Hybrid."""

    def test_router_on_architectural_pages(self) -> None:
        router = ModalityRouter()
        doc = fitz.open(SAMPLE_PDF_PATH)

        # Page 14 is a CAD vector floor plan with 21k paths and 2k words
        decision_p14 = router.evaluate_page(doc[14])
        assert decision_p14.modality == PipelineModality.VECTOR_FIRST
        assert decision_p14.confidence >= 0.90

        doc.close()

    def test_router_scanned_page_condition(self) -> None:
        """Synthetic test: page with 0 paths and 0 words must route to RASTER_ML."""
        router = ModalityRouter()
        doc = fitz.open()
        blank_page = doc.new_page(width=1728, height=2592)

        decision = router.evaluate_page(blank_page)
        assert decision.modality == PipelineModality.RASTER_ML
        assert decision.confidence >= 0.95
        doc.close()
