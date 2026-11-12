"""
drywall_detection/tests/test_vector.py

Comprehensive unit and regression tests for vector extraction, coordinate transformations,
linework filtering, and 3-tier spatial matching.
Target: drywall_detection/vector/extractor.py & drywall_detection/vector/spatial_matcher.py
"""

from __future__ import annotations
import json
import math
import numpy as np
import pytest
from shapely.geometry import box, LineString, MultiPolygon, Point, Polygon

from drywall_detection.config import (
    BASE_DPI,
    DEFAULT_DPI,
    MASTER_PDF_MEDIABOX_WIDTH_PT,
    MASTER_PDF_MEDIABOX_HEIGHT_PT,
    MASTER_PDF_ROTATION_DEG,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    CLASS_COLORS_HEX,
)
from drywall_detection.utils.coords import (
    pdf_to_pixel,
    pixel_to_pdf,
    pdf_geom_to_pixel,
    pixel_geom_to_pdf,
    pdf_bbox_to_pixel,
    pixel_bbox_to_pdf,
)
from drywall_detection.vector.extractor import (
    ExtractedWallCandidate,
    TextElement,
    VectorExtractor,
    VectorGeometry,
    VectorPageProfile,
)
from drywall_detection.vector.spatial_matcher import (
    MatchMethod,
    MatchingReport,
    SpatialMatcher,
    SpatialMatcherConfig,
    SpatialMatchResult,
)


# ==============================================================================
# 1. COORDINATE BIJECTION & ROTATION TESTS
# ==============================================================================
class TestCoordinateTransformation:
    """Verifies exact reversible affine coordinate transformation under 90° CW rotation."""

    @pytest.mark.parametrize("dpi", [72, 150, 300])
    @pytest.mark.parametrize(
        "x,y",
        [
            (0.0, 0.0),
            (1728.0, 2592.0),
            (864.0, 1296.0),
            (123.456, 789.012),
            (1700.0, 100.0),
            (50.25, 2450.75),
        ],
    )
    def test_roundtrip_bijection_90deg(self, dpi: int, x: float, y: float) -> None:
        """Confirms |pixel_to_pdf(pdf_to_pixel(p)) - p| < 10^-4 pt."""
        px, py = pdf_to_pixel(x, y, dpi=dpi, rotation=90)
        rx, ry = pixel_to_pdf(px, py, dpi=dpi, rotation=90)
        assert abs(rx - x) < 1e-4, f"X roundtrip error too large: orig={x}, recovered={rx}"
        assert abs(ry - y) < 1e-4, f"Y roundtrip error too large: orig={y}, recovered={ry}"

    def test_90deg_cw_exact_corners(self) -> None:
        """Verifies exact analytical corner mappings at 72 DPI."""
        # Unrotated native dimensions: width=1728, height=2592
        # Forward formula: px = (2592 - y) * 1.0, py = x * 1.0

        # Top-left native (0, 2592) -> Visual origin (0, 0)
        px, py = pdf_to_pixel(0.0, 2592.0, dpi=72, rotation=90)
        assert (px, py) == (0.0, 0.0)

        # Bottom-left native (0, 0) -> Visual (2592, 0)
        px, py = pdf_to_pixel(0.0, 0.0, dpi=72, rotation=90)
        assert (px, py) == (2592.0, 0.0)

        # Top-right native (1728, 2592) -> Visual (0, 1728)
        px, py = pdf_to_pixel(1728.0, 2592.0, dpi=72, rotation=90)
        assert (px, py) == (0.0, 1728.0)

        # Bottom-right native (1728, 0) -> Visual (2592, 1728)
        px, py = pdf_to_pixel(1728.0, 0.0, dpi=72, rotation=90)
        assert (px, py) == (2592.0, 1728.0)

    def test_monte_carlo_random_points(self) -> None:
        """Tests 2,000 random points across the canvas bounding box."""
        rng = np.random.default_rng(42)
        xs = rng.uniform(0.0, 1728.0, size=2000)
        ys = rng.uniform(0.0, 2592.0, size=2000)

        for x, y in zip(xs, ys):
            px, py = pdf_to_pixel(x, y, dpi=150, rotation=90)
            rx, ry = pixel_to_pdf(px, py, dpi=150, rotation=90)
            assert abs(rx - x) < 1e-5
            assert abs(ry - y) < 1e-5

    def test_shapely_polygon_roundtrip(self) -> None:
        """Verifies polygon topological and geometric preservation."""
        poly = box(150.0, 250.0, 450.0, 600.0)
        pixel_poly = pdf_geom_to_pixel(poly, dpi=150, rotation=90)
        recovered_poly = pixel_geom_to_pdf(pixel_poly, dpi=150, rotation=90)

        assert poly.equals_exact(recovered_poly, tolerance=1e-3)
        assert abs(poly.area - recovered_poly.area) < 1e-4

    def test_bbox_roundtrip(self) -> None:
        """Verifies bounding box transformation bijection."""
        bbox = (100.0, 200.0, 500.0, 800.0)
        pbbox = pdf_bbox_to_pixel(bbox, dpi=150, rotation=90)
        recovered = pixel_bbox_to_pdf(pbbox, dpi=150, rotation=90)

        for b_orig, b_rec in zip(bbox, recovered):
            assert abs(b_orig - b_rec) < 1e-4


