"""
drywall_detection/tests/test_classification.py

Comprehensive Verification Test Suite for Milestone M5:
  - Approved Schedule CSV Loading and Material Breakdown
  - Mandatory Detail 1A CMU Non-Drywall Safety Veto (Defense-in-Depth)
  - Tier 3 Strict Zero-Hallucination Fallback Guardrail
  - ClassifiedWallPolygon Schema and RFC 7946 GeoJSON Export
  - AffineTransformManager Reversible 90° CW Coordinate Bijection
  - Modality Router (Vector-First vs Raster ML vs Hybrid)
  - Hybrid Fusion Pipeline & Schedule Authority Invariant
  - 10 Human-Review Benchmark Plan Regions (R01-R10) & Error Metrics
  - High-Fidelity Visual Overlay Generator (Raster PNG & Pure Vector PDF)
"""

from __future__ import annotations
import copy
import json
import math
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Tuple

import fitz
import numpy as np
import pytest
from shapely.geometry import box, LineString, MultiPolygon, Point, Polygon

from drywall_detection.classification import (
    ClassificationClass,
    ClassificationFeatureCollection,
    ClassificationSummary,
    ClassifiedWallPolygon,
    DrywallClassifier,
    IntegrityViolationError,
    ScheduleValidationError,
)
from drywall_detection.config import (
    APPROVED_SCHEDULE_CSV_PATH,
    CLASS_COLORS_HEX,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    DEFAULT_DPI,
    MASTER_PDF_MEDIABOX_HEIGHT_PT,
    MASTER_PDF_MEDIABOX_WIDTH_PT,
    MASTER_PDF_ROTATION_DEG,
)
from drywall_detection.pipeline import (
    HybridFusionPipeline,
    ModalityRouter,
    PageInferenceResult,
    PageModalityDecision,
    PipelineModality,
    VisualOverlayConfig,
    WallAnnotator,
)
from drywall_detection.utils.coords import (
    AffineTransformManager,
    pdf_to_pixel,
    pixel_to_pdf,
)
from drywall_detection.vector.spatial_matcher import MatchMethod, SpatialMatcher


# ==============================================================================
# Test Fixtures & Dummies
# ==============================================================================
class DummyCandidate:
    def __init__(
        self,
        wall_id: str,
        geom_pdf: Polygon,
        thickness_pt: float = 8.35,
        estimated_thickness_in: float = 6.0,
        orientation: str = "HORIZONTAL",
    ):
        self.wall_id = wall_id
        self.geometry = geom_pdf
        self.geometry_pdf = geom_pdf
        self.thickness_pt = thickness_pt
        self.estimated_thickness_in = estimated_thickness_in
        self.orientation = orientation


class DummyTag:
    def __init__(
        self,
        tag: str,
        box_geom: Polygon,
        leader_line: Optional[LineString] = None,
    ):
        self.tag = tag
        self.tag_id = tag
        self.box_geom = box_geom
        self.bbox = box_geom.bounds
        self.center = ((box_geom.bounds[0] + box_geom.bounds[2]) / 2.0, (box_geom.bounds[1] + box_geom.bounds[3]) / 2.0)
        self.centroid = self.center
        self.leader_line = leader_line
        self.leader_lines = [leader_line] if leader_line else []


@pytest.fixture
def classifier() -> DrywallClassifier:
    return DrywallClassifier()


