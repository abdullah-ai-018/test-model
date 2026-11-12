"""
drywall_detection/tests/test_adversarial_m3.py

Adversarial Stress Test Suite for Milestone M3:
Target: drywall_detection/vector/spatial_matcher.py & drywall_detection/vector/schedule_parser.py

Coverage:
1. 3-Tier Spatial Matcher Pathological Scenarios:
   - Dense tag clusters (multiple tags -> single wall, multiple tags -> adjacent walls)
   - Ambiguous equidistant proximity buffers (rejection via distance delta margin)
   - Boundary tests for distance delta margin (delta < 8.0 pt vs delta >= 8.0 pt)
   - Crossing leader lines & long leaders intersecting multiple walls
   - Disconnected / leader terminating outside wall geometry
   - Degenerate / zero-length / multi-segment leaders
   - Massive empty drawings (1,000 walls with 0 tags -> 100% Uncertain fallback)
2. Detail 1A Non-Drywall CMU Safety Tampering:
   - Deliberate injection of "Drywall", "GWB", "Gypsum Wallboard", case/whitespace variations
   - Programmatic safety veto in schedule parser & spatial matcher
   - In-memory record tampering resistance
3. Review Lock Protocol Edge Cases:
   - Missing CSV, invalid CSV header, empty approved CSV, missing 1A row, corrupted binary CSV
   - Lockfile creation and exit code 2 semantics
"""

from __future__ import annotations
import csv
from pathlib import Path
import time
from typing import Dict, List, Optional
import pytest
from shapely.geometry import box, LineString, Point, Polygon

from drywall_detection.config import (
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    CLASS_COLORS_HEX,
    EXIT_CODE_AWAITING_REVIEW,
)
from drywall_detection.vector.schedule_parser import (
    SCHEDULE_14_COLUMNS,
    PartitionScheduleParser,
    PartitionTagInstance,
    ScheduleDetailRecord,
)
from drywall_detection.vector.spatial_matcher import (
    MatchMethod,
    MatchingReport,
    SpatialMatcher,
    SpatialMatcherConfig,
    SpatialMatchResult,
)


# ==============================================================================
# Helper Dummy Classes for Geometric Stress Testing
# ==============================================================================
class MockWall:
    def __init__(self, wall_id: str, geom: Polygon):
        self.wall_id = wall_id
        self.geometry = geom
        self.geometry_pdf = geom


class MockTag:
    def __init__(
        self,
        tag_id: str,
        box_geom: Polygon,
        leader_line: Optional[LineString] = None,
        leader_lines: Optional[List[LineString]] = None,
    ):
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


@pytest.fixture
def authoritative_schedule():
    """Provides schedule mapping based on authoritative parser."""
    parser = PartitionScheduleParser()
    return {k: v.to_dict() for k, v in parser._records.items()}


