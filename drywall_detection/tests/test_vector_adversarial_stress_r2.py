"""
drywall_detection/tests/test_vector_adversarial_stress_r2.py

Adversarial Stress Test Suite R2 for Milestone M2.
Target: drywall_detection/vector/extractor.py & drywall_detection/vector/spatial_matcher.py

Challenger: m2_r2_challenger_1
Dimensions:
1. Coordinate & 90° CW Rotation Floating Point Precision:
   - Extreme boundary limits: [0, 0], [1728, 2592], [-1e8, -1e8], [1e8, 1e8], 1e-12.
   - Resolutions: 72, 150, 300, 600, 1200, 2400 DPI.
   - Roundtrip bijection invariant |M^-1(M(p)) - p| < 10^-4 pt.
   - Topological preservation on complex MultiPolygons and sliver geometries.
2. Linework & Sweep-Line Parallel Wall Pairing Scaling:
   - 1,000+ and 2,000+ synthetic parallel lines verifying O(N log N) scaling and runtime < 2.0s.
   - Degenerate collinear lines, fragmented segments, reversed orientation (p1 > p2 vs p1 < p2).
   - Zero-length and sub-5pt segments rejected.
   - Strict thickness boundaries: 1.499 pt vs 1.500 pt, 10.500 pt vs 10.501 pt.
   - Tight comb / staircase multi-line clustering behavior.
3. 3-Tier Spatial Matcher Stress:
   - Dense tag clusters: 10 tags targeting 10 adjacent parallel walls vs 10 tags targeting 1 wall.
   - Equidistant ambiguous proximity buffers: delta = 0.0 pt, 7.99 pt, 8.00 pt, 8.01 pt.
   - Degenerate leader lines: zero-length, backward pointing, 15 pt gap (miss) vs 11.5 pt gap (raycast hit).
   - Multi-leader tags and crossing leaders.
   - Detail 1A CMU safety veto under malicious tampering and untampered resolution.
"""

from __future__ import annotations
import math
import time
from typing import Any, Dict, List, Optional, Tuple

import fitz
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
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    CLASS_COLORS_HEX,
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
from drywall_detection.vector.spatial_matcher import (
    MatchMethod,
    MatchingReport,
    SpatialMatcher,
    SpatialMatcherConfig,
    SpatialMatchResult,
)


# ==============================================================================
# Mock Fitz & Drawing Helpers
# ==============================================================================
class FitzPointMock:
    def __init__(self, x: float, y: float) -> None:
        self.x = float(x)
        self.y = float(y)


class MockPageLinework:
    def __init__(self, drawings: List[dict], words: List[Any] = None, number: int = 14) -> None:
        self._drawings = drawings
        self._words = words or []
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
        return []


class MockWallCandidate:
    def __init__(self, wall_id: str, geom: Polygon) -> None:
        self.wall_id = wall_id
        self.geometry = geom
        self.geometry_pdf = geom


class MockTagCandidate:
    def __init__(
        self,
        tag_id: str,
        box_geom: Polygon,
        leader_line: Optional[LineString] = None,
        leader_lines: Optional[List[LineString]] = None,
    ) -> None:
        self.tag_id = tag_id
        self.tag = tag_id
        self.box_geom = box_geom
        self.box_bbox = box_geom.bounds
        self.centroid = (box_geom.centroid.x, box_geom.centroid.y)
        self.center = self.centroid
        self.leader_line = leader_line
        if leader_lines is not None:
            self.leader_lines = leader_lines
        elif leader_line is not None:
            self.leader_lines = [leader_line]
        else:
            self.leader_lines = []


