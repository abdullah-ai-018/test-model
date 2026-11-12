"""
Unit tests for coordinate geometry and affine transformations.
Verifies exact forward and inverse bijection between native unrotated PDF point space
and visual rotated raster space under 90-degree clockwise (and multi-quadrant) rotations.
"""

from __future__ import annotations
import math
import random
import numpy as np
import pytest
from shapely.geometry import LineString, MultiPolygon, Point, Polygon

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
    transform_bbox_to_pdf,
    transform_bbox_to_pixel,
    transform_polygon_to_pdf,
    transform_polygon_to_pixel,
)


class TestPointCoordinateTransforms:
    """Test suite for point forward and inverse transformations."""

    def test_forward_matrix_determinant(self):
        """Determinant of forward matrix must equal S^2 > 0."""
        dpi = 150
        s = dpi / float(BASE_DPI)
        expected_det = s ** 2
        m = get_forward_matrix(dpi=dpi)
        det = np.linalg.det(m[:2, :2])
        assert math.isclose(det, expected_det, rel_tol=1e-6)
        assert det > 0.0

    def test_matrix_inversion_identity(self):
        """M * M^(-1) == Identity within 1e-6 tolerance across DPIs."""
        for dpi in [72, 100, 150, 200, 300]:
            m = get_forward_matrix(dpi=dpi)
            m_inv = get_inverse_matrix(dpi=dpi)
            prod = np.dot(m, m_inv)
            identity = np.eye(3, dtype=np.float64)
            assert np.allclose(prod, identity, atol=1e-6)

    def test_known_point_mapping_72_dpi(self):
        """At 72 DPI (S=1.0), (100, 200) maps to px=2592-200=2392, py=100."""
        px, py = pdf_to_pixel(100.0, 200.0, dpi=72, rotation=90)
        assert px == 2392.0
        assert py == 100.0

    def test_known_point_mapping_150_dpi(self):
        """(0, 2592) is bottom-left of unrotated page, mapping to (0, 0) rotated top-left."""
        px, py = pdf_to_pixel(0.0, 2592.0, dpi=150, rotation=90)
        assert math.isclose(px, 0.0, abs_tol=1e-5)
        assert math.isclose(py, 0.0, abs_tol=1e-5)

    def test_point_bijection_roundtrip_landmarks(self):
        """Test roundtrip bijection on key landmark coordinates at 150 DPI."""
        test_points = [
            (0.0, 0.0),
            (1728.0, 0.0),
            (0.0, 2592.0),
            (1728.0, 2592.0),
            (864.0, 1296.0),
            (500.0, 1200.0),
            (772.44, 1094.52),
        ]
        for x, y in test_points:
            px, py = pdf_to_pixel(x, y, dpi=150, rotation=90)
            rx, ry = pixel_to_pdf(px, py, dpi=150, rotation=90)
            assert math.isclose(rx, x, abs_tol=1e-4), f"Failed X bijection for ({x}, {y})"
            assert math.isclose(ry, y, abs_tol=1e-4), f"Failed Y bijection for ({x}, {y})"

    def test_point_bijection_random_samples(self):
        """Test roundtrip bijection on 100 random samples across diverse DPIs."""
        random.seed(42)
        dpis = [72, 100, 150, 200, 300]
        for dpi in dpis:
            for _ in range(20):
                x = random.uniform(0.0, MASTER_PDF_MEDIABOX_WIDTH_PT)
                y = random.uniform(0.0, MASTER_PDF_MEDIABOX_HEIGHT_PT)
                px, py = pdf_to_pixel(x, y, dpi=dpi, rotation=90)
                rx, ry = pixel_to_pdf(px, py, dpi=dpi, rotation=90)
                assert math.isclose(rx, x, abs_tol=1e-4)
                assert math.isclose(ry, y, abs_tol=1e-4)

    def test_multi_quadrant_rotations(self):
        """Verify forward and inverse roundtrip for 0, 90, 180, and 270 degree rotations."""
        x, y = 500.0, 1200.0
        for rot in [0, 90, 180, 270]:
            px, py = pdf_to_pixel(x, y, dpi=150, rotation=rot)
            rx, ry = pixel_to_pdf(px, py, dpi=150, rotation=rot)
            assert math.isclose(rx, x, abs_tol=1e-4), f"Rotation {rot} failed X bijection"
            assert math.isclose(ry, y, abs_tol=1e-4), f"Rotation {rot} failed Y bijection"

    def test_invalid_rotation_raises_value_error(self):
        """Non-orthogonal rotations must raise ValueError."""
        with pytest.raises(ValueError, match="[Uu]nsupported rotation"):
            pdf_to_pixel(100.0, 100.0, rotation=45)

        with pytest.raises(ValueError, match="[Uu]nsupported rotation"):
            pdf_to_pixel(100.0, 100.0, rotation=-90)

    def test_invalid_dpi_raises_value_error(self):
        """Zero or negative DPI must raise ValueError."""
        with pytest.raises(ValueError, match="[Dd][Pp][Ii]"):
            pdf_to_pixel(100.0, 100.0, dpi=0)

        with pytest.raises(ValueError, match="[Dd][Pp][Ii]"):
            pixel_to_pdf(100.0, 100.0, dpi=-150)

    def test_nan_or_inf_raises_value_error(self):
        """Non-finite coordinates must raise ValueError."""
        with pytest.raises(ValueError, match="finite"):
            pdf_to_pixel(float("nan"), 100.0)

        with pytest.raises(ValueError, match="finite"):
            pixel_to_pdf(100.0, float("inf"))


