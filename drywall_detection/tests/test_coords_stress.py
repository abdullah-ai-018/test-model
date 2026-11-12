"""
Adversarial stress-testing suite for coordinate transformation module (coords.py).
Evaluates boundary conditions, numerical stability, 10,000 chained roundtrips,
degenerate Shapely topologies, extreme coordinates, and exception handling.
"""

from __future__ import annotations
import math
import numpy as np
import pytest
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.validation import explain_validity

from drywall_detection.config import (
    BASE_DPI,
    DEFAULT_DPI,
    MASTER_PDF_MEDIABOX_HEIGHT_PT,
    MASTER_PDF_MEDIABOX_WIDTH_PT,
    MASTER_PDF_ROTATION_DEG,
)
from drywall_detection.utils.coords import (
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


class TestExtremeCoordinatesStress:
    """Stress tests with extreme numerical values: huge, negative, subnormal."""

    @pytest.mark.parametrize("scale_val", [1e5, 1e7, 1e9, 1e12])
    def test_huge_coordinates_roundtrip(self, scale_val: float):
        """Massive coordinates (up to 10^12) must roundtrip with high relative precision."""
        for rot in (0, 90, 180, 270):
            x, y = scale_val, scale_val * 1.5
            px, py = pdf_to_pixel(x, y, dpi=150, rotation=rot)
            rx, ry = pixel_to_pdf(px, py, dpi=150, rotation=rot)
            assert math.isclose(rx, x, rel_tol=1e-12, abs_tol=1e-4)
            assert math.isclose(ry, y, rel_tol=1e-12, abs_tol=1e-4)

    @pytest.mark.parametrize("neg_val", [-1.0, -100.0, -1e4, -1e7])
    def test_negative_coordinates_roundtrip(self, neg_val: float):
        """Negative coordinates (e.g. annotations outside crop box) must roundtrip cleanly."""
        for rot in (0, 90, 180, 270):
            x, y = neg_val, neg_val * 2.0
            px, py = pdf_to_pixel(x, y, dpi=150, rotation=rot)
            rx, ry = pixel_to_pdf(px, py, dpi=150, rotation=rot)
            assert math.isclose(rx, x, abs_tol=1e-4)
            assert math.isclose(ry, y, abs_tol=1e-4)

    def test_subnormal_and_near_zero_coordinates(self):
        """Coordinates very close to zero (1e-15, -0.0) must not cause underflow or sign flip."""
        for rot in (0, 90, 180, 270):
            x, y = 1e-15, -0.0
            px, py = pdf_to_pixel(x, y, dpi=150, rotation=rot)
            rx, ry = pixel_to_pdf(px, py, dpi=150, rotation=rot)
            assert math.isclose(rx, 0.0, abs_tol=1e-12)
            assert math.isclose(ry, 0.0, abs_tol=1e-12)

    def test_boundary_corners_exactness(self):
        """Test exact boundary coordinates: 0, width, height, and midpoints."""
        w = MASTER_PDF_MEDIABOX_WIDTH_PT
        h = MASTER_PDF_MEDIABOX_HEIGHT_PT
        boundaries = [
            (0.0, 0.0),
            (w, 0.0),
            (0.0, h),
            (w, h),
            (w / 2.0, h / 2.0),
            (0.0001, 0.0001),
            (w - 0.0001, h - 0.0001),
        ]
        for x, y in boundaries:
            for rot in (0, 90, 180, 270):
                px, py = pdf_to_pixel(x, y, dpi=150, rotation=rot)
                rx, ry = pixel_to_pdf(px, py, dpi=150, rotation=rot)
                assert math.isclose(rx, x, abs_tol=1e-4)
                assert math.isclose(ry, y, abs_tol=1e-4)


class TestChainedRoundtripPrecisionStress:
    """Stress testing 10,000 chained roundtrips to test cumulative floating-point drift."""

    def test_chained_roundtrip_10000_iterations(self):
        """
        Starting from a key partition tag coordinate (772.44, 1094.52),
        chain 10,000 continuous forward and inverse transformations:
        p_{k+1} = pixel_to_pdf(pdf_to_pixel(p_k))
        Verify that cumulative drift across 10,000 cycles remains < 1e-4 pt.
        """
        orig_x, orig_y = 772.44, 1094.52
        dpi = 150
        rotation = 90

        cur_x, cur_y = orig_x, orig_y
        max_drift_x = 0.0
        max_drift_y = 0.0

        for _ in range(10_000):
            px, py = pdf_to_pixel(cur_x, cur_y, dpi=dpi, rotation=rotation)
            cur_x, cur_y = pixel_to_pdf(px, py, dpi=dpi, rotation=rotation)
            drift_x = abs(cur_x - orig_x)
            drift_y = abs(cur_y - orig_y)
            if drift_x > max_drift_x:
                max_drift_x = drift_x
            if drift_y > max_drift_y:
                max_drift_y = drift_y

        assert max_drift_x < 1e-4, f"X drift exceeded 1e-4: {max_drift_x}"
        assert max_drift_y < 1e-4, f"Y drift exceeded 1e-4: {max_drift_y}"
        assert math.isclose(cur_x, orig_x, abs_tol=1e-4)
        assert math.isclose(cur_y, orig_y, abs_tol=1e-4)

    @pytest.mark.parametrize("dpi", [72, 150, 200, 300, 600])
    @pytest.mark.parametrize("rot", [0, 90, 180, 270])
    def test_chained_roundtrip_1000_all_orientations(self, dpi: int, rot: int):
        """Chained 1,000 roundtrips across all rotations and DPIs."""
        orig_x, orig_y = 512.12345, 1289.98765
        cur_x, cur_y = orig_x, orig_y
        for _ in range(1000):
            px, py = pdf_to_pixel(cur_x, cur_y, dpi=dpi, rotation=rot)
            cur_x, cur_y = pixel_to_pdf(px, py, dpi=dpi, rotation=rot)

        assert math.isclose(cur_x, orig_x, abs_tol=1e-4)
        assert math.isclose(cur_y, orig_y, abs_tol=1e-4)


class TestNonStandardRotationsAndExceptionsStress:
    """Stress tests on invalid, non-standard, or malicious parameters."""

    @pytest.mark.parametrize("invalid_rot", [45, 30, -90, -180, 360, 91, 89, 180.5])
    def test_invalid_rotations_raise_value_error(self, invalid_rot):
        """Any rotation not in (0, 90, 180, 270) must raise ValueError."""
        with pytest.raises(ValueError, match="[Uu]nsupported rotation"):
            pdf_to_pixel(100.0, 100.0, rotation=invalid_rot)

        with pytest.raises(ValueError, match="[Uu]nsupported rotation"):
            pixel_to_pdf(100.0, 100.0, rotation=invalid_rot)

        with pytest.raises(ValueError, match="[Uu]nsupported rotation"):
            get_forward_matrix(rotation=invalid_rot)

        with pytest.raises(ValueError, match="[Uu]nsupported rotation"):
            get_inverse_matrix(rotation=invalid_rot)

        with pytest.raises(ValueError, match="[Uu]nsupported rotation"):
            pdf_bbox_to_pixel((10.0, 10.0, 20.0, 20.0), rotation=invalid_rot)

        with pytest.raises(ValueError, match="[Uu]nsupported rotation"):
            pdf_points_to_pixel(np.array([[10.0, 10.0]]), rotation=invalid_rot)

        with pytest.raises(ValueError, match="[Uu]nsupported rotation"):
            pdf_geom_to_pixel(Point(10.0, 10.0), rotation=invalid_rot)

    @pytest.mark.parametrize("invalid_dpi", [0, -1, -72, -150])
    def test_invalid_dpi_raises_value_error(self, invalid_dpi):
        """Non-positive DPI must raise ValueError."""
        with pytest.raises(ValueError, match="[Dd][Pp][Ii]"):
            pdf_to_pixel(100.0, 100.0, dpi=invalid_dpi)

        with pytest.raises(ValueError, match="[Dd][Pp][Ii]"):
            pixel_to_pdf(100.0, 100.0, dpi=invalid_dpi)

        with pytest.raises(ValueError, match="[Dd][Pp][Ii]"):
            get_forward_matrix(dpi=invalid_dpi)

        with pytest.raises(ValueError, match="[Dd][Pp][Ii]"):
            get_inverse_matrix(dpi=invalid_dpi)

    def test_non_finite_scalars_raise_value_error(self):
        """NaN and Inf in scalar transformations must raise ValueError."""
        for non_finite in (float("nan"), float("inf"), float("-inf")):
            with pytest.raises(ValueError, match="finite"):
                pdf_to_pixel(non_finite, 100.0)
            with pytest.raises(ValueError, match="finite"):
                pdf_to_pixel(100.0, non_finite)
            with pytest.raises(ValueError, match="finite"):
                pixel_to_pdf(non_finite, 100.0)
            with pytest.raises(ValueError, match="finite"):
                pixel_to_pdf(100.0, non_finite)


class TestDegenerateShapelyGeometriesStress:
    """Stress tests on degenerate, malformed, self-intersecting, and empty Shapely geometries."""

    def test_zero_area_collinear_polygon(self):
        """A degenerate polygon with collinear vertices (zero area) should transform without crash."""
        collinear_poly = Polygon([(0.0, 0.0), (100.0, 0.0), (200.0, 0.0), (0.0, 0.0)])
        assert collinear_poly.area == 0.0

        poly_px = pdf_geom_to_pixel(collinear_poly, dpi=150, rotation=90)
        assert poly_px is not None
        assert poly_px.area == 0.0

        poly_rt = pixel_geom_to_pdf(poly_px, dpi=150, rotation=90)
        assert math.isclose(poly_rt.area, 0.0, abs_tol=1e-6)

    def test_zero_area_point_polygon(self):
        """A polygon collapsed to a single point."""
        point_poly = Polygon([(50.0, 50.0), (50.0, 50.0), (50.0, 50.0), (50.0, 50.0)])
        poly_px = pdf_geom_to_pixel(point_poly, dpi=150, rotation=90)
        assert poly_px.area == 0.0
        poly_rt = pixel_geom_to_pdf(poly_px, dpi=150, rotation=90)
        assert poly_rt.area == 0.0

    def test_self_intersecting_bowtie_polygon(self):
        """A self-intersecting bowtie polygon (invalid topology) must transform its vertices faithfully."""
        # Bowtie: (0,0) -> (100,100) -> (0,100) -> (100,0) -> (0,0)
        bowtie = Polygon([(0.0, 0.0), (100.0, 100.0), (0.0, 100.0), (100.0, 0.0), (0.0, 0.0)])
        assert not bowtie.is_valid

        bowtie_px = pdf_geom_to_pixel(bowtie, dpi=150, rotation=90)
        assert bowtie_px is not None
        assert not bowtie_px.is_valid  # Invariant: self-intersection preserved under affine

        bowtie_rt = pixel_geom_to_pdf(bowtie_px, dpi=150, rotation=90)
        assert not bowtie_rt.is_valid
        assert bowtie.equals_exact(bowtie_rt, tolerance=1e-4)

    def test_empty_geometries_handling(self):
        """Empty Shapely geometries must return empty geometries gracefully without error."""
        empty_geoms = [
            Polygon(),
            LineString(),
            Point(),
            MultiPolygon([]),
            MultiLineString([]),
            MultiPoint([]),
            GeometryCollection([]),
        ]
        for g in empty_geoms:
            g_px = pdf_geom_to_pixel(g, dpi=150, rotation=90)
            assert g_px.is_empty
            g_rt = pixel_geom_to_pdf(g_px, dpi=150, rotation=90)
            assert g_rt.is_empty

    def test_none_geometry_handling(self):
        """Passing None returns None safely."""
        assert pdf_geom_to_pixel(None) is None
        assert pixel_geom_to_pdf(None) is None

    def test_microscopic_polygon_precision(self):
        """Microscopic polygon (width 1e-4 pt) must preserve geometry and relative area."""
        micro_poly = Polygon([(100.0, 100.0), (100.0001, 100.0), (100.0001, 100.0001), (100.0, 100.0001)])
        poly_px = pdf_geom_to_pixel(micro_poly, dpi=150, rotation=90)
        poly_rt = pixel_geom_to_pdf(poly_px, dpi=150, rotation=90)
        assert micro_poly.equals_exact(poly_rt, tolerance=1e-5)


class TestMultiPolygonsWithDeeplyNestedHolesStress:
    """Stress tests for multi-polygons with 50+ holes and deeply nested structures."""

    def test_polygon_with_50_holes(self):
        """Exterior square with a grid of 50 circular-approximated holes."""
        exterior = [(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0)]
        holes = []
        # Generate 50 distinct holes (5 rows of 10 holes)
        for row in range(5):
            for col in range(10):
                cx = 50.0 + col * 90.0
                cy = 50.0 + row * 180.0
                # Small square hole 20x20
                h = [(cx, cy), (cx + 20.0, cy), (cx + 20.0, cy + 20.0), (cx, cy + 20.0)]
                holes.append(h)

        assert len(holes) == 50
        complex_poly = Polygon(shell=exterior, holes=holes)
        assert complex_poly.is_valid

        poly_px = pdf_geom_to_pixel(complex_poly, dpi=150, rotation=90)
        assert poly_px.is_valid
        assert len(poly_px.interiors) == 50

        # Check area scaling invariant
        scale = 150.0 / BASE_DPI
        expected_area = complex_poly.area * (scale ** 2)
        assert math.isclose(poly_px.area, expected_area, rel_tol=1e-5)

        poly_rt = pixel_geom_to_pdf(poly_px, dpi=150, rotation=90)
        assert poly_rt.is_valid
        assert len(poly_rt.interiors) == 50
        assert complex_poly.equals_exact(poly_rt, tolerance=1e-4)

    def test_multipolygon_with_nested_island_donut(self):
        """
        MultiPolygon representing:
        - Outer donut: [0..400] square with hole [100..300]
        - Inner island: [150..250] square located inside that hole
        """
        outer_shell = [(0.0, 0.0), (400.0, 0.0), (400.0, 400.0), (0.0, 400.0)]
        outer_hole = [(100.0, 100.0), (300.0, 100.0), (300.0, 300.0), (100.0, 300.0)]
        poly_donut = Polygon(shell=outer_shell, holes=[outer_hole])

        island_shell = [(150.0, 150.0), (250.0, 150.0), (250.0, 250.0), (150.0, 250.0)]
        poly_island = Polygon(shell=island_shell)

        mp = MultiPolygon([poly_donut, poly_island])
        assert mp.is_valid
        assert len(mp.geoms) == 2

        mp_px = pdf_geom_to_pixel(mp, dpi=150, rotation=90)
        assert mp_px.is_valid
        assert len(mp_px.geoms) == 2

        mp_rt = pixel_geom_to_pdf(mp_px, dpi=150, rotation=90)
        assert mp_rt.is_valid
        assert mp.equals_exact(mp_rt, tolerance=1e-4)


class TestBoundingBoxAndVectorizedStress:
    """Stress tests on bounding box boundaries and vectorized arrays."""

    def test_degenerate_point_bounding_box(self):
        """Bounding box collapsed to a single point (x0==x1, y0==y1)."""
        bbox = (150.0, 300.0, 150.0, 300.0)
        pbbox = pdf_bbox_to_pixel(bbox, dpi=150, rotation=90)
        assert pbbox[0] == pbbox[2]
        assert pbbox[1] == pbbox[3]
        rbbox = pixel_bbox_to_pdf(pbbox, dpi=150, rotation=90)
        assert math.isclose(rbbox[0], 150.0, abs_tol=1e-4)
        assert math.isclose(rbbox[1], 300.0, abs_tol=1e-4)
        assert math.isclose(rbbox[2], 150.0, abs_tol=1e-4)
        assert math.isclose(rbbox[3], 300.0, abs_tol=1e-4)

    def test_extreme_bounding_box(self):
        """Bounding box spanning from -1e6 to 1e6."""
        bbox = (-1e6, -1e6, 1e6, 1e6)
        pbbox = pdf_bbox_to_pixel(bbox, dpi=150, rotation=90)
        rbbox = pixel_bbox_to_pdf(pbbox, dpi=150, rotation=90)
        for orig, rt in zip(bbox, rbbox):
            assert math.isclose(orig, rt, abs_tol=1e-4)

    def test_vectorized_empty_array(self):
        """Vectorized transformation of empty (0, 2) array."""
        empty_pts = np.empty((0, 2), dtype=np.float64)
        out_px = pdf_points_to_pixel(empty_pts, dpi=150, rotation=90)
        assert out_px.shape == (0, 2)
        out_pdf = pixel_points_to_pdf(out_px, dpi=150, rotation=90)
        assert out_pdf.shape == (0, 2)

    def test_vectorized_50000_points_performance_and_precision(self):
        """Vectorized transformation of 50,000 random points."""
        np.random.seed(123)
        pts = np.random.uniform(low=-1000.0, high=5000.0, size=(50_000, 2))
        pxs = pdf_points_to_pixel(pts, dpi=150, rotation=90)
        rpts = pixel_points_to_pdf(pxs, dpi=150, rotation=90)
        max_err = np.max(np.abs(pts - rpts))
        assert max_err < 1e-4, f"Vectorized max error was {max_err}"