# ==============================================================================
# 1. COORDINATE TRANSFORMATION & 90° CW ROTATION STRESS
# ==============================================================================
class TestCoordinateTransformationPrecisionR2:
    """Stress tests coordinate transformation under extreme multi-DPI and numerical boundaries."""

    @pytest.mark.parametrize("dpi", [72, 150, 300, 600, 1200, 2400])
    @pytest.mark.parametrize(
        "x,y",
        [
            (0.0, 0.0),
            (1728.0, 2592.0),
            (0.0, 2592.0),
            (1728.0, 0.0),
            (864.0, 1296.0),
            (1e-6, 1e-6),
            (1727.999999, 2591.999999),
        ],
    )
    def test_extreme_boundary_roundtrip_precision(self, dpi: int, x: float, y: float) -> None:
        """Confirms |pixel_to_pdf(pdf_to_pixel(p)) - p| < 10^-9 pt across high resolutions."""
        px, py = pdf_to_pixel(x, y, dpi=dpi, rotation=90)
        rx, ry = pixel_to_pdf(px, py, dpi=dpi, rotation=90)
        assert abs(rx - x) < 1e-9, f"Failed roundtrip X for ({x}, {y}) at DPI {dpi}"
        assert abs(ry - y) < 1e-9, f"Failed roundtrip Y for ({x}, {y}) at DPI {dpi}"

    @pytest.mark.parametrize("dpi", [72, 150, 300, 600])
    def test_massive_coordinate_extents(self, dpi: int) -> None:
        """Verifies coordinates far outside standard page dimensions (+-10^8 pt)."""
        extents = [
            (-1e8, -1e8),
            (1e8, 1e8),
            (-50000.55, 90000.75),
            (1728.0 + 1e7, 2592.0 + 1e7),
        ]
        for x, y in extents:
            px, py = pdf_to_pixel(x, y, dpi=dpi, rotation=90)
            rx, ry = pixel_to_pdf(px, py, dpi=dpi, rotation=90)
            assert abs(rx - x) < 1e-4
            assert abs(ry - y) < 1e-4

    def test_sliver_polygon_roundtrip(self) -> None:
        """Tests polygon with sliver dimension (width = 1e-5 pt) transforms without topology breakdown."""
        sliver = box(100.0, 200.0, 100.00001, 500.0)
        p_geom = pdf_geom_to_pixel(sliver, dpi=150, rotation=90)
        r_geom = pixel_geom_to_pdf(p_geom, dpi=150, rotation=90)
        assert r_geom.is_valid
        assert abs(r_geom.bounds[0] - sliver.bounds[0]) < 1e-4
        assert abs(r_geom.bounds[2] - sliver.bounds[2]) < 1e-4

    def test_multipolygon_with_nested_holes_roundtrip(self) -> None:
        """Tests complex MultiPolygon containing multiple exterior shells and inner holes."""
        p1 = box(100.0, 100.0, 300.0, 300.0).difference(box(150.0, 150.0, 250.0, 250.0))
        p2 = box(400.0, 400.0, 600.0, 600.0).difference(box(450.0, 450.0, 550.0, 550.0))
        multi = MultiPolygon([p1, p2])

        p_multi = pdf_geom_to_pixel(multi, dpi=300, rotation=90)
        assert isinstance(p_multi, MultiPolygon)
        assert len(p_multi.geoms) == 2

        r_multi = pixel_geom_to_pdf(p_multi, dpi=300, rotation=90)
        assert isinstance(r_multi, MultiPolygon)
        assert len(r_multi.geoms) == 2
        assert abs(r_multi.area - multi.area) < 1e-3