# ==============================================================================
# 2. VECTOR PRESENCE DETECTION TESTS
# ==============================================================================
class TestVectorPresenceDetection:
    """Verifies vector page profiling and pipeline recommendation."""

    class MockPDFPage:
        def __init__(self, drawings, words, images=None, number=0):
            self._drawings = drawings
            self._words = words
            self._images = images or []
            self.number = number

        def get_drawings(self):
            return self._drawings

        def get_text(self, kind="words"):
            if kind == "words":
                return self._words
            return ""

        def get_images(self):
            return self._images

    def test_vector_cad_page_routing(self) -> None:
        """Synthetic CAD page with 150 drawings and 50 words routes to VECTOR_FIRST."""
        mock_drawings = [
            {"items": [("l", Point(0, 0), Point(10, 10))], "width": 1.2, "dashes": "[] 0"}
            for _ in range(150)
        ]
        mock_words = [(0, 0, 10, 10, f"word_{i}", 0, 0, 0) for i in range(50)]
        page = self.MockPDFPage(mock_drawings, mock_words, images=[])

        extractor = VectorExtractor()
        profile = extractor.detect_vector_content(page)

        assert profile.is_pure_vector is True
        assert profile.is_scanned_raster is False
        assert profile.is_vector_page is True
        assert profile.recommended_pipeline == "VECTOR_FIRST"
        assert profile.path_count == 150
        assert profile.word_count == 50

    def test_scanned_raster_page_routing(self) -> None:
        """Synthetic scanned page with 10 paths and 0 words routes to RASTER_ML."""
        mock_drawings = [
            {"items": [("l", Point(0, 0), Point(10, 10))], "width": 0.5, "dashes": "[] 0"}
            for _ in range(10)
        ]
        page = self.MockPDFPage(mock_drawings, words=[], images=[("img1", 0)])

        extractor = VectorExtractor()
        profile = extractor.detect_vector_content(page)

        assert profile.is_pure_vector is False
        assert profile.is_scanned_raster is True
        assert profile.is_vector_page is False
        assert profile.recommended_pipeline == "RASTER_ML"