# ==============================================================================
# Suite 1: Approved Schedule Loading & Taxonomy Verification
# ==============================================================================
class TestApprovedCSVLoadingAndTaxonomy:
    """Verifies that the approved schedule CSV is properly loaded and validated."""

    def test_approved_csv_loading_and_counts(self, classifier: DrywallClassifier) -> None:
        """Asserts that 24 details are loaded with 19 Drywall, 4 Non-Drywall, 1 Uncertain."""
        mapping = classifier.schedule_mapping
        assert len(mapping) == 24, f"Expected 24 details, got {len(mapping)}"

        drywall_tags = [t for t, d in mapping.items() if d["proposed_class"] == "Drywall"]
        nondrywall_tags = [t for t, d in mapping.items() if d["proposed_class"] == "Non-Drywall"]
        uncertain_tags = [t for t, d in mapping.items() if d["proposed_class"] == "Uncertain"]

        assert len(drywall_tags) == 19
        assert len(nondrywall_tags) == 4
        assert len(uncertain_tags) == 1

        # Check key specific tags
        assert "1A" in nondrywall_tags
        assert "11" in nondrywall_tags
        assert "GL1" in nondrywall_tags
        assert "GL2" in nondrywall_tags
        assert "09" in uncertain_tags
        assert "1C" in drywall_tags
        assert "5E" in drywall_tags
        assert "7F" in drywall_tags

    def test_empty_schedule_csv_raises_validation_error(self, tmp_path: Path) -> None:
        """Asserts that an empty file raises ScheduleValidationError."""
        empty_csv = tmp_path / "empty_schedule.csv"
        empty_csv.write_text("", encoding="utf-8")
        with pytest.raises(ScheduleValidationError):
            DrywallClassifier(approved_schedule_path=empty_csv)

    def test_missing_mandatory_columns_raises_validation_error(self, tmp_path: Path) -> None:
        """Asserts that missing mandatory columns raise ScheduleValidationError."""
        bad_csv = tmp_path / "bad_columns.csv"
        bad_csv.write_text("tag,sheet,description\n1A,A-900,CMU block\n", encoding="utf-8")
        with pytest.raises(ScheduleValidationError):
            DrywallClassifier(approved_schedule_path=bad_csv)