class TestBoundingBoxTransforms:
    """Test suite for axis-aligned bounding box transformations."""

    def test_bbox_forward_normalization_90deg(self):
        """Pixel bounding box must maintain normalized ordering px_min <= px_max and py_min <= py_max."""
        bbox = (100.0, 200.0, 300.0, 500.0)
        pbbox = pdf_bbox_to_pixel(bbox, dpi=150, rotation=90)
        px0, py0, px1, py1 = pbbox
        assert px0 <= px1
        assert py0 <= py1

    def test_bbox_full_page_coverage(self):
        """Full page unrotated bbox (0, 0, 1728, 2592) maps to (0, 0, 5400, 3600) at 150 DPI."""
        full_page = (0.0, 0.0, 1728.0, 2592.0)
        pbbox = pdf_bbox_to_pixel(full_page, dpi=150, rotation=90)
        # Visual width = 2592 * (150/72) = 5400, height = 1728 * (150/72) = 3600
        assert math.isclose(pbbox[0], 0.0, abs_tol=1e-4)
        assert math.isclose(pbbox[1], 0.0, abs_tol=1e-4)
        assert math.isclose(pbbox[2], 5400.0, abs_tol=1e-4)
        assert math.isclose(pbbox[3], 3600.0, abs_tol=1e-4)

    def test_bbox_roundtrip_bijection(self):
        """BBox roundtrip must match original within 1e-4 pt."""
        # Partition tag symbol bounding box (11.2 x 11.3 pt)
        tag_bbox = (770.0, 1080.0, 781.2, 1091.3)
        pbbox = pdf_bbox_to_pixel(tag_bbox, dpi=150, rotation=90)
        rbbox = pixel_bbox_to_pdf(pbbox, dpi=150, rotation=90)
        for orig, roundtrip in zip(tag_bbox, rbbox):
            assert math.isclose(orig, roundtrip, abs_tol=1e-4)

    def test_bbox_inverted_input_raises_error(self):
        """Inverted bounding box input must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid bounding box ordering"):
            pdf_bbox_to_pixel((300.0, 500.0, 100.0, 200.0))


class TestVectorizedPointsTransforms:
    """Test suite for vectorized (N, 2) array transformations."""

    def test_vectorized_points_roundtrip(self):
        """1000 random points vectorized forward and inverse roundtrip error < 1e-4."""
        np.random.seed(42)
        pts = np.random.uniform(
            low=[0.0, 0.0],
            high=[MASTER_PDF_MEDIABOX_WIDTH_PT, MASTER_PDF_MEDIABOX_HEIGHT_PT],
            size=(1000, 2),
        )
        pxs = pdf_points_to_pixel(pts, dpi=150, rotation=90)
        rpts = pixel_points_to_pdf(pxs, dpi=150, rotation=90)
        max_err = np.max(np.abs(pts - rpts))
        assert max_err < 1e-4

    def test_vectorized_points_invalid_shape_raises(self):
        """Non-(N, 2) array must raise ValueError."""
        with pytest.raises(ValueError, match="Expected \\(N, 2\\)"):
            pdf_points_to_pixel(np.zeros((10, 3)))


class TestShapelyGeometryTransforms:
    """Test suite for Shapely geometries (Polygon, LineString, MultiPolygon)."""

    def test_shapely_polygon_with_hole_roundtrip(self):
        """Shapely Polygon with interior hole roundtrip preserves topology and equality."""
        exterior = [(50.0, 50.0), (500.0, 50.0), (500.0, 500.0), (50.0, 500.0)]
        hole = [(150.0, 150.0), (350.0, 150.0), (350.0, 350.0), (150.0, 350.0)]
        poly = Polygon(shell=exterior, holes=[hole])
        assert poly.is_valid

        poly_px = pdf_geom_to_pixel(poly, dpi=150, rotation=90)
        assert poly_px.is_valid
        assert len(poly_px.interiors) == 1

        poly_rt = pixel_geom_to_pdf(poly_px, dpi=150, rotation=90)
        assert poly_rt.is_valid
        assert poly.equals_exact(poly_rt, tolerance=1e-4)

    def test_shapely_polygon_area_scaling_invariant(self):
        """Transformed polygon area must scale by S^2."""
        poly = Polygon([(100.0, 200.0), (300.0, 200.0), (300.0, 400.0), (100.0, 400.0)])
        dpi = 150
        scale = dpi / float(BASE_DPI)
        expected_ratio = scale ** 2

        poly_px = pdf_geom_to_pixel(poly, dpi=dpi, rotation=90)
        ratio = poly_px.area / poly.area
        assert math.isclose(ratio, expected_ratio, rel_tol=1e-5)

    def test_shapely_linestring_transform(self):
        """Leader line LineString length must scale by S, vertices roundtrip exactly."""
        line = LineString([(772.44, 1094.52), (772.44, 1082.76)])
        dpi = 150
        scale = dpi / float(BASE_DPI)

        line_px = pdf_geom_to_pixel(line, dpi=dpi, rotation=90)
        assert math.isclose(line_px.length, line.length * scale, rel_tol=1e-5)

        line_rt = pixel_geom_to_pdf(line_px, dpi=dpi, rotation=90)
        assert line.equals_exact(line_rt, tolerance=1e-4)

    def test_shapely_multipolygon_support(self):
        """MultiPolygon representing disjoint wall assemblies roundtrips cleanly."""
        poly1 = Polygon([(10.0, 10.0), (50.0, 10.0), (50.0, 50.0), (10.0, 50.0)])
        poly2 = Polygon([(100.0, 100.0), (150.0, 100.0), (150.0, 150.0), (100.0, 150.0)])
        mpoly = MultiPolygon([poly1, poly2])

        mpoly_px = pdf_geom_to_pixel(mpoly, dpi=150, rotation=90)
        assert mpoly_px.is_valid
        assert len(mpoly_px.geoms) == 2

        mpoly_rt = pixel_geom_to_pdf(mpoly_px, dpi=150, rotation=90)
        assert mpoly.equals_exact(mpoly_rt, tolerance=1e-4)

    def test_aliases_work_identically(self):
        """Ensure transform_polygon_to_pixel and transform_bbox_to_pixel aliases work."""
        bbox = (10.0, 20.0, 30.0, 40.0)
        p1 = pdf_bbox_to_pixel(bbox)
        p2 = transform_bbox_to_pixel(bbox)
        assert p1 == p2

        pt = Point(50.0, 50.0)
        pt_px1 = pdf_geom_to_pixel(pt)
        pt_px2 = transform_polygon_to_pixel(pt)
        assert pt_px1.equals_exact(pt_px2, tolerance=1e-6)