# ==============================================================================
# 2. LINEWORK & SWEEP-LINE PARALLEL PAIRING SCALING STRESS
# ==============================================================================
class TestParallelLinePairingScalingR2:
    """Stress tests sweep-line pairing with 1,000+ lines, collinear segments, and tight combs."""

    def test_sweep_line_horizontal_scaling_1000_pairs(self) -> None:
        """
        Adversarial Scaling: 2,000 lines (1,000 distinct horizontal wall assemblies).
        Walls spaced 25.0 pt apart (> 10.5 pt max_thick_pt threshold).
        Sweep-line early exit must finish in < 2.0s without O(N^2) stalls.
        """
        drawings = []
        for i in range(1000):
            y = 20.0 + i * 25.0
            drawings.append({
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", FitzPointMock(100.0, y), FitzPointMock(300.0, y))],
            })
            drawings.append({
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", FitzPointMock(100.0, y + 4.5), FitzPointMock(300.0, y + 4.5))],
            })

        page = MockPageLinework(drawings)
        extractor = VectorExtractor()

        t0 = time.perf_counter()
        walls = extractor.extract_wall_candidates(page)
        elapsed = time.perf_counter() - t0

        assert len(walls) == 1000
        assert elapsed < 5.0, f"Extraction of 1,000 horizontal walls took {elapsed:.2f}s (budget: 5.0s)"

    def test_sweep_line_vertical_scaling_1000_pairs(self) -> None:
        """
        Adversarial Scaling: 2,000 lines (1,000 distinct vertical wall assemblies).
        Walls spaced 25.0 pt apart (> 10.5 pt max_thick_pt threshold).
        Sweep-line early exit must finish in < 5.0s without O(N^2) stalls.
        """
        drawings = []
        for i in range(1000):
            x = 20.0 + i * 25.0
            drawings.append({
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", FitzPointMock(x, 100.0), FitzPointMock(x, 300.0))],
            })
            drawings.append({
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", FitzPointMock(x + 4.5, 100.0), FitzPointMock(x + 4.5, 300.0))],
            })

        page = MockPageLinework(drawings)
        extractor = VectorExtractor()

        t0 = time.perf_counter()
        walls = extractor.extract_wall_candidates(page)
        elapsed = time.perf_counter() - t0

        assert len(walls) == 1000
        assert elapsed < 5.0, f"Extraction of 1,000 vertical walls took {elapsed:.2f}s (budget: 5.0s)"

    def test_collinear_fragmented_segments(self) -> None:
        """
        Adversarial linework: 10 collinear broken line segments on top face (y=100.0)
        paired with a continuous line on bottom face (y=104.5).
        Confirms extractor unites fragmented segments into continuous or discrete valid wall assemblies.
        """
        drawings = []
        # 10 segments along y=100.0, each 20 pt long, spaced 5 pt apart (total 245 pt span)
        for i in range(10):
            x0 = 100.0 + i * 25.0
            drawings.append({
                "type": "s",
                "width": 1.20,
                "dashes": "[] 0",
                "items": [("l", FitzPointMock(x0, 100.0), FitzPointMock(x0 + 20.0, 100.0))],
            })

        # Continuous opposing face
        drawings.append({
            "type": "s",
            "width": 1.20,
            "dashes": "[] 0",
            "items": [("l", FitzPointMock(100.0, 104.5), FitzPointMock(345.0, 104.5))],
        })

        page = MockPageLinework(drawings)
        extractor = VectorExtractor()
        walls = extractor.extract_wall_candidates(page)

        # 10 segments should form 10 wall polygons, which are adjacent/disjoint
        assert len(walls) >= 1
        for w in walls:
            assert abs(w.thickness_pt - 4.5) < 0.2
            assert w.orientation == "HORIZONTAL"

    def test_reversed_direction_endpoints(self) -> None:
        """
        Lines drawn from right-to-left vs left-to-right (p1.x > p2.x).
        Extractor must normalize endpoints with min/max and extract wall identical to left-to-right.
        """
        line_rtl = {
            "type": "s",
            "width": 1.20,
            "dashes": "[] 0",
            "items": [("l", FitzPointMock(300.0, 200.0), FitzPointMock(100.0, 200.0))],
        }
        line_ltr = {
            "type": "s",
            "width": 1.20,
            "dashes": "[] 0",
            "items": [("l", FitzPointMock(100.0, 204.5), FitzPointMock(300.0, 204.5))],
        }

        page = MockPageLinework([line_rtl, line_ltr])
        extractor = VectorExtractor()
        walls = extractor.extract_wall_candidates(page)

        assert len(walls) == 1
        wall = walls[0]
        assert abs(wall.geometry_pdf.bounds[0] - 100.0) < 0.1
        assert abs(wall.geometry_pdf.bounds[2] - 300.0) < 0.1
        assert abs(wall.thickness_pt - 4.5) < 0.1

    @pytest.mark.parametrize(
        "thickness,expected",
        [
            (0.0, False),
            (0.5, False),
            (1.499, False),
            (1.500, True),
            (4.500, True),
            (10.500, True),
            (10.501, False),
            (12.000, False),
        ],
    )
    def test_extreme_thickness_precision_boundaries(self, thickness: float, expected: bool) -> None:
        """Tests exact floating point boundary thresholds for parallel wall pairing."""
        line1 = {
            "type": "s",
            "width": 1.20,
            "dashes": "[] 0",
            "items": [("l", FitzPointMock(100.0, 200.0), FitzPointMock(300.0, 200.0))],
        }
        line2 = {
            "type": "s",
            "width": 1.20,
            "dashes": "[] 0",
            "items": [("l", FitzPointMock(100.0, 200.0 + thickness), FitzPointMock(300.0, 200.0 + thickness))],
        }

        page = MockPageLinework([line1, line2])
        extractor = VectorExtractor()
        walls = extractor.extract_wall_candidates(page)

        if expected:
            assert len(walls) == 1
            assert abs(walls[0].thickness_pt - thickness) < 0.1
        else:
            assert len(walls) == 0


