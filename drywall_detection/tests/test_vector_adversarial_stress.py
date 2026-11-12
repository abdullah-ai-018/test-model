"""
drywall_detection/tests/test_vector_adversarial_stress.py

Adversarial Stress Test Suite for Vector Extraction & Coordinate Logic.
Target: drywall_detection/vector/extractor.py & drywall_detection/utils/coords.py

Challenger: challenger_m3_1
Dimensions:
1. Coordinate Transformation Precision (< 10^-4 pt invariant, multi-DPI 72/150/300/600/1200, out-of-bounds, non-finite).
2. Degenerate Geometry & Pathological Linework (zero-length, collinear, self-intersecting, NaN/Inf).
3. Parallel Line Pairing Stress (1.49 / 10.51 pt boundaries, angular skew, collinear merging, stair chaining).
4. Scaling & Memory Stress on Synthetic Sets (10,000+ paths, O(N^2) pairwise analysis).
"""

from __future__ import annotations
import math
import time
import tracemalloc
from typing import Any, List, Tuple
import numpy as np
import pytest
from shapely.geometry import box, LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union

from drywall_detection.config import (
    BASE_DPI,
    DEFAULT_DPI,
    MASTER_PDF_MEDIABOX_WIDTH_PT,
    MASTER_PDF_MEDIABOX_HEIGHT_PT,
    MASTER_PDF_ROTATION_DEG,
    CLASS_UNCERTAIN,
)
from drywall_detection.utils.coords import (
    pdf_to_pixel,
    pixel_to_pdf,
    pdf_bbox_to_pixel,
    pixel_bbox_to_pdf,
    pdf_geom_to_pixel,
    pixel_geom_to_pdf,
    pdf_points_to_pixel,
    pixel_points_to_pdf,
)
from drywall_detection.vector.extractor import (
    ExtractedWallCandidate,
    TextElement,
    VectorExtractor,
    VectorGeometry,
    VectorPageProfile,
)


class MockFitzPoint:
    """Mock Fitz Point for vector drawing items."""
    def __init__(self, x: float, y: float) -> None:
        self.x = float(x)
        self.y = float(y)


class MockFitzRect:
    """Mock Fitz Rect for bounding box tests."""
    def __init__(self, x0: float, y0: float, x1: float, y1: float) -> None:
        self.x0 = float(x0)
        self.y0 = float(y0)
        self.x1 = float(x1)
        self.y1 = float(y1)
        self.width = abs(self.x1 - self.x0)
        self.height = abs(self.y1 - self.y0)

    def intersects(self, other: Any) -> bool:
        return not (
            self.x1 < other.x0 or self.x0 > other.x1 or
            self.y1 < other.y0 or self.y0 > other.y1
        )


class MockPage:
    """Mock PyMuPDF Page for linework and drawing tests."""
    def __init__(self, drawings: List[dict], words: List[Any] = None, images: List[Any] = None, number: int = 14) -> None:
        self._drawings = drawings
        self._words = words or []
        self._images = images or []
        self.number = number

    def get_drawings(self) -> List[dict]:
        return self._drawings

    def get_text(self, kind: str = "words") -> Any:
        if kind == "words":
            return self._words
        elif kind == "dict":
            return {"blocks": []}
        return ""

    def get_images(self) -> List[Any]:
        return self._images