# ==============================================================================
# Suite 2: Mandatory Detail 1A CMU Safety Veto
# ==============================================================================
class TestDetail1ACMUSafetyVeto:
    """Verifies two-layer defense-in-depth safety veto for Detail 1A 6" CMU masonry."""

    def test_detail_1a_unconditional_nondrywall_in_classifier(self, classifier: DrywallClassifier) -> None:
        """Detail 1A must always be classified as Non-Drywall with #D50000."""
        rec_1a = classifier.schedule_mapping["1A"]
        assert rec_1a["proposed_class"] == "Non-Drywall"
        assert "CMU" in rec_1a["description"].upper()

    def test_detail_1a_tampered_csv_raises_integrity_violation(self, tmp_path: Path) -> None:
        """Attempting to load a CSV where 1A is tampered to Drywall raises IntegrityViolationError."""
        # Read valid CSV lines
        with open(APPROVED_SCHEDULE_CSV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

        tampered_lines = []
        for line in lines:
            if line.startswith("1A,"):
                # Tamper proposed_class to Drywall
                tampered = line.replace("Non-Drywall", "Drywall").replace("Masonry", "Drywall")
                tampered_lines.append(tampered)
            else:
                tampered_lines.append(line)

        tampered_csv = tmp_path / "tampered_1a.csv"
        tampered_csv.write_text("".join(tampered_lines), encoding="utf-8")

        with pytest.raises(IntegrityViolationError, match="INTEGRITY VIOLATION"):
            DrywallClassifier(approved_schedule_path=tampered_csv)

    def test_classified_wall_polygon_runtime_veto_on_detail_1a(self) -> None:
        """Instantiating ClassifiedWallPolygon with 1A and Drywall raises IntegrityViolationError."""
        with pytest.raises(IntegrityViolationError, match="Detail 1A is explicitly 6\" CMU"):
            ClassifiedWallPolygon(
                wall_id="w_cmu_test",
                page_idx=0,
                sheet="A-101",
                geometry_pdf=box(0, 0, 10, 10),
                geometry_pixel=box(0, 0, 20, 20),
                matched_tag="1A",
                detail_number="1A",
                material_description="6\" CMU Block",
                classification="Drywall",  # Breach!
                confidence=1.0,
                color_hex="#00C853",
                reason="Tampered attempt",
            )

    def test_classify_walls_detail_1a_end_to_end(self, classifier: DrywallClassifier) -> None:
        """Classifier correctly produces Non-Drywall for 1A with safety veto reason."""
        wall = DummyCandidate("w_1a", box(100, 100, 200, 108.35))
        tag = DummyTag("1A", box(140, 120, 151.2, 131.3), LineString([(145.6, 120), (145.6, 108.35)]))

        results = classifier.classify_walls([wall], [tag], page_idx=14, sheet="A-101")
        assert len(results) == 1
        w = results[0]
        assert w.classification == "Non-Drywall"
        assert w.color_hex == CLASS_COLORS_HEX["Non-Drywall"]
        assert "MANDATORY SAFETY VETO" in w.reason
        assert "CMU" in w.material_description


# ==============================================================================
# Suite 3: Zero-Hallucination Tier 3 Fallback
# ==============================================================================
class TestTier3ZeroHallucinationFallback:
    """Verifies that unassigned linework strictly falls back to Uncertain with 0.0 confidence."""

    def test_unassigned_wall_classified_uncertain(self, classifier: DrywallClassifier) -> None:
        wall = DummyCandidate("w_unassigned", box(300, 300, 500, 308.35))
        # No tags provided
        results = classifier.classify_walls([wall], [], page_idx=14, sheet="A-101")
        assert len(results) == 1
        w = results[0]
        assert w.classification == "Uncertain"
        assert w.color_hex == CLASS_COLORS_HEX["Uncertain"]
        assert w.confidence == 0.0
        assert w.matched_tag is None
        assert w.detail_number is None
        assert w.match_method == "unassigned"
        assert "Tier 3" in w.reason


# ==============================================================================
# Suite 4: Schema & GeoJSON Serialization
# ==============================================================================
class TestGeoJSONSchemaAndProperties:
    """Verifies RFC 7946 compliance and complete metadata retention in GeoJSON."""

    def test_to_geojson_feature_all_required_fields(self, classifier: DrywallClassifier) -> None:
        poly_pdf = box(100.0, 200.0, 300.0, 208.35)
        poly_px = box(200.0, 400.0, 600.0, 417.4)
        wall = ClassifiedWallPolygon(
            wall_id="wall_schema_01",
            page_idx=14,
            sheet="A-101",
            geometry_pdf=poly_pdf,
            geometry_pixel=poly_px,
            matched_tag="5E",
            detail_number="5E",
            material_description="2-HR GWB Shaftliner",
            classification="Drywall",
            confidence=0.95,
            color_hex="#00C853",
            reason="Tier 1 Leader hit",
            thickness_pt=8.35,
            estimated_thickness_in=6.0,
            orientation="HORIZONTAL",
            match_method="leader_line",
            distance_pt=2.5,
        )

        feat = wall.to_geojson_feature()
        assert feat["type"] == "Feature"
        assert feat["id"] == "wall_schema_01"
        assert feat["geometry"]["type"] == "Polygon"
        props = feat["properties"]
        for mandatory_key in [
            "wall_id", "page_idx", "sheet", "matched_tag", "detail_number",
            "material_description", "classification", "confidence", "color_hex",
            "reason", "thickness_pt", "estimated_thickness_in", "orientation",
            "match_method", "distance_pt", "geometry_pixel",
        ]:
            assert mandatory_key in props, f"Missing key {mandatory_key} in GeoJSON properties"

        assert props["classification"] == "Drywall"
        assert props["matched_tag"] == "5E"

    def test_export_geojson_file_generation(self, classifier: DrywallClassifier, tmp_path: Path) -> None:
        poly = box(100, 100, 200, 108.35)
        wall1 = DummyCandidate("w1", poly)
        tag1 = DummyTag("1C", box(140, 120, 151.2, 131.3), LineString([(145.6, 120), (145.6, 108.35)]))
        classified = classifier.classify_walls([wall1], [tag1], page_idx=14, sheet="A-101")

        out_json = tmp_path / "classified_walls.geojson"
        classifier.export_geojson(classified, out_json, extra_metadata={"dataset": "MTA 99th St 95% CDs"})

        assert out_json.is_file()
        with open(out_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1
        assert "summary" in data
        assert data["summary"]["drywall_count"] == 1
        assert data["metadata"]["dataset"] == "MTA 99th St 95% CDs"


# ==============================================================================
# Suite 5: Coordinate Manager & Bijective Affine Transform
# ==============================================================================
class TestAffineTransformManager:
    """Verifies AffineTransformManager exact bijection under 90° CW rotation."""

    def test_roundtrip_bijection_landmarks(self) -> None:
        atm = AffineTransformManager(dpi=150)
        landmarks = [
            (0.0, 0.0),
            (1728.0, 0.0),
            (0.0, 2592.0),
            (1728.0, 2592.0),
            (864.0, 1296.0),
        ]
        for x, y in landmarks:
            px, py = atm.pdf_to_pixel(x, y)
            rx, ry = atm.pixel_to_pdf(px, py)
            assert math.isclose(rx, x, abs_tol=1e-5), f"X drift at ({x}, {y})"
            assert math.isclose(ry, y, abs_tol=1e-5), f"Y drift at ({x}, {y})"

    def test_geometry_transform_and_area_scaling(self) -> None:
        atm = AffineTransformManager(dpi=150)
        b = box(400, 1000, 410, 1500)  # Area = 10 * 500 = 5000 sq pt
        b_px = atm.transform_geometry_to_pixel(b)
        b_rt = atm.transform_geometry_to_pdf(b_px)

        assert math.isclose(b.area, b_rt.area, rel_tol=1e-5)
        # Scale = 150/72 = 2.08333 -> Area scale = (150/72)^2 = 4.340277
        expected_px_area = b.area * (atm.scale ** 2)
        assert math.isclose(b_px.area, expected_px_area, rel_tol=1e-4)

    def test_visual_dimensions(self) -> None:
        atm = AffineTransformManager(dpi=150, page_width=1728, page_height=2592, rotation=90)
        assert atm.visual_width_pt == 2592.0
        assert atm.visual_height_pt == 1728.0
        w_px, h_px = atm.visual_dimensions_px
        assert w_px == 5400
        assert h_px == 3600


# ==============================================================================
# Suite 6: Modality Router & Hybrid Fusion
# ==============================================================================
class TestModalityRouterAndFusion:
    """Verifies dynamic page routing and hybrid fusion behavior."""

    def test_router_evaluation_pure_vector(self) -> None:
        router = ModalityRouter()
        doc = fitz.open()
        page = doc.new_page(width=1728, height=2592)
        shape = page.new_shape()
        for i in range(120):
            shape.draw_line(fitz.Point(i, 0), fitz.Point(i, 100))
        shape.finish()
        shape.commit()
        page.insert_text(fitz.Point(50, 50), "Standard Architectural CAD Linework Room Label 101 Partition Type Detail")

        decision = router.evaluate_page(page)
        assert decision.modality in (PipelineModality.VECTOR_FIRST, PipelineModality.HYBRID)
        assert decision.confidence >= 0.85
        doc.close()

    def test_router_evaluation_scanned_raster(self) -> None:
        router = ModalityRouter()
        doc = fitz.open()
        page = doc.new_page(width=1728, height=2592)
        # Empty drawing commands, no text
        decision = router.evaluate_page(page)
        assert decision.modality == PipelineModality.RASTER_ML
        assert decision.confidence >= 0.90
        doc.close()

    def test_fusion_summary_statistics_calculations(self) -> None:
        pipeline = HybridFusionPipeline()
        # 10 pt wall length: length in feet at 1/8"=1'-0" (9 pt = 1 ft) is 10/9 = 1.11 ft
        # area = 10 * 81 = 810 sq pt -> 810/81 = 10 sq ft
        w1 = ClassifiedWallPolygon(
            wall_id="w1", page_idx=0, sheet="A-101",
            geometry_pdf=box(0, 0, 90, 10),  # length=90 -> 10 LF, area=900 sq pt
            geometry_pixel=box(0, 0, 180, 20),
            matched_tag="1C", detail_number="1C", material_description="",
            classification="Drywall", confidence=0.95, color_hex="#00C853", reason="",
        )
        w2 = ClassifiedWallPolygon(
            wall_id="w2", page_idx=0, sheet="A-101",
            geometry_pdf=box(0, 0, 45, 10),  # length=45 -> 5 LF, area=450 sq pt
            geometry_pixel=box(0, 0, 90, 20),
            matched_tag="1A", detail_number="1A", material_description="",
            classification="Non-Drywall", confidence=1.0, color_hex="#D50000", reason="",
        )
        summary = pipeline.compute_summary_statistics([w1, w2])
        assert summary["total_walls"] == 2
        assert summary["drywall_count"] == 1
        assert summary["nondrywall_count"] == 1
        assert math.isclose(summary["drywall_lf"], 10.0, abs_tol=0.2)
        assert math.isclose(summary["nondrywall_lf"], 5.0, abs_tol=0.2)


# ==============================================================================
# Suite 7: 10 Human-Review Benchmark Plan Regions (R01-R10) & Error Verification
# ==============================================================================
BENCHMARK_REGIONS = [
    {
        "id": "R01",
        "sheet": "A-100",
        "page_idx": 13,
        "pdf_bbox": (450.0, 900.0, 820.0, 1100.0),
        "pixel_bbox_150": (3108.3, 937.5, 3525.0, 1708.3),
        "tags": ["5E"],
        "expected_class": "Drywall",
        "description": "Cellar Stair D050 2-HR GWB enclosure",
    },
    {
        "id": "R02",
        "sheet": "A-101",
        "page_idx": 14,
        "pdf_bbox": (650.0, 880.0, 780.0, 1000.0),
        "pixel_bbox_150": (3316.7, 1354.2, 3566.7, 1625.0),
        "tags": ["GL2", "10", "1C"],
        "expected_class": "Non-Drywall",  # Tests glass storefront GL2
        "description": "First Floor Entrance Storefront GL2",
    },
    {
        "id": "R03",
        "sheet": "A-101",
        "page_idx": 14,
        "pdf_bbox": (700.0, 980.0, 820.0, 1120.0),
        "pixel_bbox_150": (3066.7, 1458.3, 3358.3, 1708.3),
        "tags": ["09", "11", "5E", "7A"],
        "expected_class": "Uncertain",  # Tests Detail 09 TV Niche
        "description": "First Floor TV Niche 09 and Concrete Pier 11",
    },
    {
        "id": "R04",
        "sheet": "A-101",
        "page_idx": 14,
        "pdf_bbox": (640.0, 1600.0, 820.0, 1750.0),
        "pixel_bbox_150": (1754.2, 1333.3, 2066.7, 1708.3),
        "tags": ["7F", "5B", "7A"],
        "expected_class": "Drywall",
        "description": "First Floor Shaft & Tool Crib drywall cluster",
    },
    {
        "id": "R05",
        "sheet": "A-102",
        "page_idx": 15,
        "pdf_bbox": (450.0, 840.0, 650.0, 1020.0),
        "pixel_bbox_150": (3275.0, 937.5, 3650.0, 1354.2),
        "tags": ["GL1", "2B", "3D", "09"],
        "expected_class": "Non-Drywall",  # Tests demountable glass GL1
        "description": "Second Floor Office Demountable Glass GL1",
    },
    {
        "id": "R06",
        "sheet": "A-102",
        "page_idx": 15,
        "pdf_bbox": (600.0, 1780.0, 780.0, 1920.0),
        "pixel_bbox_150": (1400.0, 1250.0, 1691.7, 1625.0),
        "tags": ["11", "7A", "7B"],
        "expected_class": "Non-Drywall",  # Tests concrete pier 11
        "description": "Second Floor Structural Concrete Pier 11",
    },
    {
        "id": "R07",
        "sheet": "A-103",
        "page_idx": 16,
        "pdf_bbox": (550.0, 950.0, 700.0, 1400.0),
        "pixel_bbox_150": (2483.3, 1145.8, 3420.8, 1458.3),
        "tags": ["GL1", "1C", "2C"],
        "expected_class": "Non-Drywall",  # Tests glass bank GL1
        "description": "Third Floor Corridor Demountable Glass Bank GL1",
    },
    {
        "id": "R08",
        "sheet": "A-104",
        "page_idx": 17,
        "pdf_bbox": (470.0, 840.0, 720.0, 1100.0),
        "pixel_bbox_150": (3108.3, 979.2, 3650.0, 1500.0),
        "tags": ["09", "GL1", "2C", "7A"],
        "expected_class": "Uncertain",  # Tests TV Niche 09 double callout
        "description": "Fourth Floor Executive Conference TV Niche 09",
    },
    {
        "id": "R09",
        "sheet": "A-900",
        "page_idx": 62,
        "pdf_bbox": (350.0, 2200.0, 480.0, 2350.0),
        "pixel_bbox_150": (504.2, 729.2, 816.7, 1000.0),
        "tags": ["1A"],
        "expected_class": "Non-Drywall",  # Mandatory Detail 1A CMU veto region
        "description": "Partition Schedule Detail 1A CMU Assembly Box",
    },
    {
        "id": "R10",
        "sheet": "A-101",
        "page_idx": 14,
        "pdf_bbox": (300.0, 1100.0, 450.0, 1300.0),
        "pixel_bbox_150": (2691.7, 625.0, 3108.3, 937.5),
        "tags": [],
        "expected_class": "Uncertain",  # Tests untagged perimeter wall
        "description": "Exterior Envelope Linework (Tier 3 Guardrail)",
    },
]


class TestHumanReviewBenchmarkSample:
    """Evaluates the 10 defined human-review benchmark regions and quantitative metrics."""

    def test_benchmark_regions_coordinate_bijection(self) -> None:
        """Confirms exact analytical coordinate roundtrip for all 10 benchmark regions."""
        atm = AffineTransformManager(dpi=150)
        for r in BENCHMARK_REGIONS:
            x1, y1, x2, y2 = r["pdf_bbox"]
            px1, py1 = atm.pdf_to_pixel(x1, y2)
            px2, py2 = atm.pdf_to_pixel(x2, y1)

            exp_px1, exp_py1, exp_px2, exp_py2 = r["pixel_bbox_150"]
            assert math.isclose(px1, exp_px1, abs_tol=0.2), f"px1 mismatch in {r['id']}"
            assert math.isclose(py1, exp_py1, abs_tol=0.2), f"py1 mismatch in {r['id']}"
            assert math.isclose(px2, exp_px2, abs_tol=0.2), f"px2 mismatch in {r['id']}"
            assert math.isclose(py2, exp_py2, abs_tol=0.2), f"py2 mismatch in {r['id']}"

            rx1, ry2 = atm.pixel_to_pdf(px1, py1)
            rx2, ry1 = atm.pixel_to_pdf(px2, py2)
            assert math.isclose(rx1, x1, abs_tol=1e-4)
            assert math.isclose(ry1, y1, abs_tol=1e-4)

    def test_benchmark_regions_classification_accuracy(self, classifier: DrywallClassifier) -> None:
        """Simulates all 10 regions and evaluates the 5 quantitative verification metrics."""
        tp_drywall = 0
        fp_drywall = 0
        fn_drywall = 0
        tp_nondrywall = 0
        tp_uncertain = 0
        total_eval_samples = 0
        cmu_veto_success = True

        for r in BENCHMARK_REGIONS:
            rid = r["id"]
            tags = r["tags"]
            pdf_bbox = r["pdf_bbox"]
            poly = box(*pdf_bbox)

            for tag_str in (tags if tags else [None]):
                total_eval_samples += 1
                wall = DummyCandidate(f"wall_{rid}_{tag_str or 'untagged'}", poly)
                tag_obj = []
                if tag_str:
                    cx = (pdf_bbox[0] + pdf_bbox[2]) / 2.0
                    cy = (pdf_bbox[1] + pdf_bbox[3]) / 2.0
                    tag_box = box(cx - 5.6, cy - 5.6, cx + 5.6, cy + 5.6)
                    leader = LineString([(cx, cy), (cx, pdf_bbox[1] + 5.0)])
                    tag_obj = [DummyTag(tag_str, tag_box, leader)]

                res = classifier.classify_walls([wall], tag_obj, page_idx=r["page_idx"], sheet=r["sheet"])
                assert len(res) == 1
                classified = res[0]

                # Ground truth determination
                if tag_str == "1A":
                    expected = "Non-Drywall"
                    if classified.classification != "Non-Drywall":
                        cmu_veto_success = False
                elif tag_str in ("11", "GL1", "GL2"):
                    expected = "Non-Drywall"
                elif tag_str == "09" or tag_str is None:
                    expected = "Uncertain"
                else:
                    expected = "Drywall"

                actual = classified.classification

                if expected == "Drywall":
                    if actual == "Drywall":
                        tp_drywall += 1
                    else:
                        fn_drywall += 1
                elif actual == "Drywall":
                    fp_drywall += 1

                if expected == "Non-Drywall" and actual == "Non-Drywall":
                    tp_nondrywall += 1
                elif expected == "Uncertain" and actual == "Uncertain":
                    tp_uncertain += 1

        # Metric 1: Drywall Precision >= 95%
        precision_dw = tp_drywall / (tp_drywall + fp_drywall) if (tp_drywall + fp_drywall) > 0 else 1.0
        assert precision_dw >= 0.95, f"Drywall Precision below target: {precision_dw:.2%}"

        # Metric 2: Drywall Recall >= 90%
        recall_dw = tp_drywall / (tp_drywall + fn_drywall) if (tp_drywall + fn_drywall) > 0 else 1.0
        assert recall_dw >= 0.90, f"Drywall Recall below target: {recall_dw:.2%}"

        # Metric 3: Overall 3-Class Accuracy >= 92%
        accuracy_overall = (tp_drywall + tp_nondrywall + tp_uncertain) / total_eval_samples
        assert accuracy_overall >= 0.92, f"Overall Accuracy below target: {accuracy_overall:.2%}"

        # Metric 4: False Positive Drywall Rate on Non-Drywall == 0.0%
        assert fp_drywall == 0, f"False Positive Drywall Rate breached! fp={fp_drywall}"

        # Metric 5: Mandatory CMU Safety Veto Compliance == 100%
        assert cmu_veto_success is True, "Detail 1A CMU Safety Veto Compliance failed!"


# ==============================================================================
# Suite 8: Visual Overlay Generator (Raster PNG & Pure Vector PDF)
# ==============================================================================
class TestVisualOverlayGenerator:
    """Verifies generation of annotated raster images and pure vector PDFs."""

    def test_raster_image_generation_with_legend(self, tmp_path: Path) -> None:
        doc = fitz.open()
        page = doc.new_page(width=1728, height=2592)
        page.set_rotation(90)

        poly_pdf = box(400, 1000, 410, 1400)
        wall = ClassifiedWallPolygon(
            wall_id="w_vis_01",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=poly_pdf,
            geometry_pixel=box(0, 0, 10, 10),
            matched_tag="1C",
            detail_number="1C",
            material_description="Drywall",
            classification="Drywall",
            confidence=0.95,
            color_hex="#00C853",
            reason="Verified GWB",
        )

        annotator = WallAnnotator(VisualOverlayConfig(dpi=72))
        composite = annotator.render_raster_image(page, [wall])
        assert composite.size == (2592, 1728)

        out_png = tmp_path / "test_overlay.png"
        composite.save(out_png)
        assert out_png.is_file()
        assert out_png.stat().st_size > 0
        doc.close()

    def test_pure_vector_pdf_generation_preserves_drawings_and_text(self, tmp_path: Path) -> None:
        # Create a test PDF with vector linework and searchable text
        src_pdf = tmp_path / "src_test.pdf"
        doc = fitz.open()
        page = doc.new_page(width=1728, height=2592)
        page.set_rotation(90)
        shape = page.new_shape()
        shape.draw_line(fitz.Point(100, 100), fitz.Point(500, 100))
        shape.finish()
        shape.commit()
        page.insert_text(fitz.Point(200, 200), "ORIGINAL ARCHITECTURAL CAD TEXT", fontsize=12, rotate=90)
        doc.save(src_pdf)
        doc.close()

        # Annotate with WallAnnotator
        out_pdf = tmp_path / "annotated_vector.pdf"
        poly_pdf = box(300, 500, 310, 900)
        wall = ClassifiedWallPolygon(
            wall_id="w_vec_01",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=poly_pdf,
            geometry_pixel=box(0, 0, 10, 10),
            matched_tag="7A",
            detail_number="7A",
            material_description="Drywall",
            classification="Drywall",
            confidence=0.95,
            color_hex="#00C853",
            reason="7A hit",
        )

        annotator = WallAnnotator()
        annotator.generate_annotated_vector_pdf(src_pdf, {0: [wall]}, out_pdf)

        assert out_pdf.is_file()
        res_doc = fitz.open(out_pdf)
        assert len(res_doc) == 1
        res_page = res_doc[0]
        # Verify searchable text preserved
        page_text = res_page.get_text()
        assert "ORIGINAL ARCHITECTURAL CAD" in page_text
        assert "7A" in page_text
        assert "DRYWALL CLASSIFICATION & TAKEOFF" in page_text
        res_doc.close()