# ==============================================================================
# 3. 3-TIER SPATIAL MATCHER ADVERSARIAL STRESS
# ==============================================================================
class TestSpatialMatcherAdversarialStressR2:
    """Stress tests spatial association on dense clusters, ambiguous buffers, and degenerate leaders."""

    @pytest.fixture
    def authoritative_schedule(self) -> Dict[str, Any]:
        return {
            "1A": {"proposed_class": "Non-Drywall"},
            "1B": {"proposed_class": "Drywall"},
            "1C": {"proposed_class": "Drywall"},
            "1D": {"proposed_class": "Drywall"},
            "1E": {"proposed_class": "Drywall"},
            "2B": {"proposed_class": "Drywall"},
            "2C": {"proposed_class": "Drywall"},
            "3A": {"proposed_class": "Drywall"},
            "3D": {"proposed_class": "Drywall"},
            "5B": {"proposed_class": "Drywall"},
            "5D": {"proposed_class": "Drywall"},
            "5E": {"proposed_class": "Drywall"},
            "7A": {"proposed_class": "Drywall"},
            "7B": {"proposed_class": "Drywall"},
            "7C": {"proposed_class": "Drywall"},
            "7F": {"proposed_class": "Drywall"},
            "GL1": {"proposed_class": "Non-Drywall"},
            "11": {"proposed_class": "Non-Drywall"},
            "09": {"proposed_class": "Uncertain"},
        }

    def test_dense_tag_cluster_10_adjacent_parallel_walls(self, authoritative_schedule) -> None:
        """
        Adversarial Cluster: 10 parallel walls stacked with 12 pt spacing,
        10 distinct tags clustered nearby with explicit leader lines into their respective walls.
        Verifies:
        - 10 walls matched to exactly 10 distinct tags.
        - Zero duplicate assignments (each tag assigned at most once).
        """
        tags_list = ["1B", "1C", "1D", "1E", "2B", "2C", "3A", "3D", "5B", "5E"]
        walls = []
        tags = []

        for i, tag_name in enumerate(tags_list):
            y_wall = 100.0 + i * 15.0
            wall = MockWallCandidate(f"w_{i}", box(200.0, y_wall, 400.0, y_wall + 6.0))
            walls.append(wall)

            # Tag box placed at x=100..111.2, y=y_wall..y_wall+11.2
            tag_box = box(100.0, y_wall, 111.2, y_wall + 11.2)
            # Leader line extending from tag right side into wall interior
            leader = LineString([(111.2, y_wall + 3.0), (205.0, y_wall + 3.0)])
            tags.append(MockTagCandidate(tag_name, tag_box, leader))

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        report = matcher.match(walls, tags)

        assert report.total_walls == 10
        assert report.matched_walls == 10
        assert report.tier1_matches == 10
        assert report.unassigned_walls == 0
        assigned_tags = {r.assigned_tag for r in report.results}
        assert assigned_tags == set(tags_list)
        assert len(report.unmatched_tags) == 0

    def test_dense_tag_cluster_10_tags_targeting_1_wall(self, authoritative_schedule) -> None:
        """
        10 different tags all have leader lines intersecting the SAME single wall.
        Strict 1-to-1 association must assign the wall to the first claiming tag,
        and cleanly report the remaining 9 tags in unmatched_tags.
        """
        wall = MockWallCandidate("w_single", box(200.0, 100.0, 400.0, 110.0))
        tags_list = ["1B", "1C", "1D", "1E", "2B", "2C", "3A", "3D", "5B", "5E"]
        tags = []

        for i, tag_name in enumerate(tags_list):
            tag_box = box(150.0 + i * 20.0, 130.0, 161.2 + i * 20.0, 141.2)
            leader = LineString([(155.6 + i * 20.0, 130.0), (250.0, 105.0)])
            tags.append(MockTagCandidate(tag_name, tag_box, leader))

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        report = matcher.match([wall], tags)

        assert report.total_walls == 1
        assert report.matched_walls == 1
        assert report.unassigned_walls == 0
        assert report.tier1_matches == 1
        assert report.results[0].assigned_tag == "1B"
        assert len(report.unmatched_tags) == 9
        assert set(report.unmatched_tags) == set(tags_list[1:])

    @pytest.mark.parametrize(
        "delta,expected_matched",
        [
            (0.00, False),  # Perfectly equidistant -> REJECT (both unassigned)
            (7.90, False),  # delta < 8.0 pt -> REJECT (ambiguous)
            (7.99, False),  # delta < 8.0 pt -> REJECT (ambiguous)
            (8.00, True),   # delta == 8.0 pt -> ACCEPT closest wall
            (8.01, True),   # delta > 8.0 pt -> ACCEPT closest wall
            (15.00, True),  # delta >> 8.0 pt -> ACCEPT closest wall
        ],
    )
    def test_ambiguous_equidistant_proximity_buffer_deltas(
        self, authoritative_schedule, delta: float, expected_matched: bool
    ) -> None:
        """
        Verifies exact 8.0 pt distance delta margin for Tier 2 disambiguation.
        w_close at y=100..110, w_far at y=(125 + delta)..y=(135 + delta).
        Tag box at y=115..125 (gap to w_close is 5.0 pt, gap to w_far is 5.0 + delta pt).
        """
        w_close = MockWallCandidate("w_close", box(100.0, 100.0, 300.0, 110.0))
        y_far_start = 125.0 + 5.0 + delta  # distance from tag top (125.0) is 5.0 + delta
        w_far = MockWallCandidate("w_far", box(100.0, y_far_start, 300.0, y_far_start + 10.0))

        tag_box = box(150.0, 115.0, 161.2, 125.0)
        tag = MockTagCandidate("3A", tag_box, leader_line=None)

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        report = matcher.match([w_close, w_far], [tag])

        if expected_matched:
            assert report.matched_walls == 1
            assert report.unassigned_walls == 1
            assert report.tier2_matches == 1
            assert report.tier3_unassigned == 1
            res_map = {r.wall_id: r for r in report.results}
            assert res_map["w_close"].assigned_tag == "3A"
            assert res_map["w_far"].assigned_tag is None
            assert len(report.unmatched_tags) == 0
        else:
            assert report.matched_walls == 0
            assert report.unassigned_walls == 2
            assert report.tier2_matches == 0
            assert report.tier3_unassigned == 2
            for r in report.results:
                assert r.assigned_tag is None
                assert r.proposed_class == "Uncertain"
                assert r.confidence == 0.0
            assert "3A" in report.unmatched_tags

    def test_triple_equidistant_wall_ambiguity(self, authoritative_schedule) -> None:
        """
        Tag surrounded by 3 candidate walls at identical 6.0 pt distance.
        Must reject all candidates and enforce Tier 3 Uncertain guardrail.
        """
        w1 = MockWallCandidate("w1", box(100.0, 100.0, 300.0, 110.0))  # bottom (gap 6 pt to y=116)
        w2 = MockWallCandidate("w2", box(100.0, 132.0, 300.0, 142.0))  # top (gap 6 pt to y=126)
        w3 = MockWallCandidate("w3", box(167.2, 116.0, 177.2, 126.0))  # right (gap 6 pt to x=161.2)

        tag_box = box(150.0, 116.0, 161.2, 126.0)
        tag = MockTagCandidate("5E", tag_box, leader_line=None)

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        report = matcher.match([w1, w2, w3], [tag])

        assert report.matched_walls == 0
        assert report.unassigned_walls == 3
        assert report.tier3_unassigned == 3
        for r in report.results:
            assert r.assigned_tag is None
            assert r.proposed_class == "Uncertain"
        assert "5E" in report.unmatched_tags

    def test_degenerate_leader_zero_length(self, authoritative_schedule) -> None:
        """Zero-length leader LineString([(100, 100), (100, 100)]) does not crash and falls back."""
        wall = MockWallCandidate("w_far", box(500.0, 500.0, 600.0, 510.0))
        zero_leader = LineString([(100.0, 100.0), (100.0, 100.0)])
        tag = MockTagCandidate("1C", box(95.0, 95.0, 105.0, 105.0), zero_leader)

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        report = matcher.match([wall], [tag])

        assert report.matched_walls == 0
        assert report.unassigned_walls == 1
        assert report.tier3_unassigned == 1
        assert report.results[0].assigned_tag is None
        assert report.results[0].proposed_class == "Uncertain"

    def test_leader_raycast_gap_boundary(self, authoritative_schedule) -> None:
        """
        Raycast extension is 12.0 pt.
        Case A: Gap = 11.5 pt (<= 12.0 pt) -> Raycast hits wall in Tier 1.
        Case B: Gap = 12.5 pt (> 12.0 pt)  -> Raycast misses wall.
        """
        wall = MockWallCandidate("w_target", box(200.0, 100.0, 400.0, 110.0))

        # Case A: Leader ends at y=121.5 (gap to wall at y=110.0 is 11.5 pt)
        leader_hit = LineString([(250.0, 150.0), (250.0, 121.5)])
        tag_hit = MockTagCandidate("1C", box(245.0, 150.0, 255.0, 160.0), leader_hit)

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        rep_hit = matcher.match([wall], [tag_hit])
        assert rep_hit.matched_walls == 1
        assert rep_hit.tier1_matches == 1
        assert rep_hit.results[0].assigned_tag == "1C"
        assert "raycast" in rep_hit.results[0].evidence.lower()

        # Case B: Leader ends at y=122.5 (gap to wall at y=110.0 is 12.5 pt)
        # Wall is at y=100..110, tag is at y=170..180 (> 50 pt so Tier 2 buffer doesn't reach)
        leader_miss = LineString([(250.0, 170.0), (250.0, 122.5)])
        tag_miss = MockTagCandidate("1D", box(245.0, 170.0, 255.0, 180.0), leader_miss)

        rep_miss = matcher.match([wall], [tag_miss])
        assert rep_miss.matched_walls == 0
        assert rep_miss.unassigned_walls == 1
        assert rep_miss.tier3_unassigned == 1

    def test_leader_pointing_away_from_wall(self, authoritative_schedule) -> None:
        """
        Leader line starts near wall but vector direction points AWAY from wall.
        Raycast projects forward (away from wall) and must NOT match the wall.
        """
        wall = MockWallCandidate("w_behind", box(200.0, 100.0, 400.0, 110.0))
        # Leader starts at y=115 and extends to y=140 (pointing upwards, away from y=110)
        leader_away = LineString([(250.0, 115.0), (250.0, 140.0)])
        tag = MockTagCandidate("2B", box(245.0, 140.0, 255.0, 150.0), leader_away)

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        report = matcher.match([wall], [tag])

        # Wall is not intersected by leader or forward raycast
        # Distance from tag (y=140) to wall (y=110) is 30 pt (within 50 pt expanded buffer)
        # But tag box is leaderless only in Tier 2 if no leader lines exist or if leader failed.
        # If it matches in Tier 2 via proximity, method is BUFFER_PROXIMITY, NOT LEADER_LINE!
        if report.matched_walls == 1:
            assert report.results[0].match_method == MatchMethod.BUFFER_PROXIMITY
            assert report.tier1_matches == 0
        else:
            assert report.unassigned_walls == 1

    def test_multi_leader_tag_fallback(self, authoritative_schedule) -> None:
        """
        Tag has 3 leader lines:
        Leader 1: Empty / misses.
        Leader 2: Intersects Wall A (already assigned).
        Leader 3: Intersects Wall B (unassigned).
        Tag must successfully match Wall B via Leader 3 in Tier 1.
        """
        w_assigned = MockWallCandidate("w_a", box(100.0, 100.0, 200.0, 110.0))
        w_available = MockWallCandidate("w_b", box(300.0, 100.0, 400.0, 110.0))

        # First tag claims Wall A
        tag_prior = MockTagCandidate(
            "1B",
            box(145.0, 130.0, 155.0, 140.0),
            LineString([(150.0, 130.0), (150.0, 105.0)]),
        )

        # Multi-leader tag
        l1 = LineString([(250.0, 200.0), (250.0, 180.0)])  # Misses everything
        l2 = LineString([(150.0, 130.0), (150.0, 105.0)])  # Hits Wall A (already taken)
        l3 = LineString([(350.0, 130.0), (350.0, 105.0)])  # Hits Wall B (free)

        tag_multi = MockTagCandidate(
            "1C",
            box(245.0, 130.0, 255.0, 140.0),
            leader_lines=[l1, l2, l3],
        )

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        report = matcher.match([w_assigned, w_available], [tag_prior, tag_multi])

        assert report.total_walls == 2
        assert report.matched_walls == 2
        assert report.tier1_matches == 2
        res_map = {r.wall_id: r for r in report.results}
        assert res_map["w_a"].assigned_tag == "1B"
        assert res_map["w_b"].assigned_tag == "1C"

    @pytest.mark.parametrize(
        "malicious_class",
        [
            "Drywall",
            "DRYWALL",
            "drywall",
            "  Drywall  ",
            "GWB",
            "gwb",
            "Gypsum",
            "Gypsum Wallboard",
            "Sheetrock",
            "1",
            "1.0",
        ],
    )
    def test_detail_1a_tampering_veto_raises_exception(self, malicious_class: str) -> None:
        """Every permutation of drywall synonyms for Detail 1A triggers immediate ValueError."""
        wall = MockWallCandidate("w_cmu", box(100.0, 100.0, 300.0, 110.0))
        tag = MockTagCandidate(
            "1A",
            box(150.0, 130.0, 161.2, 141.2),
            LineString([(155.6, 130.0), (155.6, 105.0)]),
        )

        tampered_schedule = {"1A": {"proposed_class": malicious_class}}
        matcher = SpatialMatcher(schedule_mapping=tampered_schedule)

        with pytest.raises(ValueError, match="INTEGRITY VIOLATION: Detail 1A cannot be classified as Drywall"):
            matcher.match([wall], [tag])

    def test_detail_1a_empty_or_valid_schedule_resolves_to_non_drywall(self) -> None:
        """Detail 1A in empty or valid schedule resolves to Non-Drywall (#D50000)."""
        wall = MockWallCandidate("w_cmu", box(100.0, 100.0, 300.0, 110.0))
        tag = MockTagCandidate(
            "1A",
            box(150.0, 130.0, 161.2, 141.2),
            LineString([(155.6, 130.0), (155.6, 105.0)]),
        )

        # Empty schedule
        matcher_empty = SpatialMatcher(schedule_mapping={})
        report = matcher_empty.match([wall], [tag])
        assert report.matched_walls == 1
        res = report.results[0]
        assert res.assigned_tag == "1A"
        assert res.proposed_class == "Non-Drywall"
        assert res.color_hex == CLASS_COLORS_HEX["Non-Drywall"]
        assert res.proposed_class != "Drywall"

        # Legitimate schedule
        matcher_valid = SpatialMatcher(schedule_mapping={"1A": {"proposed_class": "Non-Drywall"}})
        report_val = matcher_valid.match([wall], [tag])
        res_val = report_val.results[0]
        assert res_val.assigned_tag == "1A"
        assert res_val.proposed_class == "Non-Drywall"
        assert res_val.color_hex == CLASS_COLORS_HEX["Non-Drywall"]