# ==============================================================================
# 1. 3-TIER SPATIAL MATCHER PATHOLOGICAL SCENARIOS
# ==============================================================================
class TestSpatialMatcherPathologicalScenarios:
    """Stress tests 3-tier matcher under adversarial geometry and dense tag conditions."""

    def test_dense_tag_cluster_pointing_to_same_wall(self, authoritative_schedule) -> None:
        """
        Adversarial Scenario: 5 different tags all have leader lines intersecting
        the SAME wall.
        Invariant:
        - Only ONE tag can be assigned to the wall (no duplicate or multi-assignment).
        - Exactly 1 wall matched, 4 tags reported in unmatched_tags.
        - Zero exceptions raised.
        """
        wall = MockWall("w_shared", box(100.0, 100.0, 300.0, 110.0))

        # 5 tags located in a cluster above the wall, all pointing into y=105
        tags = []
        for i, tag_name in enumerate(["1B", "1C", "2B", "3A", "5B"]):
            tag_box = box(120.0 + i * 20.0, 130.0, 131.2 + i * 20.0, 141.2)
            leader = LineString([(125.6 + i * 20.0, 130.0), (125.6 + i * 20.0, 105.0)])
            tags.append(MockTag(tag_name, tag_box, leader))

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        report = matcher.match([wall], tags)

        assert report.total_walls == 1
        assert report.matched_walls == 1
        assert report.unassigned_walls == 0
        assert report.tier1_matches == 1
        assert report.tier2_matches == 0
        assert report.tier3_unassigned == 0

        # Assigned tag should be the first tag that claimed it
        assert report.results[0].assigned_tag == "1B"
        assert report.results[0].match_method == MatchMethod.LEADER_LINE

        # Remaining 4 tags must be reported as unmatched
        assert len(report.unmatched_tags) == 4
        assert set(report.unmatched_tags) == {"1C", "2B", "3A", "5B"}

    def test_dense_tag_cluster_adjacent_parallel_walls(self, authoritative_schedule) -> None:
        """
        Adversarial Scenario: 5 tightly stacked parallel walls (10 pt apart) with
        5 tags clustered together.
        Invariant:
        - Strict 1-to-1 matching: 5 walls assigned to 5 distinct tags.
        - Zero cross-talk or duplicate assignments.
        """
        walls = [
            MockWall(f"w_adj_{i}", box(100.0, 100.0 + i * 15.0, 300.0, 108.0 + i * 15.0))
            for i in range(5)
        ]

        # 5 tags with direct leader lines into their respective walls
        tags = [
            MockTag(
                f"1{chr(66 + i)}",  # 1B, 1C, 1D, 1E, 1F -> but 1F not in dict so use valid tags
                box(50.0, 100.0 + i * 15.0, 61.2, 111.2 + i * 15.0),
                LineString([(61.2, 104.0 + i * 15.0), (105.0, 104.0 + i * 15.0)]),
            )
            for i, tag_name in enumerate(["1B", "1C", "1D", "1E", "2B"])
        ]
        # Fix tag names
        for t, name in zip(tags, ["1B", "1C", "1D", "1E", "2B"]):
            t.tag_id = name
            t.tag = name

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        report = matcher.match(walls, tags)

        assert report.total_walls == 5
        assert report.matched_walls == 5
        assert report.unassigned_walls == 0
        assigned_tags = {r.assigned_tag for r in report.results}
        assert assigned_tags == {"1B", "1C", "1D", "1E", "2B"}
        assert len(report.unmatched_tags) == 0

    def test_ambiguous_equidistant_proximity_buffers(self, authoritative_schedule) -> None:
        """
        Adversarial Scenario: A leaderless tag placed at exact geometric midpoint
        between two parallel walls (e.g. wall 1 at y=100-110, wall 2 at y=130-140,
        tag box at y=119.4-120.6). Distance to both walls is identical (9.4 pt).
        Invariant:
        - Distance delta margin (min_distance_margin_pt = 8.0 pt) must reject both walls.
        - Neither wall is assigned (zero guessing/hallucination).
        - Both walls fall back to Tier 3 Uncertain (confidence 0.0).
        """
        wall_north = MockWall("w_north", box(100.0, 130.0, 300.0, 140.0))
        wall_south = MockWall("w_south", box(100.0, 100.0, 300.0, 110.0))

        # Tag centered vertically between 110.0 and 130.0 -> gap is 20 pt
        # Tag box height = 10 pt, from y=115.0 to y=125.0
        # Distance to wall_south (y=110): 115.0 - 110.0 = 5.0 pt
        # Distance to wall_north (y=130): 130.0 - 125.0 = 5.0 pt
        # Delta = |5.0 - 5.0| = 0.0 pt < 8.0 pt
        tag_box = box(150.0, 115.0, 161.2, 125.0)
        tag = MockTag("3A", tag_box, leader_line=None)

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        report = matcher.match([wall_north, wall_south], [tag])

        assert report.total_walls == 2
        assert report.matched_walls == 0
        assert report.unassigned_walls == 2
        assert report.tier2_matches == 0
        assert report.tier3_unassigned == 2

        for res in report.results:
            assert res.assigned_tag is None
            assert res.match_method == MatchMethod.UNASSIGNED
            assert res.proposed_class == "Uncertain"
            assert res.confidence == 0.0
            assert res.color_hex == CLASS_COLORS_HEX["Uncertain"]

        assert "3A" in report.unmatched_tags

    def test_proximity_buffer_delta_boundary_conditions(self, authoritative_schedule) -> None:
        """
        Boundary Condition Stress:
        - Case A: Delta = 7.9 pt (< 8.0 pt threshold) -> REJECTED (ambiguous).
        - Case B: Delta = 8.0 pt (== 8.0 pt threshold) -> ACCEPTED (closest wall matched).
        """
        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)

        # Case A: d1 = 5.0 pt, d2 = 12.9 pt (delta = 7.9 pt)
        w_close_a = MockWall("w_ca", box(100.0, 100.0, 200.0, 110.0))
        # Tag box: y=115.0 to 125.0 -> d1 to w_ca (y=110.0) is 5.0 pt
        # Far wall: y=137.9 to 147.9 -> d2 to tag (y=125.0) is 12.9 pt -> delta = 7.9 pt
        tag_a = MockTag("1B", box(120.0, 115.0, 130.0, 125.0), leader_line=None)
        rep_a = matcher.match([w_close_a, MockWall("w_fa", box(100.0, 137.9, 200.0, 147.9))], [tag_a])
        assert rep_a.matched_walls == 0
        assert rep_a.tier3_unassigned == 2

        # Case B: d1 = 5.0 pt, d2 = 13.0 pt (delta = 8.0 pt exact)
        w_close_b = MockWall("w_cb", box(100.0, 100.0, 200.0, 110.0))
        # Tag box: y=115.0 to 125.0 -> d1 to w_cb (y=110.0) is 5.0 pt
        # Far wall: y=138.0 to 148.0 -> d2 to tag (y=125.0) is 13.0 pt -> delta = 8.0 pt
        tag_b = MockTag("1C", box(120.0, 115.0, 130.0, 125.0), leader_line=None)
        rep_b = matcher.match([w_close_b, MockWall("w_fb", box(100.0, 138.0, 200.0, 148.0))], [tag_b])
        assert rep_b.matched_walls == 1
        assert rep_b.tier2_matches == 1
        res_map = {r.wall_id: r for r in rep_b.results}
        assert res_map["w_cb"].assigned_tag == "1C"
        assert res_map["w_fb"].assigned_tag is None

    def test_crossing_orthogonal_leader_lines(self, authoritative_schedule) -> None:
        """
        Adversarial Scenario: Two leader lines cross each other in an 'X' pattern:
        - Tag A at (100, 150) -> Leader line to Wall A at (200, 50)
        - Tag B at (100, 50)  -> Leader line to Wall B at (200, 150)
        Lines intersect at (150, 100).
        Invariant:
        - Wall A is assigned to Tag A; Wall B is assigned to Tag B.
        - The line crossing does not corrupt individual wall associations.
        """
        wall_a = MockWall("w_a", box(195.0, 45.0, 215.0, 55.0))
        wall_b = MockWall("w_b", box(195.0, 145.0, 215.0, 155.0))

        tag_a = MockTag(
            "1B",
            box(90.0, 145.0, 101.2, 155.0),
            LineString([(100.0, 150.0), (200.0, 50.0)]),
        )
        tag_b = MockTag(
            "1C",
            box(90.0, 45.0, 101.2, 55.0),
            LineString([(100.0, 50.0), (200.0, 150.0)]),
        )

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        report = matcher.match([wall_a, wall_b], [tag_a, tag_b])

        assert report.matched_walls == 2
        assert report.tier1_matches == 2
        res_map = {r.wall_id: r for r in report.results}
        assert res_map["w_a"].assigned_tag == "1B"
        assert res_map["w_b"].assigned_tag == "1C"

    def test_long_leader_crossing_multiple_walls(self, authoritative_schedule) -> None:
        """
        Adversarial Scenario: A single long leader line (300 pt) cuts through 3 walls
        before terminating inside Wall 3.
        Invariant:
        - Matches the wall closest to the leader endpoint (Wall 3), not Wall 1 or 2.
        """
        wall1 = MockWall("w_transit_1", box(150.0, 90.0, 160.0, 110.0))
        wall2 = MockWall("w_transit_2", box(250.0, 90.0, 260.0, 110.0))
        wall3 = MockWall("w_target_3", box(350.0, 90.0, 360.0, 110.0))

        # Leader starts at x=100 and ends inside wall3 at x=355
        leader = LineString([(100.0, 100.0), (355.0, 100.0)])
        tag = MockTag("5D", box(85.0, 95.0, 96.2, 105.0), leader)

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        report = matcher.match([wall1, wall2, wall3], [tag])

        assert report.matched_walls == 1
        assert report.tier1_matches == 1
        res_map = {r.wall_id: r for r in report.results}
        # Wall 3 must get the tag because endpoint is at (355, 100)
        assert res_map["w_target_3"].assigned_tag == "5D"
        assert res_map["w_transit_1"].assigned_tag is None
        assert res_map["w_transit_2"].assigned_tag is None

    def test_leader_terminating_far_outside_geometry(self, authoritative_schedule) -> None:
        """
        Adversarial Scenario: Leader line points into empty canvas, terminating 40 pt
        away from any wall (raycast extension is only 12 pt). Tag box is 100 pt away.
        Invariant:
        - Fails Tier 1 (gap > 12 pt).
        - Fails Tier 2 (distance > 50 pt).
        - Enforces Tier 3 Uncertain (confidence 0.0).
        """
        wall = MockWall("w_distant", box(500.0, 500.0, 600.0, 510.0))

        # Leader terminates at (460.0, 505.0) -> gap is 40 pt to wall left edge (500.0)
        leader = LineString([(300.0, 505.0), (460.0, 505.0)])
        tag = MockTag("2C", box(285.0, 500.0, 296.2, 510.0), leader)

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        report = matcher.match([wall], [tag])

        assert report.matched_walls == 0
        assert report.unassigned_walls == 1
        assert report.tier3_unassigned == 1
        assert report.results[0].assigned_tag is None
        assert report.results[0].proposed_class == "Uncertain"
        assert report.results[0].confidence == 0.0
        assert "2C" in report.unmatched_tags

    def test_degenerate_zero_length_and_multisegment_leaders(self, authoritative_schedule) -> None:
        """
        Adversarial Scenario:
        - Degenerate zero-length leader LineString([(100, 100), (100, 100)]).
        - Multi-segment zigzag leader.
        Invariant: Zero division errors, valid geometry handling.
        """
        wall = MockWall("w_target", box(200.0, 190.0, 220.0, 210.0))

        # Zero-length leader
        zero_leader = LineString([(100.0, 100.0), (100.0, 100.0)])
        tag_zero = MockTag("7A", box(90.0, 95.0, 101.2, 105.0), zero_leader)

        # Zigzag 3-segment leader terminating in wall
        zigzag = LineString([(100.0, 200.0), (150.0, 250.0), (180.0, 200.0), (205.0, 200.0)])
        tag_zigzag = MockTag("7B", box(85.0, 195.0, 96.2, 205.0), zigzag)

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)
        report = matcher.match([wall], [tag_zero, tag_zigzag])

        assert report.matched_walls == 1
        assert report.tier1_matches == 1
        # Zigzag leader successfully connects to wall
        assert report.results[0].assigned_tag == "7B"

    def test_massive_empty_drawing_stress_1000_walls(self, authoritative_schedule) -> None:
        """
        Scale & Guardrail Stress:
        1,000 candidate walls distributed across an empty plan with 0 partition tags.
        Invariant:
        - 100% (1,000/1,000) walls must default to Uncertain (confidence 0.0).
        - Zero walls matched.
        - Execution completes under 1.5 seconds.
        """
        walls = []
        for i in range(1000):
            gx = (i % 30) * 80.0
            gy = (i // 30) * 70.0
            walls.append(MockWall(f"w_mass_{i}", box(gx, gy, gx + 60.0, gy + 8.0)))

        matcher = SpatialMatcher(schedule_mapping=authoritative_schedule)

        t0 = time.perf_counter()
        report = matcher.match(walls, [])
        elapsed = time.perf_counter() - t0

        assert report.total_walls == 1000
        assert report.matched_walls == 0
        assert report.unassigned_walls == 1000
        assert report.tier3_unassigned == 1000
        assert report.match_rate == 0.0
        assert elapsed < 1.5, f"Execution took {elapsed:.2f}s, expected < 1.5s"

        # Verify every individual result adheres strictly to Tier 3 contract
        for r in report.results:
            assert r.assigned_tag is None
            assert r.match_method == MatchMethod.UNASSIGNED
            assert r.proposed_class == "Uncertain"
            assert r.confidence == 0.0
            assert r.color_hex == CLASS_COLORS_HEX["Uncertain"]


# ==============================================================================
# 2. DETAIL 1A NON-DRYWALL CMU SAFETY TAMPERING
# ==============================================================================
class TestDetail1ASafetyTampering:
    """Stress tests Detail 1A safety veto against deliberate malicious injections."""

    def test_tampered_detail_1a_drywall_raises_integrity_violation(self, tmp_path: Path) -> None:
        """Approved CSV attempting to classify 1A as Drywall raises ValueError."""
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "approved.csv"
        lock_path = tmp_path / "lock.lock"
        parser = PartitionScheduleParser()

        # Malicious approved CSV
        with open(appr_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SCHEDULE_14_COLUMNS)
            writer.writeheader()
            writer.writerow({
                "tag": "1A",
                "sheet": "A-900",
                "detail_title": "1A CMU",
                "description": "6\" CMU",
                "studs": "None",
                "layers": "0",
                "gwb_thickness": "None",
                "fire_rating": "1-HR",
                "acoustic": "None",
                "finish": "None",
                "material_trade": "Masonry",
                "proposed_class": "Drywall",
                "confidence": 1.0,
                "notes": "ATTACK: Attempting to classify CMU as Drywall",
            })

        with pytest.raises(ValueError) as exc:
            parser.export_and_enforce_review_lock(
                csv_path=csv_path,
                approved_csv_path=appr_path,
                lock_path=lock_path,
                interactive_mode=False,
            )
        assert "INTEGRITY VIOLATION" in str(exc.value)

    def test_tampered_detail_1a_case_and_whitespace_variations(self, tmp_path: Path) -> None:
        """Approved CSV with ' DRYWALL ' or ' drywall ' must still trigger integrity violation."""
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "approved_ws.csv"
        lock_path = tmp_path / "lock.lock"
        parser = PartitionScheduleParser()

        with open(appr_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SCHEDULE_14_COLUMNS)
            writer.writeheader()
            writer.writerow({
                "tag": " 1A ",
                "sheet": "A-900",
                "detail_title": "1A CMU",
                "description": "6\" CMU",
                "studs": "None",
                "layers": "0",
                "gwb_thickness": "None",
                "fire_rating": "1-HR",
                "acoustic": "None",
                "finish": "None",
                "material_trade": "Masonry",
                "proposed_class": "  DRYWALL  ",
                "confidence": 1.0,
                "notes": "Whitespace attack",
            })

        with pytest.raises(ValueError) as exc:
            parser.export_and_enforce_review_lock(
                csv_path=csv_path,
                approved_csv_path=appr_path,
                lock_path=lock_path,
                interactive_mode=False,
            )
        assert "INTEGRITY VIOLATION" in str(exc.value)

    def test_tampered_detail_1a_gwb_raises_integrity_violation(self, tmp_path: Path) -> None:
        """
        Adversarial Scenario: An attacker attempts to bypass safety by classifying Detail 1A
        as 'GWB' (Gypsum Wallboard) instead of the exact string 'Drywall'.
        Requirement: The safety veto must intercept 'GWB' and raise ValueError.
        """
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "approved_gwb.csv"
        lock_path = tmp_path / "lock.lock"
        parser = PartitionScheduleParser()

        with open(appr_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SCHEDULE_14_COLUMNS)
            writer.writeheader()
            writer.writerow({
                "tag": "1A",
                "sheet": "A-900",
                "detail_title": "1A CMU",
                "description": "6\" CMU",
                "studs": "None",
                "layers": "0",
                "gwb_thickness": "None",
                "fire_rating": "1-HR",
                "acoustic": "None",
                "finish": "None",
                "material_trade": "Masonry",
                "proposed_class": "GWB",  # Drywall synonym attack
                "confidence": 1.0,
                "notes": "GWB synonym attack",
            })

        with pytest.raises(ValueError) as exc:
            parser.export_and_enforce_review_lock(
                csv_path=csv_path,
                approved_csv_path=appr_path,
                lock_path=lock_path,
                interactive_mode=False,
            )
        assert "INTEGRITY VIOLATION" in str(exc.value)

    def test_spatial_matcher_detail_1a_immutable_veto(self) -> None:
        """
        Adversarial Scenario: A maliciously crafted schedule_mapping dictionary
        passes Detail 1A mapped to Drywall, GWB, or other aliases.
        Invariant:
        SpatialMatcher intercepts tampering and raises ValueError with INTEGRITY VIOLATION.
        When schedule is untampered, it resolves 1A to Non-Drywall.
        """
        wall = MockWall("w_cmu", box(100.0, 100.0, 200.0, 110.0))
        tag = MockTag("1A", box(100.0, 115.0, 111.2, 126.2), LineString([(105.6, 115.0), (105.6, 105.0)]))

        tampered_variants = [
            {"1A": {"proposed_class": "Drywall"}},
            {"1A": {"proposed_class": "GWB"}},
            {"1A": {"proposed_class": "Gypsum Wallboard"}},
            {"1A": {"proposed_class": "drywall"}},
        ]

        for tampered_map in tampered_variants:
            matcher = SpatialMatcher(schedule_mapping=tampered_map)
            with pytest.raises(ValueError, match="INTEGRITY VIOLATION"):
                matcher.match([wall], [tag])

        # Verify untampered / empty schedule defaults safely to Non-Drywall
        matcher_clean = SpatialMatcher(schedule_mapping={})
        report = matcher_clean.match([wall], [tag])
        assert report.matched_walls == 1
        res = report.results[0]
        assert res.assigned_tag == "1A"
        assert res.proposed_class == "Non-Drywall"
        assert res.color_hex == CLASS_COLORS_HEX["Non-Drywall"]

    def test_spatial_matcher_raises_exception_on_tampered_1a(self) -> None:
        """
        Requirement: Verify that the programmatic safety veto in spatial_matcher.py
        intercepts deliberate injection of Detail 1A as Drywall/GWB and raises an immediate exception.
        """
        wall = MockWall("w_cmu", box(100.0, 100.0, 200.0, 110.0))
        tag = MockTag("1A", box(100.0, 115.0, 111.2, 126.2), LineString([(105.6, 115.0), (105.6, 105.0)]))

        matcher = SpatialMatcher(schedule_mapping={"1A": {"proposed_class": "Drywall"}})
        with pytest.raises(ValueError, match="INTEGRITY VIOLATION"):
            matcher.match([wall], [tag])

    def test_schedule_parser_in_memory_export_veto(self, tmp_path: Path) -> None:
        """
        Adversarial Scenario: An internal caller directly mutates parser._records['1A'].proposed_class = 'Drywall'.
        Invariant:
        export_and_enforce_review_lock MUST programmatically force 1A to Non-Drywall
        during CSV serialization.
        """
        csv_path = tmp_path / "tampered_export.csv"
        parser = PartitionScheduleParser()
        # Direct memory tampering
        parser._records["1A"].proposed_class = "Drywall"

        parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=tmp_path / "nonexistent.csv",
            lock_path=tmp_path / "lock.lock",
            interactive_mode=False,
        )

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = {r["tag"]: r for r in reader}

        assert rows["1A"]["proposed_class"] == "Non-Drywall", (
            f"SAFETY FAILURE: Exported CSV contained 1A as {rows['1A']['proposed_class']}!"
        )