# ==============================================================================
# 3. WALL LINEWORK & PARALLEL LINE PAIR EXTRACTION TESTS
# ==============================================================================
class TestWallLineworkExtraction:
    """Verifies CAD stroke filtering and parallel line pair wall polygon reconstruction."""

    class MockLineworkPage:
        def __init__(self, drawings):
            self._drawings = drawings
            self.number = 14

        def get_drawings(self):
            return self._drawings

    def test_parallel_horizontal_wall_pairing(self) -> None:
        """
        Two parallel horizontal lines spaced 4.5 pt apart (6" wall at 1/8"=1'-0")
        with heavy strokes (w=1.20 pt) must form a merged wall candidate polygon.
        """
        class FitzPoint:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        line1 = {
            "type": "s",
            "width": 1.20,
            "dashes": "[] 0",
            "items": [("l", FitzPoint(100.0, 500.0), FitzPoint(300.0, 500.0))],
        }
        line2 = {
            "type": "s",
            "width": 1.20,
            "dashes": "[] 0",
            "items": [("l", FitzPoint(100.0, 504.5), FitzPoint(300.0, 504.5))],
        }
        # A thin dimension line that should be filtered out
        dim_line = {
            "type": "s",
            "width": 0.48,
            "dashes": "[] 0",
            "items": [("l", FitzPoint(100.0, 520.0), FitzPoint(300.0, 520.0))],
        }
        # A dashed hidden line that should be filtered out
        dashed_line = {
            "type": "s",
            "width": 1.20,
            "dashes": "[2 2] 0",
            "items": [("l", FitzPoint(100.0, 530.0), FitzPoint(300.0, 530.0))],
        }

        page = self.MockLineworkPage([line1, line2, dim_line, dashed_line])
        extractor = VectorExtractor()

        candidates = extractor.extract_wall_candidates(page)
        assert len(candidates) >= 1

        wall = candidates[0]
        assert wall.orientation == "HORIZONTAL"
        assert abs(wall.thickness_pt - 4.5) < 0.2
        assert wall.geometry_pdf.is_valid
        assert not wall.geometry_pdf.is_empty
        assert wall.geometry_pixel is not None

    def test_parallel_vertical_wall_pairing(self) -> None:
        """Two parallel vertical lines spaced 3.65 pt apart (4-7/8" drywall wall)."""
        class FitzPoint:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        line1 = {
            "type": "s",
            "width": 1.68,
            "dashes": "[] 0",
            "items": [("l", FitzPoint(400.0, 200.0), FitzPoint(400.0, 600.0))],
        }
        line2 = {
            "type": "s",
            "width": 1.68,
            "dashes": "[] 0",
            "items": [("l", FitzPoint(403.65, 200.0), FitzPoint(403.65, 600.0))],
        }

        page = self.MockLineworkPage([line1, line2])
        extractor = VectorExtractor()

        candidates = extractor.extract_wall_candidates(page)
        assert len(candidates) == 1
        wall = candidates[0]
        assert wall.orientation == "VERTICAL"
        assert abs(wall.thickness_pt - 3.65) < 0.2