# ==============================================================================
# 1. COORDINATE TRANSFORMATION PRECISION & DRIFT STRESS
# ==============================================================================
class TestCoordinateTransformationStress:
    """Stress tests coordinate precision across boundary extremes, DPIs, and pathologies."""

    @pytest.mark.parametrize("dpi", [36, 72, 144, 150, 300, 600, 1200])
    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_extreme_corners_precision(self, dpi: int, rotation: int) -> None:
        """Tests exact 4-corner canvas mapping with strict < 10^-10 pt floating point error."""
        corners = [
            (0.0, 0.0),
            (MASTER_PDF_MEDIABOX_WIDTH_PT, 0.0),
            (0.0, MASTER_PDF_MEDIABOX_HEIGHT_PT),
            (MASTER_PDF_MEDIABOX_WIDTH_PT, MASTER_PDF_MEDIABOX_HEIGHT_PT),
        ]
        for x, y in corners:
            px, py = pdf_to_pixel(x, y, dpi=dpi, rotation=rotation)
            rx, ry = pixel_to_pdf(px, py, dpi=dpi, rotation=rotation)
            err_x = abs(rx - x)
            err_y = abs(ry - y)
            assert err_x < 1e-10, f"X drift: {err_x} at corner ({x}, {y}), dpi={dpi}, rot={rotation}"
            assert err_y < 1e-10, f"Y drift: {err_y} at corner ({x}, {y}), dpi={dpi}, rot={rotation}"

    @pytest.mark.parametrize("dpi", [72, 150, 300, 600])
    def test_subnormal_and_out_of_bounds_coordinates(self, dpi: int) -> None:
        """Verifies reversible transformation far outside normal canvas bounds."""
        test_points = [
            (-1e5, -1e5),
            (1e6, 1e6),
            (1e-12, 1e-12),
            (MASTER_PDF_MEDIABOX_WIDTH_PT + 5000.0, MASTER_PDF_MEDIABOX_HEIGHT_PT + 5000.0),
            (-500.25, 3000.75),
        ]
        for x, y in test_points:
            px, py = pdf_to_pixel(x, y, dpi=dpi, rotation=90)
            rx, ry = pixel_to_pdf(px, py, dpi=dpi, rotation=90)
            assert abs(rx - x) < 1e-4
            assert abs(ry - y) < 1e-4

    @pytest.mark.parametrize("dpi", [72, 150, 300, 600])
    def test_monte_carlo_5000_points_error_bound(self, dpi: int) -> None:
        """
        Runs 5,000 random Monte Carlo points per DPI.
        Confirms max error is strictly < 10^-4 pt (and empirically < 10^-11 pt).
        """
        rng = np.random.default_rng(20261108)
        xs = rng.uniform(-1000.0, 3000.0, size=5000)
        ys = rng.uniform(-1000.0, 4000.0, size=5000)

        pts = np.column_stack((xs, ys))
        pixels = pdf_points_to_pixel(pts, dpi=dpi, rotation=90)
        recovered = pixel_points_to_pdf(pixels, dpi=dpi, rotation=90)

        errors = np.linalg.norm(recovered - pts, axis=1)
        max_error = np.max(errors)
        mean_error = np.mean(errors)

        assert max_error < 1e-4, f"Monte Carlo max error {max_error} exceeds 10^-4 pt at DPI {dpi}"
        assert max_error < 1e-10, f"Expected float64 precision < 1e-10 pt, got {max_error}"
        assert mean_error < 1e-11

    def test_non_finite_inputs_raise_value_error(self) -> None:
        """Verifies that coords functions reject NaN and Inf gracefully."""
        invalid_coords = [
            (float("nan"), 100.0),
            (100.0, float("nan")),
            (float("inf"), 100.0),
            (100.0, float("-inf")),
        ]
        for x, y in invalid_coords:
            with pytest.raises(ValueError, match="Coordinates must be finite"):
                pdf_to_pixel(x, y, dpi=150, rotation=90)
            with pytest.raises(ValueError, match="Pixel coordinates must be finite"):
                pixel_to_pdf(x, y, dpi=150, rotation=90)

    def test_invalid_dpi_and_rotation_raise_value_error(self) -> None:
        """Verifies that invalid DPI (<= 0) or unsupported rotation raises ValueError."""
        with pytest.raises(ValueError, match="DPI must be positive"):
            pdf_to_pixel(100.0, 100.0, dpi=0)
        with pytest.raises(ValueError, match="DPI must be positive"):
            pdf_to_pixel(100.0, 100.0, dpi=-150)
        with pytest.raises(ValueError, match="Unsupported rotation"):
            pdf_to_pixel(100.0, 100.0, dpi=150, rotation=45)

    def test_inverted_bbox_raises_value_error(self) -> None:
        """Bounding boxes where min > max must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid bounding box ordering"):
            pdf_bbox_to_pixel((200.0, 100.0, 100.0, 300.0))
        with pytest.raises(ValueError, match="Invalid bounding box ordering"):
            pdf_bbox_to_pixel((100.0, 300.0, 200.0, 100.0))

    def test_zero_area_bbox_handled_safely(self) -> None:
        """Degenerate bounding boxes (zero width or height) must transform without crash."""
        p_bbox = pdf_bbox_to_pixel((100.0, 200.0, 100.0, 200.0), dpi=150, rotation=90)
        rec_bbox = pixel_bbox_to_pdf(p_bbox, dpi=150, rotation=90)
        assert abs(rec_bbox[0] - 100.0) < 1e-4
        assert abs(rec_bbox[1] - 200.0) < 1e-4

    def test_polygon_area_centroid_and_topology_conservation(self) -> None:
        """
        Tests forward and inverse transformation of complex polygon with holes (donut shape)
        and an L-shaped concave polygon.
        Confirms area conservation, centroid conservation (< 10^-4 pt), and topology.
        """
        outer = box(200.0, 400.0, 600.0, 800.0)
        hole = box(300.0, 500.0, 500.0, 700.0)
        donut = outer.difference(hole)
        assert isinstance(donut, Polygon)

        for dpi in [72, 150, 300]:
            pixel_donut = pdf_geom_to_pixel(donut, dpi=dpi, rotation=90)
            assert pixel_donut.is_valid
            assert not pixel_donut.is_empty

            scale = dpi / float(BASE_DPI)
            expected_pixel_area = donut.area * (scale ** 2)
            assert abs(pixel_donut.area - expected_pixel_area) < 1e-4

            recovered_donut = pixel_geom_to_pdf(pixel_donut, dpi=dpi, rotation=90)
            assert recovered_donut.is_valid
            assert abs(recovered_donut.area - donut.area) < 1e-4

            # Centroid conservation
            c_orig = donut.centroid
            c_rec = recovered_donut.centroid
            dist = math.hypot(c_orig.x - c_rec.x, c_orig.y - c_rec.y)
            assert dist < 1e-4, f"Centroid drift {dist} exceeds 10^-4 pt"


# ==============================================================================
# 2. DEGENERATE GEOMETRY & PATHOLOGICAL LINEWORK
# ==============================================================================
class TestDegenerateGeometryStress:
    """Stress tests linework extraction on zero-length, overlapping, and degenerate inputs."""

    def test_zero_length_segments_ignored_gracefully(self) -> None:
        """Zero-length segments (p1 == p2) must not cause ZeroDivisionError or crash."""
        drawings = [
            {
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, 200.0), MockFitzPoint(100.0, 200.0))],
            },
            {
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(300.0, 400.0), MockFitzPoint(300.0 + 1e-8, 400.0))],
            },
        ]
        page = MockPage(drawings)
        extractor = VectorExtractor()
        candidates = extractor.extract_wall_candidates(page)
        # Segments < 5.0 pt must be skipped
        assert len(candidates) == 0

    def test_nan_and_inf_linework_handled_without_crash(self) -> None:
        """Linework containing NaN or Inf must not raise unhandled exception."""
        drawings = [
            {
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(float("nan"), 100.0), MockFitzPoint(200.0, 100.0))],
            },
            {
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, float("inf")), MockFitzPoint(100.0, 200.0))],
            },
        ]
        page = MockPage(drawings)
        extractor = VectorExtractor()
        candidates = extractor.extract_wall_candidates(page)
        assert len(candidates) == 0

    def test_collinear_partially_overlapping_segments(self) -> None:
        """
        Tests multiple collinear overlapping segments forming a continuous wall face.
        Line 1: (100, 500) -> (300, 500)
        Line 2: (250, 500) -> (450, 500)  [collinear with Line 1, overlaps by 50 pt]
        Line 3: (100, 504.5) -> (450, 504.5)  [opposing parallel face]
        """
        drawings = [
            {
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, 500.0), MockFitzPoint(300.0, 500.0))],
            },
            {
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(250.0, 500.0), MockFitzPoint(450.0, 500.0))],
            },
            {
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, 504.5), MockFitzPoint(450.0, 504.5))],
            },
        ]
        page = MockPage(drawings)
        extractor = VectorExtractor()
        candidates = extractor.extract_wall_candidates(page)

        assert len(candidates) >= 1
        # Combined length should cover the entire 100 to 450 extent = 350 pt
        merged = unary_union([c.geometry_pdf for c in candidates])
        minx, miny, maxx, maxy = merged.bounds
        assert abs(maxx - minx - 350.0) < 1.0
        assert abs(maxy - miny - 4.5) < 0.2

    def test_non_solid_and_exotic_dash_patterns(self) -> None:
        """Dashed, dotted, and chain dashed lines must be filtered out."""
        dash_styles = [
            "[2 2] 0",
            "[4 2] 0",
            "[10 2 2 2] 0",
            "[1 1] 0",
        ]
        drawings = []
        for i, dash in enumerate(dash_styles):
            drawings.append({
                "type": "s",
                "width": 1.20,
                "dashes": dash,
                "items": [("l", MockFitzPoint(100.0, 100.0 + i * 10), MockFitzPoint(300.0, 100.0 + i * 10))],
            })
        page = MockPage(drawings)
        extractor = VectorExtractor()
        geom = extractor.extract_raw_geometry(page)
        # None of these should make it into heavy_lines because is_solid is False
        assert len(geom.heavy_lines) == 0

    def test_sub_threshold_lineweights_filtered(self) -> None:
        """Strokes with width < 0.84 pt must be categorized as light lines, not heavy walls."""
        drawings = [
            {
                "type": "s",
                "width": 0.83,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, 500.0), MockFitzPoint(300.0, 500.0))],
            },
            {
                "type": "s",
                "width": 0.48,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, 504.5), MockFitzPoint(300.0, 504.5))],
            },
        ]
        page = MockPage(drawings)
        extractor = VectorExtractor()
        candidates = extractor.extract_wall_candidates(page)
        assert len(candidates) == 0
        geom = extractor.extract_raw_geometry(page)
        assert len(geom.heavy_lines) == 0
        assert len(geom.light_lines) == 2


# ==============================================================================
# 3. PARALLEL LINE PAIRING BOUNDARY STRESS
# ==============================================================================
class TestParallelLinePairingStress:
    """Stress tests boundary thresholds for wall thickness and length."""

    # Real-world thickness range 2" to 14" at 1/8"=1'-0" scale:
    # 2.0" * 0.75 pt/in = 1.50 pt
    # 14.0" * 0.75 pt/in = 10.50 pt
    @pytest.mark.parametrize(
        "spacing,expected_wall",
        [
            (1.49, False),   # Just below min thickness (1.50 pt) -> REJECT
            (1.50, True),    # Exact min thickness (1.50 pt) -> ACCEPT
            (1.51, True),    # Just above min thickness -> ACCEPT
            (4.50, True),    # Nominal 6" wall -> ACCEPT
            (10.49, True),   # Just below max thickness -> ACCEPT
            (10.50, True),   # Exact max thickness (10.50 pt) -> ACCEPT
            (10.51, False),  # Just above max thickness (10.50 pt) -> REJECT
            (12.00, False),  # 16" masonry pier/chase -> REJECT
        ],
    )
    def test_horizontal_thickness_boundary(self, spacing: float, expected_wall: bool) -> None:
        """Tests exact 1.50 pt and 10.50 pt threshold enforcement for horizontal pairs."""
        drawings = [
            {
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, 500.0), MockFitzPoint(300.0, 500.0))],
            },
            {
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, 500.0 + spacing), MockFitzPoint(300.0, 500.0 + spacing))],
            },
        ]
        page = MockPage(drawings)
        extractor = VectorExtractor()
        candidates = extractor.extract_wall_candidates(page)

        if expected_wall:
            assert len(candidates) == 1, f"Failed to form wall candidate for valid spacing {spacing} pt"
            assert abs(candidates[0].thickness_pt - spacing) < 0.1
        else:
            assert len(candidates) == 0, f"Spurious wall candidate formed for invalid spacing {spacing} pt"

    @pytest.mark.parametrize(
        "spacing,expected_wall",
        [
            (1.49, False),
            (1.50, True),
            (10.50, True),
            (10.51, False),
        ],
    )
    def test_vertical_thickness_boundary(self, spacing: float, expected_wall: bool) -> None:
        """Tests exact 1.50 pt and 10.50 pt threshold enforcement for vertical pairs."""
        drawings = [
            {
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(500.0, 100.0), MockFitzPoint(500.0, 300.0))],
            },
            {
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(500.0 + spacing, 100.0), MockFitzPoint(500.0 + spacing, 300.0))],
            },
        ]
        page = MockPage(drawings)
        extractor = VectorExtractor()
        candidates = extractor.extract_wall_candidates(page)

        if expected_wall:
            assert len(candidates) == 1, f"Failed for vertical spacing {spacing}"
        else:
            assert len(candidates) == 0, f"Spurious vertical wall for spacing {spacing}"

    @pytest.mark.parametrize(
        "overlap_len,expected_wall",
        [
            (4.90, False),  # < 5.0 pt min wall length -> REJECT
            (4.99, False),  # < 5.0 pt min wall length -> REJECT
            (5.00, True),   # == 5.0 pt min wall length -> ACCEPT
            (5.01, True),   # > 5.0 pt min wall length -> ACCEPT
        ],
    )
    def test_minimum_wall_length_boundary(self, overlap_len: float, expected_wall: bool) -> None:
        """Tests min_wall_len_pt = 5.0 pt boundary enforcement."""
        drawings = [
            {
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, 500.0), MockFitzPoint(100.0 + overlap_len, 500.0))],
            },
            {
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, 504.5), MockFitzPoint(100.0 + overlap_len, 504.5))],
            },
        ]
        page = MockPage(drawings)
        extractor = VectorExtractor()
        candidates = extractor.extract_wall_candidates(page)

        if expected_wall:
            assert len(candidates) == 1
        else:
            assert len(candidates) == 0

    def test_angular_skew_threshold(self) -> None:
        """
        Tests extractor sensitivity to slight angular skews (CAD drafting imperfections).
        Threshold in extractor.py: dy < 0.15 for horizontal, dx < 0.15 for vertical.
        Line with dy = 0.14 over 100 pt -> accepted as horizontal.
        Line with dy = 0.16 over 100 pt -> rejected (neither horizontal nor vertical).
        """
        line_014 = {
            "type": "s",
            "width": 1.20,
            "dashes": "[] 0",
            "items": [("l", MockFitzPoint(100.0, 500.0), MockFitzPoint(300.0, 500.14))],
        }
        line_base = {
            "type": "s",
            "width": 1.20,
            "dashes": "[] 0",
            "items": [("l", MockFitzPoint(100.0, 504.5), MockFitzPoint(300.0, 504.5))],
        }
        page = MockPage([line_014, line_base])
        extractor = VectorExtractor()
        candidates = extractor.extract_wall_candidates(page)
        assert len(candidates) == 1, "Line with dy=0.14 should be classified as horizontal"

        line_016 = {
            "type": "s",
            "width": 1.20,
            "dashes": "[] 0",
            "items": [("l", MockFitzPoint(100.0, 500.0), MockFitzPoint(300.0, 500.16))],
        }
        page2 = MockPage([line_016, line_base])
        candidates2 = extractor.extract_wall_candidates(page2)
        assert len(candidates2) == 0, "Line with dy=0.16 exceeds 0.15 pt horizontal tolerance"

    def test_dense_linework_chaining_staircase_phenomenon(self) -> None:
        """
        Adversarial Boundary Test:
        When a drawing contains closely spaced heavy parallel lines (such as a staircase
        with 12 treads spaced 6.75 pt / 9 inches apart, all drawn with heavy stroke w=1.20),
        the pairwise pairing algorithm pairs adjacent treads and unary_union merges them
        into a single monolithic block.
        This test documents this exact behavior:
        12 lines -> 1 merged wall candidate with total thickness_pt = 74.25 pt (99 inches).
        """
        drawings = []
        for i in range(12):
            y = 500.0 + i * 6.75
            drawings.append({
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, y), MockFitzPoint(300.0, y))],
            })

        page = MockPage(drawings)
        extractor = VectorExtractor()
        candidates = extractor.extract_wall_candidates(page)

        # Empirically confirms that unary_union merges all chained boxes into 1 assembly
        assert len(candidates) == 1
        wall = candidates[0]
        assert abs(wall.thickness_pt - 74.25) < 0.5
        assert wall.estimated_thickness_in == 99.0
        # The unassigned guardrail correctly flags this anomalous candidate as Uncertain
        assert wall.proposed_class == CLASS_UNCERTAIN


# ==============================================================================
# 4. SCALING & MEMORY STRESS ON SYNTHETIC DATASETS (10,000+ PATHS)
# ==============================================================================
class TestScalingAndMemoryStress:
    """Stress tests memory consumption and scaling under large path counts."""

    def test_vector_presence_detection_scaling_20000_paths(self) -> None:
        """Profiles detect_vector_content on 20,000 paths (representative of Sheet A-101)."""
        mock_drawings = [
            {"items": [("l", MockFitzPoint(i % 1000, (i * 2) % 1000), MockFitzPoint((i + 10) % 1000, (i * 2 + 10) % 1000))]}
            for i in range(20000)
        ]
        words = [(0, 0, 10, 10, f"w_{i}", 0, 0, 0) for i in range(100)]
        page = MockPage(mock_drawings, words=words)

        extractor = VectorExtractor()
        t0 = time.perf_counter()
        profile = extractor.detect_vector_content(page)
        elapsed = time.perf_counter() - t0

        assert profile.path_count == 20000
        assert profile.is_pure_vector is True
        assert profile.recommended_pipeline == "VECTOR_FIRST"
        assert elapsed < 1.0, f"Vector presence profiling took too long: {elapsed:.2f}s"

    def test_extractor_linework_scaling_with_10000_paths(self) -> None:
        """
        Tests extractor on a page with 10,000 mixed CAD paths (9,500 thin drafting lines
        and 500 heavy wall lines forming 250 distinct parallel wall assemblies spaced 20 pt apart).
        Measures memory allocation and execution time.
        """
        tracemalloc.start()
        drawings = []

        # 9,500 light dimension and annotation lines (w = 0.48 pt)
        for i in range(9500):
            drawings.append({
                "type": "s",
                "width": 0.48,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(i % 1500, (i * 3) % 2000), MockFitzPoint((i % 1500) + 50.0, (i * 3) % 2000))],
            })

        # 500 heavy wall boundary lines forming 250 distinct parallel horizontal pairs (w = 1.20 pt)
        # Spaced 20 pt apart (> 10.5 pt, so walls do not accidentally chain-merge)
        for i in range(250):
            y = 100.0 + i * 20.0
            drawings.append({
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, y), MockFitzPoint(200.0, y))],
            })
            drawings.append({
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, y + 4.5), MockFitzPoint(200.0, y + 4.5))],
            })

        page = MockPage(drawings)
        extractor = VectorExtractor()

        t0 = time.perf_counter()
        candidates = extractor.extract_wall_candidates(page)
        elapsed = time.perf_counter() - t0

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)

        # All 250 distinct walls extracted cleanly
        assert len(candidates) == 250
        assert elapsed < 10.0, f"Extraction took {elapsed:.2f}s, expected < 10.0s for 10,000 paths"
        assert peak_mb < 50.0, f"Peak memory {peak_mb:.1f} MB exceeds 50 MB threshold"

    def test_adversarial_heavy_line_o_n2_scaling(self) -> None:
        """
        Adversarial complexity test: 1,000 heavy lines (500 distinct walls).
        Evaluates O(N^2) pairwise pairing worst-case behavior (500,000 pair evaluations).
        Must complete within 10.0 seconds without memory bloat.
        """
        drawings = []
        for i in range(500):
            y = 50.0 + i * 20.0
            drawings.append({
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, y), MockFitzPoint(200.0, y))],
            })
            drawings.append({
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", MockFitzPoint(100.0, y + 4.5), MockFitzPoint(200.0, y + 4.5))],
            })

        page = MockPage(drawings)
        extractor = VectorExtractor()

        t0 = time.perf_counter()
        candidates = extractor.extract_wall_candidates(page)
        elapsed = time.perf_counter() - t0

        assert len(candidates) == 500
        assert elapsed < 10.0, f"Pairwise pairing took {elapsed:.2f}s (exceeded 10s budget)"