# ==============================================================================
# 3. REVIEW LOCK PROTOCOL EDGE CASES
# ==============================================================================
class TestReviewLockProtocolEdgeCases:
    """Stress tests human-in-the-loop review lock protocol under missing, empty, and corrupted files."""

    def test_missing_csv_and_interactive_exit_code_2(self, tmp_path: Path) -> None:
        """When approved CSV is missing, interactive mode exits with code 2."""
        csv_path = tmp_path / "mapping.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        with pytest.raises(SystemExit) as exc:
            parser.export_and_enforce_review_lock(
                csv_path=csv_path,
                approved_csv_path=tmp_path / "does_not_exist.csv",
                lock_path=lock_path,
                interactive_mode=True,
            )
        assert exc.value.code == EXIT_CODE_AWAITING_REVIEW
        assert exc.value.code == 2
        assert lock_path.exists()

    def test_empty_approved_csv_must_not_bypass_lock(self, tmp_path: Path) -> None:
        """
        Adversarial Scenario: An empty (0-byte) approved CSV file is placed.
        Requirement: An empty CSV contains zero approved details and must NOT bypass
        the review lock or delete the lockfile. Must return False or raise ValueError.
        """
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "empty_approved.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        # Touch empty file
        appr_path.write_text("", encoding="utf-8")

        res = parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=appr_path,
            lock_path=lock_path,
            interactive_mode=False,
        )
        # Should not be approved
        assert res is False, "SECURITY FLAW: 0-byte approved CSV bypassed the review lock!"
        assert lock_path.exists(), "SECURITY FLAW: 0-byte approved CSV cleared the review lockfile!"

    def test_invalid_header_approved_csv_must_not_bypass_lock(self, tmp_path: Path) -> None:
        """
        Adversarial Scenario: An approved CSV with garbage/invalid headers (missing required columns).
        Requirement: Must reject invalid CSV schema and enforce review lock.
        """
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "invalid_header.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        appr_path.write_text("random_col1,random_col2\nfoo,bar\n", encoding="utf-8")

        res = parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=appr_path,
            lock_path=lock_path,
            interactive_mode=False,
        )
        assert res is False, "SECURITY FLAW: Approved CSV with invalid headers bypassed the review lock!"
        assert lock_path.exists(), "SECURITY FLAW: Approved CSV with invalid headers cleared the lockfile!"

    def test_missing_detail_1a_row_must_not_bypass_lock(self, tmp_path: Path) -> None:
        """
        Adversarial Scenario: An approved CSV that provides rows for 23 details but
        deliberately omits Detail 1A to circumvent the 1A CMU safety inspection.
        Requirement: Must verify that Detail 1A was reviewed and explicitly present.
        """
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "missing_1a.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        # Write approved CSV with 1B only (1A missing)
        with open(appr_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SCHEDULE_14_COLUMNS)
            writer.writeheader()
            writer.writerow({
                "tag": "1B",
                "sheet": "A-900",
                "detail_title": "1B Drywall",
                "description": "5/8\" GWB",
                "studs": "2-1/2\"",
                "layers": "2",
                "gwb_thickness": "5/8\"",
                "fire_rating": "None",
                "acoustic": "None",
                "finish": "GWB",
                "material_trade": "Drywall",
                "proposed_class": "Drywall",
                "confidence": 1.0,
                "notes": "Valid detail",
            })

        res = parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=appr_path,
            lock_path=lock_path,
            interactive_mode=False,
        )
        assert res is False, "SECURITY FLAW: Approved CSV omitting Detail 1A bypassed review!"
        assert lock_path.exists(), "SECURITY FLAW: Approved CSV omitting Detail 1A cleared lockfile!"

    def test_approved_csv_binary_corruption_raises_decode_error(self, tmp_path: Path) -> None:
        """Approved CSV containing non-UTF-8 binary garbage raises UnicodeDecodeError."""
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "corrupted.csv"
        lock_path = tmp_path / "lock.lock"
        parser = PartitionScheduleParser()

        # Write invalid binary data
        appr_path.write_bytes(b"\x80\xFF\xFE\x00\x01\x02\xFD")

        with pytest.raises(UnicodeDecodeError):
            parser.export_and_enforce_review_lock(
                csv_path=csv_path,
                approved_csv_path=appr_path,
                lock_path=lock_path,
                interactive_mode=False,
            )

    def test_valid_approved_csv_removes_existing_lockfile(self, tmp_path: Path) -> None:
        """When a valid approved CSV is provided, lockfile is cleanly unlinked."""
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "approved.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        # 1. First run creates lock
        res1 = parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=appr_path,
            lock_path=lock_path,
            interactive_mode=False,
        )
        assert res1 is False
        assert lock_path.exists()

        # 2. User approves (copy valid mapping)
        appr_path.write_text(csv_path.read_text(encoding="utf-8"), encoding="utf-8")

        # 3. Second run consumes approval and removes lock
        res2 = parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=appr_path,
            lock_path=lock_path,
            interactive_mode=False,
        )
        assert res2 is True
        assert not lock_path.exists()