# ==============================================================================
# 4. 3-TIER SPATIAL MATCHER TESTS
# ==============================================================================
class Test3TierSpatialMatcher:
    """Verifies Tier 1 (Leader Raycast), Tier 2 (Proximity Buffer), and Tier 3 (Unassigned)."""

    @pytest.fixture
    def sample_schedule(self):
        return {
            "1A": {"proposed_class": "Non-Drywall"},
            "1C": {"proposed_class": "Drywall"},
            "5E": {"proposed_class": "Drywall"},
            "7F": {"proposed_class": "Drywall"},
            "GL1": {"proposed_class": "Non-Drywall"},
            "09": {"proposed_class": "Uncertain"},
        }

    class DummyWall:
        def __init__(self, wall_id: str, geom: Polygon):
            self.wall_id = wall_id
            self.geometry = geom
            self.geometry_pdf = geom

    class DummyTag:
        def __init__(self, tag_id: str, box_geom: Polygon, leader_line: Optional[LineString] = None):
            self.tag_id = tag_id
            self.tag = tag_id
            self.box_geom = box_geom
            self.box_bbox = box_geom.bounds
            self.centroid = (box_geom.centroid.x, box_geom.centroid.y)
            self.center = self.centroid
            self.leader_line = leader_line
            self.leader_lines = [leader_line] if leader_line is not None else []

    def test_tier1_leader_direct_intersection(self, sample_schedule) -> None:
        """Leader line extending directly into wall assigns with Tier 1 and high confidence."""
        wall = self.DummyWall("w_tier1", box(100.0, 100.0, 300.0, 110.0))
        tag_box = box(150.0, 130.0, 161.2, 141.2)
        # Leader touches top of box at y=130 and enters wall at y=105
        leader = LineString([(155.6, 130.0), (155.6, 105.0)])
        tag = self.DummyTag("1C", tag_box, leader)

        matcher = SpatialMatcher(schedule_mapping=sample_schedule)
        report = matcher.match([wall], [tag])

        assert report.matched_walls == 1
        assert report.tier1_matches == 1
        assert report.tier2_matches == 0
        assert report.tier3_unassigned == 0
        res = report.results[0]
        assert res.assigned_tag == "1C"
        assert res.match_method == MatchMethod.LEADER_LINE
        assert res.confidence >= 0.90
        assert res.proposed_class == "Drywall"
        assert res.color_hex == CLASS_COLORS_HEX["Drywall"]

    def test_tier1_leader_raycast_extension_hit(self, sample_schedule) -> None:
        """Leader line stopping 5 pt short of wall cavity hits via raycast forward projection."""
        wall = self.DummyWall("w_raycast", box(100.0, 100.0, 300.0, 110.0))
        tag_box = box(150.0, 130.0, 161.2, 141.2)
        # Leader stops at y=115 (5 pt short of y=110), raycast extends 12 pt forward
        leader = LineString([(155.6, 130.0), (155.6, 115.0)])
        tag = self.DummyTag("5E", tag_box, leader)

        matcher = SpatialMatcher(schedule_mapping=sample_schedule)
        report = matcher.match([wall], [tag])

        assert report.matched_walls == 1
        assert report.tier1_matches == 1
        res = report.results[0]
        assert res.assigned_tag == "5E"
        assert res.match_method == MatchMethod.LEADER_LINE
        assert res.confidence == 0.90
        assert "raycast" in res.evidence.lower()

    def test_tier2_proximity_buffer_unique_hit(self, sample_schedule) -> None:
        """Leaderless tag positioned 10 pt from wall matches via Tier 2 (25 pt buffer)."""
        wall = self.DummyWall("w_prox", box(100.0, 100.0, 300.0, 110.0))
        # Tag box at y=120 (gap = 10 pt <= 25 pt primary buffer)
        tag_box = box(150.0, 120.0, 161.2, 131.2)
        tag = self.DummyTag("7F", tag_box, leader_line=None)

        matcher = SpatialMatcher(schedule_mapping=sample_schedule)
        report = matcher.match([wall], [tag])

        assert report.matched_walls == 1
        assert report.tier1_matches == 0
        assert report.tier2_matches == 1
        res = report.results[0]
        assert res.assigned_tag == "7F"
        assert res.match_method == MatchMethod.BUFFER_PROXIMITY
        assert res.confidence >= 0.75
        assert res.proposed_class == "Drywall"

    def test_tier2_distance_delta_disambiguation(self, sample_schedule) -> None:
        """Tag near two walls assigns closest if delta >= 8.0 pt."""
        wall_close = self.DummyWall("w_close", box(100.0, 100.0, 300.0, 110.0))
        wall_far = self.DummyWall("w_far", box(100.0, 145.0, 300.0, 155.0))
        # Tag box at y=115 to y=126.2: distance to close wall is 5 pt, distance to far wall is 18.8 pt (delta=13.8 pt >= 8 pt)
        tag_box = box(150.0, 115.0, 161.2, 126.2)
        tag = self.DummyTag("1C", tag_box, leader_line=None)

        matcher = SpatialMatcher(schedule_mapping=sample_schedule)
        report = matcher.match([wall_close, wall_far], [tag])

        assert report.matched_walls == 1
        assert report.tier2_matches == 1
        assert report.tier3_unassigned == 1
        # Close wall gets the tag
        res_map = {r.wall_id: r for r in report.results}
        assert res_map["w_close"].assigned_tag == "1C"
        assert res_map["w_close"].match_method == MatchMethod.BUFFER_PROXIMITY
        # Far wall remains unassigned
        assert res_map["w_far"].assigned_tag is None
        assert res_map["w_far"].match_method == MatchMethod.UNASSIGNED

    def test_tier3_unassigned_fallback_guardrail(self, sample_schedule) -> None:
        """Wall with no spatial tag match MUST remain strictly unassigned with 0.0 confidence."""
        wall_isolated = self.DummyWall("w_isolated", box(600.0, 600.0, 800.0, 610.0))
        matcher = SpatialMatcher(schedule_mapping=sample_schedule)
        report = matcher.match([wall_isolated], [])

        assert report.matched_walls == 0
        assert report.unassigned_walls == 1
        assert report.tier3_unassigned == 1

        res = report.results[0]
        assert res.assigned_tag is None
        assert res.match_method == MatchMethod.UNASSIGNED
        assert res.proposed_class == "Uncertain"
        assert res.confidence == 0.0
        assert res.color_hex == CLASS_COLORS_HEX["Uncertain"]
        assert "guardrail enforced" in res.evidence

    def test_detail_1a_cmu_safety_veto(self, sample_schedule) -> None:
        """Detail 1A must intercept tampering with exception, and resolve untampered to Non-Drywall."""
        wall = self.DummyWall("w_cmu", box(100.0, 100.0, 300.0, 110.0))
        leader = LineString([(155.6, 130.0), (155.6, 105.0)])
        tag = self.DummyTag("1A", box(150.0, 130.0, 161.2, 141.2), leader)

        # Adversarially attempt to pass 1A as Drywall in schedule -> raises INTEGRITY VIOLATION
        tampered_schedule = {"1A": {"proposed_class": "Drywall"}}
        matcher = SpatialMatcher(schedule_mapping=tampered_schedule)
        with pytest.raises(ValueError, match="INTEGRITY VIOLATION"):
            matcher.match([wall], [tag])

        # Untampered schedule resolves 1A to Non-Drywall
        matcher_valid = SpatialMatcher(schedule_mapping=sample_schedule)
        report = matcher_valid.match([wall], [tag])
        res = report.results[0]
        assert res.assigned_tag == "1A"
        assert res.proposed_class == "Non-Drywall"
        assert res.proposed_class != "Drywall"
        assert res.color_hex == CLASS_COLORS_HEX["Non-Drywall"]


# ==============================================================================
# 5. GROUND TRUTH BUILDER & MASK RASTERIZATION TESTS
# ==============================================================================
class TestGroundTruthBuilderAndRasterization:
    """Verifies extraction of Usman expert markups, 150 DPI Mode 'P' mask rasterization, and splits."""

    def test_synthetic_centerline_rasterization_and_validation(self, tmp_path) -> None:
        """Rasterizes synthetic centerlines into Mode 'P' mask and verifies validate_mask_array."""
        from drywall_detection.data.ground_truth_builder import (
            GroundTruthBuilder,
            GroundTruthRasterizerConfig,
            WallMarkupRecord,
        )
        from drywall_detection.datasets.unified_format import validate_mask_array
        from PIL import Image

        cfg = GroundTruthRasterizerConfig(dpi=150, default_wall_thickness_pt=8.35)
        builder = GroundTruthBuilder(cfg)

        rec = WallMarkupRecord(
            wall_id="test_wall_01",
            sheet_name="A-100",
            page_idx=0,
            pt1=(500.0, 1600.0),
            pt2=(500.0, 1800.0),
            tag="5E",
            probability=0.97,
            thickness_pt=8.35,
        )

        mask = builder.rasterize_sheet([rec], width=5400, height=3600)
        assert mask.shape == (3600, 5400)
        assert mask.dtype == np.uint8
        validated = validate_mask_array(mask, expected_shape=(3600, 5400))
        assert validated is not None

        wall_pixels = int(np.sum(mask == 1))
        assert wall_pixels > 0
        assert np.all(np.isin(np.unique(mask), [0, 1]))

        # Verify Mode 'P' PNG export
        out_png = tmp_path / "test_mask.png"
        builder.save_mask_as_indexed_png(mask, out_png)
        assert out_png.exists()

        saved_img = Image.open(out_png)
        assert saved_img.mode == "P"
        assert saved_img.size == (5400, 3600)

    def test_multiclass_precedence_in_rasterizer(self) -> None:
        """Confirms layering hierarchy: Background (0) < Uncertain (3) < Non-Drywall (2) < Drywall (1)."""
        from drywall_detection.data.ground_truth_builder import (
            GroundTruthBuilder,
            GroundTruthRasterizerConfig,
            WallMarkupRecord,
        )

        builder = GroundTruthBuilder(GroundTruthRasterizerConfig(dpi=150))

        # Two intersecting wall records at (500, 1600) -> (500, 1800)
        drywall_rec = WallMarkupRecord(
            wall_id="w_drywall",
            sheet_name="A-100",
            page_idx=0,
            pt1=(500.0, 1600.0),
            pt2=(500.0, 1800.0),
            tag="1C",
        )
        non_drywall_rec = WallMarkupRecord(
            wall_id="w_cmu",
            sheet_name="A-100",
            page_idx=0,
            pt1=(500.0, 1600.0),
            pt2=(500.0, 1800.0),
            tag="1A",
        )

        mask = builder.rasterize_sheet(
            wall_records=[drywall_rec],
            non_drywall_records=[non_drywall_rec],
            uncertain_records=None,
        )

        # Drywall must overwrite Non-Drywall where they overlap
        wall_px = int(np.sum(mask == 1))
        cmu_px = int(np.sum(mask == 2))
        assert wall_px > 0
        assert cmu_px == 0  # Completely overwritten by drywall

    def test_usman_gt_extraction_if_pdf_available(self) -> None:
        """Verifies exactly 239 red wall centerlines across Sheets A-100..A-104 when PDF is present."""
        from drywall_detection.config import USMAN_GROUND_TRUTH_PDF
        from drywall_detection.data.ground_truth_builder import GroundTruthBuilder

        if not USMAN_GROUND_TRUTH_PDF.exists():
            pytest.skip("Usman ground truth PDF not present on this system")

        builder = GroundTruthBuilder()
        extracted = builder.extract_red_centerlines(USMAN_GROUND_TRUTH_PDF)

        assert len(extracted) == 5
        assert len(extracted[0]) == 4   # A-100
        assert len(extracted[1]) == 28  # A-101
        assert len(extracted[2]) == 71  # A-102
        assert len(extracted[3]) == 67  # A-103
        assert len(extracted[4]) == 69  # A-104

        total_lines = sum(len(lines) for lines in extracted.values())
        assert total_lines == 239

        for pidx, lines in extracted.items():
            for l in lines:
                assert l.tag != ""
                assert l.thickness_pt > 0
                assert l.length_pt > 0

    def test_zero_leakage_manifest_builder(self, tmp_path) -> None:
        """Verifies drawing-level split manifest generation and strict zero-leakage invariant."""
        from drywall_detection.data.ground_truth_builder import GroundTruthBuilder

        builder = GroundTruthBuilder()
        splits_dir = tmp_path / "splits"
        manifests = builder.generate_split_manifests(splits_dir=splits_dir)

        assert (splits_dir / "train.json").exists()
        assert (splits_dir / "val.json").exists()
        assert (splits_dir / "test.json").exists()
        assert (splits_dir / "quarantine.json").exists()
        assert (splits_dir / "splits_summary.json").exists()

        with open(splits_dir / "train.json", "r", encoding="utf-8") as f:
            train_data = json.load(f)
        with open(splits_dir / "val.json", "r", encoding="utf-8") as f:
            val_data = json.load(f)
        with open(splits_dir / "test.json", "r", encoding="utf-8") as f:
            test_data = json.load(f)

        train_projs = {t["project_id"] for t in train_data["tiles"]}
        val_projs = {t["project_id"] for t in val_data["tiles"]}
        test_projs = {t["project_id"] for t in test_data["tiles"]}

        # Strict project isolation
        assert len(train_projs & val_projs) == 0
        assert len(train_projs & test_projs) == 0
        assert len(val_projs & test_projs) == 0

        # Strict drawing isolation for MTA 99th Street
        train_draws = {t["drawing_id"] for t in train_data["tiles"]}
        test_draws = {t["drawing_id"] for t in test_data["tiles"]}
        assert len(train_draws & test_draws) == 0
        assert "MTA_99TH_A-104" in test_draws
        assert "MTA_99TH_A-104" not in train_draws

